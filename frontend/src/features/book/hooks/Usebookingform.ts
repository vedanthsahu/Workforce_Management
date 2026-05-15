"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BookingFormState,
  BookingStep,
  Building,
  CreateBookingResponse,
  Floor,
  Preference,
  Seat,
  Site,
} from "../types/Bookingform.types";

import {
  createBooking,
  fetchBuildings,
  fetchFloors,
  fetchPreferences,
  fetchSeatsWithAvailability, // ← was fetchSeats (removed), use this instead
  fetchSites,
} from "../services/Bookingform.service";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function plusDaysIso(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

const DEFAULT_STATE: BookingFormState = {
  siteId: "",
  buildingId: "",
  floorId: "",
  fromDate: todayIso(),
  toDate: plusDaysIso(2),
  preferences: [],
  selectedSeatId: null,
};

export function useBookingForm() {
  const [step, setStep] = useState<BookingStep>(1);
  const [form, setForm] = useState<BookingFormState>(DEFAULT_STATE);

  const [sites, setSites] = useState<Site[]>([]);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [seats, setSeats] = useState<Seat[]>([]);
  const [availablePreferences, setAvailablePreferences] = useState<Preference[]>([]);

  const [loadingSites, setLoadingSites] = useState(false);
  const [loadingBuildings, setLoadingBuildings] = useState(false);
  const [loadingFloors, setLoadingFloors] = useState(false);
  const [loadingSeats, setLoadingSeats] = useState(false);
  const [loadingPreferences, setLoadingPreferences] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<CreateBookingResponse | null>(null);

  // ── Load sites on mount ──────────────────────────────────────────────────
  useEffect(() => {
    setLoadingSites(true);
    fetchSites()
      .then(setSites)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingSites(false));
  }, []);

  // ── Load preferences on mount ────────────────────────────────────────────
  useEffect(() => {
    setLoadingPreferences(true);
    fetchPreferences()
      .then(setAvailablePreferences)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingPreferences(false));
  }, []);

  // ── Load buildings when siteId changes ──────────────────────────────────
  useEffect(() => {
    if (!form.siteId) {
      setBuildings([]);
      setFloors([]);
      return;
    }
    setBuildings([]);
    setFloors([]);
    setLoadingBuildings(true);
    fetchBuildings(form.siteId)
      .then(setBuildings)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingBuildings(false));
  }, [form.siteId]);

  // ── Load floors when buildingId changes ─────────────────────────────────
  useEffect(() => {
    if (!form.buildingId) {
      setFloors([]);
      return;
    }
    setFloors([]);
    setLoadingFloors(true);
    fetchFloors(form.buildingId)
      .then(setFloors)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingFloors(false));
  }, [form.buildingId]);

  // ── Field setters ────────────────────────────────────────────────────────

  const setSiteId = (v: string | null) =>
    setForm((f) => ({
      ...f,
      siteId: v ?? "",
      buildingId: "",
      floorId: "",
      selectedSeatId: null,
    }));

  const setBuildingId = (v: string | null) =>
    setForm((f) => ({
      ...f,
      buildingId: v ?? "",
      floorId: "",
      selectedSeatId: null,
    }));

  const setFloorId = (v: string | null) =>
    setForm((f) => ({
      ...f,
      floorId: v ?? "",
      selectedSeatId: null,
    }));

  const setFromDate = (v: string) =>
    setForm((f) => ({
      ...f,
      fromDate: v,
      toDate: f.toDate < v ? v : f.toDate,
    }));

  const setToDate = (v: string) =>
    setForm((f) => ({ ...f, toDate: v }));

  const togglePreference = (key: string) =>
    setForm((f) => ({
      ...f,
      preferences: f.preferences.includes(key)
        ? f.preferences.filter((p) => p !== key)
        : [...f.preferences, key],
    }));

  const clearAll = () =>
    setForm((f) => ({ ...f, preferences: [] }));

  // ── Step 1 → Step 2: load seats ──────────────────────────────────────────
  // Uses fetchSeatsWithAvailability — /bookings/available is the source of
  // truth. Seats absent from that response are shown as "booked" in the UI.

  const findAvailableSeats = useCallback(async () => {
    if (!form.floorId || !form.fromDate || !form.toDate) return;

    setLoadingSeats(true);
    setError(null);

    try {
      const data = await fetchSeatsWithAvailability({
        floorId: form.floorId,
        fromDate: form.fromDate,
        toDate: form.toDate,
        preferences: form.preferences,
      });
      setSeats(data);
      setStep(2);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load seats");
    } finally {
      setLoadingSeats(false);
    }
  }, [form]);

  // ── Step 2: select seat ──────────────────────────────────────────────────

  // const selectSeat = (seatId: string) =>
  //   setForm((f) => ({ ...f, selectedSeatId: seatId }));
  const selectSeat = (seatId: string | null) => {
  setForm((f) => ({ ...f, selectedSeatId: seatId }));
};

  const goToReview = () => {
    if (!form.selectedSeatId) return;
    setStep(3);
  };

  // ── Step 3: confirm booking ──────────────────────────────────────────────

  // const confirmBooking = useCallback(async () => {
  //   if (!form.selectedSeatId) return;

  //   setSubmitting(true);
  //   setError(null);

  //   try {
  //     const result = await createBooking({
  //       siteId: form.siteId,
  //       buildingId: form.buildingId,
  //       floorId: form.floorId,
  //       seatId: form.selectedSeatId,
  //       fromDate: form.fromDate,
  //       toDate: form.toDate,
  //       preferences: form.preferences,
  //     });
  //     setConfirmation(result);
  //   } catch (e: unknown) {
  //     setError(
  //       e instanceof Error ? e.message : "Booking failed. Please try again."
  //     );
  //   } finally {
  //     setSubmitting(false);
  //   }
  // }, [form]);

  const confirmBooking = useCallback(async () => {
  if (!form.selectedSeatId) return;

  setSubmitting(true);
  setError(null);

  try {
    const result = await createBooking({
      site_id:      Number(form.siteId),
      building_id:  Number(form.buildingId),
      floor_id:     Number(form.floorId),
      seat_id:      Number(form.selectedSeatId),
      booking_date: form.fromDate,   // "YYYY-MM-DD" string, backend expects `date`
    });
    setConfirmation(result);
    setStep(3); // or however you signal success
  // } catch (e: unknown) {
  //   setError(
  //     e instanceof Error ? e.message : "Booking failed. Please try again."
  //   );
  } catch (err: any) {
  const status = err?.response?.status;
  if (status === 409) {
    setError("You already have a booking for this seat on the selected date. Please choose a different seat or date.");
  } else if (status === 400) {
    setError("Invalid booking details. Please go back and check your selection.");
  } else if (status === 403) {
    setError("You don't have permission to book this seat.");
  } else if (status === 404) {
    setError("The selected seat is no longer available. Please go back and choose another.");
  } else {
    setError(err?.response?.data?.message ?? err?.message ?? "Failed to confirm booking. Please try again.");
  }

  } finally {
    setSubmitting(false);
  }
}, [form]);

  // ── Navigation helpers ───────────────────────────────────────────────────

  const goBack = () =>
    setStep((s) => (s > 1 ? ((s - 1) as BookingStep) : s));

  const resetForm = () => {
    setForm(DEFAULT_STATE);
    setBuildings([]);
    setFloors([]);
    setSeats([]);
    setConfirmation(null);
    setError(null);
    setStep(1);
  };

  // ── Derived ──────────────────────────────────────────────────────────────

  const selectedSite     = sites.find((s) => s.id === form.siteId);
  const selectedBuilding = buildings.find((b) => b.id === form.buildingId);
  const selectedFloor    = floors.find((f) => f.id === form.floorId);
  const selectedSeat     = seats.find((s) => s.id === form.selectedSeatId);

  const dayCount = (() => {
    if (!form.fromDate || !form.toDate) return 0;
    const diff =
      new Date(form.toDate + "T00:00:00").getTime() -
      new Date(form.fromDate + "T00:00:00").getTime();
    return Math.round(diff / 86_400_000) + 1;
  })();

  const step1Valid =
    !!form.siteId &&
    !!form.buildingId &&
    !!form.floorId &&
    !!form.fromDate &&
    !!form.toDate;

  return {
    step,
    form,
    sites,
    buildings,
    floors,
    seats,
    availablePreferences,
    confirmation,
    error,
    loadingSites,
    loadingBuildings,
    loadingFloors,
    loadingSeats,
    loadingPreferences,
    submitting,
    selectedSite,
    selectedBuilding,
    selectedFloor,
    selectedSeat,
    dayCount,
    step1Valid,
    setSiteId,
    setBuildingId,
    setFloorId,
    setFromDate,
    setToDate,
    togglePreference,
    clearAll,
    findAvailableSeats,
    selectSeat,
    goToReview,
    confirmBooking,
    goBack,
    resetForm,
  };
}