/**
 * Zustand global stores for GenERP frontend.
 */

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { ChatMessage, ERPModule, ModuleUIConfig, SSEActionEvent } from "@/types/erp";
function uuidv4(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

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

// ---------------------------------------------------------------------------
// UI Store
// ---------------------------------------------------------------------------

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  theme: "light" | "dark" | "system";
  commandPaletteOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSidebarCollapsed: (v: boolean) => void;
  setTheme: (theme: "light" | "dark" | "system") => void;
  setCommandPaletteOpen: (open: boolean) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      sidebarCollapsed: false,
      theme: "system",
      commandPaletteOpen: false,

      toggleSidebar: () =>
        set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      setSidebarOpen: (open) => set({ sidebarOpen: open }),

      setSidebarCollapsed: (v) => set({ sidebarCollapsed: v }),

      setTheme: (theme) => set({ theme }),

      setCommandPaletteOpen: (open) => set({ commandPaletteOpen: open }),
    }),
    {
      name: "generp-ui",
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
);

// ---------------------------------------------------------------------------
// Notification Store
// ---------------------------------------------------------------------------

export interface AppNotification {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  body?: string;
  read: boolean;
  createdAt: Date;
  entity?: string;
  recordId?: string;
  action?: string;
}

interface NotificationState {
  notifications: AppNotification[];
  unreadCount: number;
  addNotification: (
    n: Omit<AppNotification, "id" | "createdAt" | "read">
  ) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  clearNotifications: () => void;
}

export const useNotificationStore = create<NotificationState>()((set) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (n) =>
    set((state) => {
      const notification: AppNotification = {
        ...n,
        id: uuidv4(),
        read: false,
        createdAt: new Date(),
      };
      return {
        notifications: [notification, ...state.notifications],
        unreadCount: state.unreadCount + 1,
      };
    }),

  markAsRead: (id) =>
    set((state) => {
      const notifications = state.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      );
      return {
        notifications,
        unreadCount: notifications.filter((n) => !n.read).length,
      };
    }),

  markAllAsRead: () =>
    set((state) => ({
      notifications: state.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  clearNotifications: () => set({ notifications: [], unreadCount: 0 }),
}));
