"use client";

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
} from "lucide-react";
import { useERPStore } from "@/lib/store";

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  finance: <DollarSign className="h-4 w-4" />,
  crm: <Users className="h-4 w-4" />,
  hr: <Briefcase className="h-4 w-4" />,
  supply_chain: <Package className="h-4 w-4" />,
  general: <BarChart3 className="h-4 w-4" />,
};

export function ERPNavigation() {
  const pathname = usePathname();
  const { modules } = useERPStore();

  const activeModules = modules.filter((m) => m.is_active);

  return (
    <nav className="flex flex-col h-full bg-sidebar border-r">
      {/* Logo */}
      <div className="px-4 py-5 border-b">
        <span className="text-lg font-bold tracking-tight">GenERP</span>
      </div>

      {/* Navigation links */}
      <div className="flex-1 overflow-y-auto py-4 space-y-1 px-2">
        {/* Chat */}
        <NavItem
          href="/setup"
          icon={<MessageSquare className="h-4 w-4" />}
          label="Assistant IA"
          active={pathname === "/setup" || pathname === "/"}
        />

        {/* Separator if modules exist */}
        {activeModules.length > 0 && (
          <div className="py-2">
            <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Modules ERP
            </p>
          </div>
        )}

        {/* Dynamic ERP modules */}
        {activeModules.map((module) => (
          <NavItem
            key={module.id}
            href={`/${module.name}`}
            icon={CATEGORY_ICONS[module.category] ?? <BarChart3 className="h-4 w-4" />}
            label={module.display_name}
            active={pathname === `/${module.name}`}
          />
        ))}
      </div>

      {/* Settings footer */}
      <div className="px-2 py-4 border-t">
        <NavItem
          href="/settings"
          icon={<Settings className="h-4 w-4" />}
          label="Paramètres"
          active={pathname === "/settings"}
        />
      </div>
    </nav>
  );
}

interface NavItemProps {
  href: string;
  icon: React.ReactNode;
  label: string;
  active: boolean;
}

function NavItem({ href, icon, label, active }: NavItemProps) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
        active
          ? "bg-primary text-primary-foreground"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      }`}
    >
      {icon}
      {label}
    </Link>
  );
}
