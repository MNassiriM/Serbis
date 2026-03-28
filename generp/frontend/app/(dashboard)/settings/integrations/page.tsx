"use client";

import { useState } from "react";
import {
  Webhook,
  Key,
  MessageSquare,
  Mail,
  Settings2,
  ToggleLeft,
  ToggleRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  active: boolean;
  category: string;
}

const INTEGRATIONS: Integration[] = [
  {
    id: "webhooks",
    name: "Webhooks",
    description: "Recevez des événements en temps réel via HTTP POST",
    icon: <Webhook className="h-5 w-5" />,
    active: false,
    category: "Développeurs",
  },
  {
    id: "api-keys",
    name: "Clés API",
    description: "Accédez à votre ERP via l'API REST",
    icon: <Key className="h-5 w-5" />,
    active: true,
    category: "Développeurs",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Recevez des notifications dans vos canaux Slack",
    icon: <MessageSquare className="h-5 w-5" />,
    active: false,
    category: "Communication",
  },
  {
    id: "email",
    name: "Email SMTP",
    description: "Envoyez des emails depuis votre propre serveur",
    icon: <Mail className="h-5 w-5" />,
    active: true,
    category: "Communication",
  },
];

export default function IntegrationsPage() {
  const [integrations, setIntegrations] = useState(INTEGRATIONS);

  const toggleIntegration = (id: string) => {
    setIntegrations((prev) =>
      prev.map((i) => (i.id === id ? { ...i, active: !i.active } : i))
    );
  };

  const categories = [...new Set(integrations.map((i) => i.category))];

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-1">Intégrations</h2>
        <p className="text-sm text-muted-foreground">
          Connectez GenERP à vos outils préférés
        </p>
      </div>

      {categories.map((category) => (
        <div key={category}>
          <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
            {category}
          </h3>
          <div className="space-y-3">
            {integrations
              .filter((i) => i.category === category)
              .map((integration) => (
                <div
                  key={integration.id}
                  className="flex items-center gap-4 rounded-lg border bg-card p-4 hover:bg-accent/20 transition-colors"
                >
                  <div className="rounded-lg bg-muted p-2.5 shrink-0 text-muted-foreground">
                    {integration.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium">{integration.name}</p>
                      <Badge
                        variant={integration.active ? "secondary" : "outline"}
                        className={cn(
                          "text-xs",
                          integration.active
                            ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400 border-transparent"
                            : ""
                        )}
                      >
                        {integration.active ? "Actif" : "Inactif"}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {integration.description}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-foreground"
                      title="Configurer"
                    >
                      <Settings2 className="h-4 w-4" />
                    </Button>
                    <button
                      onClick={() => toggleIntegration(integration.id)}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      aria-label={
                        integration.active ? "Désactiver" : "Activer"
                      }
                    >
                      {integration.active ? (
                        <ToggleRight className="h-6 w-6 text-emerald-500" />
                      ) : (
                        <ToggleLeft className="h-6 w-6" />
                      )}
                    </button>
                  </div>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  );
}
