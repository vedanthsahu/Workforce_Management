"use client";

import React, { useState } from "react";
import { Booking, BookingTab } from "../types/bookings.types";
import { useBookings } from "../hooks/useBookings";
import { AppSidebar } from "@/features/dashboard/components/AppSidebar";
import { useAuthContext } from "@/features/auth/context/AuthContext";
import { SidebarProvider } from "@/components/ui/sidebar";
import { cn } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  // Append T00:00:00 so it's treated as local time, not UTC midnight
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
}

function isUpcoming(isoDate: string): boolean {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return new Date(isoDate + "T00:00:00") >= today;
}

// ── Tag chip ──────────────────────────────────────────────────────────────────

interface TagProps { label: string; variant: string; }

const TAG_STYLES: Record<string, string> = {
  confirmed: "bg-[#E8F5E9] text-[#2E7D32] border border-[#A5D6A7]",
  manager:   "bg-[#E3F2FD] text-[#1565C0] border border-[#90CAF9]",
  zone:      "bg-[#F3E5F5] text-[#6A1B9A] border border-[#CE93D8]",
  sprint:    "bg-[#FFF8E1] text-[#F57F17] border border-[#FFE082]",
  recurring: "bg-[#E8EAF6] text-[#283593] border border-[#9FA8DA]",
};

const BookingTagChip: React.FC<TagProps> = ({ label, variant }) => (
  <span className={cn(
    "inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11px] font-medium whitespace-nowrap",
    TAG_STYLES[variant] ?? TAG_STYLES.zone
  )}>
    {label}
  </span>
);

// ── Booking card ──────────────────────────────────────────────────────────────

interface BookingCardProps {
  booking: Booking;
  onCancel: (id: string) => Promise<void>;
  showActions?: boolean;
}

const BookingCard: React.FC<BookingCardProps> = ({ booking, onCancel, showActions = true }) => {
  const [cancelling, setCancelling] = useState(false);

  const handleCancel = async () => {
    if (!window.confirm("Cancel this booking?")) return;
    setCancelling(true);
    try { await onCancel(booking.id); }
    finally { setCancelling(false); }
  };

  const isCancelled = booking.status === "cancelled";

  return (
    <div className="bg-white border border-[#EBEBF5] rounded-xl overflow-hidden flex flex-col hover:shadow-sm transition-shadow duration-200">
      <div className="flex items-stretch">
        {/* Left accent bar */}
        <div className={cn(
          "w-[3px] shrink-0",
          isCancelled   ? "bg-gray-200"  :
          booking.status === "pending" ? "bg-amber-400" : "bg-indigo-500"
        )} />

        <div className="flex-1 px-5 py-4">
          {/* Row 1: title + booked-on */}
          <div className="flex justify-between items-start gap-4">
            <div>
              <p className="text-[13.5px] font-semibold text-[#1A1A2E]">
                {booking.location} · {booking.floor} · Seat {booking.seat}
              </p>
              <p className="text-[12px] text-gray-500 mt-0.5">
                {formatDate(booking.date)}
                {" · "}
                {booking.isFullDay
                  ? "Full day"
                  : `${booking.startTime} – ${booking.endTime}`}
                {booking.isFullDay && (
                  <span className="ml-2 text-[11px] bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">
                    Full day
                  </span>
                )}
              </p>
            </div>
            <span className="text-[11px] text-gray-400 whitespace-nowrap mt-0.5">
              Booked {booking.bookedOn}
            </span>
          </div>

          {/* Row 2: tags */}
          <div className="flex gap-1.5 flex-wrap mt-2.5 ">
            {booking.tags.map((tag, i) => (
              <BookingTagChip key={i} label={tag.label} variant={tag.variant} />
            ))}
            {booking.isRecurring && booking.recurringPattern && (
              <BookingTagChip label={booking.recurringPattern} variant="recurring" />
            )}
          </div>
        </div>
      </div>

      {/* Action footer */}
      {showActions && !isCancelled && (
        <div className="flex justify-end gap-2 px-5 py-2.5 border-t border-gray-100 bg-[#F7F8FC]">
          <button className="px-4 py-1.5 rounded-lg border border-gray-200 bg-white text-[12.5px] font-medium text-gray-600 hover:bg-gray-50 transition-colors">
            Modify
          </button>
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="px-4 py-1.5 rounded-lg border border-red-200 bg-red-50 text-[12.5px] font-medium text-red-500 hover:bg-red-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {cancelling ? "Cancelling…" : "Cancel"}
          </button>
        </div>
      )}

      {showActions && isCancelled && (
        <div className="flex justify-end px-5 py-2.5 border-t border-gray-100">
          <button className="px-4 py-1.5 rounded-lg border border-gray-200 bg-white text-[12.5px] font-medium text-gray-600 hover:bg-gray-50 transition-colors">
            View details
          </button>
        </div>
      )}
    </div>
  );
};

