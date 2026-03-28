"use client";

import { Check, Zap, Building2, Rocket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";

interface Plan {
  id: string;
  name: string;
  price: string;
  icon: React.ReactNode;
  features: string[];
  badge?: string;
  badgeVariant?: "default" | "secondary" | "outline";
}

const PLANS: Plan[] = [
  {
    id: "free",
    name: "Gratuit",
    price: "0€",
    icon: <Zap className="h-5 w-5" />,
    features: [
      "Jusqu'à 3 modules",
      "1 000 enregistrements",
      "10 000 appels API/mois",
      "Support communautaire",
    ],
    badge: "Actuel",
    badgeVariant: "secondary",
  },
  {
    id: "pro",
    name: "Pro",
    price: "49€/mois",
    icon: <Rocket className="h-5 w-5" />,
    features: [
      "Modules illimités",
      "100 000 enregistrements",
      "500 000 appels API/mois",
      "5 membres d'équipe",
      "Support prioritaire",
      "Exports avancés",
    ],
    badge: "Recommandé",
    badgeVariant: "default",
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Sur devis",
    icon: <Building2 className="h-5 w-5" />,
    features: [
      "Tout Pro +",
      "Enregistrements illimités",
      "API illimitée",
      "Membres illimités",
      "SLA garanti",
      "Support dédié",
      "Déploiement on-premise",
    ],
  },
];

interface UsageStat {
  label: string;
  used: number;
  max: number;
  unit: string;
}

const USAGE: UsageStat[] = [
  { label: "Appels API", used: 2847, max: 10000, unit: "appels" },
  { label: "Enregistrements", used: 342, max: 1000, unit: "entrées" },
  { label: "Modules actifs", used: 2, max: 3, unit: "modules" },
];

export default function BillingPage() {
  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-1">Facturation</h2>
        <p className="text-sm text-muted-foreground">
          Gérez votre abonnement et suivez votre utilisation
        </p>
      </div>

      {/* Usage */}
      <div className="rounded-lg border bg-card p-5 space-y-4">
        <h3 className="text-sm font-semibold">Utilisation ce mois</h3>
        <div className="space-y-4">
          {USAGE.map((stat) => {
            const pct = Math.round((stat.used / stat.max) * 100);
            return (
              <div key={stat.label} className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">{stat.label}</span>
                  <span className="font-medium tabular-nums">
                    {stat.used.toLocaleString("fr-FR")} /{" "}
                    {stat.max.toLocaleString("fr-FR")} {stat.unit}
                  </span>
                </div>
                <Progress value={pct} className="h-1.5" />
              </div>
            );
          })}
        </div>
      </div>

      <Separator />

      {/* Plans */}
      <div>
        <h3 className="text-sm font-semibold mb-4">Choisir un plan</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`rounded-xl border p-5 space-y-4 ${
                plan.id === "free"
                  ? "border-primary/30 bg-primary/5"
                  : "bg-card"
              }`}
            >
              {/* Header */}
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <div className="text-muted-foreground">{plan.icon}</div>
                  <span className="font-semibold">{plan.name}</span>
                </div>
                {plan.badge && (
                  <Badge variant={plan.badgeVariant ?? "secondary"} className="text-xs">
                    {plan.badge}
                  </Badge>
                )}
              </div>

              <p className="text-2xl font-bold">{plan.price}</p>

              {/* Features */}
              <ul className="space-y-2">
                {plan.features.map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm">
                    <Check className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                    <span className="text-muted-foreground">{f}</span>
                  </li>
                ))}
              </ul>

              <Button
                variant={plan.id === "free" ? "outline" : "default"}
                size="sm"
                className="w-full"
                disabled={plan.id === "free"}
              >
                {plan.id === "free"
                  ? "Plan actuel"
                  : plan.id === "enterprise"
                  ? "Nous contacter"
                  : "Mettre à niveau"}
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
