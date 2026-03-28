"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuthStore } from "@/lib/store";
import { createDataApi } from "@/lib/api";
import type { FormConfig } from "@/types/erp";

interface ERPFormProps {
  config: FormConfig;
  apiBase: string;
  editingId: string | null;
  onSuccess: () => void;
  onCancel: () => void;
}

export function ERPForm({
  config,
  apiBase,
  editingId,
  onSuccess,
  onCancel,
}: ERPFormProps) {
  const { token } = useAuthStore();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Build a basic Zod schema from the JSON Schema
  const zodSchema = buildZodSchema(config.json_schema);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm({ resolver: zodResolver(zodSchema) });

  // Extract entity name from apiBase
  const entityName = apiBase.split("/").at(-1) ?? "";
  const tenantId = apiBase.split("/")[4] ?? "";

  // Load existing data if editing
  useEffect(() => {
    if (!editingId || !token) return;
    const api = createDataApi(tenantId, token);
    api
      .get<Record<string, unknown>>(entityName, editingId)
      .then((data) => reset(data))
      .catch(console.error);
  }, [editingId, token, entityName, tenantId, reset]);

  const onSubmit = async (data: Record<string, unknown>) => {
    if (!token) return;
    setSubmitting(true);
    setError(null);

    const api = createDataApi(tenantId, token);
    try {
      if (editingId) {
        await api.update(entityName, editingId, data);
      } else {
        await api.create(entityName, data);
      }
      reset();
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setSubmitting(false);
    }
  };

  const properties = config.json_schema.properties as Record<
    string,
    { type: string; title: string; description?: string }
  >;
  const requiredFields = (config.json_schema.required as string[]) ?? [];

  return (
    <div className="max-w-2xl mx-auto">
      <div className="rounded-lg border bg-card p-6 shadow-sm">
        <h2 className="text-lg font-semibold mb-6">{config.title}</h2>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
          {Object.entries(properties).map(([fieldName, fieldSchema]) => (
            <FormField
              key={fieldName}
              name={fieldName}
              schema={fieldSchema}
              required={requiredFields.includes(fieldName)}
              register={register}
              error={errors[fieldName]?.message as string | undefined}
              uiSchema={
                config.ui_schema[fieldName] as
                  | Record<string, string>
                  | undefined
              }
            />
          ))}

          {error && (
            <div className="rounded-md bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {submitting
                ? "Enregistrement…"
                : editingId
                ? "Mettre à jour"
                : "Créer"}
            </button>
            <button
              type="button"
              onClick={onCancel}
              className="flex-1 rounded-md border px-4 py-2 text-sm font-medium hover:bg-muted transition-colors"
            >
              Annuler
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface FormFieldProps {
  name: string;
  schema: { type: string; title: string; description?: string };
  required: boolean;
  register: ReturnType<typeof useForm>["register"];
  error?: string;
  uiSchema?: Record<string, string>;
}

function FormField({
  name,
  schema,
  required,
  register,
  error,
  uiSchema,
}: FormFieldProps) {
  const widget = uiSchema?.["ui:widget"];
  const isTextarea = widget === "textarea" || schema.type === "text";

  return (
    <div className="space-y-1.5">
      <label className="text-sm font-medium leading-none">
        {schema.title}
        {required && <span className="text-destructive ml-1">*</span>}
      </label>

      {schema.type === "boolean" ? (
        <input
          type="checkbox"
          {...register(name)}
          className="h-4 w-4 rounded border"
        />
      ) : isTextarea ? (
        <textarea
          {...register(name)}
          rows={3}
          className="w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
        />
      ) : (
        <input
          type={schema.type === "integer" || schema.type === "number" ? "number" : widget === "date" ? "date" : "text"}
          {...register(name)}
          className="w-full rounded-md border px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
        />
      )}

      {schema.description && (
        <p className="text-xs text-muted-foreground">{schema.description}</p>
      )}
      {error && <p className="text-xs text-destructive">{error}</p>}
    </div>
  );
}

/**
 * Convert a JSON Schema to a Zod schema for basic validation.
 * For production, use @rjsf/validator-ajv8 with full JSON Schema validation.
 */
function buildZodSchema(jsonSchema: Record<string, unknown>): z.ZodTypeAny {
  const properties = (jsonSchema.properties as Record<
    string,
    { type: string; title: string }
  >) ?? {};
  const required = (jsonSchema.required as string[]) ?? [];

  const shape: Record<string, z.ZodTypeAny> = {};

  for (const [key, field] of Object.entries(properties)) {
    let schema: z.ZodTypeAny;

    switch (field.type) {
      case "integer":
      case "number":
        schema = z.coerce.number();
        break;
      case "boolean":
        schema = z.coerce.boolean();
        break;
      default:
        schema = z.string();
    }

    if (!required.includes(key)) {
      shape[key] = schema.optional();
    } else {
      shape[key] = schema;
    }
  }

  return z.object(shape);
}
