import { axiosInstance } from "@/lib/http/axios";
import type {
  DashboardData,
  Booking,
  TeamMember,
  Announcement,
  FavouriteSeat,
  DashboardStats,
  WeekDay,
} from "../types/dashboard.types";
import type { User } from "@/features/auth/types/auth.types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ─── Static / Mock Data ──────────────────────────────────────────────────────

const MOCK_WEEK_DAYS: WeekDay[] = [
  { date: 13, dayLabel: "Mon", isToday: false, hasBooking: false, hasDot: false },
  { date: 14, dayLabel: "Tue", isToday: false, hasBooking: false, hasDot: false },
  { date: 15, dayLabel: "Wed", isToday: false, hasBooking: true, hasDot: true },
  { date: 16, dayLabel: "Thu", isToday: true, hasBooking: true, hasDot: true },
  { date: 17, dayLabel: "Fri", isToday: false, hasBooking: false, hasDot: false },
  { date: 18, dayLabel: "Mon", isToday: false, hasBooking: false, hasDot: false },
  { date: 19, dayLabel: "Tue", isToday: false, hasBooking: false, hasDot: false },
];

const MOCK_STATS: DashboardStats = {
  daysInMonth: 9,
  trend: 2,
  teamInOffice: 4,
  nextSeat: "A-12",
  nextSeatFloor: "Floor 3 · W HQ · W",
};

const MOCK_BOOKINGS: Booking[] = [
  {
    id: "1",
    location: "San Francisco HQ",
    floor: "Floor 2",
    date: "Sept 3-14",
    startTime: "9:00 AM",
    endTime: "6:00 PM",
    status: "Confirmed",
    isRecurring: true,
    seatId: "A-12",
    managerNote: ""
  },
  {
    id: "2",
    location: "San Francisco HQ",
    floor: "Floor 2",
    date: "Sept 3-14",
    startTime: "9:00 AM",
    endTime: "5:00 PM",
    status: "Confirmed",
    isRecurring: true,
     seatId: "A-13",
    managerNote: ""
  },
];

const MOCK_TEAM: TeamMember[] = [
  { id: "1", name: "Mike K.", initials: "MK", floor: "Floor 2", avatarColor: "#E8D5B7" },
  { id: "2", name: "Amy L.", initials: "AL", floor: "Floor 3", avatarColor: "#B7D5E8" },
  { id: "3", name: "Raj B.", initials: "RB", floor: "Floor 2", avatarColor: "#D5E8B7" },
  { id: "4", name: "Priya K.", initials: "PK", floor: "Floor 2", avatarColor: "#E8B7D5" },
  { id: "5", name: "John D.", initials: "JD", floor: "Floor 1", avatarColor: "#B7E8D5" },
  { id: "6", name: "Tom C.", initials: "TC", floor: "Floor 3", avatarColor: "#D5B7E8" },
];

const MOCK_ANNOUNCEMENTS: Announcement[] = [
  {
    id: "1",
    title: "Floor 4 maintenance – Apr 17",
    description: "Roof top passed from 10am – 1pm",
    type: "warning",
  },
  {
    id: "2",
    title: "Parking lot B closed this week",
    description: "Use parking lot D or E seats available",
    type: "info",
  },
  {
    id: "3",
    title: "Austin Hub now open for bookings",
    description: "100 Congress Ave · 50 seats available",
    type: "success",
  },
];

const MOCK_FAVOURITE_SEAT: FavouriteSeat = {
  id: "1",
  label: "Seat A-12",
  location: "Floor 3 · W HQ · Window seat",
  description: "Booked · Create another",
  floor: "Floor 3",
};

// ─── Service Functions ────────────────────────────────────────────────────────

// Fetch real user from /me endpoint
async function getCurrentUser(): Promise<User> {
  const { data } = await axiosInstance.get<User>("/me");
  return data;
}

export async function getDashboardData(): Promise<DashboardData> {
  // Fetch real user from backend, fall back to mock if it fails
  let user: User;
  try {
    user = await getCurrentUser();
  } catch {
    user = { user_id: "1", name: "Sara", email: "sara@company.com" };
  }

  return {
    user,                              // ← real user from /me
    stats: MOCK_STATS,
    weekDays: MOCK_WEEK_DAYS,
    upcomingBookings: MOCK_BOOKINGS,
    teamInOfficeToday: MOCK_TEAM,
    announcements: MOCK_ANNOUNCEMENTS,
    favouriteSeat: MOCK_FAVOURITE_SEAT,
    teamOnlineCount: 2,
    teamOfflineCount: 2,
    nextBookingDate: "Apr 19",
  };
}

export async function getUpcomingBookings(): Promise<Booking[]> {
  return Promise.resolve(MOCK_BOOKINGS);
}

export async function getTeamInOfficeToday(): Promise<TeamMember[]> {
  return Promise.resolve(MOCK_TEAM);
}

export async function getAnnouncements(): Promise<Announcement[]> {
  return Promise.resolve(MOCK_ANNOUNCEMENTS);
}

export async function getFavouriteSeats(): Promise<FavouriteSeat[]> {
  return Promise.resolve([MOCK_FAVOURITE_SEAT]);
}

export async function bookSeat(seatId: string, date: string): Promise<{ success: boolean }> {
  console.log("Booking seat:", seatId, date);
  return Promise.resolve({ success: true });
}

export async function cancelBooking(bookingId: string): Promise<{ success: boolean }> {
  console.log("Cancelling booking:", bookingId);
  return Promise.resolve({ success: true });
}