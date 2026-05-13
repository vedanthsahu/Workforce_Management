export interface Site {
  id: string;
  name: string;
  city: string;
  country: string;
  timezone: string;
}

export interface Building {
  id: string;
  siteId: string;
  name: string;
}

export interface Floor {
  id: string;
  buildingId: string;
  name: string;
  number: number;
}

// ── Preferences (fetched from API) ────────────────────────────────────────────

export interface Preference {
  id: string;
  key: string;
  name: string;
  category?: string | null;
  description?: string | null;
  icon?: string | null;
}

// ── Booking form state ────────────────────────────────────────────────────────

export interface BookingFormState {
  // Step 1
  siteId: string;
  buildingId: string;
  floorId: string;
  fromDate: string;
  toDate: string;
  preferences: string[];       // ← was PreferenceKey[]

  // Step 2
  selectedSeatId: string | null;
}

// ── Seat (for floor map step) ─────────────────────────────────────────────────

export type SeatStatus = "available" | "booked" | "unavailable" | "yours";

export interface Seat {
  id: string;
  label: string;
  row: number;
  col: number;
  status: SeatStatus;
  matchesPreferences: boolean;
  amenities: string[];         // ← was PreferenceKey[]
}

// ── Booking confirmation payload ──────────────────────────────────────────────

export interface CreateBookingPayload {
  siteId: string;
  buildingId: string;
  floorId: string;
  seatId: string;
  fromDate: string;
  toDate: string;
  preferences: string[];       // ← was PreferenceKey[]
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