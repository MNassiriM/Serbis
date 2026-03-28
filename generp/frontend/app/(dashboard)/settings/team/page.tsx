"use client";

import { useState } from "react";
import { UserPlus, MoreHorizontal, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

type Role = "owner" | "admin" | "manager" | "employee" | "viewer";
type Status = "active" | "pending" | "inactive";

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: Role;
  status: Status;
}

const ROLE_LABELS: Record<Role, string> = {
  owner: "Propriétaire",
  admin: "Administrateur",
  manager: "Manager",
  employee: "Employé",
  viewer: "Observateur",
};

const ROLE_VARIANTS: Record<Role, "default" | "secondary" | "outline"> = {
  owner: "default",
  admin: "default",
  manager: "secondary",
  employee: "secondary",
  viewer: "outline",
};

const STATUS_COLORS: Record<Status, string> = {
  active: "text-emerald-600",
  pending: "text-amber-600",
  inactive: "text-muted-foreground",
};

const MOCK_MEMBERS: TeamMember[] = [
  {
    id: "1",
    name: "Alice Martin",
    email: "alice@exemple.fr",
    role: "owner",
    status: "active",
  },
  {
    id: "2",
    name: "Bob Dupont",
    email: "bob@exemple.fr",
    role: "admin",
    status: "active",
  },
  {
    id: "3",
    name: "Claire Bernard",
    email: "claire@exemple.fr",
    role: "manager",
    status: "active",
  },
  {
    id: "4",
    name: "David Leroy",
    email: "david@exemple.fr",
    role: "employee",
    status: "pending",
  },
];

export default function TeamSettingsPage() {
  const [members, setMembers] = useState<TeamMember[]>(MOCK_MEMBERS);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<Role>("employee");
  const [sending, setSending] = useState(false);

  const handleInvite = async () => {
    if (!inviteEmail) return;
    setSending(true);
    await new Promise((r) => setTimeout(r, 600));
    const newMember: TeamMember = {
      id: String(Date.now()),
      name: inviteEmail.split("@")[0],
      email: inviteEmail,
      role: inviteRole,
      status: "pending",
    };
    setMembers((prev) => [...prev, newMember]);
    setSending(false);
    setInviteOpen(false);
    setInviteEmail("");
  };

  const handleRemove = (id: string) => {
    if (confirm("Retirer ce membre ?")) {
      setMembers((prev) => prev.filter((m) => m.id !== id));
    }
  };

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold mb-1">Équipe</h2>
          <p className="text-sm text-muted-foreground">
            {members.length} membre(s) dans votre organisation
          </p>
        </div>
        <Button onClick={() => setInviteOpen(true)} className="gap-1.5">
          <UserPlus className="h-4 w-4" />
          Inviter un membre
        </Button>
      </div>

      {/* Members list */}
      <div className="rounded-lg border divide-y">
        {members.map((member) => (
          <div
            key={member.id}
            className="flex items-center gap-3 px-4 py-3 hover:bg-muted/30 transition-colors"
          >
            <Avatar className="h-8 w-8 shrink-0">
              <AvatarFallback className="text-xs bg-primary/10 text-primary">
                {member.name
                  .split(" ")
                  .map((w) => w[0])
                  .slice(0, 2)
                  .join("")
                  .toUpperCase()}
              </AvatarFallback>
            </Avatar>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">{member.name}</p>
              <p className="text-xs text-muted-foreground truncate">
                {member.email}
              </p>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <Badge variant={ROLE_VARIANTS[member.role]} className="text-xs">
                {ROLE_LABELS[member.role]}
              </Badge>
              <span
                className={`text-xs font-medium ${STATUS_COLORS[member.status]}`}
              >
                {member.status === "active"
                  ? "Actif"
                  : member.status === "pending"
                  ? "En attente"
                  : "Inactif"}
              </span>
            </div>

            {member.role !== "owner" && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem className="gap-2 cursor-pointer text-sm">
                    <Mail className="h-3.5 w-3.5" />
                    Renvoyer l&apos;invitation
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="gap-2 cursor-pointer text-sm text-destructive focus:text-destructive"
                    onClick={() => handleRemove(member.id)}
                  >
                    Retirer
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        ))}
      </div>

      {/* Invite dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Inviter un membre</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="invite-email">Adresse email</Label>
              <Input
                id="invite-email"
                type="email"
                placeholder="collegue@exemple.fr"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="invite-role">Rôle</Label>
              <select
                id="invite-role"
                value={inviteRole}
                onChange={(e) => setInviteRole(e.target.value as Role)}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              >
                <option value="admin">Administrateur</option>
                <option value="manager">Manager</option>
                <option value="employee">Employé</option>
                <option value="viewer">Observateur</option>
              </select>
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setInviteOpen(false)}
            >
              Annuler
            </Button>
            <Button
              onClick={handleInvite}
              disabled={!inviteEmail || sending}
              className="gap-1.5"
            >
              <Mail className="h-4 w-4" />
              {sending ? "Envoi…" : "Envoyer l'invitation"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
