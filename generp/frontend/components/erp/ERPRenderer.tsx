"use client";

import { useState } from "react";
import { LayoutList, LayoutDashboard, Trello, Image } from "lucide-react";
import type { ModuleUIConfig } from "@/types/erp";
import { ERPDataTable } from "./ERPDataTable";
import { ERPForm } from "./ERPForm";
import { ERPDashboard } from "./ERPDashboard";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ERPRendererProps {
  moduleConfig: ModuleUIConfig;
  tenantId: string;
  moduleName: string;
}

type View = "list" | "create" | "dashboard" | "kanban" | "gallery";

interface ViewOption {
  id: View;
  label: string;
  icon: React.ReactNode;
  available: (category: string) => boolean;
}

const VIEW_OPTIONS: ViewOption[] = [
  {
    id: "list",
    label: "Liste",
    icon: <LayoutList className="h-4 w-4" />,
    available: () => true,
  },
  {
    id: "kanban",
    label: "Kanban",
    icon: <Trello className="h-4 w-4" />,
    available: (cat) => cat === "crm",
  },
  {
    id: "gallery",
    label: "Galerie",
    icon: <Image className="h-4 w-4" />,
    available: () => true,
  },
  {
    id: "dashboard",
    label: "Tableau de bord",
    icon: <LayoutDashboard className="h-4 w-4" />,
    available: () => true,
  },
];

const VIEW_LABELS: Record<View, string> = {
  list: "Liste",
  create: "Créer",
  dashboard: "Tableau de bord",
  kanban: "Kanban",
  gallery: "Galerie",
};

export function ERPRenderer({ moduleConfig, tenantId, moduleName }: ERPRendererProps) {
  const [currentView, setCurrentView] = useState<View>("list");
  const [editingId, setEditingId] = useState<string | null>(null);

  // Derive category from api_base or moduleName
  const category = moduleConfig.api_base?.includes("crm")
    ? "crm"
    : moduleConfig.api_base?.includes("finance")
    ? "finance"
    : moduleConfig.api_base?.includes("hr")
    ? "hr"
    : moduleConfig.api_base?.includes("supply")
    ? "supply_chain"
    : "general";

  const availableViews = VIEW_OPTIONS.filter((v) => v.available(category));

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="border-b bg-background px-6 py-3 shrink-0">
          <div className="flex items-center justify-between gap-4">
            <h1 className="text-xl font-semibold">{moduleConfig.display_name}</h1>

            <div className="flex items-center gap-2">
              {/* View selector */}
              <div className="flex items-center rounded-md border bg-muted/50 p-0.5 gap-0.5">
                {availableViews.map((opt) => (
                  <Tooltip key={opt.id}>
                    <TooltipTrigger asChild>
                      <button
                        onClick={() => setCurrentView(opt.id)}
                        className={cn(
                          "rounded p-1.5 transition-colors",
                          currentView === opt.id
                            ? "bg-background text-foreground shadow-sm"
                            : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {opt.icon}
                        <span className="sr-only">{opt.label}</span>
                      </button>
                    </TooltipTrigger>
                    <TooltipContent>{opt.label}</TooltipContent>
                  </Tooltip>
                ))}
              </div>

              {/* Create button */}
              <Button
                size="sm"
                className="h-8 gap-1.5 text-xs"
                onClick={() => {
                  setEditingId(null);
                  setCurrentView("create");
                }}
              >
                + {VIEW_LABELS.create}
              </Button>
            </div>
          </div>
        </div>

        {/* View content */}
        <div className="flex-1 overflow-auto p-6">
          {currentView === "list" && (
            <ERPDataTable
              config={moduleConfig.list_view}
              apiBase={moduleConfig.api_base}
              tenantId={tenantId}
              onEdit={(id) => {
                setEditingId(id);
                setCurrentView("create");
              }}
              onCreateNew={() => {
                setEditingId(null);
                setCurrentView("create");
              }}
            />
          )}

          {currentView === "kanban" && (
            <div className="flex items-center justify-center h-48 rounded-lg border border-dashed text-muted-foreground">
              Vue Kanban disponible pour CRM pipeline
            </div>
          )}

          {currentView === "gallery" && (
            <div className="flex items-center justify-center h-48 rounded-lg border border-dashed text-muted-foreground">
              Vue Galerie — bientôt disponible
            </div>
          )}

          {currentView === "create" && (
            <ERPForm
              config={moduleConfig.create_form}
              apiBase={moduleConfig.api_base}
              editingId={editingId}
              onSuccess={() => {
                setEditingId(null);
                setCurrentView("list");
              }}
              onCancel={() => {
                setEditingId(null);
                setCurrentView("list");
              }}
            />
          )}

          {currentView === "dashboard" && (
            <ERPDashboard
              config={moduleConfig.dashboard}
              apiBase={moduleConfig.api_base}
            />
          )}
        </div>
      </div>
    </TooltipProvider>
  );
}
