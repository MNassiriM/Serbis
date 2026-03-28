"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  DollarSign,
  MessageSquare,
  Settings,
  Users,
  Briefcase,
  Package,
  FolderKanban,
  ChevronLeft,
  ChevronRight,
  Bot,
} from "lucide-react";
import { useERPStore, useUIStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

// -----------------------------------------------------------------------
// Built-in modules
// -----------------------------------------------------------------------

interface BuiltinModule {
  href: string;
  icon: React.ReactNode;
  label: string;
  accentClass: string;
  activeBg: string;
}

const BUILTIN_MODULES: BuiltinModule[] = [
  {
    href: "/finance",
    icon: <DollarSign className="h-4 w-4" />,
    label: "Finance",
    accentClass: "text-emerald-600 dark:text-emerald-400",
    activeBg: "bg-emerald-50 dark:bg-emerald-950/40",
  },
  {
    href: "/crm",
    icon: <Users className="h-4 w-4" />,
    label: "CRM",
    accentClass: "text-blue-600 dark:text-blue-400",
    activeBg: "bg-blue-50 dark:bg-blue-950/40",
  },
  {
    href: "/hr",
    icon: <Briefcase className="h-4 w-4" />,
    label: "Ressources Humaines",
    accentClass: "text-violet-600 dark:text-violet-400",
    activeBg: "bg-violet-50 dark:bg-violet-950/40",
  },
  {
    href: "/supply",
    icon: <Package className="h-4 w-4" />,
    label: "Supply Chain",
    accentClass: "text-orange-600 dark:text-orange-400",
    activeBg: "bg-orange-50 dark:bg-orange-950/40",
  },
  {
    href: "/projects",
    icon: <FolderKanban className="h-4 w-4" />,
    label: "Projets",
    accentClass: "text-cyan-600 dark:text-cyan-400",
    activeBg: "bg-cyan-50 dark:bg-cyan-950/40",
  },
];

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  finance: <DollarSign className="h-4 w-4" />,
  crm: <Users className="h-4 w-4" />,
  hr: <Briefcase className="h-4 w-4" />,
  supply_chain: <Package className="h-4 w-4" />,
  general: <BarChart3 className="h-4 w-4" />,
};

// -----------------------------------------------------------------------
// NavItem
// -----------------------------------------------------------------------

interface NavItemProps {
  href: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
  collapsed: boolean;
  badge?: number;
  accentClass?: string;
  activeBg?: string;
}

function NavItem({
  href,
  icon,
  label,
  active,
  collapsed,
  badge,
  accentClass = "text-foreground",
  activeBg = "bg-accent",
}: NavItemProps) {
  const content = (
    <Link
      href={href}
      className={cn(
        "relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150 group",
        active
          ? cn("text-foreground", activeBg)
          : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
        collapsed && "justify-center px-2"
      )}
    >
      {/* Active indicator bar */}
      {active && (
        <span
          className={cn(
            "absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full",
            accentClass.replace("text-", "bg-")
          )}
        />
      )}
      <span
        className={cn(
          "shrink-0",
          active ? accentClass : "text-muted-foreground group-hover:text-foreground"
        )}
      >
        {icon}
      </span>
      {!collapsed && (
        <span className="flex-1 truncate">{label}</span>
      )}
      {!collapsed && badge != null && badge > 0 && (
        <Badge
          variant="secondary"
          className="ml-auto h-5 px-1.5 text-xs font-medium min-w-[20px] flex items-center justify-center"
        >
          {badge > 99 ? "99+" : badge}
        </Badge>
      )}
    </Link>
  );

  if (collapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" className="flex items-center gap-2">
          {label}
          {badge != null && badge > 0 && (
            <Badge variant="secondary" className="h-4 px-1 text-xs">
              {badge}
            </Badge>
          )}
        </TooltipContent>
      </Tooltip>
    );
  }

  return content;
}

// -----------------------------------------------------------------------
// Section label
// -----------------------------------------------------------------------

function SectionLabel({ label, collapsed }: { label: string; collapsed: boolean }) {
  if (collapsed) {
    return <div className="my-1 border-t border-border/60 mx-2" />;
  }
  return (
    <div className="px-3 pt-3 pb-1">
      <p className="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-widest">
        {label}
      </p>
    </div>
  );
}

// -----------------------------------------------------------------------
// Sidebar
// -----------------------------------------------------------------------

export function Sidebar() {
  const pathname = usePathname();
  const { modules } = useERPStore();
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore();

  const aiModules = modules.filter((m) => m.is_active);

  return (
    <TooltipProvider delayDuration={200}>
      <aside
        className={cn(
          "flex flex-col h-full bg-sidebar border-r border-sidebar-border transition-all duration-300 shrink-0",
          sidebarCollapsed ? "w-14" : "w-60"
        )}
      >
        {/* Logo + collapse button */}
        <div
          className={cn(
            "flex items-center border-b border-sidebar-border px-3 h-14 shrink-0",
            sidebarCollapsed ? "justify-center" : "justify-between"
          )}
        >
          {!sidebarCollapsed && (
            <Link
              href="/"
              className="flex items-center gap-2 font-semibold text-sm hover:opacity-80 transition-opacity"
            >
              <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shrink-0">
                G
              </div>
              <span>GenERP</span>
            </Link>
          )}
          {sidebarCollapsed && (
            <Link href="/">
              <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">
                G
              </div>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              "h-7 w-7 text-muted-foreground hover:text-foreground",
              sidebarCollapsed && "hidden"
            )}
            onClick={() => setSidebarCollapsed(true)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
        </div>

        {/* Expand button when collapsed */}
        {sidebarCollapsed && (
          <div className="flex justify-center py-2 border-b border-sidebar-border/50">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground hover:text-foreground"
              onClick={() => setSidebarCollapsed(false)}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* Navigation */}
        <ScrollArea className="flex-1 py-2">
          <div className="px-2 space-y-0.5">
            {/* Assistant IA */}
            <NavItem
              href="/setup"
              icon={<Bot className="h-4 w-4" />}
              label="Assistant IA"
              active={pathname === "/setup" || pathname === "/"}
              collapsed={sidebarCollapsed}
            />

            {/* Built-in modules */}
            <SectionLabel label="Modules" collapsed={sidebarCollapsed} />

            {BUILTIN_MODULES.map((mod) => (
              <NavItem
                key={mod.href}
                href={mod.href}
                icon={mod.icon}
                label={mod.label}
                active={pathname.startsWith(mod.href)}
                collapsed={sidebarCollapsed}
                accentClass={mod.accentClass}
                activeBg={mod.activeBg}
              />
            ))}

            {/* AI-generated modules */}
            {aiModules.length > 0 && (
              <>
                <SectionLabel label="Personnalisé" collapsed={sidebarCollapsed} />
                {aiModules.map((module) => (
                  <NavItem
                    key={module.id}
                    href={`/${module.name}`}
                    icon={
                      CATEGORY_ICONS[module.category] ?? (
                        <BarChart3 className="h-4 w-4" />
                      )
                    }
                    label={module.display_name}
                    active={pathname === `/${module.name}`}
                    collapsed={sidebarCollapsed}
                  />
                ))}
              </>
            )}
          </div>
        </ScrollArea>

        {/* Footer */}
        <div className="border-t border-sidebar-border px-2 py-2 space-y-0.5">
          <NavItem
            href="/settings"
            icon={<Settings className="h-4 w-4" />}
            label="Paramètres"
            active={pathname.startsWith("/settings")}
            collapsed={sidebarCollapsed}
          />
        </div>
      </aside>
    </TooltipProvider>
  );
}
