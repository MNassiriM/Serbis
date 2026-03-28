"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Search,
  Moon,
  Sun,
  Monitor,
  LogOut,
  Settings,
  User,
  ChevronRight,
} from "lucide-react";
import { useAuthStore, useUIStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { NotificationCenter } from "./NotificationCenter";

// -----------------------------------------------------------------------
// Breadcrumb helper
// -----------------------------------------------------------------------

const ROUTE_LABELS: Record<string, string> = {
  setup: "Assistant IA",
  finance: "Finance",
  crm: "CRM",
  hr: "Ressources Humaines",
  supply: "Supply Chain",
  projects: "Projets",
  settings: "Paramètres",
  profile: "Profil",
  team: "Équipe",
  billing: "Facturation",
  integrations: "Intégrations",
  security: "Sécurité",
};

function Breadcrumb() {
  const pathname = usePathname();
  const parts = pathname.split("/").filter(Boolean);

  if (parts.length === 0) {
    return <span className="text-sm text-muted-foreground">Accueil</span>;
  }

  return (
    <nav className="flex items-center gap-1.5 text-sm">
      <Link
        href="/"
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        Accueil
      </Link>
      {parts.map((part, i) => {
        const href = "/" + parts.slice(0, i + 1).join("/");
        const label = ROUTE_LABELS[part] ?? part.charAt(0).toUpperCase() + part.slice(1);
        const isLast = i === parts.length - 1;
        return (
          <React.Fragment key={href}>
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
            {isLast ? (
              <span className="font-medium text-foreground">{label}</span>
            ) : (
              <Link
                href={href}
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {label}
              </Link>
            )}
          </React.Fragment>
        );
      })}
    </nav>
  );
}

// -----------------------------------------------------------------------
// TopBar
// -----------------------------------------------------------------------

export function TopBar() {
  const { tenantName, clearAuth } = useAuthStore();
  const { theme, setTheme, setCommandPaletteOpen } = useUIStore();
  const router = useRouter();

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  const initials = tenantName
    ? tenantName
        .split(" ")
        .slice(0, 2)
        .map((w) => w[0])
        .join("")
        .toUpperCase()
    : "G";

  const nextTheme: Record<string, "light" | "dark" | "system"> = {
    light: "dark",
    dark: "system",
    system: "light",
  };

  const themeIcon = {
    light: <Sun className="h-4 w-4" />,
    dark: <Moon className="h-4 w-4" />,
    system: <Monitor className="h-4 w-4" />,
  }[theme];

  return (
    <header className="h-14 border-b bg-background/95 backdrop-blur sticky top-0 z-50 flex items-center px-4 gap-4">
      {/* Left: branding */}
      <div className="flex items-center gap-2 min-w-0">
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold text-sm hover:opacity-80 transition-opacity shrink-0"
        >
          <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">
            G
          </div>
          <span className="hidden sm:block truncate max-w-[160px]">
            {tenantName ?? "GenERP"}
          </span>
        </Link>
      </div>

      {/* Center: breadcrumb */}
      <div className="flex-1 flex items-center justify-center min-w-0 hidden md:flex">
        <Breadcrumb />
      </div>

      {/* Right: actions */}
      <div className="flex items-center gap-1 ml-auto">
        {/* Search / Command Palette */}
        <Button
          variant="ghost"
          size="sm"
          className="hidden sm:flex items-center gap-2 text-muted-foreground hover:text-foreground h-8 px-3 text-xs border border-border/60 rounded-md"
          onClick={() => setCommandPaletteOpen(true)}
        >
          <Search className="h-3.5 w-3.5" />
          <span>Rechercher…</span>
          <kbd className="pointer-events-none ml-1 hidden h-5 select-none items-center gap-1 rounded border bg-muted px-1.5 font-mono text-[10px] font-medium opacity-100 sm:flex">
            ⌘K
          </kbd>
        </Button>

        <Button
          variant="ghost"
          size="icon"
          className="sm:hidden h-8 w-8"
          onClick={() => setCommandPaletteOpen(true)}
        >
          <Search className="h-4 w-4" />
        </Button>

        {/* Notifications */}
        <NotificationCenter />

        {/* Theme toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setTheme(nextTheme[theme])}
          title={`Thème: ${theme}`}
        >
          {themeIcon}
        </Button>

        {/* User dropdown */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "h-8 w-8 rounded-full ring-offset-background",
                "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              )}
            >
              <Avatar className="h-7 w-7">
                <AvatarFallback className="text-xs bg-primary text-primary-foreground">
                  {initials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-48">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">
                  {tenantName ?? "Utilisateur"}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  Administrateur
                </p>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link href="/settings/profile" className="flex items-center gap-2 cursor-pointer">
                <User className="h-4 w-4" />
                Profil
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings" className="flex items-center gap-2 cursor-pointer">
                <Settings className="h-4 w-4" />
                Paramètres
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive cursor-pointer flex items-center gap-2"
              onClick={handleLogout}
            >
              <LogOut className="h-4 w-4" />
              Déconnexion
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
