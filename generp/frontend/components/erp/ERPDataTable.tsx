"use client";

import { useEffect, useState, useCallback } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type VisibilityState,
} from "@tanstack/react-table";
import {
  ArrowUpDown,
  Pencil,
  Trash2,
  Download,
  Filter,
  Columns3,
  Database,
  Plus,
} from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { createDataApi } from "@/lib/api";
import type { ListViewConfig } from "@/types/erp";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox-simple";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ERPDataTableProps {
  config: ListViewConfig;
  apiBase: string;
  tenantId: string;
  onEdit: (id: string) => void;
  onCreateNew?: () => void;
}

// ---------------------------------------------------------------------------
// Cell renderer
// ---------------------------------------------------------------------------

function CellRenderer({
  type,
  value,
}: {
  type: string;
  value: unknown;
}): React.ReactElement {
  if (value == null) return <span className="text-muted-foreground">—</span>;

  switch (type) {
    case "boolean":
      return (
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
            value
              ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-400"
              : "bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400"
          )}
        >
          {value ? "Oui" : "Non"}
        </span>
      );
    case "currency":
      return (
        <span className="tabular-nums">
          {new Intl.NumberFormat("fr-FR", {
            style: "currency",
            currency: "EUR",
          }).format(Number(value))}
        </span>
      );
    case "date":
      return (
        <span>{new Date(String(value)).toLocaleDateString("fr-FR")}</span>
      );
    case "datetime":
      return <span>{new Date(String(value)).toLocaleString("fr-FR")}</span>;
    default:
      return <span>{String(value)}</span>;
  }
}

// ---------------------------------------------------------------------------
// Skeleton rows
// ---------------------------------------------------------------------------

