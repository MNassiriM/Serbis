"use client";

import { CheckCircle } from "lucide-react";
import type { ChatMessage } from "@/types/erp";

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? "bg-primary text-primary-foreground rounded-br-sm"
            : "bg-muted text-foreground rounded-bl-sm"
        }`}
      >
        {/* Message content — supports basic markdown bold */}
        <div
          className="text-sm whitespace-pre-wrap leading-relaxed"
          dangerouslySetInnerHTML={{
            __html: renderMarkdown(message.content),
          }}
        />

        {/* Inline action badges */}
        {message.actions && message.actions.length > 0 && (
          <div className="mt-3 space-y-2">
            {message.actions.map((action, i) => (
              <ActionBadge key={i} action={action.action} />
            ))}
          </div>
        )}

        <p
          className={`mt-1 text-[10px] ${
            isUser ? "text-primary-foreground/60" : "text-muted-foreground"
          }`}
        >
          {formatTime(message.timestamp)}
        </p>
      </div>
    </div>
  );
}

function ActionBadge({ action }: { action: string }) {
  const labels: Record<string, string> = {
    schema_generated: "Schéma généré ✓",
    schema_confirmed: "Schéma confirmé ✓",
    schema_deployed: "Base de données créée ✓",
  };

  const label = labels[action] ?? action;

  return (
    <div className="flex items-center gap-2 rounded-lg bg-background/20 px-3 py-2 text-xs font-medium">
      <CheckCircle className="h-3.5 w-3.5 shrink-0" />
      {label}
    </div>
  );
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Minimal markdown renderer — supports **bold** only.
 * For production, use a proper markdown library.
 */
function renderMarkdown(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");
}
