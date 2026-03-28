"use client";

import { useEffect, useState } from "react";
import {
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { ArrowUpDown, Pencil, Trash2 } from "lucide-react";
import { useAuthStore } from "@/lib/store";
import { createDataApi } from "@/lib/api";
import type { ListViewConfig } from "@/types/erp";

interface ERPDataTableProps {
  config: ListViewConfig;
  apiBase: string;
  tenantId: string;
  onEdit: (id: string) => void;
}

export function ERPDataTable({
  config,
  apiBase,
  tenantId,
  onEdit,
}: ERPDataTableProps) {
  const { token } = useAuthStore();
  const [data, setData] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [sorting, setSorting] = useState<SortingState>([]);

  // Derive entity name from apiBase path
  const entityName = apiBase.split("/").at(-1) ?? "";

  useEffect(() => {
    if (!token) return;
    const api = createDataApi(tenantId, token);
    setLoading(true);
    api
      .list<Record<string, unknown>>(entityName)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [apiBase, tenantId, token, entityName]);

  const handleDelete = async (id: string) => {
    if (!token || !confirm("Supprimer cet enregistrement ?")) return;
    const api = createDataApi(tenantId, token);
    await api.delete(entityName, id);
    setData((prev) => prev.filter((row) => row.id !== id));
  };

  const columns: ColumnDef<Record<string, unknown>>[] = [
    ...config.columns.map(
      (col): ColumnDef<Record<string, unknown>> => ({
        id: col.id,
        accessorKey: col.accessorKey,
        header: ({ column }) =>
          col.sortable ? (
            <button
              className="flex items-center gap-1 hover:text-foreground"
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
      cell: ({ row }) => (
        <div className="flex gap-2 justify-end">
          <button
            onClick={() => onEdit(row.original.id as string)}
            className="rounded p-1 hover:bg-muted text-muted-foreground hover:text-foreground transition-colors"
            title="Modifier"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            onClick={() => handleDelete(row.original.id as string)}
            className="rounded p-1 hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
            title="Supprimer"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: {
      pagination: { pageSize: config.pagination.pageSize },
    },
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-muted-foreground">
        Chargement…
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left font-medium text-muted-foreground"
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
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-8 text-center text-muted-foreground"
                >
                  Aucun enregistrement. Créez le premier !
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-muted/30 transition-colors">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3">
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
        </span>
        <div className="flex gap-2">
          <button
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="px-3 py-1 rounded border disabled:opacity-50 hover:bg-muted transition-colors"
          >
            Précédent
          </button>
          <span className="px-3 py-1">
            Page {table.getState().pagination.pageIndex + 1} /{" "}
            {table.getPageCount()}
          </span>
          <button
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="px-3 py-1 rounded border disabled:opacity-50 hover:bg-muted transition-colors"
          >
            Suivant
          </button>
        </div>
      </div>
    </div>
  );
}

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
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            value ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
          }`}
        >
          {value ? "Oui" : "Non"}
        </span>
      );
    case "currency":
      return (
        <span>
          {new Intl.NumberFormat("fr-FR", {
            style: "currency",
            currency: "EUR",
          }).format(Number(value))}
        </span>
      );
    case "date":
      return (
        <span>
          {new Date(String(value)).toLocaleDateString("fr-FR")}
        </span>
      );
    case "datetime":
      return (
        <span>
          {new Date(String(value)).toLocaleString("fr-FR")}
        </span>
      );
    default:
      return <span>{String(value)}</span>;
  }
}
