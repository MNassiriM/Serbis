"use client";

import { useState } from "react";
import { Building2, Upload, Save } from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const PLAN_LABELS: Record<string, { label: string; variant: "default" | "secondary" | "outline" }> = {
  free: { label: "Gratuit", variant: "secondary" },
  pro: { label: "Pro", variant: "default" },
  enterprise: { label: "Enterprise", variant: "outline" },
};

export default function ProfileSettingsPage() {
  const { tenantName } = useAuthStore();
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const [form, setForm] = useState({
    name: tenantName ?? "",
    industry: "",
    size: "11-50",
  });

  const handleSave = async () => {
    setSaving(true);
    // Simulate save
    await new Promise((r) => setTimeout(r, 800));
    setSaving(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const plan = "free"; // Would come from auth store
  const planInfo = PLAN_LABELS[plan] ?? PLAN_LABELS.free;

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h2 className="text-lg font-semibold mb-1">Profil de l&apos;entreprise</h2>
        <p className="text-sm text-muted-foreground">
          Informations générales sur votre organisation
        </p>
      </div>

      {/* Logo upload */}
      <div className="flex items-center gap-5">
        <div className="w-16 h-16 rounded-xl bg-primary/10 flex items-center justify-center text-2xl font-bold text-primary border-2 border-dashed border-primary/30">
          {form.name?.[0]?.toUpperCase() ?? "G"}
        </div>
        <div>
          <Button variant="outline" size="sm" className="gap-1.5">
            <Upload className="h-4 w-4" />
            Changer le logo
          </Button>
          <p className="text-xs text-muted-foreground mt-1.5">
            PNG, JPG jusqu&apos;à 2Mo
          </p>
        </div>
      </div>

      <Separator />

      {/* Form fields */}
      <div className="space-y-5">
        <div className="space-y-1.5">
          <Label htmlFor="name">Nom de l&apos;entreprise</Label>
          <Input
            id="name"
            value={form.name}
            onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            placeholder="Mon Entreprise SARL"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="industry">Secteur d&apos;activité</Label>
          <Input
            id="industry"
            value={form.industry}
            onChange={(e) =>
              setForm((p) => ({ ...p, industry: e.target.value }))
            }
            placeholder="Technologie, Commerce, Services…"
          />
        </div>

        <div className="space-y-1.5">
          <Label htmlFor="size">Taille de l&apos;entreprise</Label>
          <select
            id="size"
            value={form.size}
            onChange={(e) =>
              setForm((p) => ({ ...p, size: e.target.value }))
            }
            className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="1-10">1 – 10 employés</option>
            <option value="11-50">11 – 50 employés</option>
            <option value="51-200">51 – 200 employés</option>
            <option value="200+">200+ employés</option>
          </select>
        </div>
      </div>

      <Separator />

      {/* Plan info */}
      <div className="rounded-lg border bg-card p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Building2 className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">Plan actuel</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Votre abonnement GenERP
              </p>
            </div>
          </div>
          <Badge variant={planInfo.variant}>{planInfo.label}</Badge>
        </div>
      </div>

      {/* Save button */}
      <div className="flex gap-3">
        <Button onClick={handleSave} disabled={saving} className="gap-1.5">
          <Save className="h-4 w-4" />
          {saving ? "Enregistrement…" : saved ? "Enregistré !" : "Sauvegarder"}
        </Button>
      </div>
    </div>
  );
}