// ── Stat card ─────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: number | string;
  subLabel?: string;
  icon: React.ReactNode;
  accentClass: string;
}

const StatCard: React.FC<StatCardProps> = ({ label, value, subLabel, icon, accentClass }) => (
  <div className={cn(
    "flex-1 bg-white border border-[#EBEBF5] rounded-xl p-4 flex flex-col gap-1 min-w-[160px]",
    "border-l-[3px]", accentClass
  )}>
    <div className="flex justify-between items-center mb-1">
      <span className="text-[10px] font-semibold tracking-widest uppercase text-gray-400">
        {label}
      </span>
      <span className="text-gray-400">{icon}</span>
    </div>
    <div className="text-[26px] font-bold text-[#1A1A2E] leading-none">{value}</div>
    {subLabel && (
      <div className="text-[11.5px] text-gray-400 mt-1">{subLabel}</div>
    )}
  </div>
);

// ── Tabs ──────────────────────────────────────────────────────────────────────

const TABS: { id: BookingTab; label: string }[] = [
  { id: "upcoming",  label: "Upcoming"  },
  { id: "past",      label: "Past"      },
  { id: "recurring", label: "Recurring" },
  { id: "cancelled", label: "Cancelled" },
];

// ── Icons ─────────────────────────────────────────────────────────────────────

const CalIcon = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
    <rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" />
  </svg>
);
const CheckIcon = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" viewBox="0 0 24 24">
    <path d="M5 13l4 4L19 7" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
