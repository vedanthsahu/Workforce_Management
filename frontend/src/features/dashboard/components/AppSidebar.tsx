"use client";

import { useState } from "react";
import { useAuthContext } from "@/features/auth/context/AuthContext";

import { Badge } from "@/components/ui/badge";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar";
import {
  LayoutDashboard,
  CalendarDays,
  BookOpen,
  Monitor,
  CalendarCheck,
  Search,
  Bell,
  Star,
  LogOut,
  MapPin,
  Armchair,
} from "lucide-react";
import { getInitials, type User } from "@/features/auth/types/auth.types";
import { cn } from "@/lib/utils";

// ─── Nav config ───────────────────────────────────────────────────────────────

const MAIN_NAV = [
  { id: "dashboard",  label: "Dashboard",        icon: LayoutDashboard },
  { id: "book",       label: "Book a seat",      icon: CalendarDays },
  { id: "bookings",   label: "My bookings",      icon: BookOpen,   badge: 3,     badgeRed: true },
  { id: "team",       label: "Book for someone", icon: Monitor,    badge: "New", badgeGreen: true },
  { id: "schedule",   label: "My schedule",      icon: CalendarCheck },
];

const OFFICE_NAV = [
  { id: "find", label: "Find teammates", icon: Search },
];

const PERSONAL_NAV = [
  { id: "notifications", label: "Notifications", icon: Bell, badge: 2, badgeRed: true },
  { id: "favourites",    label: "Preferences",   icon: Star },
];

// ─── Props ────────────────────────────────────────────────────────────────────

interface AppSidebarProps {
  user: User | null;
  activeItem?: string;
  onNavigate?: (id: string) => void;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

/** Resolve the best display name from the updated User shape */
function resolveDisplayName(user: User): string {
  return user.display_name ?? user.full_name ?? user.name ?? "Loading...";
}

/** Resolve the subtitle: job title > role > email */
function resolveSubtitle(user: User): string {
  return user.job_title ?? user.role ?? user.email ?? "";
}

/** Resolve location: office_location > home_site_id */
function resolveLocation(user: User): string | null {
  return user.office_location ?? null;
}

/** Resolve the initials for the avatar */
function resolveInitials(user: User): string {
  const name = user.display_name ?? user.full_name ?? user.name;
  return name ? getInitials(name) : (user.email?.[0]?.toUpperCase() ?? "?");
}

// ─── Component ────────────────────────────────────────────────────────────────

export function AppSidebar({ user, activeItem = "dashboard", onNavigate }: AppSidebarProps) {
  const [active, setActive] = useState(activeItem);
  const { state } = useSidebar();
  const { logout } = useAuthContext();
  const isCollapsed = state === "collapsed";

  const initials    = user ? resolveInitials(user) : "?";
  const displayName = user ? resolveDisplayName(user) : "Loading...";
  const displaySub  = user ? resolveSubtitle(user) : "";
  const displayLoc  = user ? resolveLocation(user) : null;

  // New fields
  const daysInOffice  = user?.days_in_office ?? null;
  const favoriteSeat  = user?.favorite_seat ?? null;

  const handleNav = (id: string) => {
    setActive(id);
    onNavigate?.(id);
  };

  return (
    <Sidebar collapsible="icon">
      {/* ── Logo ─────────────────────────────────────────────────────────── */}
      <SidebarHeader className="px-3 py-4">
        <div className={cn("flex items-center gap-2", isCollapsed && "justify-center")}>
          <div className="w-6 h-6 rounded-md bg-indigo-600 flex items-center justify-center shrink-0">
            <BookOpen className="w-3 h-3 text-white" />
          </div>
          {!isCollapsed && (
            <span className="text-[13px] font-semibold text-sidebar-foreground tracking-tight">
              SeatBook
            </span>
          )}
        </div>
      </SidebarHeader>

      <SidebarContent>
        {/* ── Main ─────────────────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupLabel>Main</SidebarGroupLabel>
          <SidebarMenu>
            {MAIN_NAV.map((item) => (
              <SidebarMenuItem key={item.id}>
                <SidebarMenuButton
                  isActive={active === item.id}
                  tooltip={item.label}
                  onClick={() => handleNav(item.id)}
                  className="justify-between"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <item.icon className="w-4 h-4 shrink-0" />
                    <span className="truncate text-[12.5px]">{item.label}</span>
                  </div>
                  {item.badge !== undefined && (
                    <Badge
                      className={cn(
                        "text-[10px] h-[18px] min-w-[18px] px-1.5 rounded-full leading-none font-medium border-0 shrink-0",
                        item.badgeRed   && "bg-red-500 text-white hover:bg-red-500",
                        item.badgeGreen && "bg-emerald-100 text-emerald-700 hover:bg-emerald-100"
                      )}
                    >
                      {item.badge}
                    </Badge>
                  )}
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>

        {/* ── Office ───────────────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupLabel>Office</SidebarGroupLabel>
          <SidebarMenu>
            {OFFICE_NAV.map((item) => (
              <SidebarMenuItem key={item.id}>
                <SidebarMenuButton
                  isActive={active === item.id}
                  tooltip={item.label}
                  onClick={() => handleNav(item.id)}
                >
                  <item.icon className="w-4 h-4 shrink-0" />
                  <span className="truncate text-[12.5px]">{item.label}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>

        {/* ── Personal ─────────────────────────────────────────────────────── */}
        <SidebarGroup>
          <SidebarGroupLabel>Personal</SidebarGroupLabel>
          <SidebarMenu>
            {PERSONAL_NAV.map((item) => (
              <SidebarMenuItem key={item.id}>
                <SidebarMenuButton
                  isActive={active === item.id}
                  tooltip={item.label}
                  onClick={() => handleNav(item.id)}
                  className="justify-between"
                >
                  <div className="flex items-center gap-2.5 min-w-0">
                    <item.icon className="w-4 h-4 shrink-0" />
                    <span className="truncate text-[12.5px]">{item.label}</span>
                  </div>
                  {item.badge !== undefined && (
                    <Badge className="text-[10px] h-[18px] min-w-[18px] px-1.5 rounded-full leading-none font-medium border-0 bg-red-500 text-white hover:bg-red-500 shrink-0">
                      {item.badge}
                    </Badge>
                  )}
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>

      {/* ── User footer ──────────────────────────────────────────────────────── */}
      <SidebarFooter className="px-3 py-4 border-t border-sidebar-border">
        <div className={cn("flex items-center gap-2", isCollapsed && "justify-center")}>
          {/* Avatar */}
          <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-[10px] font-semibold text-indigo-700 shrink-0">
            {initials}
          </div>

          {!isCollapsed && (
            <>
              <div className="flex-1 min-w-0">
                {/* Name */}
                <p className="text-[11.5px] font-medium text-sidebar-foreground truncate leading-tight">
                  {displayName}
                </p>
                
              </div>

              <button
                onClick={logout}
                className="shrink-0 text-sidebar-foreground/40 hover:text-red-500 transition-colors"
                title="Logout"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </>
          )}
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}