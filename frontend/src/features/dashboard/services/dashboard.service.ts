import { axiosInstance } from "@/lib/http/axios";
import type {
  DashboardData,
  Booking,
  TeamMember,
  Announcement,
  FavouriteSeat,
  DashboardStats,
  WeekDay,
  ApiBooking,
  ApiTeamGroup,
  TodayBookingInfo,
} from "../types/dashboard.types";
import type { User } from "@/features/auth/types/auth.types";

// ─── Error Types ──────────────────────────────────────────────────────────────

export type DashboardSectionError = {
  section: "user" | "currentBookings" | "futureBookings" | "team";
  code: string;
  message: string;
  status?: number;
};

export type DashboardResult =
  | { ok: true; data: DashboardData; errors: DashboardSectionError[] }
  | { ok: false; fatal: DashboardSectionError };

// ─── Helpers ──────────────────────────────────────────────────────────────────

function mapBookingStatus(status: string): "Confirmed" | "Pending" | "Cancelled" {
  const s = status.toUpperCase();
  if (s === "CONFIRMED" || s === "ACTIVE") return "Confirmed";
  if (s === "CANCELLED" || s === "CANCELED") return "Cancelled";
  return "Pending";
}

function formatBookingDate(isoDate: string): string {
  const d = new Date(isoDate + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function toInitials(fullName: string): string {
  return fullName
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0].toUpperCase())
    .join("");
}

const AVATAR_COLORS = [
  "#E8D5B7", "#B7D5E8", "#D5E8B7", "#E8B7D5",
  "#B7E8D5", "#D5B7E8", "#E8E8B7", "#B7B7E8",
];

function pickAvatarColor(index: number): string {
  return AVATAR_COLORS[index % AVATAR_COLORS.length];
}

function buildWeekDays(bookedDates: Set<string>): WeekDay[] {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const DAY_LABELS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];

  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() - 3 + i);
    const iso = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    const isToday = i === 3;
    const hasBooking = bookedDates.has(iso);
    return {
      date: d.getDate(),
      dayLabel: DAY_LABELS[d.getDay()],
      isToday,
      hasBooking,
      hasDot: isToday || hasBooking,
    };
  });
}

function deriveOccupancy(
  teamGroups: ApiTeamGroup[],
  currentUserId: string,
): { officeOccupancy: number; occupancyLabel: string } {
  const totalCapacity = teamGroups.reduce((acc, g) => acc + g.total_members, 0);
  const bookedToday = teamGroups.reduce((acc, g) => acc + g.booked_today_count, 0);
  const pct = totalCapacity > 0 ? Math.round((bookedToday / totalCapacity) * 100) : 0;
  let occupancyLabel: string;
  if (pct >= 85) occupancyLabel = "High traffic today";
  else if (pct >= 50) occupancyLabel = "Moderate traffic today";
  else occupancyLabel = "Light traffic today";
  return { officeOccupancy: pct, occupancyLabel };
}

function mapFavouriteSeat(user: User): FavouriteSeat | null {
  const s = user.favorite_seat;
  if (!s) return null;
  const floor = s.floor_name ?? (s.floor_id ? `Floor ${s.floor_id}` : "");
  const site = s.site_name ?? s.building_name ?? "Office";
  return {
    id: s.seat_id,
    label: s.seat_code ?? s.seat_id,
    location: [floor, site].filter(Boolean).join(" · "),
    description: "Favourite seat",
    floor,
  };
}

function mapApiBooking(b: ApiBooking): Booking {
  return {
    id: b.booking_id,
    location: b.site_name ?? "Office",
    floor: b.floor_name ?? (b.floor_id ? `Floor ${b.floor_id}` : ""),
    date: formatBookingDate(b.booking_date),
    startTime: "9:00 AM",
    endTime: "6:00 PM",
    status: mapBookingStatus(b.booking_status),
    isRecurring: false,
    seatId: b.seat_code ?? b.seat_id,
    managerNote: "",
  };
}