const RepeatIcon = () => (
  <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24">
    <path d="M17 2l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M3 11V9a4 4 0 014-4h14" strokeLinecap="round" />
    <path d="M7 22l-4-4 4-4" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M21 13v2a4 4 0 01-4 4H3" strokeLinecap="round" />
  </svg>
);
const RefreshIcon = () => (
  <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
    <path d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
      strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

// ── Page ──────────────────────────────────────────────────────────────────────

const MyBookingsPage: React.FC = () => {
  const {
    displayedBookings,
    summary,
    activeTab,
    isLoading,
    error,
    setActiveTab,
    handleCancelBooking,
  } = useBookings();
  const { user } = useAuthContext();

  // For the "upcoming" tab: split into future and past using the date field
  const upcomingCards = displayedBookings.filter(
    (b) => b.status !== "cancelled" && isUpcoming(b.date)
  );
  const pastCards = displayedBookings.filter(
    (b) => b.status !== "cancelled" && !isUpcoming(b.date)
  );

  return (
    <SidebarProvider>
      <div className="flex h-screen bg-[#F7F8FC] font-sans overflow-hidden w-full">

        <AppSidebar user={user} />

        <main className="flex-1 overflow-y-auto px-8 py-6 flex flex-col gap-5">

          {/* ── Header ── */}
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-[20px] font-bold text-[#1A1A2E] leading-tight">My Bookings</h1>
              <p className="text-[12.5px] text-gray-400 mt-0.5">
                Your upcoming and past seat reservations
              </p>
            </div>
            <div className="flex gap-2.5 items-center">
              <button className="h-8 px-3.5 rounded-lg border border-gray-200 bg-white text-[12.5px] font-medium text-gray-600 hover:bg-gray-50 transition-colors">
                Export CSV
              </button>
              <button className="h-8 px-4 rounded-lg bg-indigo-600 text-white text-[12.5px] font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-1.5">
                <span className="text-base leading-none">+</span>
                New booking
              </button>
              <button className="h-8 w-8 rounded-lg border border-gray-200 bg-white flex items-center justify-center text-gray-400 hover:bg-gray-50 transition-colors">
                <RefreshIcon />
              </button>
            </div>
          </div>

          {/* ── Stat cards ── */}
          <div className="flex gap-4">
            <StatCard
              label="Upcoming"
              value={summary.upcomingCount}
              subLabel={summary.nextBookingDate ?? undefined}
              icon={<CalIcon />}
              accentClass="border-l-indigo-400"
            />
            <StatCard
              label="Completed this month"
              value={summary.completedThisMonth}
              subLabel={`${summary.daysInOffice} days in office`}
              icon={<CheckIcon />}
              accentClass="border-l-emerald-400"
            />
            <StatCard
              label="Recurring bookings"
              value={summary.recurringCount}
              subLabel={summary.recurringPattern ?? undefined}
              icon={<RepeatIcon />}
              accentClass="border-l-amber-400"
            />
          </div>

          {/* ── Tabs ── */}
          <div className="flex border-b border-[#EBEBF5]">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "px-5 py-2.5 text-[13px] font-medium border-b-2 -mb-px transition-colors duration-150",
                  activeTab === tab.id
                    ? "border-indigo-600 text-indigo-600 font-semibold"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ── Content ── */}
          <div className="flex flex-col gap-3">

            {/* Loading */}
            {isLoading && (
              <div className="text-center py-12 text-gray-400 text-[13.5px]">
                Loading bookings…
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-4 text-red-500 text-[13px]">
                {error}
              </div>
            )}

            {/* Empty state */}
            {!isLoading && !error && displayedBookings.length === 0 && (
              <div className="text-center py-16 text-gray-400 text-[13.5px] bg-white rounded-xl border border-dashed border-gray-200">
                No {activeTab} bookings found.
              </div>
            )}

            {/* ── Upcoming tab ── */}
            {!isLoading && !error && activeTab === "upcoming" && (
              <>
                {upcomingCards.length > 0 ? (
                  upcomingCards.map((booking) => (
                    <BookingCard
                      key={booking.id}
                      booking={booking}
                      onCancel={handleCancelBooking}
                      showActions
                    />
                  ))
                ) : (
                  <div className="text-center py-16 text-gray-400 text-[13.5px] bg-white rounded-xl border border-dashed border-gray-200">
                    No upcoming bookings.
                  </div>
                )}

                {/* Past bookings section below upcoming */}
                {pastCards.length > 0 && (
                  <>
                    <p className="text-[11px] font-semibold tracking-widest uppercase text-gray-400 mt-2">
                      Past Bookings
                    </p>
                    {pastCards.map((booking) => (
                      <BookingCard
                        key={booking.id}
                        booking={booking}
                        onCancel={handleCancelBooking}
                        showActions={false}
                      />
                    ))}
                  </>
                )}
              </>
            )}

            {/* ── All other tabs: flat list ── */}
            {!isLoading && !error && activeTab !== "upcoming" &&
              displayedBookings.map((booking) => (
                <BookingCard
                  key={booking.id}
                  booking={booking}
                  onCancel={handleCancelBooking}
                  showActions={activeTab !== "past"}
                />
              ))
            }
          </div>
        </main>
      </div>
    </SidebarProvider>
  );
};

export default MyBookingsPage;