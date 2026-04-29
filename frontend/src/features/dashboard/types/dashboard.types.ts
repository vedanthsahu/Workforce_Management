import { User } from "@/features/auth/types/auth.types";

export type { User } from "@/features/auth/types/auth.types"; // ← share one source of truth

export interface Booking {
  id: string;
  location: string;
  floor: string;
  date: string;
  startTime: string;
  endTime: string;
  status: "Confirmed" | "Pending" | "Cancelled";
  isRecurring: boolean;
  seatId: string;
  managerNote: string;
}

export interface TeamMember {
  id: string;
  name: string;
  initials: string;
  floor: string;
  avatarColor?: string;
}

export interface Announcement {
  id: string;
  title: string;
  description: string;
  type: "warning" | "info" | "success";
  date?: string;
}

export interface FavouriteSeat {
  id: string;
  label: string;
  location: string;
  description: string;
  floor: string;
}

export interface DashboardStats {
  daysInMonth: number;
  trend: number;
  teamInOffice: number;
  nextSeat: string;
  nextSeatFloor: string;
}

export interface WeekDay {
  date: number;
  dayLabel: string;
  isToday: boolean;
  hasBooking: boolean;
  hasDot: boolean;
}

export interface DashboardData {
  user: User;
  stats: DashboardStats;
  weekDays: WeekDay[];
  upcomingBookings: Booking[];
  teamInOfficeToday: TeamMember[];
  announcements: Announcement[];
  favouriteSeat: FavouriteSeat;
  teamOnlineCount: number;
  teamOfflineCount: number;
  nextBookingDate: string;
}