// function mapApiTeamToMembers(groups: ApiTeamGroup[], currentUserId: string): TeamMember[] {
//   const members: TeamMember[] = [];
//   let colorIndex = 0;
//   for (const group of groups) {
//     for (const m of group.members) {
//       if (m.user_id === currentUserId) continue;
//       members.push({
//         id: m.user_id,
//         name: m.full_name,
//         initials: toInitials(m.full_name),
//         floor: m.seat?.floor_id ? `Floor ${m.seat.floor_id}` : "—",
//         avatarColor: pickAvatarColor(colorIndex++),
//       });
//     }
//   }
//   return members;
// }
function mapApiTeamToMembers(groups: ApiTeamGroup[], currentUserId: string): TeamMember[] {
  const members: TeamMember[] = [];
  let colorIndex = 0;
  for (const group of groups) {
    for (const m of group.members) {
      if (m.user_id === currentUserId) continue;
      if (!m.seat) continue;
      members.push({
        id: m.user_id,
        name: m.full_name,
        initials: toInitials(m.full_name),
        floor: m.seat?.floor_id ? `Floor ${m.seat.floor_id}` : "—",
        avatarColor: pickAvatarColor(colorIndex++),
        seatCode: m.seat?.seat_code ?? undefined,   
        email: m.email ?? undefined,                 
        buildingId: m.seat?.building_id ?? undefined,
      });
    }
  }
  return members;
}

function extractTodayBookingInfo(currentBookings: ApiBooking[]): TodayBookingInfo {
  if (currentBookings.length === 0) {
    return { hasTodayBooking: false, seatCode: null, floor: null, bookingId: null };
  }
  const b = currentBookings[0];
  return {
    hasTodayBooking: true,
    seatCode: b.seat_code ?? b.seat_id,
    floor: b.floor_name ?? (b.floor_id ? `Floor ${b.floor_id}` : null),
    bookingId: b.booking_id,
  };
}

function deriveStats(
  currentBookings: ApiBooking[],
  teamGroups: ApiTeamGroup[],
  currentUserId: string,
): DashboardStats {
  const totalMembers = teamGroups.reduce((acc, g) => {
    const selfInGroup = g.members.some((m) => m.user_id === currentUserId);
    return acc + g.total_members - (selfInGroup ? 1 : 0);
  }, 0);

  const bookedToday = teamGroups.reduce((acc, g) => {
    const selfMember = g.members.find((m) => m.user_id === currentUserId);
    const selfBookedToday = selfMember?.seat != null;
    return acc + g.booked_today_count - (selfBookedToday ? 1 : 0);
  }, 0);

  const { officeOccupancy, occupancyLabel } = deriveOccupancy(teamGroups, currentUserId);

  return {
    daysInMonth: currentBookings.length,
    trend: 0,
    teamInOffice: bookedToday,
    teamRemoteCount: totalMembers - bookedToday,
    // officeOccupancy,
    // occupancyLabel,
    officeVisitsThisYear: 0,
    teamRank: 0,
  };
}

// ─── Static mock data ─────────────────────────────────────────────────────────

const MOCK_ANNOUNCEMENTS: Announcement[] = [
  { id: "1", title: "Floor 4 maintenance – Apr 17", description: "Bookings paused from 10am – 1pm", type: "warning" },
  { id: "2", title: "Parking lot B closed this week", description: "Use parking lot D as alternate", type: "info" },
  { id: "3", title: "Austin Hub now open for bookings", description: "100 Congress Ave · 45 seats available", type: "success" },
];

// ─── Error classifier ─────────────────────────────────────────────────────────

function classifyError(
  err: unknown,
  section: DashboardSectionError["section"],
): DashboardSectionError {

   console.log("[classifyError]", {
    hasResponse: !!(err as any)?.response,
    status: (err as any)?.response?.status,
    message: (err as any)?.message,
    code: (err as any)?.code,
  });
  if (err && typeof err === "object" && "response" in err) {
    const axiosErr = err as { response?: { status?: number; data?: { detail?: { code?: string; message?: string } | string } } };
    const status = axiosErr.response?.status;
    const detail = axiosErr.response?.data?.detail;

    // 401 — user needs to re-authenticate
    if (status === 401) {
      return { section, code: "unauthenticated", message: "Your session has expired. Please log in again.", status };
    }
    // 403 — access denied
    if (status === 403) {
      return { section, code: "forbidden", message: "You don't have permission to access this data.", status };
    }
    // Structured backend error
    if (detail && typeof detail === "object" && detail.code) {
      return { section, code: detail.code, message: detail.message ?? "An error occurred.", status };
    }
    // Generic HTTP error
    if (status) {
      return { section, code: `http_${status}`, message: `Request failed (${status}). Please try again.`, status };
    }
  }
  // Network / unknown
  return { section, code: "network_error", message: "Could not connect to the server. Check your connection.", };
}

// ─── API fetchers ─────────────────────────────────────────────────────────────

async function getCurrentUser(): Promise<User> {
  const { data } = await axiosInstance.get<User>("/auth/me");
  return data;
}

