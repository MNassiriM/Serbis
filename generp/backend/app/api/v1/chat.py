"""
Chat endpoint — main conversation interface via Server-Sent Events (SSE).
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.deployment_agent import DeploymentAgent
from app.agents.orchestrator import Intent, run_orchestrator
from app.core.dependencies import CurrentTenant, DBSession
from app.models.tenant import Tenant
from app.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


async def _event_stream(
    request: ChatRequest,
    tenant: Tenant,
    db: AsyncSession,
) -> AsyncGenerator[str, None]:
    """
    Core SSE generator.

    Yields events in the format:
      data: {"type": "text"|"action"|"ui_update"|"error"|"done", ...}
    """
    conv_service = ConversationService(db)

    # Resolve/create conversation
    conversation = await conv_service.get_or_create_conversation(
        tenant_id=tenant.id,
        conversation_id=request.conversation_id,
    )

    # Persist user message
    await conv_service.add_message(conversation, role="user", content=request.message)

    # Load history and pending schema from previous messages
    history = await conv_service.get_conversation_history(conversation.id)
    pending_schema = await conv_service.get_pending_schema(conversation.id)

    try:
        # Run the orchestrator
        state = await run_orchestrator(
            tenant_id=str(tenant.id),
            conversation_id=str(conversation.id),
            user_message=request.message,
            conversation_history=history,
            pending_schema=pending_schema,
        )

        # Stream the text response character by character (simulate streaming)
        # In production, use LangChain streaming callbacks for true token streaming
        if state.response_text:
            yield _sse({"type": "text", "content": state.response_text})

        # Emit action events
        for action in state.actions:
            yield _sse({"type": "action", **action})

        # If schema was confirmed, deploy it
        if (
            state.intent == Intent.CONFIRM_SCHEMA
            and not state.error
            and state.actions
            and any(a.get("action") == "schema_confirmed" for a in state.actions)
        ):
            confirmed_action = next(
                a for a in state.actions if a.get("action") == "schema_confirmed"
            )
            schema = confirmed_action.get("schema")
            if schema:
                try:
                    deployment_agent = DeploymentAgent(db_session=db)
                    deploy_result = await deployment_agent.deploy(
                        tenant_id=str(tenant.id), schema=schema
                    )
                    yield _sse(
                        {
                            "type": "action",
                            "action": "schema_deployed",
                            "data": deploy_result,
                        }
                    )
                except Exception as exc:
                    logger.error("Deployment error: %s", exc)
                    yield _sse(
                        {
                            "type": "error",
                            "message": f"Erreur lors du déploiement : {exc}",
                        }
                    )

        # Emit UI update events
        for ui_update in state.ui_updates:
            yield _sse({"type": "ui_update", **ui_update})

        # Persist assistant message with metadata
        message_metadata: dict[str, Any] = {}
        if state.pending_schema:
            message_metadata["pending_schema"] = state.pending_schema
        if state.actions:
            message_metadata["actions"] = state.actions

        await conv_service.add_message(
            conversation,
            role="assistant",
            content=state.response_text,
            metadata=message_metadata,
        )
        await conv_service.commit()

        # Send conversation ID so frontend can track it
        yield _sse(
            {
                "type": "meta",
                "conversation_id": str(conversation.id),
            }
        )

    except Exception as exc:
        logger.exception("Chat endpoint error: %s", exc)
        yield _sse(
            {
                "type": "error",
                "message": "Une erreur interne est survenue. Veuillez réessayer.",
            }
        )

    finally:
        yield _sse({"type": "done"})


def _sse(data: dict[str, Any]) -> str:
    """Format a dict as an SSE data line."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def chat(
    request: ChatRequest,
    tenant: CurrentTenant,
    db: DBSession,
) -> StreamingResponse:
    """
    Main conversation endpoint.

    Accepts a user message and streams back the assistant response via SSE.

    SSE event types:
    - text: streaming response text
    - action: an agent action was taken (schema_generated, schema_deployed, etc.)
    - ui_update: a module UI config was generated/updated
    - meta: conversation metadata (conversation_id)
    - error: an error occurred
    - done: stream is complete
    """
    return StreamingResponse(
        _event_stream(request, tenant, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering
            "Connection": "keep-alive",
        },
    )
