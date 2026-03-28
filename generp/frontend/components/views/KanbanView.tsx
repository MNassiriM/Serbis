"use client";

import * as React from "react";
import { useState } from "react";
import { MoreHorizontal, Eye, Pencil, Trash2, GripVertical } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

// -----------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------

export interface KanbanColumn {
  id: string;
  title: string;
  color: string; // tailwind bg class e.g. "bg-blue-500"
}

export interface KanbanCard {
  id: string;
  title: string;
  value?: number;
  status?: string;
  assignee?: string;
  dueDate?: string;
  [key: string]: unknown;
}

interface KanbanViewProps {
  columns: KanbanColumn[];
  items: Record<string, KanbanCard[]>; // columnId -> cards
  onMoveItem: (cardId: string, toColumnId: string) => void;
  onView?: (card: KanbanCard) => void;
  onEdit?: (card: KanbanCard) => void;
  onDelete?: (card: KanbanCard) => void;
}

// -----------------------------------------------------------------------
// KanbanCard component
// -----------------------------------------------------------------------

function KanbanCardComponent({
  card,
  columnId,
  onView,
  onEdit,
  onDelete,
  onDragStart,
}: {
  card: KanbanCard;
  columnId: string;
  onView?: (card: KanbanCard) => void;
  onEdit?: (card: KanbanCard) => void;
  onDelete?: (card: KanbanCard) => void;
  onDragStart: (card: KanbanCard, fromColumnId: string) => void;
}) {
  return (
    <div
      draggable
      onDragStart={() => onDragStart(card, columnId)}
      className={cn(
        "group bg-card border rounded-lg p-3 shadow-sm cursor-grab active:cursor-grabbing",
        "hover:shadow-md hover:border-border/80 transition-all duration-150",
        "select-none"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          <GripVertical className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
          <p className="text-sm font-medium leading-snug line-clamp-2">
            {card.title}
          </p>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="shrink-0 rounded p-0.5 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-muted">
              <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            {onView && (
              <DropdownMenuItem
                onClick={() => onView(card)}
                className="gap-2 cursor-pointer text-sm"
              >
                <Eye className="h-3.5 w-3.5" />
                Voir
              </DropdownMenuItem>
            )}
            {onEdit && (
              <DropdownMenuItem
                onClick={() => onEdit(card)}
                className="gap-2 cursor-pointer text-sm"
              >
                <Pencil className="h-3.5 w-3.5" />
                Modifier
              </DropdownMenuItem>
            )}
            {onDelete && (
              <DropdownMenuItem
                onClick={() => onDelete(card)}
                className="gap-2 cursor-pointer text-sm text-destructive focus:text-destructive"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Supprimer
              </DropdownMenuItem>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Body */}
      <div className="space-y-2 mt-2">
        {/* Value */}
        {card.value != null && (
          <p className="text-sm font-semibold text-foreground">
            {new Intl.NumberFormat("fr-FR", {
              style: "currency",
              currency: "EUR",
              maximumFractionDigits: 0,
            }).format(card.value)}
          </p>
        )}

        {/* Status badge */}
        {card.status && (
          <Badge variant="secondary" className="text-xs">
            {card.status}
          </Badge>
        )}

        {/* Footer: due date + assignee */}
        <div className="flex items-center justify-between mt-1">
          {card.dueDate && (
            <span className="text-[11px] text-muted-foreground">
              {new Date(card.dueDate).toLocaleDateString("fr-FR", {
                day: "numeric",
                month: "short",
              })}
            </span>
          )}
          {card.assignee && (
            <Avatar className="h-5 w-5 ml-auto">
              <AvatarFallback className="text-[10px] bg-primary/10 text-primary">
                {card.assignee
                  .split(" ")
                  .map((w: string) => w[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase()}
              </AvatarFallback>
            </Avatar>
          )}
        </div>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------
// KanbanView
// -----------------------------------------------------------------------

export function KanbanView({
  columns,
  items,
  onMoveItem,
  onView,
  onEdit,
  onDelete,
}: KanbanViewProps) {
  const [dragging, setDragging] = useState<{
    card: KanbanCard;
    fromColumnId: string;
  } | null>(null);
  const [overColumnId, setOverColumnId] = useState<string | null>(null);

  const handleDragStart = (card: KanbanCard, fromColumnId: string) => {
    setDragging({ card, fromColumnId });
  };

  const handleDragOver = (
    e: React.DragEvent<HTMLDivElement>,
    columnId: string
  ) => {
    e.preventDefault();
    setOverColumnId(columnId);
  };

  const handleDrop = (columnId: string) => {
    if (dragging && dragging.fromColumnId !== columnId) {
      onMoveItem(dragging.card.id, columnId);
    }
    setDragging(null);
    setOverColumnId(null);
  };

  const handleDragEnd = () => {
    setDragging(null);
    setOverColumnId(null);
  };

  return (
    <div className="flex gap-4 h-full overflow-x-auto pb-4">
      {columns.map((col) => {
        const cards = items[col.id] ?? [];
        const isOver = overColumnId === col.id;

        return (
          <div
            key={col.id}
            className={cn(
              "flex flex-col shrink-0 w-72 rounded-xl transition-all duration-150",
              isOver
                ? "ring-2 ring-primary/50 bg-primary/5"
                : "bg-muted/30"
            )}
            onDragOver={(e) => handleDragOver(e, col.id)}
            onDrop={() => handleDrop(col.id)}
            onDragEnd={handleDragEnd}
          >
            {/* Column header */}
            <div className="flex items-center justify-between px-3 py-2.5">
              <div className="flex items-center gap-2">
                <span
                  className={cn("w-2.5 h-2.5 rounded-full shrink-0", col.color)}
                />
                <span className="text-sm font-semibold">{col.title}</span>
              </div>
              <Badge variant="secondary" className="h-5 px-1.5 text-xs min-w-[20px]">
                {cards.length}
              </Badge>
            </div>

            {/* Cards */}
            <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-2 min-h-[120px]">
              {cards.map((card) => (
                <KanbanCardComponent
                  key={card.id}
                  card={card}
                  columnId={col.id}
                  onView={onView}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onDragStart={handleDragStart}
                />
              ))}

              {/* Drop indicator */}
              {isOver && dragging && (
                <div className="h-16 rounded-lg border-2 border-dashed border-primary/40 bg-primary/5 animate-fade-in" />
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
