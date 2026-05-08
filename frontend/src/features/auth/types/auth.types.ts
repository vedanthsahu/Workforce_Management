export interface FavoriteSeatResponse {
  seat_id: string;
  seat_code: string;
  floor_id?: string | null;
  floor_name?: string | null;
  site_id?: string | null;
  site_name?: string | null;
  building_id?: string | null;
  building_name?: string | null;
}

export interface User {
  user_id: string;
  tenant_id: string;
  email: string;
  full_name?: string | null;
  display_name?: string | null;
  name?: string | null;
  role?: string | null;
  status?: string | null;
  home_site_id?: string | null;
  department?: string | null;
  job_title?: string | null;
  office_location?: string | null;
  // ← new fields
  favorite_seat?: FavoriteSeatResponse | null;
  days_in_office?: number;
}

export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}