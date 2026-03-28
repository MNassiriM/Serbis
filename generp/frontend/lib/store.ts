/**
 * Zustand global stores for GenERP frontend.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatMessage, ERPModule, ModuleUIConfig, SSEActionEvent } from "@/types/erp";

// ---------------------------------------------------------------------------
// Auth store
// ---------------------------------------------------------------------------

interface AuthState {
  token: string | null;
  tenantId: string | null;
  tenantName: string | null;
  setAuth: (token: string, tenantId: string, tenantName: string) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      tenantId: null,
      tenantName: null,
      setAuth: (token, tenantId, tenantName) =>
        set({ token, tenantId, tenantName }),
      clearAuth: () => set({ token: null, tenantId: null, tenantName: null }),
    }),
    { name: "generp-auth" }
  )
);

// ---------------------------------------------------------------------------
// Chat store
// ---------------------------------------------------------------------------

interface ChatState {
  messages: ChatMessage[];
  conversationId: string | null;
  isStreaming: boolean;
  pendingSchema: unknown | null;
  addMessage: (message: ChatMessage) => void;
  appendToLastAssistantMessage: (content: string) => void;
  setStreaming: (streaming: boolean) => void;
  setConversationId: (id: string) => void;
  setPendingSchema: (schema: unknown | null) => void;
  addAction: (action: SSEActionEvent) => void;
  clearMessages: () => void;
}

export const useChatStore = create<ChatState>()((set) => ({
  messages: [],
  conversationId: null,
  isStreaming: false,
  pendingSchema: null,

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  appendToLastAssistantMessage: (content) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        messages[messages.length - 1] = { ...last, content: last.content + content };
      }
      return { messages };
    }),

  setStreaming: (streaming) => set({ isStreaming: streaming }),

  setConversationId: (id) => set({ conversationId: id }),

  setPendingSchema: (schema) => set({ pendingSchema: schema }),

  addAction: (action) =>
    set((state) => {
      const messages = [...state.messages];
      const last = messages[messages.length - 1];
      if (last?.role === "assistant") {
        const existingActions = last.actions ?? [];
        messages[messages.length - 1] = {
          ...last,
          actions: [...existingActions, action],
        };
      }
      return { messages };
    }),

  clearMessages: () =>
    set({ messages: [], conversationId: null, pendingSchema: null }),
}));

// ---------------------------------------------------------------------------
// ERP Modules store
// ---------------------------------------------------------------------------

interface ERPState {
  modules: ERPModule[];
  activeModule: string | null;
  setModules: (modules: ERPModule[]) => void;
  addOrUpdateModule: (module: ERPModule) => void;
  setActiveModule: (name: string | null) => void;
  getModuleConfig: (name: string) => ModuleUIConfig | undefined;
}

export const useERPStore = create<ERPState>()((set, get) => ({
  modules: [],
  activeModule: null,

  setModules: (modules) => set({ modules }),

  addOrUpdateModule: (module) =>
    set((state) => {
      const existing = state.modules.findIndex((m) => m.name === module.name);
      if (existing >= 0) {
        const updated = [...state.modules];
        updated[existing] = module;
        return { modules: updated };
      }
      return { modules: [...state.modules, module] };
    }),

  setActiveModule: (name) => set({ activeModule: name }),

  getModuleConfig: (name) => {
    const module = get().modules.find((m) => m.name === name);
    return module?.ui_config as ModuleUIConfig | undefined;
  },
}));
