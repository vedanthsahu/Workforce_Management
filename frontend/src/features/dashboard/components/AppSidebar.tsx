"use client";

import { useRouter, usePathname } from "next/navigation";
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
} from "lucide-react";
import { getInitials, type User } from "@/features/auth/types/auth.types";
import { cn } from "@/lib/utils";

// ─── Route map ────────────────────────────────────────────────────────────────

const ROUTE_MAP: Record<string, string> = {
  dashboard:     "/dashboard",
  book:          "/book",
  mybookings:    "/mybookings",
  team:          "/team",
  schedule:      "/schedule",
  find:          "/find",
  notifications: "/notifications",
  favourites:    "/favourites",
};

// ─── Nav config ───────────────────────────────────────────────────────────────

const MAIN_NAV = [
  { id: "dashboard",  label: "Dashboard",        icon: LayoutDashboard },
  { id: "book",       label: "Book a seat",      icon: CalendarDays },
  { id: "mybookings", label: "My bookings",      icon: BookOpen,   badge: 3,     badgeRed: true },
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

// ─── Props — activeItem & onNavigate removed ──────────────────────────────────

interface AppSidebarProps {
  user: User | null;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function resolveDisplayName(user: User): string {
  return user.display_name ?? user.full_name ?? user.name ?? "Loading...";
}

function resolveSubtitle(user: User): string {
  return user.job_title ?? user.role ?? user.email ?? "";
}

function resolveInitials(user: User): string {
  const name = user.display_name ?? user.full_name ?? user.name;
  return name ? getInitials(name) : (user.email?.[0]?.toUpperCase() ?? "?");
}

// ─── Logout Dialog ────────────────────────────────────────────────────────────

function LogoutDialog({
  open,
  displayName,
  initials,
  onConfirm,
  onCancel,
  isLoggingOut,
}: {
  open: boolean;
  displayName: string;
  initials: string;
  onConfirm: () => void;
  onCancel: () => void;
  isLoggingOut: boolean;
}) {
  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-50 bg-black/30 backdrop-blur-[2px] animate-fade-in"
        onClick={onCancel}
      />

      {/* Dialog */}
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
        <div className="pointer-events-auto bg-white rounded-2xl shadow-2xl shadow-black/10 w-full max-w-[320px] overflow-hidden animate-dialog-in">

          {/* Top section */}
          <div className="px-5 pt-6 pb-5 flex flex-col items-center text-center gap-3">
            {/* Avatar with ring pulse */}
            <div className="relative">
              <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center text-[14px] font-semibold text-indigo-700 ring-4 ring-indigo-50">
                {initials}
              </div>
              <div className="absolute -bottom-0.5 -right-0.5 w-4 h-4 rounded-full bg-emerald-400 border-2 border-white" />
            </div>

            <div className="space-y-1">
              <p className="text-[14px] font-semibold text-gray-900">Sign out?</p>
              <p className="text-[12px] text-gray-400 leading-relaxed">
               Are you sure you want to sign out of your account?
              </p>
            </div>
          </div>

          {/* Divider */}
          <div className="h-px bg-gray-100 mx-5" />

          {/* Actions */}
          <div className="px-5 py-4 flex  gap-2">
            <button
              onClick={onConfirm}
              disabled={isLoggingOut}
              className={cn(
                "w-full h-[38px] rounded-xl text-[12.5px] font-semibold transition-all duration-150",
                "bg-red-500 text-white hover:bg-red-600 active:scale-[0.98]",
                "flex items-center justify-center gap-2",
                "disabled:opacity-70 disabled:cursor-not-allowed disabled:scale-100",
              )}
            >
              {isLoggingOut ? (
                <>
                  <svg className="w-3.5 h-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4l3-3-3-3v4a8 8 0 100 16v-4l-3 3 3 3v-4a8 8 0 01-8-8z" />
                  </svg>
                  Signing out…
                </>
              ) : (
                <>
                  <LogOut className="w-3.5 h-3.5" />
                  Yes, sign out
                </>
              )}
            </button>

            <button
              onClick={onCancel}
              disabled={isLoggingOut}
              className="w-full h-[38px] rounded-xl text-[12.5px] font-medium text-gray-600 bg-gray-100 hover:bg-gray-200 active:scale-[0.98] transition-all duration-150 disabled:opacity-50"
            >
              Stay signed in
            </button>
          </div>

        </div>
      </div>
    </>
  );
}
// ─── Component ────────────────────────────────────────────────────────────────

export function AppSidebar({ user }: AppSidebarProps) {
  const router   = useRouter();
  const pathname = usePathname();                        // ← active state from URL

  const [showLogout,  setShowLogout]  = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const { state } = useSidebar();
  const { logout } = useAuthContext();
  const isCollapsed = state === "collapsed";

  const initials    = user ? resolveInitials(user)    : "?";
  const displayName = user ? resolveDisplayName(user) : "Loading...";
  const displaySub  = user ? resolveSubtitle(user)    : "";

  // Derive active item from current URL — no prop needed
  const activeItem = Object.entries(ROUTE_MAP).find(
    ([, path]) => pathname.startsWith(path)
  )?.[0] ?? "dashboard";

  const handleNav = (id: string) => {
    const path = ROUTE_MAP[id];
    if (path) router.push(path);
  };

  const handleLogoutConfirm = async () => {
    setIsLoggingOut(true);
    await new Promise((r) => setTimeout(r, 700));
    logout();
  };

  return (
    <>
      <LogoutDialog
        open={showLogout}
        displayName={displayName}
        initials={initials}
        onConfirm={handleLogoutConfirm}
        onCancel={() => setShowLogout(false)}
        isLoggingOut={isLoggingOut}
      />

      <Sidebar collapsible="icon">
        {/* Logo */}
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
          {/* Main */}
          <SidebarGroup>
            <SidebarGroupLabel>Main</SidebarGroupLabel>
            <SidebarMenu>
              {MAIN_NAV.map((item) => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton
                    isActive={activeItem === item.id}
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
                          item.badgeGreen && "bg-emerald-100 text-emerald-700 hover:bg-emerald-100",
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

          {/* Office */}
          <SidebarGroup>
            <SidebarGroupLabel>Office</SidebarGroupLabel>
            <SidebarMenu>
              {OFFICE_NAV.map((item) => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton
                    isActive={activeItem === item.id}
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

          {/* Personal */}
          <SidebarGroup>
            <SidebarGroupLabel>Personal</SidebarGroupLabel>
            <SidebarMenu>
              {PERSONAL_NAV.map((item) => (
                <SidebarMenuItem key={item.id}>
                  <SidebarMenuButton
                    isActive={activeItem === item.id}
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

        {/* User footer */}
        <SidebarFooter className="px-3 py-4 border-t border-sidebar-border">
          <div className={cn("flex items-center gap-2 relative", isCollapsed && "justify-center")}>
            <div className="relative shrink-0">
              <div className="w-7 h-7 rounded-full bg-indigo-100 flex items-center justify-center text-[10px] font-semibold text-indigo-700">
                {initials}
              </div>
              <div className="absolute -bottom-px -right-px w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-white" />
            </div>

            {!isCollapsed && (
              <>
                <div className="flex-1 min-w-0">
                  <p className="text-[11.5px] font-medium text-sidebar-foreground truncate leading-tight">
                    {displayName}
                  </p>
                  {displaySub && (
                    <p className="text-[10px] text-sidebar-foreground/50 truncate leading-tight mt-0.5">
                      {displaySub}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => setShowLogout(true)}
                  className="shrink-0 w-6 h-6 rounded-md flex items-center justify-center text-sidebar-foreground/40 hover:text-red-500 hover:bg-red-50 transition-all duration-150 active:scale-90"
                  title="Sign out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </>
            )}

            {isCollapsed && (
              <button
                onClick={() => setShowLogout(true)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                title="Sign out"
              />
            )}
          </div>
        </SidebarFooter>
      </Sidebar>
    </>
  );
}