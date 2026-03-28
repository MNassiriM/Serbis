"use client";

import { useState } from "react";
import type { ModuleUIConfig } from "@/types/erp";
import { ERPDataTable } from "./ERPDataTable";
import { ERPForm } from "./ERPForm";
import { ERPDashboard } from "./ERPDashboard";

interface ERPRendererProps {
  moduleConfig: ModuleUIConfig;
  tenantId: string;
  moduleName: string;
}

type View = "list" | "create" | "dashboard";

export function ERPRenderer({ moduleConfig, tenantId, moduleName }: ERPRendererProps) {
  const [currentView, setCurrentView] = useState<View>("list");
  const [editingId, setEditingId] = useState<string | null>(null);

  return (
    <div className="flex flex-col h-full">
      {/* View tabs */}
      <div className="border-b bg-background px-6 py-3">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">{moduleConfig.display_name}</h1>
          <nav className="flex gap-1">
            {(["list", "dashboard", "create"] as View[]).map((view) => (
              <button
                key={view}
                onClick={() => setCurrentView(view)}
                className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  currentView === view
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted"
                }`}
              >
                {VIEW_LABELS[view]}
              </button>
            ))}
          </nav>
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
          />
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
  );
}

const VIEW_LABELS: Record<View, string> = {
  list: "Liste",
  create: "Créer",
  dashboard: "Tableau de bord",
};
