"use client";

import { useState } from "react";
import { useDashboard } from "../hooks/useDashboard";
import { cancelBooking } from "../services/dashboard.service";
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
  MapPin,
  Repeat2,
  TriangleAlert,
  Info,
  CircleCheck,
  RefreshCw,
  ArrowUp,
  ArrowDown,
  Star,
  ExternalLink,
  ChevronRight,
  LayoutGrid,
  Clock,
} from "lucide-react";
import type { Announcement, Booking, TeamMember } from "../types/dashboard.types";
import { cn } from "@/lib/utils";

// ─── Hero Banner ──────────────────────────────────────────────────────────────

// function HeroBanner({
//   userName,
//   nextBookingDate,
// }: {
//   userName: string;
//   nextBookingDate: string;
// }) {
//   return (
//     <div className="rounded-xl bg-indigo-600 px-5 py-7 flex flex-col sm:flex-row sm:items-center justify-between gap-3 sm:gap-4">
//       <div className="min-w-0">
//         <p className="text-white font-semibold text-[20px] leading-snug">
//           No seat booked for today, {userName} 👋
//         </p>
//         <p className="text-indigo-300 text-[11px] mt-0.5 mb-3 leading-snug">
//           Your team is mostly in – SF, Floor 7 – 4 teammates present
//         </p>
//         <div className="flex items-center gap-2 flex-wrap">
//           <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
//             <Users className="w-3 h-3 shrink-0" />
//             4 teammates in office
//           </span>
//           <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
//             <CalendarDays className="w-3 h-3 shrink-0" />
//             Next booking: {nextBookingDate}
//           </span>
//         </div>
//       </div>
//       <Button
//         size="sm"
//         className="bg-white text-indigo-700 hover:bg-indigo-50 text-[11.5px] font-semibold shrink-0 h-[30px] px-3.5 rounded-lg shadow-none border-0 self-start sm:self-auto"
//       >
//         Book Now →
//       </Button>
//     </div>
//   );
// }
function HeroBanner({ userName }: { userName: string }) {
  return (
    <div className="rounded-xl bg-indigo-600 px-5 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 relative overflow-hidden">
      {/* Background orbs */}
      <div className="absolute w-40 h-40 rounded-full bg-white/5 -top-14 right-36 pointer-events-none" />
      <div className="absolute w-24 h-24 rounded-full bg-white/[0.04] -bottom-8 right-12 pointer-events-none" />

      {/* Left */}
      <div className="min-w-0 flex flex-col gap-2.5 z-10">
        <p className="text-white font-semibold text-[25px] leading-snug">
          Good morning, {userName}👋
        </p>
        <p className="text-indigo-300 text-[11px] leading-snug">
          SF HQ · Floor 2 · 4 teammates in office
        </p>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
            <Users className="w-3 h-3 shrink-0" />
            4 teammates in office
          </span>
          {/* <span className="inline-flex items-center gap-1.5 bg-indigo-500/50 text-indigo-100 text-[10.5px] font-medium px-2.5 py-[5px] rounded-full">
            <Clock className="w-3 h-3 shrink-0" />
            9:00 AM – 6:00 PM
          </span> */}
        </div>
      </div>

      {/* Right */}
      <div className="flex flex-col items-end gap-2 z-10 shrink-0 self-start sm:self-auto">
        <div className="bg-white/10 border border-white/40 rounded-xl px-5 py-2.5 text-center min-w-[80px]">
          <p className="text-indigo-300/60 text-[9px] uppercase tracking-widest mb-1">Seat</p>
          <p className="text-white font-semibold text-[22px] leading-none">A-12</p>
          <p className="text-indigo-300/55 text-[9px] mt-1">Floor 2 · Window</p>
        </div>
        <div className="flex gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            className="text-indigo-200/80 hover:bg-white/10 text-[11px] h-[30px] px-3 rounded-lg border border-white/20 shadow-none"
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

function WeekStrip() {
  const today = 16;

  const days = [
    { date: 13, label: "SUN" },
    { date: 14, label: "MON" },
    { date: 15, label: "WED" },
    { date: 16, label: "THU" },
    { date: 17, label: "FRI" },
    { date: 18, label: "SAT" },
    { date: 19, label: "SUN" },
  ];

  return (
    <div className=" border-gray-100 rounded-xl px-3 py-4 flex items-center gap-2 overflow-x-auto scrollbar-none">
      {days.map((day) => {
        const isToday = day.date === today;
        const isAdjacent = day.date === today - 1 || day.date === today + 1;
        const isFaded = !isToday && !isAdjacent;

        return (
          <div
            key={day.date}
            className={cn(
              "flex flex-col items-center justify-center flex-1 min-w-[44px] h-[62px] rounded-xl cursor-pointer transition-all select-none gap-1 border",
              isToday
                ? "bg-indigo-600 border-indigo-600 shadow-sm"
                : isAdjacent
                ? "bg-white border-gray-200"
                : "bg-gray-50 border-gray-100 opacity-40"
            )}
          >
            <span className={cn(
              "text-[9px] font-semibold uppercase tracking-wider leading-none",
              isToday ? "text-indigo-200" : "text-gray-400"
            )}>
              {isToday ? "Today" : day.label}
            </span>

            <span className={cn(
              "text-[15px] font-bold leading-none",
              isToday ? "text-white" : "text-gray-700"
            )}>
              {day.date}
            </span>

            {/* Dot */}
            <span className={cn(
              "w-[5px] h-[5px] rounded-full",
              isToday
                ? "bg-red-400"
                : isAdjacent
                ? "bg-emerald-400"
                : "bg-transparent"
            )} />
          </div>
        );
      })}
    </div>
  );
}


function StatCards({
  daysInMonth, trend, teamInOffice, nextSeat, nextSeatFloor,
}: {
  daysInMonth: number;
  trend: number;
  teamInOffice: number;
  nextSeat: string;
  nextSeatFloor: string;
}) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">

      {/* ── Days in office ── blue tint */}
      {/* <div className="bg-white border border-blue-100 border-t-[3px] border-l-[3px] border-t-blue-500 rounded-xl p-3"> */}
      <div className="bg-white border border-blue-100 rounded-xl p-3 relative overflow-hidden">
  <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-blue-500 to-transparent" />
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Days in office</p>
          <div className="w-7 h-7 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
            <CalendarDays className="w-3.5 h-3.5 text-blue-500" />
          </div>
        </div>
        <p className="text-[24px] font-bold text-gray-900 leading-none">{daysInMonth}
          <span className="text-[12px] font-normal text-gray-400 ml-1">/mo</span>
        </p>
        <p className="text-[10.5px] text-gray-400 mt-1">this month</p>
        <div className={cn("inline-flex items-center gap-1 mt-1.5 text-[10.5px] font-medium px-1.5 py-0.5 rounded-md", trend > 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500")}>
          {trend > 0 ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
          <span>+{Math.abs(trend)} vs last</span>
        </div>
      </div>

      {/* ── Team present ── green tint */}
      {/* <div className="bg-white border border-emerald-100 border-t-[3px] border-l-[3px] border-t-emerald-500  rounded-xl p-3"> */}
      <div className="bg-white border border-emerald-100 rounded-xl p-3 relative overflow-hidden">
  <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-emerald-500 to-transparent" />
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Team present</p>
          <div className="w-7 h-7 rounded-lg bg-emerald-100 flex items-center justify-center shrink-0">
            <Users className="w-3.5 h-3.5 text-emerald-600" />
          </div>
        </div>
        <p className="text-[24px] font-bold text-gray-900 leading-none">{teamInOffice}</p>
        <p className="text-[10.5px] text-gray-400 mt-1">of 6 in office today</p>
      </div>

      {/* ── Fav seat ── violet tint — spans 2 cols on mobile */}
      {/* <div className="bg-white border border-violet-100 border-t-[3px] border-l-[3px] border-t-violet-500  rounded-xl p-3 col-span-2 sm:col-span-1"> */}
      <div className="bg-white border border-violet-100 rounded-xl p-3 relative overflow-hidden col-span-2 sm:col-span-1">
  <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-violet-500 to-transparent" />
        <div className="flex items-center justify-between mb-2">
          <p className="text-[11px] text-gray-500 font-medium uppercase tracking-wide">Fav. seat</p>
          <div className="w-7 h-7 rounded-lg bg-violet-100 flex items-center justify-center shrink-0">
            <LayoutGrid className="w-3.5 h-3.5 text-violet-500" />
          </div>
        </div>
        <p className="text-[24px] font-bold text-gray-900 leading-none">{nextSeat}</p>
        <p className="text-[10.5px] text-gray-400 mt-1">{nextSeatFloor}</p>
      </div>

    </div>
  );
}

// ─── Booking Card ─────────────────────────────────────────────────────────────
// Each booking is its own white card with a 3px green left accent border.
// Row 1: bold title (location · floor) + status badge + recurring tag
// Row 2: seat id · date/time in muted text
// Divider
// Row 3: Modify | Cancel buttons (left) + View details (right)
// Optional footer: "Manager booked · SF HQ Sprint Day"

function BookingCard({ booking, onCancel }: { booking: Booking; onCancel: (id: string) => void }) {
  const isConfirmed = booking.status === "Confirmed";

  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden flex">
      {/* Left accent strip — 3px wide, full height */}
      <div className={cn("w-[3px] shrink-0 self-stretch rounded-l-xl", isConfirmed ? "bg-emerald-400" : "bg-yellow-400")} />

      <div className="flex-1 px-4 py-3.5 min-w-0">

        {/* ── Row 1: location + badges ── */}
        <div className="flex items-start justify-between gap-2 flex-wrap">
          <p className="text-[12.5px] font-semibold text-gray-900 leading-snug">
            {booking.location} · {booking.floor}
          </p>
          <div className="flex items-center gap-2 shrink-0">
            {/* Status badge */}
            <span className={cn(
              "text-[10px] font-semibold px-2 py-[3px] rounded-md",
              isConfirmed ? "bg-emerald-50 text-emerald-700" : "bg-yellow-50 text-yellow-700"
            )}>
              {booking.status}
            </span>
            {/* Recurring tag */}
            {booking.isRecurring && (
              <span className="inline-flex items-center gap-1 text-[10px] text-gray-400 font-medium">
                <Repeat2 className="w-3 h-3" />
                Recurring · Thu
              </span>
            )}
          </div>
        </div>

        {/* ── Row 2: seat · date · time ── */}
        <p className="text-[11px] text-gray-400 mt-1 leading-snug">
          Seat {booking.seatId ?? "B-04"} · {booking.date} · {booking.startTime} – {booking.endTime}
        </p>

        {/* ── Divider + actions ── */}
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
          {/* <button className="text-[11px] text-indigo-600 hover:underline shrink-0">
            View details
          </button> */}
        </div>

        {/* ── Optional manager note ── */}
        {booking.managerNote && (
          <p className="text-[10px] text-gray-400 mt-1.5">
            {booking.managerNote}
          </p>
        )}
      </div>
    </div>
  );
}

function UpcomingBookings({ bookings, onCancel }: { bookings: Booking[]; onCancel: (id: string) => void }) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      {/* Section header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100">
        <p className="text-[12.5px] font-semibold text-gray-900">Upcoming bookings</p>
        <button className="text-[11px] text-indigo-600 hover:underline flex items-center gap-0.5">
          View all <ChevronRight className="w-3 h-3" />
        </button>
      </div>

      {/* Booking cards list */}
      <div className="p-3 space-y-2.5">
        {bookings.map((b) => (
          <BookingCard key={b.id} booking={b} onCancel={onCancel} />
        ))}

        <p className="text-[10.5px] text-gray-400 px-1">
          Manager booked · SF HQ Sprint Day
        </p>
      </div>
    </div>
  );
}

