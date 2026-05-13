// ── Workspace / location ──────────────────────────────────────────────────────

export interface Site {
  id: string;
  name: string;
  city: string;
  country: string;
  timezone: string; // e.g. "Asia/Kolkata"
}

export interface Building {
  id: string;
  siteId: string;
  name: string;
}

export interface Floor {
  id: string;
  buildingId: string;
  name: string; // e.g. "7th Floor"
  number: number;
}

// ── Preferences ───────────────────────────────────────────────────────────────

export type PreferenceKey = "window" | "cafeteria" | "elevator" | "dualMonitor";

export interface Preference {
  key: PreferenceKey;
  label: string;
  icon: string; // Lucide icon name or emoji fallback
}

// ── Booking form state ────────────────────────────────────────────────────────

export interface BookingFormState {
  // Step 1
  siteId: string;
  buildingId: string;
  floorId: string;
  fromDate: string; // ISO date "YYYY-MM-DD"
  toDate: string;
  preferences: PreferenceKey[];

  // Step 2
  selectedSeatId: string | null;

  // Step 3 – read-only summary derived from above
}

// ── Seat (for floor map step) ─────────────────────────────────────────────────

export type SeatStatus = "available" | "booked" | "unavailable" | "yours";

export interface Seat {
  id: string;
  label: string; // e.g. "A-14"
  row: number;
  col: number;
  status: SeatStatus;
  matchesPreferences: boolean;
  amenities: PreferenceKey[];
}

// ── Booking confirmation payload ──────────────────────────────────────────────

export interface CreateBookingPayload {
  siteId: string;
  buildingId: string;
  floorId: string;
  seatId: string;
  fromDate: string;
  toDate: string;
  preferences: PreferenceKey[];
}

export interface CreateBookingResponse {
  bookingId: string;
  confirmationCode: string;
  seat: string;
  location: string;
  floor: string;
  fromDate: string;
  toDate: string;
}

// ── Step enum ─────────────────────────────────────────────────────────────────

export type BookingStep = 1 | 2 | 3;