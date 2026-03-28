"use client";

import { useState, useEffect } from "react";
import {
  FolderKanban,
  Plus,
  CheckSquare,
  Clock,
  BarChart3,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { createProjectsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";

type ProjectRecord = Record<string, unknown>;

function SimpleTable({
  data,
  loading,
  columns,
  emptyIcon,
}: {
  data: ProjectRecord[];
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
          {emptyIcon ?? <FolderKanban className="h-10 w-10" />}
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
                  {c.render ? c.render(row[c.key]) : String(row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ProjectsPage() {
  const { token } = useAuthStore();
  const [activeTab, setActiveTab] = useState("projects");
  const [projects, setProjects] = useState<ProjectRecord[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token || activeTab !== "projects") return;
    const api = createProjectsApi(token);
    setLoading(true);
    api.projects
      .list()
      .then((data) => setProjects(data as ProjectRecord[]))
      .catch(() => setProjects([]))
      .finally(() => setLoading(false));
  }, [token, activeTab]);

  return (
    <div className="flex flex-col h-full">
      <div className="border-b px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-cyan-50 dark:bg-cyan-950/40 p-2">
            <FolderKanban className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Projets</h1>
            <p className="text-xs text-muted-foreground">
              Gérez vos projets, tâches et équipes
            </p>
          </div>
        </div>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Nouveau projet
        </Button>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="px-6 pt-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="projects">
                Projets
                {projects.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px]">
                    {projects.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="tasks">Tâches</TabsTrigger>
              <TabsTrigger value="timeline">Timeline</TabsTrigger>
              <TabsTrigger value="dashboard">Tableau de bord</TabsTrigger>
            </TabsList>

            <div className="mt-4">
              <TabsContent value="projects">
                <SimpleTable
                  data={projects}
                  loading={loading}
                  columns={[
                    { key: "name", label: "Projet" },
                    {
                      key: "status",
                      label: "Statut",
                      render: (v) => (
                        <Badge variant="secondary">{String(v ?? "—")}</Badge>
                      ),
                    },
                    {
                      key: "progress",
                      label: "Progression",
                      render: (v) => (
                        <div className="flex items-center gap-2 min-w-[120px]">
                          <Progress value={Number(v ?? 0)} className="h-1.5 flex-1" />
                          <span className="text-xs text-muted-foreground w-8 text-right">
                            {Number(v ?? 0)}%
                          </span>
                        </div>
                      ),
                    },
                    { key: "due_date", label: "Échéance" },
                  ]}
                />
              </TabsContent>

              <TabsContent value="tasks">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <CheckSquare className="h-5 w-5 mr-2" />
                  Tâches — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="timeline">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <Clock className="h-5 w-5 mr-2" />
                  Timeline Gantt — bientôt disponible
                </div>
              </TabsContent>

              <TabsContent value="dashboard">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {[
                    { label: "Projets actifs", value: String(projects.filter((p) => p.status !== "completed").length), icon: <FolderKanban className="h-4 w-4" /> },
                    { label: "Tâches en cours", value: "—", icon: <CheckSquare className="h-4 w-4" /> },
                    { label: "Taux de complétion", value: "—", icon: <BarChart3 className="h-4 w-4" /> },
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
