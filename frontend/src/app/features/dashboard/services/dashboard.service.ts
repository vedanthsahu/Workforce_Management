import { BookingFormData, DashboardStats, NextBooking, Office } from "../schemas/dashboard.schema";

const BASE_URL = "http://127.0.0.1:8000";

export const fetchDashboardStats = async (): Promise<DashboardStats> => {
  const res = await fetch(`${BASE_URL}/dashboard/stats`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    const error: any = new Error("Failed to fetch stats");
    error.status = res.status;
    throw error;
  }

  return res.json();
};

export const fetchOffices = async (): Promise<Office[]> => {
  const res = await fetch(`${BASE_URL}/offices`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    const error: any = new Error("Failed to fetch offices");
    error.status = res.status;
    throw error;
  }

  return res.json();
};

export const fetchNextBooking = async (): Promise<NextBooking | null> => {
  const res = await fetch(`${BASE_URL}/bookings/next`, {
    method: "GET",
    headers: { "Content-Type": "application/json" },
  });

  if (!res.ok) {
    const error: any = new Error("Failed to fetch next booking");
    error.status = res.status;
    throw error;
  }

  return res.json();
};

export const initiateBooking = async (payload: BookingFormData) => {
  const res = await fetch(`${BASE_URL}/bookings/initiate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const error: any = new Error("Failed to initiate booking");
    error.status = res.status;
    throw error;
  }

  return res.json();
};