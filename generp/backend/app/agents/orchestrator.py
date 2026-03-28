"""
LangGraph orchestrator — routes user messages to the correct agent.

Graph topology:
    START → intent_classifier → [schema_agent | ui_agent | clarification | error_handler] → END
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Literal

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.agents.schema_agent import SchemaAgent
from app.agents.ui_agent import UIAgent
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Intent(str, Enum):
    DESCRIBE_BUSINESS = "DESCRIBE_BUSINESS"
    ADD_MODULE = "ADD_MODULE"
    MODIFY_FIELD = "MODIFY_FIELD"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"
    CONFIGURE_WORKFLOW = "CONFIGURE_WORKFLOW"
    GENERAL_QUESTION = "GENERAL_QUESTION"
    CONFIRM_SCHEMA = "CONFIRM_SCHEMA"
    REJECT_SCHEMA = "REJECT_SCHEMA"
    QUERY_DATA = "QUERY_DATA"  # "montre-moi les factures en retard"


class OrchestratorState(BaseModel):
    """State passed between nodes in the LangGraph graph."""

    # Input
    tenant_id: str
    conversation_id: str
    user_message: str
    conversation_history: list[dict[str, str]] = []

    # Intermediate
    intent: Intent | None = None
    pending_schema: dict[str, Any] | None = None  # schema awaiting user confirmation

    # Output
    response_text: str = ""
    actions: list[dict[str, Any]] = []  # actions taken (schema_generated, etc.)
    ui_updates: list[dict[str, Any]] = []  # module UI configs to push to frontend
    error: str | None = None


_llm = ChatAnthropic(
    model=settings.llm_model,
    temperature=settings.llm_temperature,
    max_tokens=settings.llm_max_tokens,
    api_key=settings.anthropic_api_key,
)

_schema_agent = SchemaAgent(llm=_llm)
_ui_agent = UIAgent(llm=_llm)

# ---------------------------------------------------------------------------
# Intent classifier node
# ---------------------------------------------------------------------------

_INTENT_SYSTEM_PROMPT = """Tu es un classificateur d'intentions pour une plateforme ERP.
Analyse le message de l'utilisateur et retourne UNIQUEMENT un objet JSON avec ce format :
{"intent": "<INTENT>", "confidence": 0.0-1.0, "reasoning": "<explication courte>"}

Intentions possibles :
- DESCRIBE_BUSINESS : l'utilisateur décrit son entreprise, son secteur, ses besoins généraux
- ADD_MODULE : l'utilisateur veut ajouter un module spécifique (CRM, Finance, RH, etc.)
- MODIFY_FIELD : l'utilisateur veut modifier un champ ou une entité existante
- CLARIFICATION_NEEDED : message ambigu, impossible à classer avec certitude
- CONFIGURE_WORKFLOW : l'utilisateur décrit un processus métier à automatiser
- GENERAL_QUESTION : question générale sur la plateforme ou l'ERP
- CONFIRM_SCHEMA : l'utilisateur confirme le schéma proposé ("oui", "c'est parfait", "ok")
- REJECT_SCHEMA : l'utilisateur rejette ou veut modifier le schéma ("non", "modifier", "changer")

