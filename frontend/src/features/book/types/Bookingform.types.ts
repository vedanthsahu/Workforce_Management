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

// export interface Seat {
//   id: string;
//   label: string;
//   row: number;
//   col: number;
//   status: SeatStatus;
//   matchesPreferences: boolean;
//   amenities: string[];         // ← was PreferenceKey[]
// }
export interface Seat {
  id:                 string;
  svgId:              string;   // ← add this if missing
  label:              string;
  row?:               number;
  col?:               number;
  status:             "available" | "booked" | "unavailable" | "yours";
  matchesPreferences: boolean;
  amenities:          string[];
}

// ── Booking confirmation payload ──────────────────────────────────────────────

// export interface CreateBookingPayload {
//   siteId: string;
//   buildingId: string;
//   floorId: string;
//   seatId: string;
//   fromDate: string;
//   toDate: string;
//   preferences: string[];       // ← was PreferenceKey[]
// }

// export interface CreateBookingResponse {
//   bookingId: string;
//   confirmationCode: string;
//   seat: string;
//   location: string;
//   floor: string;
//   fromDate: string;
//   toDate: string;
// }

export interface CreateBookingPayload {
  site_id: number;
  building_id: number;
  floor_id: number;
  seat_id: number;
  booking_date: string; // "YYYY-MM-DD"
}

export interface CreateBookingResponse {
  booking_id: string;
  tenant_id: string;
  user_id: string;
  seat_id: string;
  site_id: string | null;
  building_id: string | null;
  floor_id: string | null;
  seat_code: string | null;
  site_name: string | null;
  building_name: string | null;
  floor_name: string | null;
  booking_date: string;
  booking_status: string;
  source_channel: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  created_at: string | null;
}

// ── Step enum ─────────────────────────────────────────────────────────────────

export type BookingStep = 1 | 2 | 3;