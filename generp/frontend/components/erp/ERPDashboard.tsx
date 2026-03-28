"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Database, Calendar, TrendingUp, RefreshCw } from "lucide-react";
import type { DashboardConfig } from "@/types/erp";
import { useAuthStore } from "@/lib/store";
import { createDataApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

interface ERPDashboardProps {
  config: DashboardConfig;
  apiBase: string;
}

const ICONS: Record<string, React.ReactNode> = {
  database: <Database className="h-5 w-5" />,
  calendar: <Calendar className="h-5 w-5" />,
  trending: <TrendingUp className="h-5 w-5" />,
};

export function ERPDashboard({ config, apiBase }: ERPDashboardProps) {
  const { token, tenantId } = useAuthStore();
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const [chartData, setChartData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const entityName = apiBase.split("/").at(-1) ?? "";

  const fetchData = useCallback(async () => {
    if (!token || !tenantId) return;
    setLoading(true);
    setError(null);

    try {
      const api = createDataApi(tenantId, token);
      const records = await api.list<Record<string, unknown>>(entityName);

      // Calculate basic metrics from real data
      const calculatedMetrics: Record<string, number> = {};
      config.metrics.forEach((m) => {
        if (m.query === "count") {
          calculatedMetrics[m.key] = records.length;
        } else if (m.query.startsWith("sum:")) {
          const field = m.query.replace("sum:", "");
          calculatedMetrics[m.key] = records.reduce((acc, r) => {
            const val = Number(r[field] ?? 0);
            return acc + (isNaN(val) ? 0 : val);
          }, 0);
        } else if (m.query.startsWith("avg:")) {
          const field = m.query.replace("avg:", "");
          if (records.length === 0) {
            calculatedMetrics[m.key] = 0;
          } else {
            const sum = records.reduce((acc, r) => {
              const val = Number(r[field] ?? 0);
              return acc + (isNaN(val) ? 0 : val);
            }, 0);
            calculatedMetrics[m.key] = Math.round(sum / records.length);
          }
        } else {
          calculatedMetrics[m.key] = records.length;
        }
      });
      setMetrics(calculatedMetrics);

      // Build chart data from records grouped by month
      const byMonth: Record<string, number> = {};
      records.forEach((r) => {
        const dateStr = String(
          r.created_at ?? r.date ?? r.createdAt ?? ""
        );
        if (dateStr) {
          const d = new Date(dateStr);
          if (!isNaN(d.getTime())) {
            const key = d.toLocaleDateString("fr-FR", {
              month: "short",
              year: "2-digit",
            });
            byMonth[key] = (byMonth[key] ?? 0) + 1;
          }
        }
      });

      // If no date data, generate last 6 months with counts = 0
      const chartRows =
        Object.keys(byMonth).length > 0
          ? Object.entries(byMonth)
              .slice(-6)
              .map(([month, count]) => ({ month, count }))
          : Array.from({ length: 6 }, (_, i) => {
              const d = new Date();
              d.setMonth(d.getMonth() - (5 - i));
              return {
                month: d.toLocaleDateString("fr-FR", {
                  month: "short",
                  year: "2-digit",
                }),
                count: 0,
              };
            });

      setChartData(chartRows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du chargement");
    } finally {
      setLoading(false);
    }
  }, [token, tenantId, entityName, config.metrics]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-7 w-48" />
        <div className="grid grid-cols-2 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
        <Skeleton className="h-56 rounded-lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-4">
        <p className="text-sm text-destructive">{error}</p>
        <Button variant="outline" size="sm" onClick={fetchData} className="gap-1.5">
          <RefreshCw className="h-4 w-4" />
          Réessayer
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{config.title}</h2>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground"
          onClick={fetchData}
          title="Actualiser"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {config.metrics.map((metric) => {
          const value = metrics[metric.key] ?? 0;
          const formatted =
            metric.key.includes("amount") ||
            metric.key.includes("revenue") ||
            metric.key.includes("total")
              ? new Intl.NumberFormat("fr-FR", {
                  style: "currency",
                  currency: "EUR",
                  maximumFractionDigits: 0,
                }).format(value)
              : value.toLocaleString("fr-FR");

          return (
            <div
              key={metric.key}
              className="rounded-lg border bg-card p-4 shadow-sm hover:shadow-md transition-shadow"
            >
              <div className="flex items-center gap-3">
                <div className="rounded-md bg-primary/10 p-2 text-primary shrink-0">
                  {ICONS[metric.icon] ?? <Database className="h-5 w-5" />}
                </div>
                <div className="min-w-0">
                  <p className="text-sm text-muted-foreground truncate">
                    {metric.label}
                  </p>
                  <p
                    className={cn(
                      "font-bold mt-0.5",
                      formatted.length > 10 ? "text-xl" : "text-2xl"
                    )}
                  >
                    {formatted}
                  </p>
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Charts */}
      {config.charts.map((chart) => (
        <div
          key={chart.title}
          className="rounded-lg border bg-card p-4 shadow-sm"
        >
          <h3 className="text-sm font-medium text-muted-foreground mb-4">
            {chart.title}
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey={chart.x_key === "month" ? "month" : chart.x_key}
                tick={{ fontSize: 12 }}
                className="text-muted-foreground"
              />
              <YAxis tick={{ fontSize: 12 }} className="text-muted-foreground" />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "6px",
                  fontSize: "12px",
                }}
              />
              <Bar
                dataKey={chart.y_key === "count" || !chart.y_key ? "count" : chart.y_key}
                fill="hsl(var(--primary))"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ))}
    </div>
  );
}
