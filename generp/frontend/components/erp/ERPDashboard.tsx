"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Database, Calendar } from "lucide-react";
import type { DashboardConfig } from "@/types/erp";

interface ERPDashboardProps {
  config: DashboardConfig;
  apiBase: string;
}

export function ERPDashboard({ config, apiBase }: ERPDashboardProps) {
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const [chartData, setChartData] = useState<Record<string, unknown>[]>([]);

  // In a real implementation, these would fetch from the API.
  // For MVP, we show placeholder data.
  useEffect(() => {
    const mockMetrics: Record<string, number> = {};
    config.metrics.forEach((m) => {
      mockMetrics[m.key] = Math.floor(Math.random() * 100);
    });
    setMetrics(mockMetrics);

    const mockChart = Array.from({ length: 6 }, (_, i) => {
      const date = new Date();
      date.setMonth(date.getMonth() - (5 - i));
      return {
        month: date.toLocaleDateString("fr-FR", { month: "short", year: "2-digit" }),
        count: Math.floor(Math.random() * 30) + 5,
      };
    });
    setChartData(mockChart);
  }, [config, apiBase]);

  const ICONS: Record<string, React.ReactNode> = {
    database: <Database className="h-5 w-5" />,
    calendar: <Calendar className="h-5 w-5" />,
  };

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold">{config.title}</h2>

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-4">
        {config.metrics.map((metric) => (
          <div
            key={metric.key}
            className="rounded-lg border bg-card p-4 shadow-sm"
          >
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-primary/10 p-2 text-primary">
                {ICONS[metric.icon] ?? <Database className="h-5 w-5" />}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{metric.label}</p>
                <p className="text-2xl font-bold">{metrics[metric.key] ?? 0}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      {config.charts.map((chart) => (
        <div key={chart.title} className="rounded-lg border bg-card p-4 shadow-sm">
          <h3 className="text-sm font-medium text-muted-foreground mb-4">
            {chart.title}
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey={chart.x_key}
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
                dataKey={chart.y_key}
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
