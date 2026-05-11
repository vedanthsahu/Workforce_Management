// ─── Booking Types ────────────────────────────────────────────────────────────

export type BookingStatus = "confirmed" | "cancelled" | "pending";

export type BookingTab = "upcoming" | "past" | "recurring" | "cancelled";

export interface BookingTag {
  label: string;
  variant: "confirmed" | "manager" | "zone" | "sprint" | "recurring";
}

export interface Booking {
  id: string;
  location: string;
  floor: string;
  seat: string;
  date: string; // ISO date string e.g. "2025-04-17"
  startTime: string; // "09:00 AM"
  endTime: string; // "06:00 PM"
  isFullDay: boolean;
  status: BookingStatus;
  bookedOn: string; // "Booked Apr 16"
  tags: BookingTag[];
  isRecurring?: boolean;
  recurringPattern?: string; // "Thu recurring"
}

export interface BookingSummary {
  upcomingCount: number;
  nextBookingDate: string | null; // "Next: Apr 17 · B-04"
  completedThisMonth: number;
  daysInOffice: number;
  recurringCount: number;
  recurringPattern: string | null; // "Every Tue & Thu"
}

export interface BookingsState {
  bookings: Booking[];
  summary: BookingSummary;
  activeTab: BookingTab;
  isLoading: boolean;
  error: string | null;
}

export interface RawBooking {
  booking_id: string;
  tenant_id: string;
  user_id: string;
  seat_id: string;
  site_id: string;
  building_id: string;
  floor_id: string;
  seat_code: string;
  site_name: string;
  building_name: string;
  floor_name: string;
  booking_date: string;
  booking_status: "CONFIRMED" | "CANCELLED" | "PENDING" | "ACTIVE";
  source_channel: string;
  check_in_at: string | null;
  checked_out_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string;
  updated_at: string;
  // optional enrichment fields (may not always be present)
  is_full_day?: boolean;
  start_time?: string;
  end_time?: string;
  is_recurring?: boolean;
  recurring_pattern?: string;
  tags?: string[];
}