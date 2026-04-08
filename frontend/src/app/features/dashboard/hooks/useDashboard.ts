
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { format } from "date-fns";
import {
  BookingFormData,
  bookingSchema,
  DashboardStats,
  Floor,
  NextBooking,
  Office,
} from "../schemas/dashboard.schema";
import { initiateBooking } from "../services/dashboard.service";
import { useBooking } from "@/app/store/BookingContext";


// ─── Static data ─────────────────────────────────────────────────────────────
const STATIC_OFFICES: Office[] = [
  { id: "sf-hq",      name: "San Francisco HQ", address: "123 Market St",   floors: 5, available: 45 },
  { id: "ny-office",  name: "New York Office",  address: "456 Broadway",     floors: 3, available: 28 },
  { id: "austin-hub", name: "Austin Hub",       address: "789 Congress Ave", floors: 2, available: 18 },
];

const STATIC_STATS: DashboardStats = { bookings: 3, availableSeats: 91, teamMembers: 24 };

const STATIC_NEXT_BOOKING: NextBooking = {
  date: "Tomorrow, March 30",
  office: "San Francisco HQ - Floor 3",
  seat: "Seat A-12",
};

// ─── Helpers ─────────────────────────────────────────────────────────────────
// Stable seed per office so floors don't re-randomise on every render
const FLOOR_SEED: Record<string, number[]> = {};

const buildFloors = (office: Office): Floor[] => {
  if (!FLOOR_SEED[office.id]) {
    FLOOR_SEED[office.id] = Array.from(
      { length: office.floors },
      () => Math.floor(Math.random() * 20) + 10
    );
  }
  return Array.from({ length: office.floors }, (_, i) => ({
    id: `${office.id}-floor-${i + 1}`,
    name: `Floor ${i + 1}`,
    available: FLOOR_SEED[office.id][i],
  }));
};

// ─── Hook ─────────────────────────────────────────────────────────────────────
export const useDashboard = () => {
  const router = useRouter();
  const { updateBookingData } = useBooking();

  // Always start with static data — APIs replace these only when they succeed
  const [offices, setOffices]         = useState<Office[]>(STATIC_OFFICES);
  const [stats, setStats]             = useState<DashboardStats>(STATIC_STATS);
  const [nextBooking, setNextBooking] = useState<NextBooking>(STATIC_NEXT_BOOKING);
  const [dataLoading, setDataLoading] = useState(false);
  const [submitting, setSubmitting]   = useState(false);
  const [apiError, setApiError]       = useState("");

  // ── Form ───────────────────────────────────────────────────────────────────
  const form = useForm<BookingFormData>({
    resolver: zodResolver(bookingSchema),
    defaultValues: { office: "", floor: "", date: format(new Date(), "yyyy-MM-dd") },
    mode: "onChange",
  });

  const selectedOffice = form.watch("office");

  // ── Derive floors inline — no effect, always in sync ──────────────────────
  const selectedOfficeData = offices.find((o) => o.id === selectedOffice);
  const floors: Floor[]    = selectedOfficeData ? buildFloors(selectedOfficeData) : [];

  // ── Reset floor field whenever the selected office changes ─────────────────
  useEffect(() => {
    form.setValue("floor", "", { shouldValidate: false });
  }, [selectedOffice]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Try to load live data; silently keep statics on any failure ────────────
  useEffect(() => {
    const loadData = async () => {
      setDataLoading(true);
      try {
        const svc = await import("../services/dashboard.service");
        const [officeData, statsData, nextBookingData] = await Promise.all([
          svc.fetchOffices(),
          svc.fetchDashboardStats(),
          svc.fetchNextBooking(),
        ]);
        setOffices(officeData);
        setStats(statsData);
        if (nextBookingData) setNextBooking(nextBookingData);
      } catch {
        // APIs not ready — static fallbacks remain in state
      } finally {
        setDataLoading(false);
      }
    };

    // loadData();
  }, []);

  // ── Submit ─────────────────────────────────────────────────────────────────
  const onSubmit = async (data: BookingFormData) => {
    setSubmitting(true);
    setApiError("");

    try {
      await initiateBooking(data);
      updateBookingData({ office: data.office, floor: data.floor, date: data.date });
      router.push("/seat-selection");
    } catch (err: any) {
      const status = err?.response?.status || err?.status;

      if (status === 401) {
        setApiError("Session expired. Please log in again.");
        setTimeout(() => router.push("/login"), 1500);
      } else if (status === 409) {
        setApiError("You already have a booking for this date.");
      } else if (status === 500) {
        setApiError("Server error. Please try again later.");
      } else if (err?.message === "Network Error") {
        setApiError("Network error. Check your internet connection.");
      } else {
        // API not ready — navigate directly (dev fallback)
        updateBookingData({ office: data.office, floor: data.floor, date: data.date });
        router.push("/seat-selection");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return {
    form,
    onSubmit,
    offices,
    floors,
    selectedOffice, 
    stats,
    nextBooking,
    dataLoading,
    submitting,
    apiError,
  };
};