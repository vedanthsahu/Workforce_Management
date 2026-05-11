import { axiosInstance } from "@/lib/http/axios";
import { Booking, BookingSummary, RawBooking } from "../types/bookings.types";

const BASE = "/bookings";


// ── Status normaliser ─────────────────────────────────────────────────────────
function normaliseStatus(raw: string): "confirmed" | "cancelled" | "pending" {
  const s = raw.toUpperCase();
  if (s === "CONFIRMED" || s === "ACTIVE") return "confirmed";
  if (s === "CANCELLED" || s === "CANCELED") return "cancelled";
  return "pending";
}

// ── Mapper ────────────────────────────────────────────────────────────────────
function mapRawBooking(raw: RawBooking): Booking {
  const bookedDate = new Date(raw.created_at);
  const bookedOn = bookedDate.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });

  const status = normaliseStatus(raw.booking_status);

  // Build tags — status first, then any server-supplied extras
  const tagList: { label: string; variant: "confirmed" | "manager" | "sprint" | "zone" | "recurring" }[] = [];

  if (status === "confirmed") {
    tagList.push({ label: "Confirmed", variant: "confirmed" });
  }

  for (const t of raw.tags ?? []) {
    if (t === "confirmed") continue; // already added above
    if (t === "manager_booked") tagList.push({ label: "Manager booked", variant: "manager" });
    else if (t === "sprint_day")      tagList.push({ label: "Sprint day",      variant: "sprint" });
    else if (t === "engineering_zone") tagList.push({ label: "Engineering zone", variant: "zone" });
    else tagList.push({ label: t, variant: "zone" });
  }

  return {
    id:              raw.booking_id,
    location:        raw.site_name     ?? "Office",
    floor:           raw.floor_name    ?? (raw.floor_id ? `Floor ${raw.floor_id}` : ""),
    seat:            raw.seat_code     ?? raw.seat_id,
    date:            raw.booking_date,
    startTime:       raw.start_time    ?? "9:00 AM",
    endTime:         raw.end_time      ?? "6:00 PM",
    isFullDay:       raw.is_full_day   ?? false,
    status,
    bookedOn,
    tags:            tagList,
    isRecurring:     raw.is_recurring  ?? false,
    recurringPattern: raw.recurring_pattern,
  };
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function fetchPastBookings(): Promise<Booking[]> {
  const { data } = await axiosInstance.get<RawBooking[]>(`${BASE}/me/past`);
  return data.map(mapRawBooking);
}

export async function fetchCurrentBookings(): Promise<Booking[]> {
  const { data } = await axiosInstance.get<RawBooking[]>(`${BASE}/me/current`);
  return data.map(mapRawBooking);
}

export async function fetchFutureBookings(): Promise<Booking[]> {
  const { data } = await axiosInstance.get<RawBooking[]>(`${BASE}/me/future`);
  return data.map(mapRawBooking);
}

export async function cancelBooking(bookingId: string): Promise<void> {
  await axiosInstance.delete(`${BASE}/${bookingId}`);
}

// ── Summary aggregation ───────────────────────────────────────────────────────
export function deriveBookingSummary(
  current: Booking[],
  future: Booking[],
  past: Booking[]
): BookingSummary {
  const upcoming = [...current, ...future];
  const nextBooking = upcoming[0];

  const nextBookingDate = nextBooking
    ? (() => {
        const d = new Date(nextBooking.date);
        const label = d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
        return `Next: ${label} · ${nextBooking.seat}`;
      })()
    : null;

  const now = new Date();
  const completedThisMonth = past.filter((b) => {
    const d = new Date(b.date);
    return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
  }).length;

  const recurring = upcoming.filter((b) => b.isRecurring);
  const recurringPattern =
    recurring.length > 0 ? (recurring[0].recurringPattern ?? null) : null;

  return {
    upcomingCount:       upcoming.length,
    nextBookingDate,
    completedThisMonth,
    daysInOffice:        completedThisMonth,
    recurringCount:      recurring.length,
    recurringPattern,
  };
}