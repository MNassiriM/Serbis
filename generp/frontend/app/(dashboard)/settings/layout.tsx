"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const SETTINGS_NAV = [
  { href: "/settings/profile", label: "Profil" },
  { href: "/settings/team", label: "Équipe" },
  { href: "/settings/billing", label: "Facturation" },
  { href: "/settings/integrations", label: "Intégrations" },
  { href: "/settings/security", label: "Sécurité" },
];

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b px-6 py-4 shrink-0">
        <h1 className="text-xl font-semibold">Paramètres</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Gérez votre compte et vos préférences
        </p>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Side nav */}
        <nav className="w-48 border-r px-3 py-4 shrink-0 space-y-0.5">
          {SETTINGS_NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center rounded-md px-3 py-2 text-sm font-medium transition-colors",
                pathname === item.href || pathname.startsWith(item.href + "/")
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Content */}
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
