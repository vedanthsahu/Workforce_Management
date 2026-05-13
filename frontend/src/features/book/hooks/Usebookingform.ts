// "use client";

// import { useCallback, useEffect, useState } from "react";
// import { BookingFormState, BookingStep, Building, CreateBookingResponse, Floor, PreferenceKey, Seat, Site } from "../types/Bookingform.types";
// import { createBooking, fetchBuildings, fetchFloors, fetchSeats, fetchSites } from "../services/Bookingform.service";


// // ── Default form state ────────────────────────────────────────────────────────

// function todayIso(): string {
//   return new Date().toISOString().slice(0, 10);
// }

// function plusDaysIso(n: number): string {
//   const d = new Date();
//   d.setDate(d.getDate() + n);
//   return d.toISOString().slice(0, 10);
// }

// const DEFAULT_STATE: BookingFormState = {
//   siteId: "",
//   buildingId: "",
//   floorId: "",
//   fromDate: todayIso(),
//   toDate: plusDaysIso(2),
//   preferences: [],
//   selectedSeatId: null,
// };

// // ── Hook ──────────────────────────────────────────────────────────────────────

// export function useBookingForm() {
//   // ── Navigation ──────────────────────────────────────────────────────────────
//   const [step, setStep] = useState<BookingStep>(1);

//   // ── Form values ─────────────────────────────────────────────────────────────
//   const [form, setForm] = useState<BookingFormState>(DEFAULT_STATE);

//   // ── Reference data ──────────────────────────────────────────────────────────
//   const [sites, setSites]         = useState<Site[]>([]);
//   const [buildings, setBuildings] = useState<Building[]>([]);
//   const [floors, setFloors]       = useState<Floor[]>([]);
//   const [seats, setSeats]         = useState<Seat[]>([]);

//   // ── Loading / error per resource ────────────────────────────────────────────
//   const [loadingSites,     setLoadingSites]     = useState(false);
//   const [loadingBuildings, setLoadingBuildings] = useState(false);
//   const [loadingFloors,    setLoadingFloors]    = useState(false);
//   const [loadingSeats,     setLoadingSeats]     = useState(false);
//   const [submitting,       setSubmitting]       = useState(false);

//   const [error,            setError]            = useState<string | null>(null);
//   const [confirmation,     setConfirmation]     = useState<CreateBookingResponse | null>(null);

//   // ── Load sites on mount ─────────────────────────────────────────────────────
//   useEffect(() => {
//     setLoadingSites(true);
//     fetchSites()
//       .then(setSites)
//       .catch((e) => setError(e.message))
//       .finally(() => setLoadingSites(false));
//   }, []);

//   // ── Load buildings when site changes ────────────────────────────────────────
//   useEffect(() => {
//     if (!form.siteId) { setBuildings([]); return; }
//     setLoadingBuildings(true);
//     setForm((f) => ({ ...f, buildingId: "", floorId: "" }));
//     setFloors([]);
//     fetchBuildings(form.siteId)
//       .then(setBuildings)
//       .catch((e) => setError(e.message))
//       .finally(() => setLoadingBuildings(false));
//   }, [form.siteId]);

//   // ── Load floors when building changes ───────────────────────────────────────
//   useEffect(() => {
//     if (!form.buildingId) { setFloors([]); return; }
//     setLoadingFloors(true);
//     setForm((f) => ({ ...f, floorId: "" }));
//     fetchFloors(form.buildingId)
//       .then(setFloors)
//       .catch((e) => setError(e.message))
//       .finally(() => setLoadingFloors(false));
//   }, [form.buildingId]);

//   // ── Field setters ───────────────────────────────────────────────────────────

//   const setSiteId     = (v: string) => setForm((f) => ({ ...f, siteId: v }));
//   const setBuildingId = (v: string) => setForm((f) => ({ ...f, buildingId: v }));
//   const setFloorId    = (v: string) => setForm((f) => ({ ...f, floorId: v }));
//   const setFromDate   = (v: string) => setForm((f) => ({
//     ...f,
//     fromDate: v,
//     toDate: f.toDate < v ? v : f.toDate,
//   }));
//   const setToDate     = (v: string) => setForm((f) => ({ ...f, toDate: v }));

//   const togglePreference = (key: PreferenceKey) =>
//     setForm((f) => ({
//       ...f,
//       preferences: f.preferences.includes(key)
//         ? f.preferences.filter((p) => p !== key)
//         : [...f.preferences, key],
//     }));

//   const clearAll = () => setForm((f) => ({ ...f, preferences: [] }));

//   // ── Step 1 → Step 2: load seats ─────────────────────────────────────────────

