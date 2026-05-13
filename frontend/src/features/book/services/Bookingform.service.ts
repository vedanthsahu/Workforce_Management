import {
  Site,
  Building,
  Floor,
  Seat,
  CreateBookingPayload,
  CreateBookingResponse,
} from "../types/Bookingform.types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";

// ── Helpers ───────────────────────────────────────────────────────────────────

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "Unknown error");
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json() as Promise<T>;
}

// ── Sites ─────────────────────────────────────────────────────────────────────

export async function fetchSites(): Promise<Site[]> {
  return apiFetch<Site[]>("/api/sites");
}

// ── Buildings ─────────────────────────────────────────────────────────────────

export async function fetchBuildings(siteId: string): Promise<Building[]> {
  return apiFetch<Building[]>(`/api/sites/${siteId}/buildings`);
}

// ── Floors ────────────────────────────────────────────────────────────────────

export async function fetchFloors(buildingId: string): Promise<Floor[]> {
  return apiFetch<Floor[]>(`/api/buildings/${buildingId}/floors`);
}

// ── Seats ─────────────────────────────────────────────────────────────────────

export interface FetchSeatsParams {
  floorId: string;
  fromDate: string;
  toDate: string;
  preferences?: string[];
}

export async function fetchSeats(params: FetchSeatsParams): Promise<Seat[]> {
  const qs = new URLSearchParams({
    fromDate: params.fromDate,
    toDate: params.toDate,
    ...(params.preferences?.length
      ? { preferences: params.preferences.join(",") }
      : {}),
  });
  return apiFetch<Seat[]>(`/api/floors/${params.floorId}/seats?${qs}`);
}

// ── Create booking ────────────────────────────────────────────────────────────

export async function createBooking(
  payload: CreateBookingPayload
): Promise<CreateBookingResponse> {
  return apiFetch<CreateBookingResponse>("/api/bookings", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}