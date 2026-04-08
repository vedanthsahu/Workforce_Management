import { z } from "zod";

export const bookingSchema = z.object({
  office: z.string().min(1, "Please select an office"),
  floor: z.string().min(1, "Please select a floor"),
  date: z.string().min(1, "Please select a date"),
});

export type BookingFormData = z.infer<typeof bookingSchema>;

export interface Office {
  id: string;
  name: string;
  address: string;
  floors: number;
  available: number;
}

export interface Floor {
  id: string;
  name: string;
  available: number;
}

export interface DashboardStats {
  bookings: number;
  availableSeats: number;
  teamMembers: number;
}

export interface NextBooking {
  date: string;
  office: string;
  seat: string;
}