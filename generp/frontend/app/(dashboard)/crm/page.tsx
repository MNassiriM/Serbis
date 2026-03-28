"use client";

import { useState, useEffect } from "react";
import {
  Users,
  Plus,
  TrendingUp,
  Building2,
  Activity,
  LayoutList,
  Trello,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { createCrmApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { KanbanView, type KanbanColumn, type KanbanCard } from "@/components/views/KanbanView";

// -----------------------------------------------------------------------
// Default pipeline columns
// -----------------------------------------------------------------------

const PIPELINE_COLUMNS: KanbanColumn[] = [
  { id: "lead", title: "Prospects", color: "bg-slate-400" },
  { id: "qualified", title: "Qualifiés", color: "bg-blue-500" },
  { id: "proposal", title: "Propositions", color: "bg-violet-500" },
  { id: "negotiation", title: "Négociation", color: "bg-amber-500" },
  { id: "won", title: "Gagnés", color: "bg-emerald-500" },
  { id: "lost", title: "Perdus", color: "bg-red-500" },
];

// -----------------------------------------------------------------------
// Simple table
// -----------------------------------------------------------------------

function SimpleTable({
  data,
  loading,
  columns,
  emptyIcon,
}: {
  data: Record<string, unknown>[];
  loading: boolean;
  columns: { key: string; label: string; render?: (v: unknown) => React.ReactNode }[];
  emptyIcon?: React.ReactNode;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded" />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="text-muted-foreground/30 mb-3">
          {emptyIcon ?? <Users className="h-10 w-10" />}
        </div>
        <p className="text-sm text-muted-foreground">Aucun enregistrement</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 border-b">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className="px-4 py-3 text-left font-medium text-muted-foreground"
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.map((row, i) => (
            <tr key={String(row.id ?? i)} className="hover:bg-muted/30 transition-colors">
              {columns.map((c) => (
                <td key={c.key} className="px-4 py-3">
                  {c.render
                    ? c.render(row[c.key])
                    : String(row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// -----------------------------------------------------------------------
// CRM Page
// -----------------------------------------------------------------------

export default function CRMPage() {
  const { token } = useAuthStore();
  const [activeTab, setActiveTab] = useState("pipeline");
  const [pipelineView, setPipelineView] = useState<"kanban" | "list">("kanban");
  const [contacts, setContacts] = useState<Record<string, unknown>[]>([]);
  const [companies, setCompanies] = useState<Record<string, unknown>[]>([]);
  const [deals, setDeals] = useState<KanbanCard[]>([]);
  const [loading, setLoading] = useState(false);

  // Group deals by stage
  const dealsByStage = PIPELINE_COLUMNS.reduce<Record<string, KanbanCard[]>>(
    (acc, col) => {
      acc[col.id] = deals.filter(
        (d) =>
          String(d.stage ?? d.status ?? "lead").toLowerCase() === col.id
      );
      return acc;
    },
    {}
  );

  const handleMoveDeal = async (cardId: string, toColumnId: string) => {
    if (!token) return;
    setDeals((prev) =>
      prev.map((d) =>
        d.id === cardId ? { ...d, stage: toColumnId } : d
      )
    );
    const api = createCrmApi(token);
    await api.deals
      .moveStage(cardId, toColumnId)
      .catch(() => {
        // rollback optimistic update on error
        setDeals((prev) =>
          prev.map((d) => (d.id === cardId ? { ...d } : d))
        );
      });
  };

  useEffect(() => {
    if (!token) return;
    const api = createCrmApi(token);

    if (activeTab === "pipeline") {
      setLoading(true);
      api.deals
        .list()
        .then((data) => {
          setDeals(
            (data as Record<string, unknown>[]).map((d) => ({
              id: String(d.id),
              title: String(d.name ?? d.title ?? "Deal"),
              value: d.value != null ? Number(d.value) : undefined,
              status: d.status as string | undefined,
              assignee: d.assignee as string | undefined,
              dueDate: d.due_date as string | undefined,
              stage: d.stage,
            }))
          );
        })
        .catch(() => setDeals([]))
        .finally(() => setLoading(false));
    } else if (activeTab === "contacts") {
      setLoading(true);
      api.contacts
        .list()
        .then((data) => setContacts(data as Record<string, unknown>[]))
        .catch(() => setContacts([]))
        .finally(() => setLoading(false));
    } else if (activeTab === "companies") {
      setLoading(true);
      api.companies
        .list()
        .then((data) => setCompanies(data as Record<string, unknown>[]))
        .catch(() => setCompanies([]))
        .finally(() => setLoading(false));
    }
  }, [token, activeTab]);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-blue-50 dark:bg-blue-950/40 p-2">
            <Users className="h-5 w-5 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">CRM</h1>
            <p className="text-xs text-muted-foreground">
              Gérez vos contacts, sociétés et pipeline
            </p>
          </div>
        </div>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Nouveau contact
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex-1 overflow-auto">
        <div className="px-6 pt-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="pipeline">Pipeline</TabsTrigger>
              <TabsTrigger value="contacts">
                Contacts
                {contacts.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px]">
                    {contacts.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="companies">Sociétés</TabsTrigger>
              <TabsTrigger value="activities">Activités</TabsTrigger>
              <TabsTrigger value="dashboard">Tableau de bord</TabsTrigger>
            </TabsList>

            <div className="mt-4">
              <TabsContent value="pipeline">
                {/* View switcher */}
                <div className="flex items-center justify-between mb-4">
                  <p className="text-sm text-muted-foreground">
                    {deals.length} deal(s) au total
                  </p>
                  <div className="flex items-center gap-1 rounded-md border bg-muted/50 p-0.5">
                    <button
                      onClick={() => setPipelineView("kanban")}
                      className={`rounded p-1.5 transition-colors ${
                        pipelineView === "kanban"
                          ? "bg-background shadow-sm text-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                      title="Vue Kanban"
                    >
                      <Trello className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => setPipelineView("list")}
                      className={`rounded p-1.5 transition-colors ${
                        pipelineView === "list"
                          ? "bg-background shadow-sm text-foreground"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                      title="Vue liste"
                    >
                      <LayoutList className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {loading ? (
                  <div className="flex gap-4">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <Skeleton key={i} className="h-48 w-64 rounded-xl" />
                    ))}
                  </div>
                ) : pipelineView === "kanban" ? (
                  <div className="h-[calc(100vh-260px)]">
                    <KanbanView
                      columns={PIPELINE_COLUMNS}
                      items={dealsByStage}
                      onMoveItem={handleMoveDeal}
                    />
                  </div>
                ) : (
                  <SimpleTable
                    data={deals}
                    loading={false}
                    columns={[
                      { key: "title", label: "Titre" },
                      {
                        key: "value",
                        label: "Valeur",
                        render: (v) =>
                          v != null
                            ? new Intl.NumberFormat("fr-FR", {
                                style: "currency",
                                currency: "EUR",
                              }).format(Number(v))
                            : "—",
                      },
                      {
                        key: "stage",
                        label: "Étape",
                        render: (v) => (
                          <Badge variant="secondary">{String(v ?? "—")}</Badge>
                        ),
                      },
                    ]}
                  />
                )}
              </TabsContent>

              <TabsContent value="contacts">
                <SimpleTable
                  data={contacts}
                  loading={loading}
                  columns={[
                    { key: "name", label: "Nom" },
                    { key: "email", label: "Email" },
                    { key: "phone", label: "Téléphone" },
                    { key: "company", label: "Société" },
                  ]}
                  emptyIcon={<Users className="h-10 w-10" />}
                />
              </TabsContent>

              <TabsContent value="companies">
                <SimpleTable
                  data={companies}
                  loading={loading}
                  columns={[
                    { key: "name", label: "Nom" },
                    { key: "industry", label: "Secteur" },
                    { key: "size", label: "Taille" },
                  ]}
                  emptyIcon={<Building2 className="h-10 w-10" />}
                />
              </TabsContent>

              <TabsContent value="activities">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <Activity className="h-5 w-5 mr-2" />
                  Activités — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="dashboard">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {[
                    { label: "Contacts", value: String(contacts.length), icon: <Users className="h-4 w-4" /> },
                    { label: "Sociétés", value: String(companies.length), icon: <Building2 className="h-4 w-4" /> },
                    { label: "Deals actifs", value: String(deals.filter((d) => d.stage !== "won" && d.stage !== "lost").length), icon: <TrendingUp className="h-4 w-4" /> },
                  ].map((m) => (
                    <div key={m.label} className="rounded-lg border bg-card p-4">
                      <div className="flex items-center gap-2 text-muted-foreground mb-2">
                        {m.icon}
                        <span className="text-xs font-medium uppercase tracking-wider">
                          {m.label}
                        </span>
                      </div>
                      <p className="text-2xl font-bold">{m.value}</p>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
