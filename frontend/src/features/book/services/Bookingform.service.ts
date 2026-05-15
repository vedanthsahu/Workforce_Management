import { axiosInstance } from "@/lib/http/axios";
import {
  Site,
  Building,
  Floor,
  Seat,
  CreateBookingPayload,
  CreateBookingResponse,
  Preference,
} from "../types/Bookingform.types";

// ── Sites ─────────────────────────────────────────────────────────────────────

export async function fetchSites(): Promise<Site[]> {
  const { data } = await axiosInstance.get<any[]>("/sites");
  return data.map((s) => ({
    id: s.site_id,
    name: s.site_name,
    city: s.city ?? "",
    country: s.country ?? "",
    timezone: s.timezone ?? "",
  }));
}

// ── Buildings ─────────────────────────────────────────────────────────────────

export async function fetchBuildings(siteId: string): Promise<Building[]> {
  const { data } = await axiosInstance.get<any[]>("/buildings", {
    params: { site_id: siteId },
  });
  return data.map((b) => ({
    id: b.building_id,
    siteId: b.site_id,
    name: b.building_name,
  }));
}

// ── Floors ────────────────────────────────────────────────────────────────────

export async function fetchFloors(buildingId: string): Promise<Floor[]> {
  const { data } = await axiosInstance.get<any[]>(
    `/buildings/${buildingId}/floors`
  );
  return data.map((f) => ({
    id: f.floor_id,
    buildingId: f.building_id ?? buildingId,
    name: f.floor_name ?? f.floor_code ?? `Floor ${f.floor_id}`,
    number: parseInt(f.floor_code ?? "0", 10),
  }));
}

// ── Seat ID → SVG id mapping ─────────────────────────────────────────────────
//
// WHY seat_id and NOT seat_code:
//
// seat_code (e.g. "A-F2-001", "T3-7-001") is zone-relative — the last segment
// is the seat number WITHIN that zone only. Every zone has its own seat "001",
// "002" etc., so parsing seat_code causes many-to-one collisions on svgId "1".
//
// seat_id is the globally unique backend PK and maps 1-to-1 with SVG <g> nodes:
//   seat_id=1  → <g id="1">
//   seat_id=24 → <g id="s24">
//   seat_id=N  → <g id="N">
//
// Always use seat_id to derive svgId.
//
export function seatIdToSvgId(seatId: string | number): string {
  const num = parseInt(String(seatId), 10);
  if (isNaN(num)) {
    console.warn(`[seatIdToSvgId] cannot parse seat_id "${seatId}"`);
    return String(seatId);
  }
  return num === 24 ? "s24" : String(num);
}

// Kept for backwards compatibility — always delegates to seatIdToSvgId
export function seatCodeToSvgId(_seatCode: string, fallbackId: string | number): string {
  return seatIdToSvgId(fallbackId);
}

// ── Normalise status ──────────────────────────────────────────────────────────

export function normalizeStatus(
  raw: string | undefined,
  isBookable?: boolean
): "available" | "booked" | "unavailable" | "yours" {
  switch ((raw ?? "").toUpperCase()) {
    case "ACTIVE":
    case "AVAILABLE": return "available";
    case "BOOKED":
    case "CONFIRMED": return "booked";
    case "YOURS":     return "yours";
    default:          return isBookable ? "available" : "unavailable";
  }
}

// ── Seat Availability ─────────────────────────────────────────────────────────
//
// Backend route: GET /bookings/available
// Params:
//   floor_id     (int, required)
//   booking_date (date string "YYYY-MM-DD", required)
//
// This is the SINGLE SOURCE OF TRUTH for seat availability on a given date.
// Only seats returned here are available. Everything else is booked/unavailable.

export interface SeatAvailability {
  seat_id: string | number;
  seat_code: string;
  seat_type?: string;
  seat_neighborhood?: string;
  status: string;
  is_bookable?: boolean;
}

export async function fetchAvailability(params: {
  floorId: string;
  fromDate: string;
}): Promise<SeatAvailability[]> {
  const { data } = await axiosInstance.get<SeatAvailability[]>("/bookings/available", {
    params: {
      floor_id:     params.floorId,
      booking_date: params.fromDate,
    },
  });
  return data;
}

// ── Seats ─────────────────────────────────────────────────────────────────────
//
// NOTE: fetchSeats (GET /floors/:id/seats) is intentionally NOT used for
// availability checks anymore. It returns ALL seats regardless of booking
// status and caused UI mismatches. Use fetchSeatsWithAvailability instead.

export interface FetchSeatsParams {
  floorId: string;
  fromDate: string;
  toDate: string;
  preferences?: string[];
}