function SkeletonRows({ cols }: { cols: number }) {
  return (
    <>
      {Array.from({ length: 8 }).map((_, i) => (
        <tr key={i} className="border-b">
          {Array.from({ length: cols }).map((_, j) => (
            <td key={j} className="px-4 py-3">
              <Skeleton className="h-4 w-full" />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ onCreateNew }: { onCreateNew?: () => void }) {
  return (
    <tr>
      <td colSpan={999}>
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-14 h-14 rounded-full bg-muted flex items-center justify-center mb-4">
            <Database className="h-6 w-6 text-muted-foreground" />
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">
            Aucun enregistrement
          </p>
          <p className="text-xs text-muted-foreground/60 mb-4">
            Créez votre premier enregistrement pour commencer.
          </p>
          {onCreateNew && (
            <Button size="sm" onClick={onCreateNew} className="gap-1.5">
              <Plus className="h-4 w-4" />
              Créer le premier
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// ERPDataTable
// ---------------------------------------------------------------------------

export function ERPDataTable({
  config,
  apiBase,
  tenantId,
  onEdit,
  onCreateNew,
}: ERPDataTableProps) {
  const { token } = useAuthStore();
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [filterOpen, setFilterOpen] = useState(false);
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>({});

  const entityName = apiBase.split("/").at(-1) ?? "";

  const loadData = useCallback(() => {
    if (!token) return;
    const api = createDataApi(tenantId, token);
    setLoading(true);
    api
      .list<Record<string, unknown>>(entityName)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [token, tenantId, entityName]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleDelete = async (id: string) => {
    if (!token || !confirm("Supprimer cet enregistrement ?")) return;
    const api = createDataApi(tenantId, token);
    await api.delete(entityName, id);
    setData((prev) => prev.filter((row) => row.id !== id));
  };

  const handleBulkDelete = async () => {
    const selectedIds = Object.keys(rowSelection).map(
      (idx) => data[parseInt(idx)]?.id as string
    );
    if (!token || !confirm(`Supprimer ${selectedIds.length} enregistrement(s) ?`))
      return;
    const api = createDataApi(tenantId, token);
    await Promise.all(selectedIds.map((id) => api.delete(entityName, id)));
    setData((prev) =>
      prev.filter((row) => !selectedIds.includes(row.id as string))
    );
    setRowSelection({});
  };

  const handleExportCsv = () => {
    const rows = table.getFilteredRowModel().rows;
    const visibleCols = config.columns.filter(
      (c) => columnVisibility[c.id] !== false
    );
    const header = visibleCols.map((c) => c.header).join(",");
    const lines = rows.map((row) =>
      visibleCols
        .map((c) => {
          const val = row.original[c.accessorKey];
          return `"${String(val ?? "").replace(/"/g, '""')}"`;
        })
        .join(",")
    );
    const csv = [header, ...lines].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${entityName}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Apply local column filters
  const filteredData = data.filter((row) => {
    return Object.entries(columnFilters).every(([key, value]) => {
      if (!value) return true;
      const cellVal = String(row[key] ?? "").toLowerCase();
      return cellVal.includes(value.toLowerCase());
    });
  });

  const columns: ColumnDef<Record<string, unknown>>[] = [
    // Select checkbox column
    {
      id: "select",
      header: ({ table }) => (
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() ? "indeterminate" : false)
          }
          onCheckedChange={(v) => table.toggleAllPageRowsSelected(!!v)}
          aria-label="Tout sélectionner"
        />
      ),
      cell: ({ row }) => (
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(v) => row.toggleSelected(!!v)}
          aria-label="Sélectionner la ligne"
          onClick={(e) => e.stopPropagation()}
        />
      ),
      enableSorting: false,
      enableHiding: false,
    },
    ...config.columns.map(
      (col): ColumnDef<Record<string, unknown>> => ({
        id: col.id,
        accessorKey: col.accessorKey,
        header: ({ column }) =>
          col.sortable ? (
            <button
              className="flex items-center gap-1 hover:text-foreground transition-colors"
              onClick={() =>
                column.toggleSorting(column.getIsSorted() === "asc")
              }
            >
              {col.header}
              <ArrowUpDown className="h-3.5 w-3.5" />
            </button>
          ) : (
            col.header
          ),
        cell: ({ getValue }) => (
          <CellRenderer type={col.type} value={getValue()} />
        ),
      })
    ),
    {
      id: "actions",
      header: "",
      enableHiding: false,
      cell: ({ row }) => (
        <div className="flex gap-1 justify-end">
          <button
            onClick={() => onEdit(row.original.id as string)}
            className="rounded p-1.5 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Modifier"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => handleDelete(row.original.id as string)}
            className="rounded p-1.5 hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
            title="Supprimer"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      ),
    },
  ];

  const table = useReactTable({
    data: filteredData,
    columns,
    state: { sorting, rowSelection, columnVisibility },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize: config.pagination.pageSize },
    },
  });

  const selectedCount = Object.keys(rowSelection).length;

  return (
    <div className="space-y-3">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <div className="flex-1" />
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 h-8 text-xs"
          onClick={() => setFilterOpen(true)}
        >
          <Filter className="h-3.5 w-3.5" />
          Filtres
        </Button>

        {/* Column visibility */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm" className="gap-1.5 h-8 text-xs">
              <Columns3 className="h-3.5 w-3.5" />
              Colonnes
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {table
              .getAllColumns()
              .filter((col) => col.getCanHide())
              .map((col) => (
                <DropdownMenuCheckboxItem
                  key={col.id}
                  className="capitalize text-sm"
                  checked={col.getIsVisible()}
                  onCheckedChange={(v) => col.toggleVisibility(!!v)}
                >
                  {config.columns.find((c) => c.id === col.id)?.header ?? col.id}
                </DropdownMenuCheckboxItem>
              ))}
          </DropdownMenuContent>
        </DropdownMenu>

        <Button
          variant="outline"
          size="sm"
          className="gap-1.5 h-8 text-xs"
          onClick={handleExportCsv}
        >
          <Download className="h-3.5 w-3.5" />
          Exporter CSV
        </Button>

        {onCreateNew && (
          <Button size="sm" className="gap-1.5 h-8 text-xs" onClick={onCreateNew}>
            <Plus className="h-3.5 w-3.5" />
            Nouveau
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 border-b">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className={cn(
                      "px-4 py-3 text-left font-medium text-muted-foreground",
                      header.id === "select" && "w-10"
                    )}
                  >
                    {flexRender(
                      header.column.columnDef.header,
                      header.getContext()
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y">
            {loading ? (
              <SkeletonRows cols={columns.length} />
            ) : table.getRowModel().rows.length === 0 ? (
              <EmptyState onCreateNew={onCreateNew} />
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className={cn(
                    "hover:bg-muted/30 transition-colors",
                    row.getIsSelected() && "bg-blue-50/50 dark:bg-blue-950/20"
                  )}
                >
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className={cn(
                        "px-4 py-3",
                        cell.column.id === "select" && "w-10"
                      )}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between text-sm text-muted-foreground">
        <span>
          {table.getFilteredRowModel().rows.length} enregistrement(s)
          {selectedCount > 0 && (
            <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-xs">
              {selectedCount} sélectionné(s)
            </Badge>
          )}
        </span>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="h-7 px-3 text-xs"
          >
            Précédent
          </Button>
          <span className="flex items-center px-2 text-xs">
            Page {table.getState().pagination.pageIndex + 1} /{" "}
            {Math.max(table.getPageCount(), 1)}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="h-7 px-3 text-xs"
          >
            Suivant
          </Button>
        </div>
      </div>

      {/* Bulk action bar */}
      {selectedCount > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 animate-slide-in-down">
          <div className="flex items-center gap-3 bg-foreground text-background rounded-full px-5 py-3 shadow-xl">
            <span className="text-sm font-medium">
              {selectedCount} sélectionné(s)
            </span>
            <div className="h-4 w-px bg-background/20" />
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-3 text-xs text-background hover:bg-background/10 hover:text-background gap-1.5"
              onClick={handleExportCsv}
            >
              <Download className="h-3.5 w-3.5" />
              Exporter ({selectedCount})
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-3 text-xs text-red-400 hover:bg-red-400/10 hover:text-red-300 gap-1.5"
              onClick={handleBulkDelete}
            >
              <Trash2 className="h-3.5 w-3.5" />
              Supprimer ({selectedCount})
            </Button>
          </div>
        </div>
      )}

      {/* Filter Sheet */}
      <Sheet open={filterOpen} onOpenChange={setFilterOpen}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>Filtres</SheetTitle>
          </SheetHeader>
          <div className="mt-6 space-y-4">
            {config.columns.map((col) => (
              <div key={col.id} className="space-y-1.5">
                <label className="text-sm font-medium">{col.header}</label>
                <input
                  type="text"
                  placeholder={`Filtrer ${col.header}…`}
                  value={columnFilters[col.accessorKey] ?? ""}
                  onChange={(e) =>
                    setColumnFilters((prev) => ({
                      ...prev,
                      [col.accessorKey]: e.target.value,
                    }))
                  }
                  className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
            ))}
            <Button
              variant="outline"
              size="sm"
              className="w-full mt-4"
              onClick={() => setColumnFilters({})}
            >
              Réinitialiser les filtres
            </Button>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
