"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  DollarSign,
  Users,
  Briefcase,
  Package,
  FolderKanban,
  Settings,
  Bot,
  FilePlus,
  UserPlus,
  FolderPlus,
  MessageSquare,
  BarChart3,
} from "lucide-react";
import { useUIStore, useERPStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";

interface CommandItemDef {
  id: string;
  label: string;
  icon: React.ReactNode;
  href?: string;
  action?: () => void;
  keywords?: string[];
}

export function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen } = useUIStore();
  const { modules } = useERPStore();
  const router = useRouter();

  const aiModules = modules.filter((m) => m.is_active);

  const navigationItems: CommandItemDef[] = [
    {
      id: "nav-home",
      label: "Accueil",
      icon: <LayoutDashboard className="h-4 w-4" />,
      href: "/",
      keywords: ["home", "accueil", "dashboard"],
    },
    {
      id: "nav-setup",
      label: "Assistant IA",
      icon: <Bot className="h-4 w-4" />,
      href: "/setup",
      keywords: ["assistant", "ia", "chat", "setup"],
    },
    {
      id: "nav-finance",
      label: "Finance",
      icon: <DollarSign className="h-4 w-4" />,
      href: "/finance",
      keywords: ["finance", "facture", "paiement", "invoice"],
    },
    {
      id: "nav-crm",
      label: "CRM",
      icon: <Users className="h-4 w-4" />,
      href: "/crm",
      keywords: ["crm", "contact", "client", "pipeline"],
    },
    {
      id: "nav-hr",
      label: "Ressources Humaines",
      icon: <Briefcase className="h-4 w-4" />,
      href: "/hr",
      keywords: ["rh", "hr", "employe", "recrutement"],
    },
    {
      id: "nav-supply",
      label: "Supply Chain",
      icon: <Package className="h-4 w-4" />,
      href: "/supply",
      keywords: ["supply", "stock", "produit", "fournisseur"],
    },
    {
      id: "nav-projects",
      label: "Projets",
      icon: <FolderKanban className="h-4 w-4" />,
      href: "/projects",
      keywords: ["projet", "tache", "task"],
    },
    {
      id: "nav-settings",
      label: "Paramètres",
      icon: <Settings className="h-4 w-4" />,
      href: "/settings",
      keywords: ["parametres", "settings", "config"],
    },
    ...aiModules.map((m) => ({
      id: `nav-ai-${m.name}`,
      label: m.display_name,
      icon: <BarChart3 className="h-4 w-4" />,
      href: `/${m.name}`,
      keywords: [m.name, m.display_name, m.category],
    })),
  ];

  const actionItems: CommandItemDef[] = [
    {
      id: "action-new-invoice",
      label: "Nouvelle facture",
      icon: <FilePlus className="h-4 w-4" />,
      href: "/finance?tab=invoices&action=new",
      keywords: ["nouvelle", "facture", "invoice"],
    },
    {
      id: "action-new-contact",
      label: "Nouveau contact",
      icon: <UserPlus className="h-4 w-4" />,
      href: "/crm?tab=contacts&action=new",
      keywords: ["nouveau", "contact", "crm"],
    },
    {
      id: "action-new-employee",
      label: "Nouvel employé",
      icon: <UserPlus className="h-4 w-4" />,
      href: "/hr?tab=employees&action=new",
      keywords: ["nouvel", "employe", "rh"],
    },
    {
      id: "action-new-project",
      label: "Nouveau projet",
      icon: <FolderPlus className="h-4 w-4" />,
      href: "/projects?action=new",
      keywords: ["nouveau", "projet"],
    },
  ];

  const handleSelect = (item: CommandItemDef) => {
    setCommandPaletteOpen(false);
    if (item.action) {
      item.action();
    } else if (item.href) {
      router.push(item.href);
    }
  };

  const handleAskAssistant = (query: string) => {
    setCommandPaletteOpen(false);
    if (query) {
      router.push(`/setup?q=${encodeURIComponent(query)}`);
    } else {
      router.push("/setup");
    }
  };

  // Close on Escape (handled by backdrop click + keyboard)
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setCommandPaletteOpen(false);
      }
    };
    if (commandPaletteOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  if (!commandPaletteOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[20vh]"
      onClick={() => setCommandPaletteOpen(false)}
    >
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-fade-in" />

      {/* Panel */}
      <div
        className="relative w-full max-w-lg mx-4 rounded-xl border bg-popover shadow-2xl animate-slide-in-down overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <Command>
          <CommandInput placeholder="Rechercher une page, une action…" autoFocus />
          <CommandList>
            <CommandEmpty>
              <div className="py-8 text-center">
                <MessageSquare className="h-8 w-8 mx-auto text-muted-foreground/40 mb-2" />
                <p className="text-sm text-muted-foreground mb-3">Aucun résultat</p>
                <AskAssistantButton onAsk={handleAskAssistant} />
              </div>
            </CommandEmpty>

            {/* Navigation */}
            <CommandGroup heading="Navigation">
              {navigationItems.map((item) => (
                <CommandItem
                  key={item.id}
                  keywords={[item.label, ...(item.keywords ?? [])]}
                  onClick={() => handleSelect(item)}
                  className="flex items-center gap-2.5 cursor-pointer"
                >
                  <span className="text-muted-foreground">{item.icon}</span>
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>

            <CommandSeparator />

            {/* Actions */}
            <CommandGroup heading="Actions rapides">
              {actionItems.map((item) => (
                <CommandItem
                  key={item.id}
                  keywords={[item.label, ...(item.keywords ?? [])]}
                  onClick={() => handleSelect(item)}
                  className="flex items-center gap-2.5 cursor-pointer"
                >
                  <span className="text-muted-foreground">{item.icon}</span>
                  {item.label}
                </CommandItem>
              ))}
            </CommandGroup>

            <CommandSeparator />

            {/* IA */}
            <CommandGroup heading="Intelligence Artificielle">
              <CommandItem
                keywords={["assistant", "ia", "demander", "question"]}
                onClick={() => handleAskAssistant("")}
                className="flex items-center gap-2.5 cursor-pointer"
              >
                <Bot className="h-4 w-4 text-muted-foreground" />
                Demander à l&apos;assistant IA…
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </div>
    </div>
  );
}

function AskAssistantButton({ onAsk }: { onAsk: (q: string) => void }) {
  return (
    <button
      onClick={() => onAsk("")}
      className={cn(
        "inline-flex items-center gap-2 px-3 py-1.5 rounded-md text-sm",
        "border border-dashed border-border text-muted-foreground",
        "hover:border-primary hover:text-foreground transition-colors"
      )}
    >
      <Bot className="h-4 w-4" />
      Demander à l&apos;assistant IA
    </button>
  );
}
