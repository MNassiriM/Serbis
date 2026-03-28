"use client";

import { notFound } from "next/navigation";
import { use } from "react";
import { ERPRenderer } from "@/components/erp/ERPRenderer";
import { useAuthStore, useERPStore } from "@/lib/store";

interface ModulePageProps {
  params: Promise<{ module: string }>;
}

export default function ModulePage({ params }: ModulePageProps) {
  const { module: moduleName } = use(params);
  const { tenantId } = useAuthStore();
  const { getModuleConfig } = useERPStore();

  const config = getModuleConfig(moduleName);

  if (!config || !tenantId) {
    return notFound();
  }

  return (
    <div className="h-full">
      <ERPRenderer
        moduleConfig={config}
        tenantId={tenantId}
        moduleName={moduleName}
      />
    </div>
  );
}
