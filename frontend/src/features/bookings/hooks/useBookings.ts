"use client";

import { useState, useEffect, useCallback } from "react";
import {
  fetchCurrentBookings,
  fetchFutureBookings,
  fetchPastBookings,
  cancelBooking,
  deriveBookingSummary,
  fetchTeamGroups,
  fetchCurrentUser,
} from "../services/bookings.service";
import { Booking, BookingSummary, BookingTab } from "../types/bookings.types";
import type { ApiTeamGroup } from "@/features/dashboard/types/dashboard.types";
import type { User } from "@/features/auth/types/auth.types";

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
  const [teamGroups, setTeamGroups] = useState<ApiTeamGroup[]>([]);
  const [currentUserId, setCurrentUserId] = useState<string>("");
  const [summary, setSummary] = useState<BookingSummary>({
    upcomingCount: 0,
    nextBookingDate: null,
    completedThisMonth: 0,
    daysInOffice: 0,
    teamInOffice: 0,
  });

  const loadBookings = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // ✅ Capture all 5 results including current user
      const [current, future, past, groups, user] = await Promise.all([
        fetchCurrentBookings(),
        fetchFutureBookings(),
        fetchPastBookings(),
        fetchTeamGroups(),
        fetchCurrentUser(),
      ]);

      setCurrentBookings(current);
      setFutureBookings(future);
      setPastBookings(past);
      setTeamGroups(groups);
      setCurrentUserId(user.user_id);

      // ✅ Pass userId so self is excluded from the team count
      setSummary(deriveBookingSummary(current, future, past, groups, user.user_id));
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
      // Optimistic update: remove from current and future lists
      setCurrentBookings((prev) => prev.filter((b) => b.id !== bookingId));
      setFutureBookings((prev) => prev.filter((b) => b.id !== bookingId));
      // Re-derive summary with updated booking lists and existing teamGroups
      setCurrentBookings((current) => {
        setFutureBookings((future) => {
          setPastBookings((past) => {
            setSummary(deriveBookingSummary(current, future, past, teamGroups, currentUserId));
            return past;
          });
          return future;
        });
        return current;
      });
    },
    [teamGroups, currentUserId]
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