"use client";

import * as React from "react";
import { Bell, Info, CheckCircle, AlertTriangle, XCircle, X } from "lucide-react";
import { useNotificationStore, type AppNotification } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";

// -----------------------------------------------------------------------
// Relative time helper
// -----------------------------------------------------------------------

function relativeTime(date: Date): string {
  const now = Date.now();
  const diff = now - new Date(date).getTime();
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(diff / 3600000);
  const days = Math.floor(diff / 86400000);

  if (minutes < 1) return "À l'instant";
  if (minutes < 60) return `il y a ${minutes}min`;
  if (hours < 24) return `il y a ${hours}h`;
  return `il y a ${days}j`;
}

// -----------------------------------------------------------------------
// Notification icon by type
// -----------------------------------------------------------------------

const TYPE_ICONS: Record<AppNotification["type"], React.ReactNode> = {
  info: <Info className="h-4 w-4 text-blue-500" />,
  success: <CheckCircle className="h-4 w-4 text-emerald-500" />,
  warning: <AlertTriangle className="h-4 w-4 text-amber-500" />,
  error: <XCircle className="h-4 w-4 text-red-500" />,
};

// -----------------------------------------------------------------------
// NotificationItem
// -----------------------------------------------------------------------

function NotificationItem({
  notification,
  onRead,
}: {
  notification: AppNotification;
  onRead: (id: string) => void;
}) {
  return (
    <div
      className={cn(
        "flex gap-3 px-4 py-3 border-b border-border/50 last:border-0 transition-colors",
        !notification.read
          ? "bg-blue-50/50 dark:bg-blue-950/20 hover:bg-blue-50 dark:hover:bg-blue-950/30"
          : "hover:bg-muted/40"
      )}
      onClick={() => !notification.read && onRead(notification.id)}
      role="button"
      tabIndex={0}
    >
      <div className="shrink-0 mt-0.5">{TYPE_ICONS[notification.type]}</div>
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-sm leading-snug",
            !notification.read ? "font-semibold text-foreground" : "font-medium text-foreground/80"
          )}
        >
          {notification.title}
        </p>
        {notification.body && (
          <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">
            {notification.body}
          </p>
        )}
        <p className="text-[11px] text-muted-foreground/60 mt-1">
          {relativeTime(notification.createdAt)}
        </p>
      </div>
      {!notification.read && (
        <div className="shrink-0 mt-1.5 w-2 h-2 rounded-full bg-blue-500" />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------
// NotificationCenter
// -----------------------------------------------------------------------

export function NotificationCenter() {
  const [open, setOpen] = React.useState(false);
  const { notifications, unreadCount, markAsRead, markAllAsRead } =
    useNotificationStore();

  const panelRef = React.useRef<HTMLDivElement>(null);

  // Close on outside click
  React.useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    if (open) {
      document.addEventListener("mousedown", handleClick);
    }
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  return (
    <div ref={panelRef} className="relative">
      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 relative"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full ring-2 ring-background" />
        )}
      </Button>

      {open && (
        <div
          className={cn(
            "absolute right-0 top-full mt-2 w-80 rounded-xl border bg-popover shadow-xl z-50",
            "animate-slide-in-down"
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold">Notifications</h3>
              {unreadCount > 0 && (
                <Badge variant="secondary" className="h-5 px-1.5 text-xs">
                  {unreadCount}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1">
              {unreadCount > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 text-xs text-muted-foreground hover:text-foreground"
                  onClick={markAllAsRead}
                >
                  Tout marquer lu
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6"
                onClick={() => setOpen(false)}
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>

          {/* Content */}
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center px-4">
              <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
                <Bell className="h-5 w-5 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium text-muted-foreground">
                Aucune notification
              </p>
              <p className="text-xs text-muted-foreground/60 mt-1">
                Vous êtes à jour !
              </p>
            </div>
          ) : (
            <ScrollArea className="max-h-80">
              {notifications.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onRead={markAsRead}
                />
              ))}
            </ScrollArea>
          )}
        </div>
      )}
    </div>
  );
}
