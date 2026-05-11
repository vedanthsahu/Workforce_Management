 "use client";

import { useCallback, useEffect, useState } from "react";

import type { DashboardData } from "../types/dashboard.types";
import { cancelBooking, DashboardSectionError, getDashboardData } from "../services/dashboard.service";

const MAX_VISIBLE_BOOKINGS = 2;

type HookState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "fatal"; error: DashboardSectionError }
  | { status: "ready"; data: DashboardData; sectionErrors: DashboardSectionError[] };

export function useDashboard() {
  const [state, setState] = useState<HookState>({ status: "idle" });

  const load = useCallback(async () => {
    setState({ status: "loading" });
    const result = await getDashboardData();

    if (!result.ok) {
      setState({ status: "fatal", error: result.fatal });
      return;
    }

    setState({ status: "ready", data: result.data, sectionErrors: result.errors });
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleCancelBooking = useCallback(async (bookingId: string) => {
    if (state.status !== "ready") return;
    await cancelBooking(bookingId);
    // Optimistically remove from local state
    setState((prev) => {
      if (prev.status !== "ready") return prev;
      return {
        ...prev,
        data: {
          ...prev.data,
          upcomingBookings: prev.data.upcomingBookings.filter((b) => b.id !== bookingId),
        },
      };
    });
  }, [state.status]);

  const handleCancelToday = useCallback(async (bookingId: string) => {
    if (state.status !== "ready") return;
    await cancelBooking(bookingId);
    setState((prev) => {
      if (prev.status !== "ready") return prev;
      return {
        ...prev,
        data: {
          ...prev.data,
          todayBooking: { hasTodayBooking: false, seatCode: null, floor: null, bookingId: null },
        },
      };
    });
  }, [state.status]);

  // Derived values — safe regardless of state
  const data = state.status === "ready" ? state.data : null;
  const visibleBookings = data?.upcomingBookings.slice(0, MAX_VISIBLE_BOOKINGS) ?? [];
  const totalBookingsCount = data?.upcomingBookings.length ?? 0;
  const sectionErrors = state.status === "ready" ? state.sectionErrors : [];

  return {
    // State
    isLoading: state.status === "idle" || state.status === "loading",
    isFatal: state.status === "fatal",
    fatalError: state.status === "fatal" ? state.error : null,
    data,
    sectionErrors,
    // Actions
    refetch: load,
    visibleBookings,
    totalBookingsCount,
    handleCancelBooking,
    handleCancelToday,
  };
}