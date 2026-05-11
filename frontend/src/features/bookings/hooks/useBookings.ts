 "use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchCurrentBookings,
  fetchFutureBookings,
  fetchPastBookings,
  cancelBooking,
  deriveBookingSummary,
} from "../services/bookings.service";
import { Booking, BookingSummary, BookingTab } from "../types/bookings.types";

interface UseBookingsReturn {
  // Data
  displayedBookings: Booking[];
  summary: BookingSummary;
  activeTab: BookingTab;
  // State
  isLoading: boolean;
  error: string | null;
  // Actions
  setActiveTab: (tab: BookingTab) => void;
  handleCancelBooking: (bookingId: string) => Promise<void>;
  refetch: () => void;
}

export function useBookings(): UseBookingsReturn {
  const [activeTab, setActiveTab] = useState<BookingTab>("upcoming");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [currentBookings, setCurrentBookings] = useState<Booking[]>([]);
  const [futureBookings, setFutureBookings] = useState<Booking[]>([]);
  const [pastBookings, setPastBookings] = useState<Booking[]>([]);
  const [summary, setSummary] = useState<BookingSummary>({
    upcomingCount: 0,
    nextBookingDate: null,
    completedThisMonth: 0,
    daysInOffice: 0,
    recurringCount: 0,
    recurringPattern: null,
  });

  const loadBookings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [current, future, past] = await Promise.all([
        fetchCurrentBookings(),
        fetchFutureBookings(),
        fetchPastBookings(),
      ]);
      setCurrentBookings(current);
      setFutureBookings(future);
      setPastBookings(past);
      setSummary(deriveBookingSummary(current, future, past));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load bookings");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBookings();
  }, [loadBookings]);

  const handleCancelBooking = useCallback(
    async (bookingId: string) => {
      await cancelBooking(bookingId);
      // Optimistic update: remove from all lists
      setCurrentBookings((prev) => prev.filter((b) => b.id !== bookingId));
      setFutureBookings((prev) => prev.filter((b) => b.id !== bookingId));
      // Re-derive summary
      setSummary((prev) => ({
        ...prev,
        upcomingCount: Math.max(0, prev.upcomingCount - 1),
      }));
    },
    []
  );

  // Derive which bookings to show for the active tab
  const displayedBookings = (() => {
    switch (activeTab) {
      case "upcoming":
        return [...currentBookings, ...futureBookings];
      case "past":
        return pastBookings;
      case "recurring":
        return [...currentBookings, ...futureBookings].filter((b) => b.isRecurring);
      case "cancelled":
        return [...currentBookings, ...futureBookings, ...pastBookings].filter(
          (b) => b.status === "cancelled"
        );
      default:
        return [];
    }
  })();

  return {
    displayedBookings,
    summary,
    activeTab,
    isLoading,
    error,
    setActiveTab,
    handleCancelBooking,
    refetch: loadBookings,
  };
}