"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { tenantsApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

export default function LoginPage() {
  const router = useRouter();
  const { setAuth } = useAuthStore();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // For MVP: simple tenant creation form (combined register+login)
  const [form, setForm] = useState({
    name: "",
    industry: "",
    size: "1-10" as const,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await tenantsApi.create({
        name: form.name,
        industry: form.industry,
        size: form.size,
      });

      setAuth(result.access_token, result.tenant.id, result.tenant.name);
      router.push("/setup");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de connexion");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-md space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold">GenERP</h1>
          <p className="text-muted-foreground">
            Créez votre ERP personnalisé en quelques minutes
          </p>
        </div>

        <div className="rounded-xl border bg-card p-8 shadow-sm space-y-6">
          <div>
            <h2 className="text-xl font-semibold">Commencer gratuitement</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Aucune carte bancaire requise
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Nom de l&apos;entreprise</label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="Acme SAS"
                className="w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Secteur d&apos;activité</label>
              <input
                type="text"
                required
                value={form.industry}
                onChange={(e) => setForm({ ...form, industry: e.target.value })}
                placeholder="Communication, Retail, Conseil…"
                className="w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-sm font-medium">Taille de l&apos;équipe</label>
              <select
                value={form.size}
                onChange={(e) =>
                  setForm({ ...form, size: e.target.value as typeof form.size })
                }
                className="w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="1-10">1-10 personnes</option>
                <option value="11-50">11-50 personnes</option>
                <option value="51-200">51-200 personnes</option>
                <option value="200+">200+ personnes</option>
              </select>
            </div>

            {error && (
              <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {loading ? "Création en cours…" : "Créer mon ERP →"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
