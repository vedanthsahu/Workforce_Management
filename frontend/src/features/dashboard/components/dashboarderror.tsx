"use client";

import { AlertTriangle, WifiOff, Lock, RefreshCw, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

import { useRouter } from "next/navigation";
import { DashboardSectionError } from "../services/dashboard.service";

// ─── Fatal Error Screen ───────────────────────────────────────────────────────
// Replaces the entire dashboard body when user/auth fetch fails.

export function FatalErrorScreen({
  error,
  onRetry,
}: {
  error: DashboardSectionError;
  onRetry: () => void;
}) {
  const router = useRouter();
  const isAuth = error.code === "unauthenticated" || error.status === 401;

  return (
    <div className="flex-1 flex items-center justify-center p-6">
      <div className="flex flex-col items-center text-center max-w-[280px] gap-4 animate-fade-in">
        {/* Icon */}
        <div className={cn(
          "w-14 h-14 rounded-2xl flex items-center justify-center",
          isAuth ? "bg-amber-50" : "bg-red-50"
        )}>
          {isAuth
            ? <Lock className="w-6 h-6 text-amber-500" />
            : error.code === "network_error"
            ? <WifiOff className="w-6 h-6 text-red-400" />
            : <AlertTriangle className="w-6 h-6 text-red-400" />
          }
        </div>

        {/* Text */}
        <div className="space-y-1">
          <p className="text-[14px] font-semibold text-gray-900">
            {isAuth ? "Session expired" : "Couldn't load dashboard"}
          </p>
          <p className="text-[12px] text-gray-400 leading-relaxed">{error.message}</p>
          {error.code !== "unauthenticated" && (
            <p className="text-[10.5px] text-gray-300 font-mono mt-1">{error.code}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {isAuth ? (
            <Button
              size="sm"
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-[11.5px] h-[32px] px-4 rounded-xl shadow-sm active:scale-95 transition-all"
              onClick={() => router.push("/login")}
            >
              <LogIn className="w-3.5 h-3.5 mr-1.5" />
              Log in again
            </Button>
          ) : (
            <Button
              size="sm"
              variant="outline"
              className="text-[11.5px] h-[32px] px-4 rounded-xl border-gray-200 hover:bg-gray-50 active:scale-95 transition-all"
              onClick={onRetry}
            >
              <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
              Try again
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Section Error Banner ─────────────────────────────────────────────────────
// Inline notice inside a section when only that section's data failed.
// Sits at the top of the section card, doesn't remove other content.

const SECTION_LABELS: Record<DashboardSectionError["section"], string> = {
  user: "Profile",
  currentBookings: "Today's booking",
  futureBookings: "Upcoming bookings",
  team: "Team data",
};

export function SectionErrorBanner({ errors }: { errors: DashboardSectionError[] }) {
  if (errors.length === 0) return null;

  return (
    <div className="space-y-1.5 animate-fade-in-up">
      {errors.map((err) => (
        <div
          key={err.section}
          className="flex items-start gap-2.5 bg-amber-50 border border-amber-100 rounded-xl px-3 py-2.5"
        >
          <AlertTriangle className="w-3.5 h-3.5 text-amber-500 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <p className="text-[11.5px] font-medium text-amber-800 leading-snug">
              {SECTION_LABELS[err.section]} couldn't load
            </p>
            <p className="text-[10.5px] text-amber-600 mt-0.5 leading-snug">{err.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Empty State placeholder ──────────────────────────────────────────────────
// Use inside a section panel when data is empty due to a soft error.

export function SectionEmptyState({
  icon: Icon,
  label,
}: {
  icon: React.ElementType;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-6 gap-2 text-center">
      <div className="w-9 h-9 rounded-xl bg-gray-50 flex items-center justify-center">
        <Icon className="w-4 h-4 text-gray-300" />
      </div>
      <p className="text-[11px] text-gray-400">{label}</p>
    </div>
  );
}