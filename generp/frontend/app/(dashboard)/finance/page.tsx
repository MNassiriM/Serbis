"use client";

import { useState, useEffect } from "react";
import {
  DollarSign,
  Plus,
  TrendingUp,
  FileText,
  CreditCard,
  Receipt,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { createFinanceApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

// -----------------------------------------------------------------------
// Simple data table for module tabs
// -----------------------------------------------------------------------

interface SimpleRow {
  id: string;
  [key: string]: unknown;
}

function SimpleTable({
  data,
  loading,
  columns,
}: {
  data: SimpleRow[];
  loading: boolean;
  columns: { key: string; label: string; render?: (v: unknown) => React.ReactNode }[];
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
        <DollarSign className="h-10 w-10 text-muted-foreground/30 mb-3" />
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
          {data.map((row) => (
            <tr key={row.id} className="hover:bg-muted/30 transition-colors">
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

// -----------------------------------------------------------------------
// Finance metric card
// -----------------------------------------------------------------------

function MetricCard({
  label,
  value,
  icon,
  trend,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  trend?: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-muted-foreground font-medium uppercase tracking-wider">
          {label}
        </span>
        <div className="text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 rounded-md p-1.5">
          {icon}
        </div>
      </div>
      <p className="text-2xl font-bold">{value}</p>
      {trend && (
        <p className="text-xs text-emerald-600 mt-1 flex items-center gap-1">
          <TrendingUp className="h-3 w-3" />
          {trend}
        </p>
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// Page
// -----------------------------------------------------------------------

export default function FinancePage() {
  const { token } = useAuthStore();
  const [activeTab, setActiveTab] = useState("dashboard");
  const [invoices, setInvoices] = useState<SimpleRow[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token || activeTab !== "invoices") return;
    const api = createFinanceApi(token);
    setLoading(true);
    api.invoices
      .list()
      .then((data) => setInvoices(data as SimpleRow[]))
      .catch(() => setInvoices([]))
      .finally(() => setLoading(false));
  }, [token, activeTab]);

  return (
    <div className="flex flex-col h-full">
      {/* Module header */}
      <div className="border-b px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-emerald-50 dark:bg-emerald-950/40 p-2">
            <DollarSign className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Finance</h1>
            <p className="text-xs text-muted-foreground">
              Gérez vos factures, paiements et dépenses
            </p>
          </div>
        </div>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Nouvelle facture
        </Button>
      </div>

      {/* Tabs */}
      <div className="flex-1 overflow-auto">
        <div className="px-6 pt-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="dashboard">Tableau de bord</TabsTrigger>
              <TabsTrigger value="invoices">
                Factures
                <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px]">
                  {invoices.length}
                </Badge>
              </TabsTrigger>
              <TabsTrigger value="quotes">Devis</TabsTrigger>
              <TabsTrigger value="payments">Paiements</TabsTrigger>
              <TabsTrigger value="expenses">Dépenses</TabsTrigger>
            </TabsList>

            <div className="mt-4">
              <TabsContent value="dashboard">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                  <MetricCard
                    label="Chiffre d'affaires"
                    value="—"
                    icon={<TrendingUp className="h-4 w-4" />}
                  />
                  <MetricCard
                    label="Factures envoyées"
                    value="—"
                    icon={<FileText className="h-4 w-4" />}
                  />
                  <MetricCard
                    label="Paiements reçus"
                    value="—"
                    icon={<CreditCard className="h-4 w-4" />}
                  />
                  <MetricCard
                    label="Dépenses"
                    value="—"
                    icon={<Receipt className="h-4 w-4" />}
                  />
                </div>
                <div className="rounded-lg border bg-card p-6 text-center text-sm text-muted-foreground">
                  Connectez votre module Finance pour voir les graphiques ici.
                </div>
              </TabsContent>

              <TabsContent value="invoices">
                <SimpleTable
                  data={invoices}
                  loading={loading}
                  columns={[
                    { key: "id", label: "ID" },
                    { key: "client", label: "Client" },
                    { key: "amount", label: "Montant" },
                    {
                      key: "status",
                      label: "Statut",
                      render: (v) => (
                        <Badge variant="secondary">{String(v ?? "—")}</Badge>
                      ),
                    },
                    { key: "date", label: "Date" },
                  ]}
                />
              </TabsContent>

              <TabsContent value="quotes">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  Module Devis — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="payments">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  Module Paiements — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="expenses">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  Module Dépenses — connexion API requise
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