//   const findAvailableSeats = useCallback(async () => {
//     if (!form.floorId || !form.fromDate || !form.toDate) return;
//     setLoadingSeats(true);
//     setError(null);
//     try {
//       const data = await fetchSeats({
//         floorId: form.floorId,
//         fromDate: form.fromDate,
//         toDate: form.toDate,
//         preferences: form.preferences,
//       });
//       setSeats(data);
//       setStep(2);
//     } catch (e: unknown) {
//       setError(e instanceof Error ? e.message : "Failed to load seats");
//     } finally {
//       setLoadingSeats(false);
//     }
//   }, [form]);

//   // ── Step 2: select seat ──────────────────────────────────────────────────────

//   const selectSeat = (seatId: string) =>
//     setForm((f) => ({ ...f, selectedSeatId: seatId }));

//   const goToReview = () => {
//     if (!form.selectedSeatId) return;
//     setStep(3);
//   };

//   // ── Step 3: confirm booking ──────────────────────────────────────────────────

//   const confirmBooking = useCallback(async () => {
//     if (!form.selectedSeatId) return;
//     setSubmitting(true);
//     setError(null);
//     try {
//       const result = await createBooking({
//         siteId:      form.siteId,
//         buildingId:  form.buildingId,
//         floorId:     form.floorId,
//         seatId:      form.selectedSeatId,
//         fromDate:    form.fromDate,
//         toDate:      form.toDate,
//         preferences: form.preferences,
//       });
//       setConfirmation(result);
//     } catch (e: unknown) {
//       setError(e instanceof Error ? e.message : "Booking failed. Please try again.");
//     } finally {
//       setSubmitting(false);
//     }
//   }, [form]);

//   // ── Navigation helpers ───────────────────────────────────────────────────────

//   const goBack = () => setStep((s) => (s > 1 ? ((s - 1) as BookingStep) : s));

//   const resetForm = () => {
//     setForm(DEFAULT_STATE);
//     setSeats([]);
//     setConfirmation(null);
//     setError(null);
//     setStep(1);
//   };

//   // ── Derived ──────────────────────────────────────────────────────────────────

//   const selectedSite     = sites.find((s) => s.id === form.siteId);
//   const selectedBuilding = buildings.find((b) => b.id === form.buildingId);
//   const selectedFloor    = floors.find((f) => f.id === form.floorId);
//   const selectedSeat     = seats.find((s) => s.id === form.selectedSeatId);

//   const dayCount = (() => {
//     if (!form.fromDate || !form.toDate) return 0;
//     const diff =
//       new Date(form.toDate + "T00:00:00").getTime() -
//       new Date(form.fromDate + "T00:00:00").getTime();
//     return Math.round(diff / 86_400_000) + 1;
//   })();

//   const step1Valid = !!form.siteId && !!form.buildingId && !!form.floorId &&
//     !!form.fromDate && !!form.toDate;

//   return {
//     // state
//     step,
//     form,
//     sites,
//     buildings,
//     floors,
//     seats,
//     confirmation,
//     error,
//     // loading flags
//     loadingSites,
//     loadingBuildings,
//     loadingFloors,
//     loadingSeats,
//     submitting,
//     // derived
//     selectedSite,
//     selectedBuilding,
//     selectedFloor,
//     selectedSeat,
//     dayCount,
//     step1Valid,
//     // actions
//     setSiteId,
//     setBuildingId,
//     setFloorId,
//     setFromDate,
//     setToDate,
//     togglePreference,
//     clearAll,
//     findAvailableSeats,
//     selectSeat,
//     goToReview,
//     confirmBooking,
//     goBack,
//     resetForm,
//   };
// }


"use client";

import { useCallback, useEffect, useState } from "react";
import {
  BookingFormState,
  BookingStep,
  Building,
  CreateBookingResponse,
  Floor,
  PreferenceKey,
  Seat,
  Site,
} from "../types/Bookingform.types";

import {
  createBooking,
  fetchBuildings,
  fetchFloors,
  fetchSeats,
  fetchSites,
} from "../services/Bookingform.service";

