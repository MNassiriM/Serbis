"use client";

import { useState, useEffect } from "react";
import { Package, Plus, Warehouse, Truck, ShoppingCart } from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { createSupplyApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

type SupplyRecord = Record<string, unknown>;

function SimpleTable({
  data,
  loading,
  columns,
  emptyIcon,
}: {
  data: SupplyRecord[];
  loading: boolean;
  columns: { key: string; label: string; render?: (v: unknown) => React.ReactNode }[];
  emptyIcon?: React.ReactNode;
}) {
  if (loading) {
    return (
      <div className="space-y-2">
        {Array.from({ length: 5 }).map((_, i) => (
          <Skeleton key={i} className="h-12 w-full rounded" />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="text-muted-foreground/30 mb-3">
          {emptyIcon ?? <Package className="h-10 w-10" />}
        </div>
        <p className="text-sm text-muted-foreground">Aucun enregistrement</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 border-b">
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                className="px-4 py-3 text-left font-medium text-muted-foreground"
              >
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y">
          {data.map((row, i) => (
            <tr key={String(row.id ?? i)} className="hover:bg-muted/30 transition-colors">
              {columns.map((c) => (
                <td key={c.key} className="px-4 py-3">
                  {c.render ? c.render(row[c.key]) : String(row[c.key] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SupplyPage() {
  const { token } = useAuthStore();
  const [activeTab, setActiveTab] = useState("products");
  const [products, setProducts] = useState<SupplyRecord[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token || activeTab !== "products") return;
    const api = createSupplyApi(token);
    setLoading(true);
    api.products
      .list()
      .then((data) => setProducts(data as SupplyRecord[]))
      .catch(() => setProducts([]))
      .finally(() => setLoading(false));
  }, [token, activeTab]);

  return (
    <div className="flex flex-col h-full">
      <div className="border-b px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-orange-50 dark:bg-orange-950/40 p-2">
            <Package className="h-5 w-5 text-orange-600 dark:text-orange-400" />
          </div>
          <div>
            <h1 className="text-xl font-semibold">Supply Chain</h1>
            <p className="text-xs text-muted-foreground">
              Gérez vos produits, stocks et fournisseurs
            </p>
          </div>
        </div>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Nouveau produit
        </Button>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="px-6 pt-4">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="products">
                Produits
                {products.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 h-4 px-1 text-[10px]">
                    {products.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="stock">Stock</TabsTrigger>
              <TabsTrigger value="suppliers">Fournisseurs</TabsTrigger>
              <TabsTrigger value="orders">Commandes</TabsTrigger>
              <TabsTrigger value="dashboard">Tableau de bord</TabsTrigger>
            </TabsList>

            <div className="mt-4">
              <TabsContent value="products">
                <SimpleTable
                  data={products}
                  loading={loading}
                  columns={[
                    { key: "name", label: "Produit" },
                    { key: "sku", label: "Référence" },
                    {
                      key: "price",
                      label: "Prix",
                      render: (v) =>
                        v != null
                          ? new Intl.NumberFormat("fr-FR", {
                              style: "currency",
                              currency: "EUR",
                            }).format(Number(v))
                          : "—",
                    },
                    {
                      key: "stock",
                      label: "Stock",
                      render: (v) => (
                        <Badge
                          variant={Number(v) > 10 ? "secondary" : "outline"}
                          className={Number(v) <= 5 ? "border-red-300 text-red-600" : ""}
                        >
                          {String(v ?? "—")}
                        </Badge>
                      ),
                    },
                  ]}
                />
              </TabsContent>

              <TabsContent value="stock">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <Warehouse className="h-5 w-5 mr-2" />
                  Gestion du stock — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="suppliers">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <Truck className="h-5 w-5 mr-2" />
                  Fournisseurs — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="orders">
                <div className="flex items-center justify-center h-40 rounded-lg border border-dashed text-muted-foreground text-sm">
                  <ShoppingCart className="h-5 w-5 mr-2" />
                  Commandes — connexion API requise
                </div>
              </TabsContent>

              <TabsContent value="dashboard">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {[
                    { label: "Produits", value: String(products.length), icon: <Package className="h-4 w-4" /> },
                    { label: "Valeur stock", value: "—", icon: <Warehouse className="h-4 w-4" /> },
                    { label: "Commandes en cours", value: "—", icon: <ShoppingCart className="h-4 w-4" /> },
                  ].map((m) => (
                    <div key={m.label} className="rounded-lg border bg-card p-4">
                      <div className="flex items-center gap-2 text-muted-foreground mb-2">
                        {m.icon}
                        <span className="text-xs font-medium uppercase tracking-wider">
                          {m.label}
                        </span>
                      </div>
                      <p className="text-2xl font-bold">{m.value}</p>
                    </div>
                  ))}
                </div>
              </TabsContent>
            </div>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
