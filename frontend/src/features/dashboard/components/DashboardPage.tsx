"use client";

import { useDashboard } from "../hooks/useDashboard";
import { useAuthContext } from "@/features/auth/context/AuthContext";
import { AppSidebar } from "./AppSidebar";
import { Button } from "@/components/ui/button";
import {
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import {
  CalendarDays,
  Users,
  Repeat2,
  TriangleAlert,
  Info,
  CircleCheck,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  ExternalLink,
  ChevronRight,
  Building2,
  Star,
} from "lucide-react";
import type {
  Announcement,
  Booking,
  FavouriteSeat,
  TeamMember,
  TodayBookingInfo,
  WeekDay,
} from "../types/dashboard.types";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";

// ─── Hero Banner ──────────────────────────────────────────────────────────────

function HeroBanner({
  userName,
  todayBooking,
  teamInOfficeCount,
  nextBookingDate,
  onCancelToday,
}: {
  userName: string;
  todayBooking: TodayBookingInfo;
  teamInOfficeCount: number;
  nextBookingDate: string;
  onCancelToday: () => void;
}) {
  if (!todayBooking.hasTodayBooking) {
    return (
      <div className="rounded-xl bg-indigo-600 px-5 py-7 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
        <div className="min-w-0">
          <p className="text-white font-semibold text-[20px] leading-snug">
            No seat booked for today, {userName} 👋
          </p>
          <p className="text-indigo-300 text-[11px] mt-0.5 mb-3 leading-snug">
            Your team is mostly in – {teamInOfficeCount} teammate{teamInOfficeCount !== 1 ? "s" : ""} present today
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
              <Users className="w-3 h-3 shrink-0" />
              {teamInOfficeCount} teammate{teamInOfficeCount !== 1 ? "s" : ""} in office
            </span>
            {nextBookingDate !== "—" && (
              <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
                <CalendarDays className="w-3 h-3 shrink-0" />
                Next booking: {nextBookingDate}
              </span>
            )}
          </div>
        </div>
        <Button
          size="sm"
          className="bg-white text-indigo-700 hover:bg-indigo-50 text-[11.5px] font-semibold shrink-0 h-[30px] px-3.5 rounded-lg shadow-none border-0 self-start sm:self-auto"
        >
          Book Now →
        </Button>
      </div>
    );
  }

  return (
    <div className="rounded-xl bg-indigo-600 px-5 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative overflow-hidden">
      <div className="absolute w-40 h-40 rounded-full bg-white/5 -top-14 right-36 pointer-events-none" />
      <div className="absolute w-24 h-24 rounded-full bg-white/[0.04] -bottom-8 right-12 pointer-events-none" />

      <div className="min-w-0 flex flex-col gap-2.5 z-10">
        <p className="text-white font-semibold text-[25px] leading-snug">
          Good morning, {userName} 👋
        </p>
        <p className="text-indigo-300 text-[11px] leading-snug">
          {todayBooking.floor ?? "Office"} · {teamInOfficeCount} teammate{teamInOfficeCount !== 1 ? "s" : ""} in office
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
            <Users className="w-3 h-3 shrink-0" />
            {teamInOfficeCount} teammate{teamInOfficeCount !== 1 ? "s" : ""} in office
          </span>
          {nextBookingDate !== "—" && (
              <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
                <CalendarDays className="w-3 h-3 shrink-0" />
                Next booking: {nextBookingDate}
              </span>
            )}
        </div>
      </div>

      <div className="flex flex-col items-end gap-2 z-10 shrink-0 self-start sm:self-auto">
        <div className="bg-white/10 border border-white/40 rounded-xl px-5 py-2.5 text-center min-w-[80px]">
          <p className="text-indigo-300/60 text-[9px] uppercase tracking-widest mb-1">Seat</p>
          <p className="text-white font-semibold text-[22px] leading-none">{todayBooking.seatCode}</p>
          <p className="text-indigo-300/55 text-[9px] mt-1">{todayBooking.floor ?? "Office"}</p>
        </div>
        <div className="flex gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            className="text-indigo-200/80 hover:bg-white/10 text-[11px] h-[30px] px-3 rounded-lg border border-white/20 shadow-none"
            onClick={onCancelToday}
          >
            Cancel
          </Button>
          <Button
            size="sm"
            className="bg-white text-indigo-700 hover:bg-indigo-50 text-[11px] font-semibold h-[30px] px-3.5 rounded-lg shadow-none border-0"
          >
            Modify →
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Week Strip ───────────────────────────────────────────────────────────────


function WeekStrip({ days }: { days: WeekDay[] }) {
  const todayIdx = days.findIndex((d) => d.isToday);
console.log(days.find(d => d.isToday));
  return (
    <div className="border-gray-100 rounded-xl px-3 py-4 flex items-center gap-2 overflow-x-auto scrollbar-none">
      {days.map((day, idx) => {
        const isYesterdayOrTomorrow =
          todayIdx !== -1 && Math.abs(idx - todayIdx) === 1;

        return (
          <div
            key={`${day.dayLabel}-${day.date}`}
            className={cn(
              "flex flex-col items-center justify-center flex-1 min-w-[44px] h-[62px] rounded-xl cursor-pointer transition-all select-none gap-1 border-2",
              day.isToday
                ? "bg-indigo-600 border-indigo-500"
                : isYesterdayOrTomorrow
                ? "bg-gray-50 border-emerald-200"
                : "bg-gray-50 border-transparent"
            )}
          >
            <span
              className={cn(
                "text-[9px] font-semibold uppercase tracking-wider leading-none",
                day.isToday ? "text-indigo-200" : "text-gray-400"
              )}
            >
              {day.isToday ? "Today" : day.dayLabel}
            </span>
            <span
              className={cn(
                "text-[15px] font-bold leading-none",
                day.isToday ? "text-white" : "text-gray-700"
              )}
            >
              {day.date}
            </span>
            <span
              className={cn(
                "w-[5px] h-[5px] rounded-full",
                day.hasBooking ? "bg-emerald-200" : "bg-red-400"
              )}
              
            />
          </div>
        );
      })}
    </div>
  );
}
// ─── Stat Cards ───────────────────────────────────────────────────────────────

function StatCards({
  daysInOffice,
  trend,
  teamInOffice,
  officeOccupancy,
  occupancyLabel,
}: {
  daysInOffice: number;
  trend: number;
  teamInOffice: number;
  officeOccupancy: number;
  occupancyLabel: string;
}) {
  // Colour the occupancy bar and badge based on traffic level
  const occupancyColor =
    officeOccupancy >= 85
      ? { bar: "bg-red-400", badge: "bg-red-50 text-red-600", accent: "from-red-400" }
      : officeOccupancy >= 50
      ? { bar: "bg-amber-400", badge: "bg-amber-50 text-amber-600", accent: "from-amber-400" }
      : { bar: "bg-violet-400", badge: "bg-violet-50 text-violet-600", accent: "from-violet-400" };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">

      {/* Days in office */}
      <div className="bg-white border border-blue-100 rounded-xl p-3 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-blue-500 to-transparent" />
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Days in office</p>
          <div className="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
            <CalendarDays className="w-3.5 h-3.5 text-blue-500" />
          </div>
        </div>
        <p className="text-[24px] font-bold text-gray-900 leading-none">
          {daysInOffice}
          <span className="text-[12px] font-normal text-gray-400 ml-1">/mo</span>
        </p>
        <p className="text-[10.5px] text-gray-400 mt-1">this month</p>
        {trend !== 0 && (
          <div
            className={cn(
              "inline-flex items-center gap-1 mt-1.5 text-[10.5px] font-medium px-1.5 py-0.5 rounded-md",
              trend > 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"
            )}
          >
            {trend > 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
            <span>{Math.abs(trend)} vs last</span>
          </div>
        )}
      </div>

      {/* Team present */}
      <div className="bg-white border border-emerald-100 rounded-xl p-3 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-emerald-500 to-transparent" />
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Team present</p>
          <div className="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
            <Users className="w-3.5 h-3.5 text-emerald-600" />
          </div>
        </div>
        <p className="text-[24px] font-bold text-gray-900 leading-none">{teamInOffice}</p>
        <p className="text-[10.5px] text-gray-400 mt-1">in office today</p>
      </div>

      {/* Office occupancy — replaces Next Seat */}
      <div className="bg-white border border-violet-100 rounded-xl p-3 relative overflow-hidden col-span-2 sm:col-span-1">
        <div className={cn("absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r to-transparent", occupancyColor.accent)} />
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Office occupancy</p>
          <div className="w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center shrink-0">
            <Building2 className="w-3.5 h-3.5 text-violet-500" />
          </div>
        </div>
        <p className="text-[24px] font-bold text-gray-900 leading-none">
          {officeOccupancy}
          <span className="text-[12px] font-normal text-gray-400 ml-0.5">%</span>
        </p>
        {/* Progress bar */}
        <div className="mt-2 h-[3px] w-full bg-gray-100 rounded-full overflow-hidden">
          <div
            className={cn("h-full rounded-full transition-all duration-500", occupancyColor.bar)}
            style={{ width: `${officeOccupancy}%` }}
          />
        </div>
        <p className={cn("text-[10.5px] font-medium mt-1.5 px-1.5 py-0.5 rounded-md inline-block", occupancyColor.badge)}>
          {occupancyLabel}
        </p>
      </div>

    </div>
  );
}

// ─── Booking Card ─────────────────────────────────────────────────────────────

function BookingCard({
  booking,
  onCancel,
}: {
  booking: Booking;
  onCancel: (id: string) => void;
}) {
  const isConfirmed = booking.status === "Confirmed";

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden flex">
      <div
        className={cn(
          "w-[3px] shrink-0 self-stretch rounded-l-xl",
          isConfirmed ? "bg-emerald-400" : "bg-yellow-400"
        )}
      />
      <div className="flex-1 px-4 py-3.5 min-w-0">
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <p className="text-[12.5px] font-semibold text-gray-900 leading-snug">
            {booking.location} · {booking.floor}
          </p>
          <div className="flex items-center gap-2 shrink-0">
            <span
              className={cn(
                "text-[10px] font-semibold px-2 py-[3px] rounded-md",
                isConfirmed
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-yellow-50 text-yellow-700"
              )}
            >
              {booking.status}
            </span>
            {booking.isRecurring && (
              <span className="inline-flex items-center gap-1 text-[10px] text-gray-400 font-medium">
                <Repeat2 className="w-3 h-3" />
                Recurring
              </span>
            )}
          </div>
        </div>
        <p className="text-[11px] text-gray-400 mt-1 leading-snug">
          Seat {booking.seatId} · {booking.date} · {booking.startTime} – {booking.endTime}
        </p>
        <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-gray-50 gap-2">
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              className="h-[22px] text-[11px] px-2.5 rounded-md border-gray-200 text-gray-600 shadow-none font-normal hover:bg-gray-50"
            >
              Modify
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-[22px] text-[11px] px-2.5 rounded-md text-red-500 hover:text-red-600 hover:bg-red-50 shadow-none font-normal"
              onClick={() => onCancel(booking.id)}
            >
              Cancel
            </Button>
          </div>
        </div>
        {booking.managerNote && (
          <p className="text-[10px] text-gray-400 mt-1.5">{booking.managerNote}</p>
        )}
      </div>
    </div>
  );
}

// ─── Upcoming Bookings ────────────────────────────────────────────────────────

function UpcomingBookings({
  bookings,
  onCancel,
  totalCount,
}: {
  bookings: Booking[];
  onCancel: (id: string) => void;
  totalCount: number;
}) {
  const router = useRouter();

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
        <p className="text-[12.5px] font-semibold text-gray-900">Upcoming bookings</p>
        {totalCount > 2 && (
          <button
            onClick={() => router.push("/bookings")}
            className="text-[11px] text-indigo-600 hover:underline flex items-center gap-0.5"
          >
            View all ({totalCount})
            <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
      <div className="p-3 space-y-2.5">
        {bookings.length === 0 ? (
          <p className="text-[11px] text-gray-400 px-1 py-2">No upcoming bookings.</p>
        ) : (
          bookings.map((b) => (
            <BookingCard key={b.id} booking={b} onCancel={onCancel} />
          ))
        )}
      </div>
    </div>
  );
}

// ─── Team in Office ───────────────────────────────────────────────────────────

function TeamInOffice({
  members,
  inOfficeCount,
  remoteCount,
}: {
  members: TeamMember[];
  inOfficeCount: number;
  remoteCount: number;
}) {
  const floorCounts: Record<string, number> = {};
  for (const m of members) {
    if (m.floor && m.floor !== "—") {
      floorCounts[m.floor] = (floorCounts[m.floor] ?? 0) + 1;
    }
  }
  const topFloor = Object.entries(floorCounts).sort((a, b) => b[1] - a[1])[0]?.[0];

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-50">
        <p className="text-[12.5px] font-semibold text-gray-900">Team in office today</p>
        <span className="text-[11px] text-gray-400">
          {inOfficeCount} in · {remoteCount} remote
        </span>
      </div>
      <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {members.length === 0 ? (
          <p className="text-[11px] text-gray-400 col-span-2 px-1 py-2">
            No teammates in office today.
          </p>
        ) : (
          members.map((m) => (
            <div
              key={m.id}
              className="flex items-center gap-2 bg-gray-50 rounded-lg px-2.5 py-2"
            >
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0"
                style={{ backgroundColor: m.avatarColor || "#E8E8E8", color: "#555" }}
              >
                {m.initials}
              </div>
              <div className="min-w-0">
                <p className="text-[11.5px] font-medium text-gray-800 leading-tight truncate">
                  {m.name}
                </p>
                <p className="text-[10px] text-gray-400 leading-tight">{m.floor}</p>
              </div>
            </div>
          ))
        )}
      </div>
      {topFloor && (
        <div className="px-4 pb-3">
          <p className="text-[10.5px] text-gray-400">
            Most of your team is on{" "}
            <span className="text-indigo-600 font-medium">{topFloor}</span> today.{" "}
            <button className="text-indigo-600 hover:underline">Book nearby →</button>
          </p>
        </div>
      )}
    </div>
  );
}

// ─── Announcements ────────────────────────────────────────────────────────────

const ANNOUNCEMENT_CONFIG: Record<
  string,
  { icon: React.ReactNode; borderColor: string; iconBg: string; iconColor: string }
> = {
  warning: {
    icon: <TriangleAlert className="w-3 h-3" />,
    borderColor: "border-l-amber-400",
    iconBg: "bg-amber-50",
    iconColor: "text-amber-500",
  },
  info: {
    icon: <Info className="w-3 h-3" />,
    borderColor: "border-l-blue-400",
    iconBg: "bg-blue-50",
    iconColor: "text-blue-500",
  },
  success: {
    icon: <CircleCheck className="w-3 h-3" />,
    borderColor: "border-l-emerald-400",
    iconBg: "bg-emerald-50",
    iconColor: "text-emerald-600",
  },
};

// function Announcements({ items }: { items: Announcement[] }) {
//   return (
//     <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
//       <div className="px-4 py-2.5 border-b border-gray-50">
//         <p className="text-[12.5px] font-semibold text-gray-900">Office announcements</p>
//       </div>
//       <div className="px-3 py-3 space-y-2">
//         {items.map((item) => {
//           const cfg = ANNOUNCEMENT_CONFIG[item.type];
//           return (
//             <div
//               key={item.id}
//               className={cn("flex items-start gap-2.5 border-l-2 pl-2.5 py-1", cfg.borderColor)}
//             >
//               <span
//                 className={cn(
//                   "mt-0.5 w-4 h-4 rounded flex items-center justify-center shrink-0",
//                   cfg.iconBg,
//                   cfg.iconColor
//                 )}
//               >
//                 {cfg.icon}
//               </span>
//               <div className="min-w-0">
//                 <p className="text-[11.5px] font-medium text-gray-800 leading-snug">{item.title}</p>
//                 <p className="text-[10.5px] text-gray-400 leading-snug mt-0.5">{item.description}</p>
//               </div>
//             </div>
//           );
//         })}
//       </div>
//     </div>
//   );
// }

// ─── Favourite Seat ───────────────────────────────────────────────────────────

function FavouriteSeatCard({ seat }: { seat: FavouriteSeat | null }) {
  if (!seat) {
    return (
      <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
        <div className="px-4 py-2.5 border-b border-gray-50">
          <p className="text-[12.5px] font-semibold text-gray-900">Favourite seat</p>
        </div>
        <div className="p-3">
          <p className="text-[11px] text-gray-400 px-1 py-2">No favourite seat saved yet.</p>
        </div>
      </div>
    );
  }

  // Derive short label for the avatar (up to 4 chars from seat code)
  const avatarLabel = seat.label.replace(/^seat\s*/i, "").slice(0, 4);

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-50">
        <p className="text-[12.5px] font-semibold text-gray-900">Favourite seat</p>
        <button className="text-[11px] text-indigo-600 hover:underline flex items-center gap-0.5">
          Quick book →
        </button>
      </div>
      <div className="p-3">
        <div className="flex items-center gap-3 bg-indigo-50 border border-indigo-100 rounded-xl px-3 py-2.5">
          <div className="w-10 h-10 rounded-xl bg-orange-400 flex items-center justify-center shrink-0">
            <span className="text-white text-[10px] font-bold leading-none text-center px-0.5">
              {avatarLabel}
            </span>
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <p className="text-[12px] font-semibold text-gray-900 leading-snug">{seat.label}</p>
              <Star className="w-3 h-3 text-amber-400 fill-amber-400 shrink-0" />
            </div>
            <p className="text-[10.5px] text-gray-500 leading-snug">{seat.location}</p>
            <p className="text-[10px] text-gray-400 mt-0.5">{seat.description}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="flex-1 p-4 sm:p-6 space-y-4 animate-pulse">
      <div className="h-[120px] bg-indigo-100 rounded-xl" />
      <div className="h-[82px] bg-gray-100 rounded-xl" />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <div className="h-[100px] bg-blue-50 rounded-xl" />
        <div className="h-[100px] bg-emerald-50 rounded-xl" />
        <div className="h-[100px] bg-violet-50 rounded-xl col-span-2 sm:col-span-1" />
      </div>
      <div className="h-[110px] bg-gray-100 rounded-xl" />
      <div className="h-[110px] bg-gray-100 rounded-xl" />
    </div>
  );
}

// ─── Dashboard Page ───────────────────────────────────────────────────────────

export default function DashboardPage() {
  const {
    data,
    isLoading,
    error,
    refetch,
    visibleBookings,
    totalBookingsCount,
    handleCancelBooking,
    handleCancelToday,
  } = useDashboard();

  const { user } = useAuthContext();
  const currentUser = user ?? data?.user ?? null;

  return (
    <SidebarProvider>
      <div className="flex min-h-screen bg-[#F7F8FA] w-full">
        <AppSidebar user={currentUser} />

        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">

          {/* Top bar */}
          <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-100 sticky top-0 z-10">
            <div className="flex items-center gap-3">
              <SidebarTrigger className="text-gray-400 hover:text-gray-600 -ml-1" />
              <h1 className="text-[14.5px] font-bold text-gray-900">Dashboard</h1>
            </div>
            <button className="text-gray-300 hover:text-gray-500 transition-colors">
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Body */}
          {isLoading ? (
            <DashboardSkeleton />
          ) : error ? (
            <div className="flex-1 flex items-center justify-center p-6">
              <div className="text-center">
                <p className="text-red-500 text-sm mb-3">Failed to load dashboard</p>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => refetch()}
                  className="text-xs"
                >
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Retry
                </Button>
              </div>
            </div>
          ) : data ? (
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">

              <HeroBanner
                userName={currentUser?.name ?? currentUser?.display_name ?? "there"}
                todayBooking={data.todayBooking}
                teamInOfficeCount={data.stats.teamInOffice}
                nextBookingDate={data.nextBookingDate}
                onCancelToday={() => {
                  if (data.todayBooking.bookingId) {
                    handleCancelToday(data.todayBooking.bookingId);
                  }
                }}
              />

              <WeekStrip days={data.weekDays} />

              {/* ↓ Updated: daysInOffice from API, officeOccupancy replaces nextSeat */}
              <StatCards
                daysInOffice={data.daysInOffice}
                trend={data.stats.trend}
                teamInOffice={data.stats.teamInOffice}
                officeOccupancy={data.stats.officeOccupancy}
                occupancyLabel={data.stats.occupancyLabel}
              />

              <div className="flex flex-col lg:flex-row gap-4 lg:gap-5 items-start">

                {/* Left column */}
                <div className="flex-1 min-w-0 w-full space-y-4">
                  <UpcomingBookings
                    bookings={visibleBookings}
                    onCancel={handleCancelBooking}
                    totalCount={totalBookingsCount}
                  />
                  <TeamInOffice
                    members={data.teamInOfficeToday}
                    inOfficeCount={data.stats.teamInOffice}
                    remoteCount={data.stats.teamRemoteCount}
                  />
                </div>

                {/* Right rail */}
                <div className="w-full lg:w-[258px] lg:shrink-0 space-y-4">
                  {/* <Announcements items={data.announcements} /> */}

                  <FavouriteSeatCard seat={data.favouriteSeat} />
                </div>

              </div>
            </div>
          ) : null}
        </main>
      </div>
    </SidebarProvider>
  );
}