// ── Default form state ────────────────────────────────────────────────────────

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

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useBookingForm() {
  // ── Navigation ──────────────────────────────────────────────────────────────
  const [step, setStep] = useState<BookingStep>(1);

  // ── Form values ─────────────────────────────────────────────────────────────
  const [form, setForm] = useState<BookingFormState>(DEFAULT_STATE);

  // ── Reference data ──────────────────────────────────────────────────────────
  const [sites, setSites] = useState<Site[]>([]);
  const [buildings, setBuildings] = useState<Building[]>([]);
  const [floors, setFloors] = useState<Floor[]>([]);
  const [seats, setSeats] = useState<Seat[]>([]);

  // ── Loading / error per resource ───────────────────────────────────────────
  const [loadingSites, setLoadingSites] = useState(false);
  const [loadingBuildings, setLoadingBuildings] = useState(false);
  const [loadingFloors, setLoadingFloors] = useState(false);
  const [loadingSeats, setLoadingSeats] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState<string | null>(null);

  const [confirmation, setConfirmation] =
    useState<CreateBookingResponse | null>(null);

  // ── Load sites on mount ────────────────────────────────────────────────────
  useEffect(() => {
    setLoadingSites(true);

    fetchSites()
      .then(setSites)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingSites(false));
  }, []);

  // ── Load buildings when site changes ───────────────────────────────────────
  useEffect(() => {
    if (!form.siteId) {
      setBuildings([]);
      return;
    }

    setLoadingBuildings(true);

    setForm((f) => ({
      ...f,
      buildingId: "",
      floorId: "",
    }));

    setFloors([]);

    fetchBuildings(form.siteId)
      .then(setBuildings)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingBuildings(false));
  }, [form.siteId]);

  // ── Load floors when building changes ──────────────────────────────────────
  useEffect(() => {
    if (!form.buildingId) {
      setFloors([]);
      return;
    }

    setLoadingFloors(true);

    setForm((f) => ({
      ...f,
      floorId: "",
    }));

    fetchFloors(form.buildingId)
      .then(setFloors)
      .catch((e) => setError(e.message))
      .finally(() => setLoadingFloors(false));
  }, [form.buildingId]);

  // ── Field setters ──────────────────────────────────────────────────────────

  const setSiteId = (v: string | null) =>
    setForm((f) => ({
      ...f,
      siteId: v ?? "",
    }));

  const setBuildingId = (v: string | null) =>
    setForm((f) => ({
      ...f,
      buildingId: v ?? "",
    }));

  const setFloorId = (v: string | null) =>
    setForm((f) => ({
      ...f,
      floorId: v ?? "",
    }));

  const setFromDate = (v: string) =>
    setForm((f) => ({
      ...f,
      fromDate: v,
      toDate: f.toDate < v ? v : f.toDate,
    }));

  const setToDate = (v: string) =>
    setForm((f) => ({
      ...f,
      toDate: v,
    }));

  const togglePreference = (key: PreferenceKey) =>
    setForm((f) => ({
      ...f,
      preferences: f.preferences.includes(key)
        ? f.preferences.filter((p) => p !== key)
        : [...f.preferences, key],
    }));

  const clearAll = () =>
    setForm((f) => ({
      ...f,
      preferences: [],
    }));

  // ── Step 1 → Step 2: load seats ────────────────────────────────────────────

  const findAvailableSeats = useCallback(async () => {
    if (!form.floorId || !form.fromDate || !form.toDate) return;

    setLoadingSeats(true);
    setError(null);

    try {
      const data = await fetchSeats({
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

  // ── Step 2: select seat ────────────────────────────────────────────────────

  const selectSeat = (seatId: string) =>
    setForm((f) => ({
      ...f,
      selectedSeatId: seatId,
    }));

  const goToReview = () => {
    if (!form.selectedSeatId) return;
    setStep(3);
  };

  // ── Step 3: confirm booking ────────────────────────────────────────────────

  const confirmBooking = useCallback(async () => {
    if (!form.selectedSeatId) return;

    setSubmitting(true);
    setError(null);

    try {
      const result = await createBooking({
        siteId: form.siteId,
        buildingId: form.buildingId,
        floorId: form.floorId,
        seatId: form.selectedSeatId,
        fromDate: form.fromDate,
        toDate: form.toDate,
        preferences: form.preferences,
      });

      setConfirmation(result);
    } catch (e: unknown) {
      setError(
        e instanceof Error
          ? e.message
          : "Booking failed. Please try again."
      );
    } finally {
      setSubmitting(false);
    }
  }, [form]);

  // ── Navigation helpers ─────────────────────────────────────────────────────

  const goBack = () =>
    setStep((s) => (s > 1 ? ((s - 1) as BookingStep) : s));

  const resetForm = () => {
    setForm(DEFAULT_STATE);
    setSeats([]);
    setConfirmation(null);
    setError(null);
    setStep(1);
  };

  // ── Derived ────────────────────────────────────────────────────────────────

  const selectedSite = sites.find((s) => s.id === form.siteId);

  const selectedBuilding = buildings.find(
    (b) => b.id === form.buildingId
  );

  const selectedFloor = floors.find(
    (f) => f.id === form.floorId
  );

  const selectedSeat = seats.find(
    (s) => s.id === form.selectedSeatId
  );

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
    // state
    step,
    form,
    sites,
    buildings,
    floors,
    seats,
    confirmation,
    error,

    // loading flags
    loadingSites,
    loadingBuildings,
    loadingFloors,
    loadingSeats,
    submitting,

    // derived
    selectedSite,
    selectedBuilding,
    selectedFloor,
    selectedSeat,
    dayCount,
    step1Valid,

    // actions
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

