"use client";

import { useState } from "react";
import { Shield, Lock, Key, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

export default function SecurityPage() {
  const [passwords, setPasswords] = useState({
    current: "",
    new: "",
    confirm: "",
  });
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    if (passwords.new !== passwords.confirm) {
      alert("Les mots de passe ne correspondent pas");
      return;
    }
    setSaving(true);
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    setPasswords({ current: "", new: "", confirm: "" });
  };

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-1">Sécurité</h2>
        <p className="text-sm text-muted-foreground">
          Gérez la sécurité de votre compte
        </p>
      </div>

      {/* Password */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Lock className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Changer le mot de passe</h3>
        </div>
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label>Mot de passe actuel</Label>
            <Input
              type="password"
              value={passwords.current}
              onChange={(e) =>
                setPasswords((p) => ({ ...p, current: e.target.value }))
              }
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Nouveau mot de passe</Label>
            <Input
              type="password"
              value={passwords.new}
              onChange={(e) =>
                setPasswords((p) => ({ ...p, new: e.target.value }))
              }
              placeholder="••••••••"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Confirmer le mot de passe</Label>
            <Input
              type="password"
              value={passwords.confirm}
              onChange={(e) =>
                setPasswords((p) => ({ ...p, confirm: e.target.value }))
              }
              placeholder="••••••••"
            />
          </div>
          <Button
            onClick={handleSave}
            disabled={saving || !passwords.current || !passwords.new}
            size="sm"
            className="gap-1.5"
          >
            <Lock className="h-4 w-4" />
            {saving ? "Mise à jour…" : "Mettre à jour"}
          </Button>
        </div>
      </div>

      <Separator />

      {/* 2FA */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Authentification à deux facteurs</h3>
        </div>
        <div className="rounded-lg border bg-amber-50/50 dark:bg-amber-950/20 border-amber-200/60 dark:border-amber-800/40 p-4">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-200">
                2FA non activé
              </p>
              <p className="text-xs text-amber-700/80 dark:text-amber-300/80 mt-0.5">
                Activez l&apos;authentification à deux facteurs pour sécuriser davantage votre compte.
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="mt-3 gap-1.5">
            <Shield className="h-4 w-4" />
            Activer la 2FA
          </Button>
        </div>
      </div>

      <Separator />

      {/* API Tokens */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Key className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-semibold">Jetons d&apos;accès API</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Gérez vos jetons d&apos;accès depuis{" "}
          <a
            href="/settings/integrations"
            className="text-primary hover:underline"
          >
            Intégrations → Clés API
          </a>
          .
        </p>
      </div>
    </div>
  );
}
