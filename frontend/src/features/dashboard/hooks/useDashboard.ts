"use client";

import { useState, useEffect } from "react";
import { getDashboardData, cancelBooking } from "../services/dashboard.service";
import type { DashboardData } from "../types/dashboard.types";

export function useDashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllBookings, setShowAllBookings] = useState(false);

  async function fetchData() {
    try {
      setIsLoading(true);
      setError(null);
      const dashboardData = await getDashboardData();
      setData(dashboardData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, []);

  const refetch = async () => {
    setShowAllBookings(false);
    await fetchData();
  };

  const handleCancelBooking = async (id: string) => {
    await cancelBooking(id);
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        upcomingBookings: prev.upcomingBookings.filter((b) => b.id !== id),
      };
    });
  };

  const handleCancelToday = async (bookingId: string) => {
    await cancelBooking(bookingId);
    setData((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        todayBooking: {
          hasTodayBooking: false,
          seatCode: null,
          floor: null,
          bookingId: null,
        },
      };
    });
  };

  const allBookings = data?.upcomingBookings ?? [];

  const visibleBookings = (data?.upcomingBookings ?? []).slice(0, 2);

return {
  data,
  isLoading,
  error,
  refetch,
  visibleBookings,
  totalBookingsCount: data?.upcomingBookings.length ?? 0,
  handleCancelBooking,
  handleCancelToday,
};
}