// ─── Team in Office ───────────────────────────────────────────────────────────

function TeamInOffice({ members }: { members: TeamMember[] }) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-50">
        <p className="text-[12.5px] font-semibold text-gray-900">Team in office today</p>
        <span className="text-[11px] text-gray-400">4 in · 2 remote</span>
      </div>
      <div className="p-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {members.map((m) => (
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
              <p className="text-[11.5px] font-medium text-gray-800 leading-tight truncate">{m.name}</p>
              <p className="text-[10px] text-gray-400 leading-tight">{m.floor}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="px-4 pb-3">
        <p className="text-[10.5px] text-gray-400">
          Most of your team is on{" "}
          <span className="text-indigo-600 font-medium">Floor 2</span> today.{" "}
          <button className="text-indigo-600 hover:underline">Book nearby →</button>
        </p>
      </div>
    </div>
  );
}

// ─── Announcements ────────────────────────────────────────────────────────────
// Each announcement has a coloured left-bordered row (not icon badge).
// warning → amber left border + amber icon
// info    → blue left border + blue icon
// success → green left border + green icon

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

function Announcements({ items }: { items: Announcement[] }) {
  return (
    <div className="bg-white border border-gray-100 rounded-xl overflow-hidden">
      <div className="px-4 py-2.5 border-b border-gray-50">
        <p className="text-[12.5px] font-semibold text-gray-900">Office announcements</p>
      </div>
      <div className="px-3 py-3 space-y-2">
        {items.map((item) => {
          const cfg = ANNOUNCEMENT_CONFIG[item.type];
          return (
            <div
              key={item.id}
              className={cn(
                "flex items-start gap-2.5 border-l-2 pl-2.5 py-1",
                cfg.borderColor
              )}
            >
              <span className={cn("mt-0.5 w-4 h-4 rounded flex items-center justify-center shrink-0", cfg.iconBg, cfg.iconColor)}>
                {cfg.icon}
              </span>
              <div className="min-w-0">
                <p className="text-[11.5px] font-medium text-gray-800 leading-snug">{item.title}</p>
                <p className="text-[10.5px] text-gray-400 leading-snug mt-0.5">{item.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Favourite Seat ───────────────────────────────────────────────────────────
// Orange/amber seat badge, indigo-50 card background, "Quick book →" link.

function FavouriteSeatCard() {
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
          {/* Orange seat badge */}
          <div className="w-10 h-10 rounded-xl bg-orange-400 flex items-center justify-center shrink-0">
            <span className="text-white text-[11px] font-bold leading-none">A-12</span>
          </div>
          <div className="min-w-0">
            <p className="text-[12px] font-semibold text-gray-900 leading-snug">Seat A-12</p>
            <p className="text-[10.5px] text-gray-500 leading-snug">
              Floor 3 · SF HQ · Window seat ☀
            </p>
            <p className="text-[10px] text-gray-400 mt-0.5">
              Booked ·{" "}
              <button className="text-indigo-600 hover:underline">Create another</button>
            </p>
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
      <div className="h-[76px] bg-indigo-100 rounded-xl" />
      <div className="h-[50px] bg-gray-100 rounded-xl" />
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
  const { data, isLoading, error } = useDashboard();
  const { user } = useAuthContext();
  const [bookings, setBookings] = useState<Booking[]>([]);

  const handleCancelBooking = async (id: string) => {
    await cancelBooking(id);
    const source = bookings.length > 0 ? bookings : data?.upcomingBookings ?? [];
    setBookings(source.filter((b) => b.id !== id));
  };

  const displayBookings = bookings.length > 0 ? bookings : data?.upcomingBookings ?? [];
  const currentUser = user ?? data?.user ?? null;

  return (
    <SidebarProvider>
      <div className="flex min-h-screen bg-[#F7F8FA] w-full">

        <AppSidebar user={currentUser} />

        <main className="flex-1 flex flex-col min-w-0 overflow-hidden">

          {/* ── Top bar ─────────────────────────────────────────────────────── */}
          <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-100 sticky top-0 z-10">
            <div className="flex items-center gap-3">
              <SidebarTrigger className="text-gray-400 hover:text-gray-600 -ml-1" />
              <h1 className="text-[14.5px] font-bold text-gray-900">Dashboard</h1>
            </div>
            <button className="text-gray-300 hover:text-gray-500 transition-colors">
              <ExternalLink className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* ── Body ────────────────────────────────────────────────────────── */}
          {isLoading ? (
            <DashboardSkeleton />
          ) : error ? (
            <div className="flex-1 flex items-center justify-center p-6">
              <div className="text-center">
                <p className="text-red-500 text-sm mb-3">Failed to load dashboard</p>
                <Button size="sm" variant="outline" onClick={() => window.location.reload()} className="text-xs">
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Retry
                </Button>
              </div>
            </div>
          ) : data ? (
            <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">

              <HeroBanner
                userName={currentUser?.name ?? "there"}
               
              />

              <WeekStrip />
              <StatCards
                    daysInMonth={data.stats.daysInMonth}
                    trend={data.stats.trend}
                    teamInOffice={data.stats.teamInOffice}
                    nextSeat={data.stats.nextSeat}
                    nextSeatFloor={data.stats.nextSeatFloor}
                  />

              {/* Responsive two-column layout */}
              <div className="flex flex-col lg:flex-row gap-4 lg:gap-5 items-start">

                {/* Left column */}
                <div className="flex-1 min-w-0 w-full space-y-4">
                  
                  <UpcomingBookings bookings={displayBookings} onCancel={handleCancelBooking} />
                  <TeamInOffice members={data.teamInOfficeToday} />
                </div>

                {/* Right rail */}
                <div className="w-full lg:w-[258px] lg:shrink-0 space-y-4">
                  <Announcements items={data.announcements} />
                  <FavouriteSeatCard />
                </div>

              </div>
            </div>
          ) : null}
        </main>
      </div>
    </SidebarProvider>
  );
}