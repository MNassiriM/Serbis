"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { v4 as uuidv4 } from "uuid";

import { streamChat } from "@/lib/api";
import { useAuthStore, useChatStore, useERPStore } from "@/lib/store";
import type {
  ChatMessage,
  ERPModule,
  SSEActionEvent,
  SSEEvent,
} from "@/types/erp";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

export function ChatInterface() {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const { token } = useAuthStore();
  const {
    messages,
    conversationId,
    isStreaming,
    addMessage,
    setStreaming,
    setConversationId,
    setPendingSchema,
    addAction,
  } = useChatStore();
  const { addOrUpdateModule } = useERPStore();

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isStreaming || !token) return;

    setInput("");

    // Add user message immediately
    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    addMessage(userMessage);

    // Prepare assistant placeholder
    const assistantMessage: ChatMessage = {
      id: uuidv4(),
      role: "assistant",
      content: "",
      timestamp: new Date(),
      actions: [],
    };
    addMessage(assistantMessage);
    setStreaming(true);

    try {
      let fullText = "";

      await streamChat(
        { message: text, conversation_id: conversationId ?? undefined },
        token,
        (event: SSEEvent) => {
          handleSSEEvent(event, fullText, (text) => {
            fullText = text;
          });
        }
      );
    } catch (error) {
      console.error("Chat error:", error);
      // Update last assistant message with error
      useChatStore.setState((state) => {
        const msgs = [...state.messages];
        const last = msgs[msgs.length - 1];
        if (last.role === "assistant") {
          msgs[msgs.length - 1] = {
            ...last,
            content:
              "Une erreur est survenue. Veuillez réessayer.",
          };
        }
        return { messages: msgs };
      });
    } finally {
      setStreaming(false);
    }
  };

  function handleSSEEvent(
    event: SSEEvent,
    currentText: string,
    updateText: (t: string) => void
  ) {
    switch (event.type) {
      case "text": {
        const newText = currentText + event.content;
        updateText(newText);
        // Update last assistant message content
        useChatStore.setState((state) => {
          const msgs = [...state.messages];
          const last = msgs[msgs.length - 1];
          if (last?.role === "assistant") {
            msgs[msgs.length - 1] = { ...last, content: newText };
          }
          return { messages: msgs };
        });
        break;
      }

      case "action": {
        addAction(event as SSEActionEvent);
        if (event.action === "schema_generated" && event.schema) {
          setPendingSchema(event.schema);
        }
        break;
      }

      case "ui_update": {
        // Register the new module in the ERP store
        const module: ERPModule = {
          id: uuidv4(),
          name: event.module,
          display_name: event.display_name,
          category: event.category,
          schema_definition: {} as ERPModule["schema_definition"],
          ui_config: event.config,
          api_routes: {},
          is_active: true,
        };
        addOrUpdateModule(module);
        break;
      }

      case "meta": {
        if (event.conversation_id) {
          setConversationId(event.conversation_id);
        }
        break;
      }

      case "error": {
        console.error("SSE error:", event.message);
        break;
      }

      case "done":
        break;
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full bg-background">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {isEmpty ? (
          <WelcomeScreen />
        ) : (
          <>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isStreaming && messages[messages.length - 1]?.role === "assistant" &&
              messages[messages.length - 1]?.content === "" && (
                <TypingIndicator />
              )}
          </>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="border-t bg-background px-4 py-4">
        <div className="max-w-3xl mx-auto flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Décrivez votre entreprise ou posez une question…"
            rows={2}
            className="flex-1 resize-none rounded-xl border border-input bg-background px-4 py-3 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            disabled={isStreaming}
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || !input.trim()}
            className="rounded-xl bg-primary p-3 text-primary-foreground shadow-sm hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Envoyer"
          >
            <Send className="h-5 w-5" />
          </button>
        </div>
        <p className="text-center text-xs text-muted-foreground mt-2">
          Appuyez sur Entrée pour envoyer · Shift+Entrée pour un saut de ligne
        </p>
      </div>
    </div>
  );
}

function WelcomeScreen() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center px-4 py-16 space-y-6">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center text-3xl">
        🤖
      </div>
      <div className="space-y-2">
        <h2 className="text-2xl font-semibold tracking-tight">
          Bienvenue sur GenERP
        </h2>
        <p className="text-muted-foreground max-w-md">
          Décrivez votre entreprise et vos besoins en langage naturel.
          Je vais générer votre ERP personnalisé automatiquement.
        </p>
      </div>
      <div className="grid gap-3 w-full max-w-sm text-left">
        {EXAMPLE_PROMPTS.map((prompt) => (
          <ExamplePrompt key={prompt} text={prompt} />
        ))}
      </div>
    </div>
  );
}

const EXAMPLE_PROMPTS = [
  "Je dirige une agence de communication avec 8 commerciaux. Je veux gérer mes prospects et ma facturation.",
  "J'ai une boutique e-commerce et je veux suivre mes commandes, mes clients et mon stock.",
  "Je gère un cabinet de conseil RH. J'ai besoin d'un CRM et d'un suivi de mes missions.",
];

function ExamplePrompt({ text }: { text: string }) {
  const { isStreaming } = useChatStore();

  const handleClick = () => {
    if (isStreaming) return;
    useChatStore.setState({ messages: [] });
    // Trigger send with this text via store manipulation
    // In a real app, you'd use a ref or context to call handleSend
    const event = new CustomEvent("generp:set-input", { detail: text });
    window.dispatchEvent(event);
  };

  return (
    <button
      onClick={handleClick}
      className="text-left rounded-lg border border-dashed border-border px-4 py-3 text-sm text-muted-foreground hover:border-primary hover:text-foreground transition-colors"
    >
      {text}
    </button>
  );
}