async function fetchCurrentBookingsRaw(): Promise<ApiBooking[]> {
  const { data } = await axiosInstance.get<ApiBooking[]>("/bookings/me/current");
  return data;
}

async function fetchFutureBookingsRaw(): Promise<ApiBooking[]> {
  const { data } = await axiosInstance.get<ApiBooking[]>("/bookings/me/future");
  return data;
}

async function fetchTeamGroupsRaw(): Promise<ApiTeamGroup[]> {
  const { data } = await axiosInstance.get<ApiTeamGroup[]>("/teams/me");
  return data;
}

// ─── Main export ──────────────────────────────────────────────────────────────

export async function getDashboardData(): Promise<DashboardResult> {
  // Step 1: User is fatal — nothing renders without it
  let user: User;
  try {
    user = await getCurrentUser();
  } catch (err) {
    const fatal = classifyError(err, "user");
    return { ok: false, fatal };
  }

  const currentUserId = user.user_id;
  const sectionErrors: DashboardSectionError[] = [];

  // Step 2: Fetch remaining sections independently — failures are non-fatal
  const [currentRawResult, futureRawResult, teamGroupsResult] = await Promise.allSettled([
    fetchCurrentBookingsRaw(),
    fetchFutureBookingsRaw(),
    fetchTeamGroupsRaw(),
  ]);

  // Unwrap with fallbacks + collect non-fatal errors
  const currentRaw: ApiBooking[] = (() => {
    if (currentRawResult.status === "fulfilled") return currentRawResult.value;
    sectionErrors.push(classifyError(currentRawResult.reason, "currentBookings"));
    return [];
  })();

  const futureRaw: ApiBooking[] = (() => {
    if (futureRawResult.status === "fulfilled") return futureRawResult.value;
    sectionErrors.push(classifyError(futureRawResult.reason, "futureBookings"));
    return [];
  })();

  const teamGroups: ApiTeamGroup[] = (() => {
    if (teamGroupsResult.status === "fulfilled") return teamGroupsResult.value;
    sectionErrors.push(classifyError(teamGroupsResult.reason, "team"));
    return [];
  })();

  // Step 3: Assemble dashboard data
  const teamInOfficeToday = mapApiTeamToMembers(teamGroups, currentUserId);
  const stats = deriveStats(currentRaw, teamGroups, currentUserId);
  const todayBooking = extractTodayBookingInfo(currentRaw);

  const allBookedDates = new Set([
    ...currentRaw.map((b) => b.booking_date),
    ...futureRaw.map((b) => b.booking_date),
  ]);
  const weekDays = buildWeekDays(allBookedDates);

  const upcomingBookings = [...futureRaw]
    .sort((a, b) => new Date(a.booking_date).getTime() - new Date(b.booking_date).getTime())
    .map(mapApiBooking);

  const nextBookingDate = upcomingBookings[0]?.date ?? "—";

  return {
    ok: true,
    data: {
      user,
      stats,
      weekDays,
      upcomingBookings,
      teamInOfficeToday,
      announcements: MOCK_ANNOUNCEMENTS,
      favouriteSeat: mapFavouriteSeat(user),
      teamOnlineCount: stats.teamInOffice,
      teamOfflineCount: stats.teamRemoteCount,
      nextBookingDate,
      todayBooking,
      daysInOffice: user.days_in_office ?? 0,
    },
    errors: sectionErrors,
  };
}

// ─── Individual exports ───────────────────────────────────────────────────────

export async function getUpcomingBookings(): Promise<Booking[]> {
  const raw = await fetchFutureBookingsRaw();
  return raw.map(mapApiBooking);
}

export async function getTeamInOfficeToday(): Promise<TeamMember[]> {
  const user = await getCurrentUser();
  const groups = await fetchTeamGroupsRaw();
  return mapApiTeamToMembers(groups, user.user_id);
}

export async function getAnnouncements(): Promise<Announcement[]> {
  return Promise.resolve(MOCK_ANNOUNCEMENTS);
}

export async function getFavouriteSeats(): Promise<FavouriteSeat[]> {
  const user = await getCurrentUser();
  const seat = mapFavouriteSeat(user);
  return seat ? [seat] : [];
}

export async function bookSeat(seatId: string, date: string): Promise<{ success: boolean }> {
  return Promise.resolve({ success: true });
}

export async function cancelBooking(bookingId: string): Promise<{ success: boolean }> {
  await axiosInstance.delete(`/bookings/${bookingId}`);
  return { success: true };
}