Réponds UNIQUEMENT avec le JSON, sans texte supplémentaire."""


async def intent_classifier_node(state: OrchestratorState) -> OrchestratorState:
    """Classify the user's intent using Claude."""
    messages = [
        SystemMessage(content=_INTENT_SYSTEM_PROMPT),
        HumanMessage(content=state.user_message),
    ]
    response = await _llm.ainvoke(messages)
    content = str(response.content).strip()

    try:
        parsed = json.loads(content)
        state.intent = Intent(parsed["intent"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.warning("Intent classification failed: %s — raw: %s", exc, content)
        state.intent = Intent.CLARIFICATION_NEEDED

    return state


# ---------------------------------------------------------------------------
# Clarification node
# ---------------------------------------------------------------------------

_CLARIFICATION_PROMPT = """Tu es l'assistant GenERP. L'utilisateur a envoyé un message ambigu.
Pose une question courte et précise en français pour comprendre son besoin.
Sois concis (1-2 phrases max). Ne pose qu'une seule question."""


async def clarification_node(state: OrchestratorState) -> OrchestratorState:
    """Ask the user for clarification when intent is ambiguous."""
    messages = [
        SystemMessage(content=_CLARIFICATION_PROMPT),
        HumanMessage(content=state.user_message),
    ]
    response = await _llm.ainvoke(messages)
    state.response_text = str(response.content)
    return state


# ---------------------------------------------------------------------------
# Schema confirmation handler
# ---------------------------------------------------------------------------


async def confirm_schema_node(state: OrchestratorState) -> OrchestratorState:
    """
    User confirmed the pending schema.
    Trigger DDL execution and UI generation.
    """
    if not state.pending_schema:
        state.response_text = (
            "Je n'ai pas de schéma en attente de validation. "
            "Décrivez d'abord votre activité pour que je puisse générer un schéma."
        )
        return state

    schema = state.pending_schema

    # Generate UI configs for each entity
    ui_configs = await _ui_agent.generate_ui_configs(
        schema=schema,
        tenant_id=state.tenant_id,
    )

    state.actions.append(
        {
            "action": "schema_confirmed",
            "schema": schema,
        }
    )
    state.ui_updates = ui_configs
    state.pending_schema = None  # clear pending schema

    entity_names = [e["display_name"] for e in schema.get("entities", [])]
    state.response_text = (
        f"Parfait ! J'ai créé votre ERP avec les modules suivants : "
        f"{', '.join(entity_names)}. "
        "Votre interface est prête. Vous pouvez commencer à saisir vos données."
    )
    return state


async def reject_schema_node(state: OrchestratorState) -> OrchestratorState:
    """User rejected the schema — ask what to change."""
    state.response_text = (
        "D'accord, que souhaitez-vous modifier ? "
        "Décrivez les changements et je mettrai à jour le schéma."
    )
    return state


# ---------------------------------------------------------------------------
# Error handler node
# ---------------------------------------------------------------------------


async def error_handler_node(state: OrchestratorState) -> OrchestratorState:
    """Handle unexpected errors gracefully."""
    logger.error("Error in orchestrator: %s", state.error)
    state.response_text = (
        "Une erreur est survenue lors du traitement de votre demande. "
        "Veuillez réessayer ou reformuler votre message."
    )
    return state


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------


def route_after_classifier(
    state: OrchestratorState,
) -> Literal[
    "schema_agent", "clarification", "confirm_schema", "reject_schema", "error_handler"
]:
    """Decide which node to call next based on the classified intent."""
    intent = state.intent

    if intent in (Intent.DESCRIBE_BUSINESS, Intent.ADD_MODULE):
        return "schema_agent"
    elif intent == Intent.CONFIRM_SCHEMA:
        return "confirm_schema"
    elif intent == Intent.REJECT_SCHEMA:
        return "reject_schema"
    elif intent == Intent.CLARIFICATION_NEEDED:
        return "clarification"
    else:
        # GENERAL_QUESTION, MODIFY_FIELD, CONFIGURE_WORKFLOW → clarification for now
        return "clarification"


# ---------------------------------------------------------------------------
# Build the LangGraph StateGraph
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """Construct and compile the orchestrator state graph."""
    builder: StateGraph = StateGraph(OrchestratorState)

    # Nodes
    builder.add_node("intent_classifier", intent_classifier_node)
    builder.add_node("schema_agent", _schema_agent.run)
    builder.add_node("clarification", clarification_node)
    builder.add_node("confirm_schema", confirm_schema_node)
    builder.add_node("reject_schema", reject_schema_node)
    builder.add_node("error_handler", error_handler_node)

    # Edges
    builder.add_edge(START, "intent_classifier")
    builder.add_conditional_edges("intent_classifier", route_after_classifier)

    # All terminal nodes → END
    for terminal in [
        "schema_agent",
        "clarification",
        "confirm_schema",
        "reject_schema",
        "error_handler",
    ]:
        builder.add_edge(terminal, END)

    return builder.compile()


# Singleton compiled graph
_graph = build_graph()


async def run_orchestrator(
    tenant_id: str,
    conversation_id: str,
    user_message: str,
    conversation_history: list[dict[str, str]] | None = None,
    pending_schema: dict[str, Any] | None = None,
) -> OrchestratorState:
    """
    Entry point to run the orchestrator for a single user message.

    Returns the final OrchestratorState with response_text, actions, ui_updates.
    """
    initial_state = OrchestratorState(
        tenant_id=tenant_id,
        conversation_id=conversation_id,
        user_message=user_message,
        conversation_history=conversation_history or [],
        pending_schema=pending_schema,
    )

    try:
        final_state: OrchestratorState = await _graph.ainvoke(initial_state)  # type: ignore[assignment]
        return final_state
    except Exception as exc:
        logger.exception("Orchestrator error: %s", exc)
        initial_state.error = str(exc)
        return await error_handler_node(initial_state)