// ── Seats + Availability ──────────────────────────────────────────────────────
//
// /bookings/available is the sole source of truth.
//
// Rule:
//   - Seat returned by /available  → status from backend (available/yours/etc.)
//   - Seat NOT returned            → "booked" (backend excluded it intentionally)
//
// We get the full seat list from /floors/:id/seats only to know which SVG
// nodes exist on this floor, then we overlay availability on top.
// The availability status always wins — no fallback to the seats-list status.

export async function fetchSeatsWithAvailability(
  params: FetchSeatsParams
): Promise<Seat[]> {
  // Step 1 — get the full seat roster for this floor (for SVG node list only)
  const { data: seatListRaw } = await axiosInstance.get<any[]>(
    `/floors/${params.floorId}/seats`,
    {
      params: {
        fromDate: params.fromDate,
        toDate:   params.toDate,
        ...(params.preferences?.length
          ? { preferences: params.preferences.join(",") }
          : {}),
      },
    }
  );

  // Step 2 — get availability (source of truth for status)
  const availability = await fetchAvailability({
    floorId:  params.floorId,
    fromDate: params.fromDate,
  });

  // Build svgId → availability entry map from /available response.
  // Key insight: use seat_id (globally unique PK) not seat_code (zone-relative).
  const availMap = new Map<string, SeatAvailability>();
  availability.forEach((a) => {
    const svgId = seatIdToSvgId(a.seat_id);  // seat_id=1 → "1", seat_id=24 → "s24"
    availMap.set(svgId, a);
    console.log(
      `[fetchAvailability] seat_id="${a.seat_id}" seat_code="${a.seat_code}" → svgId="${svgId}" status="${a.status}"`
    );
  });

  // Normalise selected preferences to lowercase for comparison
  const selectedPrefs = (params.preferences ?? []).map((p) => p.toLowerCase());

  // Step 3 — map every seat from the roster, overlaying availability status
  return seatListRaw.map((s) => {
    const seatCode = s.seat_code ?? "";
    const svgId    = seatIdToSvgId(s.seat_id);  // use seat_id, not seat_code

    // Look up this seat in /available
    const availEntry = availMap.get(svgId);

    // ⚠️  KEY RULE: if not in availMap, backend excluded it → it is booked.
    // Never fall back to the /floors/seats status — that endpoint doesn't
    // reflect per-date booking state.
    // const status: "available" | "booked" | "unavailable" | "yours" = availEntry
    //   ? normalizeStatus(availEntry.status, availEntry.is_bookable)
    //   : "booked";
    const status: "available" | "booked" | "unavailable" | "yours" = availEntry
  ? normalizeStatus(availEntry.status, availEntry.is_bookable)
  : "unavailable";  // ← was "booked"

    // Build amenities list from seat_type and seat_neighborhood.
    // These are used to match against user-selected preferences.
    const amenities: string[] = [];
    const seatType         = (availEntry?.seat_type         ?? s.seat_type         ?? "").toLowerCase();
    const seatNeighborhood = (availEntry?.seat_neighborhood ?? s.seat_neighborhood ?? "").toLowerCase();
    if (seatType)         amenities.push(seatType);
    if (seatNeighborhood) amenities.push(seatNeighborhood);

    // Seat matches preferences when it is available AND at least one selected
    // preference matches this seat's amenity tokens (type or neighborhood).
    const matchesPreferences =
      status === "available" &&
      selectedPrefs.length > 0 &&
      selectedPrefs.some((pref) =>
        amenities.some((a) => a.includes(pref) || pref.includes(a))
      );

    console.log(
      `[fetchSeatsWithAvailability] seat_code="${seatCode}" svgId="${svgId}" ` +
      `inAvailable=${!!availEntry} status="${status}" ` +
      `amenities=${JSON.stringify(amenities)} matchesPreferences=${matchesPreferences}`
    );

    return {
      id:                 String(s.seat_id),
      svgId,
      label:              seatCode || `Seat ${s.seat_id}`,
      row:                0,
      col:                0,
      status,
      matchesPreferences,
      amenities,
    };
  });
}

// ── Create booking ────────────────────────────────────────────────────────────

export async function createBooking(
  payload: CreateBookingPayload
): Promise<CreateBookingResponse> {
  const { data } = await axiosInstance.post<CreateBookingResponse>(
    "/bookings",
    payload
  );
  return data;
}

// ── Preferences ───────────────────────────────────────────────────────────────

export async function fetchPreferences(): Promise<Preference[]> {
  const { data } = await axiosInstance.get<{ amenities: any[] }>("/preferences");
  return data.amenities.map((a) => ({
    id:          a.id,
    key:         a.key,
    name:        a.name,
    category:    a.category    ?? null,
    description: a.description ?? null,
    icon:        a.icon        ?? null,
  }));
}