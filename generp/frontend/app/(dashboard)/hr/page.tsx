"use client";

import { useState, useEffect } from "react";
import { Briefcase, Plus, Users, Calendar, Star } from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { createHrApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

type HrRecord = Record<string, unknown>;

function SimpleTable({
  data,
  loading,
  columns,
  emptyIcon,
}: {
  data: HrRecord[];
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
          {emptyIcon ?? <Briefcase className="h-10 w-10" />}
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

export default function HRPage() {
  const { token } = useAuthStore();
  const [activeTab, setActiveTab] = useState("employees");
  const [employees, setEmployees] = useState<HrRecord[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token || activeTab !== "employees") return;
    const api = createHrApi(token);
    setLoading(true);
    api.employees
      .list()
      .then((data) => setEmployees(data as HrRecord[]))
      .catch(() => setEmployees([]))
      .finally(() => setLoading(false));
  }, [token, activeTab]);

  return (
    <div className="flex flex-col h-full">
      <div className="border-b px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-violet-50 dark:bg-violet-950/40 p-2">
            <Briefcase className="h-5 w-5 text-violet-600 dark:text-violet-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Ressources Humaines</h1>
            <p className="text-xs text-muted-foreground">
              Gérez vos employés, recrutements et congés
            </p>
          </div>
        </div>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Nouvel employé
        </Button>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="px-6 pt-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="employees">
                Employés
                {employees.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px]">
                    {employees.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="recruitment">Recrutement</TabsTrigger>
              <TabsTrigger value="leaves">Congés</TabsTrigger>
              <TabsTrigger value="evaluations">Évaluations</TabsTrigger>
              <TabsTrigger value="dashboard">Tableau de bord</TabsTrigger>
            </TabsList>

            <div className="mt-4">
              <TabsContent value="employees">
                <SimpleTable
                  data={employees}
                  loading={loading}
                  columns={[
                    {
                      key: "name",
                      label: "Nom",
                      render: (v) => (
                        <div className="flex items-center gap-2">
                          <Avatar className="h-7 w-7">
                            <AvatarFallback className="text-xs bg-violet-100 text-violet-700">
                              {String(v ?? "?")
                                .split(" ")
                                .map((w) => w[0])
                                .slice(0, 2)
                                .join("")
                                .toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <span>{String(v ?? "—")}</span>
                        </div>
                      ),
                    },
                    { key: "email", label: "Email" },
                    { key: "department", label: "Département" },
                    { key: "position", label: "Poste" },
                    {
                      key: "status",
                      label: "Statut",
                      render: (v) => (
                        <Badge variant="secondary">{String(v ?? "—")}</Badge>
                      ),
                    },
                  ]}
                  emptyIcon={<Users className="h-10 w-10" />}
                />
              </TabsContent>

              <TabsContent value="recruitment">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <Users className="h-5 w-5 mr-2" />
                  Recrutement — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="leaves">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <Calendar className="h-5 w-5 mr-2" />
                  Gestion des congés — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="evaluations">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <Star className="h-5 w-5 mr-2" />
                  Évaluations — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="dashboard">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {[
                    { label: "Employés actifs", value: String(employees.length), icon: <Users className="h-4 w-4" /> },
                    { label: "Recrutements en cours", value: "—", icon: <Briefcase className="h-4 w-4" /> },
                    { label: "Congés ce mois", value: "—", icon: <Calendar className="h-4 w-4" /> },
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
