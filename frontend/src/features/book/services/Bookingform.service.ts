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

// ── Seats ─────────────────────────────────────────────────────────────────────

export interface FetchSeatsParams {
  floorId: string;
  fromDate: string;
  toDate: string;
  preferences?: string[];
}

export async function fetchSeats(params: FetchSeatsParams): Promise<Seat[]> {
  const { data } = await axiosInstance.get<any[]>(
    `/floors/${params.floorId}/seats`,
    {
      params: {
        fromDate: params.fromDate,
        toDate: params.toDate,
        ...(params.preferences?.length
          ? { preferences: params.preferences.join(",") }
          : {}),
      },
    }
  );
  return data.map((s) => ({
    id: s.seat_id,
    label: s.seat_code ?? s.seat_id,
    row: parseInt(s.seat_code?.split("-")[0] ?? "1", 10),
    col: parseInt(s.seat_code?.split("-")[1] ?? "1", 10),
    status: s.status ?? (s.is_bookable ? "available" : "unavailable"),
    matchesPreferences: false, // backend doesn't return this — compute if needed
    amenities: [],             // backend doesn't return this — extend if needed
  }));
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

export async function fetchPreferences(): Promise<Preference[]> {
  const { data } = await axiosInstance.get<{ amenities: any[] }>("/preferences");
  return data.amenities.map((a) => ({
    id: a.id,
    key: a.key,
    name: a.name,
    category: a.category ?? null,
    description: a.description ?? null,
    icon: a.icon ?? null,
  }));
}