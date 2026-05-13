"use client";

import React, { useState } from "react";
import {
  Building2,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  MonitorDot,
  RefreshCw,
  Settings2,
  UtensilsCrossed,
  Waves,
  Wind,
  X,
} from "lucide-react";

import { AppSidebar } from "@/features/dashboard/components/AppSidebar";
import { useAuthContext } from "@/features/auth/context/AuthContext";
import { SidebarProvider } from "@/components/ui/sidebar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

import { useBookingForm } from "../hooks/Usebookingform";
import { PreferenceKey, Seat } from "../types/Bookingform.types";

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string): string {
  const d = new Date(iso + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

// ── Preference config ─────────────────────────────────────────────────────────

const PREFERENCES: { key: PreferenceKey; label: string; icon: React.ReactNode }[] = [
  { key: "window",      label: "Window Seat",   icon: <Wind size={20} className="text-green-500" /> },
  { key: "cafeteria",   label: "Near Cafeteria", icon: <UtensilsCrossed size={20} className="text-orange-400" /> },
  { key: "elevator",    label: "Near Elevator",  icon: <Waves size={20} className="text-violet-500" /> },
  { key: "dualMonitor", label: "Dual Monitor",   icon: <MonitorDot size={20} className="text-blue-500" /> },
];

// ── Step indicator ────────────────────────────────────────────────────────────

interface StepDotProps {
  number: number;
  label: string;
  sublabel: string;
  active: boolean;
  done: boolean;
}

const StepDot: React.FC<StepDotProps> = ({ number, label, sublabel, active, done }) => (
  <div className="flex items-center gap-3">
    <div className={cn(
      "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold shrink-0 transition-colors",
      done   ? "bg-indigo-600 text-white" :
      active ? "bg-indigo-600 text-white" :
               "border-2 border-gray-300 text-gray-400 bg-white"
    )}>
      {done ? <CheckCircle2 size={16} /> : number}
    </div>
    <div>
      <p className={cn("text-[13px] font-semibold leading-tight", active ? "text-[#1A1A2E]" : "text-gray-400")}>
        {label}
      </p>
      <p className="text-[11px] text-gray-400 leading-tight mt-0.5">{sublabel}</p>
    </div>
  </div>
);

const StepArrow = () => (
  <ChevronRight size={16} className="text-gray-300 shrink-0" />
);

// ── Section header ────────────────────────────────────────────────────────────

const SectionHeader: React.FC<{ icon: React.ReactNode; title: string; subtitle: string }> = ({ icon, title, subtitle }) => (
  <div className="flex items-center gap-3 mb-5">
    <div className="w-8 h-8 rounded-lg bg-indigo-50 flex items-center justify-center text-indigo-600 shrink-0">
      {icon}
    </div>
    <div>
      <p className="text-[14px] font-bold text-[#1A1A2E] leading-tight">{title}</p>
      <p className="text-[12px] text-gray-400 mt-0.5">{subtitle}</p>
    </div>
  </div>
);

// ── Seat tile (for floor map step) ───────────────────────────────────────────

const SeatTile: React.FC<{ seat: Seat; selected: boolean; onSelect: () => void }> = ({
  seat, selected, onSelect,
}) => {
  const isSelectable = seat.status === "available";
  return (
    <button
      onClick={isSelectable ? onSelect : undefined}
      disabled={!isSelectable}
      className={cn(
        "w-10 h-10 rounded-lg text-[10px] font-semibold flex flex-col items-center justify-center border transition-all duration-150",
        seat.status === "booked"       && "bg-gray-100 border-gray-200 text-gray-300 cursor-not-allowed",
        seat.status === "unavailable"  && "bg-red-50 border-red-100 text-red-300 cursor-not-allowed",
        seat.status === "available" && !selected && !seat.matchesPreferences &&
          "bg-white border-[#EBEBF5] text-gray-600 hover:border-indigo-300 hover:bg-indigo-50",
        seat.status === "available" && !selected && seat.matchesPreferences &&
          "bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100",
        selected && "bg-indigo-600 border-indigo-600 text-white shadow-md scale-105",
      )}
    >
      <span>{seat.label}</span>
      {seat.matchesPreferences && !selected && (
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 mt-0.5" />
      )}
    </button>
  );
};

// ── Summary row ───────────────────────────────────────────────────────────────

const SummaryRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex justify-between items-center py-3 border-b border-[#EBEBF5] last:border-0">
    <span className="text-[12.5px] text-gray-500">{label}</span>
    <span className="text-[13px] font-semibold text-[#1A1A2E]">{value}</span>
  </div>
);

// ── Date input ────────────────────────────────────────────────────────────────

const DateInput: React.FC<{ label: string; value: string; min?: string; onChange: (v: string) => void }> = ({
  label, value, min, onChange,
}) => (
  <div className="flex-1 min-w-0">
    <p className="text-[11px] font-medium text-gray-500 mb-1.5">{label}</p>
    <div className="relative">
      <CalendarDays size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" />
      <input
        type="date"
        value={value}
        min={min}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          "w-full h-10 pl-8 pr-3 rounded-lg border border-[#EBEBF5] bg-white",
          "text-[13px] text-[#1A1A2E] focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent",
          "cursor-pointer"
        )}
      />
    </div>
  </div>
);

// ── Page ──────────────────────────────────────────────────────────────────────

const BookASeatPage: React.FC = () => {
  const { user } = useAuthContext();
  const {
    step,
    form,
    sites,
    buildings,
    floors,
    seats,
    confirmation,
    error,
    loadingSites,
    loadingBuildings,
    loadingFloors,
    loadingSeats,
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
  } = useBookingForm();

  // Group seats by row for the floor map
  const seatRows = seats.reduce<Record<number, Seat[]>>((acc, seat) => {
    (acc[seat.row] = acc[seat.row] ?? []).push(seat);
    return acc;
  }, {});

  const todayIso = new Date().toISOString().slice(0, 10);

  return (
    <SidebarProvider>
      <div className="flex h-screen bg-[#F7F8FC] font-sans overflow-hidden w-full">
        <AppSidebar user={user} />

        <main className="flex-1 overflow-y-auto px-8 py-6 flex flex-col gap-5">

          {/* ── Header ── */}
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-[20px] font-bold text-[#1A1A2E] leading-tight">Book a Seat</h1>
              <p className="text-[12.5px] text-gray-400 mt-0.5">
                Reserve your workspace in a few steps
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={resetForm}
              className="h-8 gap-1.5 text-[12.5px] text-gray-600"
            >
              <RefreshCw size={13} />
              Start over
            </Button>
          </div>

          {/* ── Step indicator ── */}
          <div className="flex items-center gap-3 bg-white border border-[#EBEBF5] rounded-xl px-6 py-4">
            <StepDot
              number={1}
              label="Workspace & Preferences"
              sublabel="Select your workspace, dates and preferences"
              active={step === 1}
              done={step > 1}
            />
            <StepArrow />
            <StepDot
              number={2}
              label="Select a Seat"
              sublabel="Choose your preferred seat on the floor map"
              active={step === 2}
              done={step > 2}
            />
            <StepArrow />
            <StepDot
              number={3}
              label="Review & Confirm"
              sublabel="Review your booking and confirm"
              active={step === 3}
              done={!!confirmation}
            />
          </div>

          {/* ── Error banner ── */}
          {error && (
            <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-3 text-red-500 text-[13px] flex items-center justify-between">
              {error}
              <button onClick={() => {}} className="ml-4 text-red-400 hover:text-red-600">
                <X size={14} />
              </button>
            </div>
          )}

          {/* ════════════════════════════════════════════════════
              STEP 1 – Workspace & Preferences
          ════════════════════════════════════════════════════ */}
          {step === 1 && (
            <div className="bg-white border border-[#EBEBF5] rounded-xl p-6 flex flex-col gap-7">

              {/* Title */}
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-indigo-50 flex items-center justify-center">
                  <Building2 size={20} className="text-indigo-600" />
                </div>
                <div>
                  <p className="text-[15px] font-bold text-[#1A1A2E]">Workspace & Preferences</p>
                  <p className="text-[12px] text-gray-400">Tell us where and when you plan to work</p>
                </div>
              </div>

              <Separator />

              {/* 1. Select Workspace */}
              <section>
                <SectionHeader
                  icon={<Building2 size={15} />}
                  title="1. Select Workspace"
                  subtitle="Choose your office location, building and floor"
                />
                <div className="grid grid-cols-3 gap-4">
                  {/* Site */}
                  <div>
                    <p className="text-[11px] font-medium text-gray-500 mb-1.5">Site (Office Location)</p>
                    <Select value={form.siteId} onValueChange={setSiteId} disabled={loadingSites}>
                      <SelectTrigger className="h-10 text-[13px] border-[#EBEBF5]">
                        <SelectValue placeholder={loadingSites ? "Loading…" : "Select site"} />
                      </SelectTrigger>
                      <SelectContent>
                        {sites.map((s) => (
                          <SelectItem key={s.id} value={s.id}>
                            <div>
                              <p className="text-[13px] font-medium">{s.name}</p>
                              <p className="text-[11px] text-gray-400">{s.city}, {s.country} · {s.timezone}</p>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Building */}
                  <div>
                    <p className="text-[11px] font-medium text-gray-500 mb-1.5">Building</p>
                    <Select
                      value={form.buildingId}
                      onValueChange={setBuildingId}
                      disabled={!form.siteId || loadingBuildings}
                    >
                      <SelectTrigger className="h-10 text-[13px] border-[#EBEBF5]">
                        <SelectValue placeholder={loadingBuildings ? "Loading…" : "Select building"} />
                      </SelectTrigger>
                      <SelectContent>
                        {buildings.map((b) => (
                          <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Floor */}
                  <div>
                    <p className="text-[11px] font-medium text-gray-500 mb-1.5">Floor</p>
                    <Select
                      value={form.floorId}
                      onValueChange={setFloorId}
                      disabled={!form.buildingId || loadingFloors}
                    >
                      <SelectTrigger className="h-10 text-[13px] border-[#EBEBF5]">
                        <SelectValue placeholder={loadingFloors ? "Loading…" : "Select floor"} />
                      </SelectTrigger>
                      <SelectContent>
                        {floors.map((f) => (
                          <SelectItem key={f.id} value={f.id}>{f.name}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </section>

              {/* 2. Select Dates */}
              <section>
                <SectionHeader
                  icon={<CalendarDays size={15} />}
                  title="2. Select Dates"
                  subtitle="Choose the dates you'll be coming to the office"
                />
                <div className="flex gap-4 items-end">
                  <div className="flex gap-3 flex-1 items-center">
                    <DateInput
                      label="From"
                      value={form.fromDate}
                      min={todayIso}
                      onChange={setFromDate}
                    />
                    <ChevronRight size={16} className="text-gray-300 shrink-0 mt-5" />
                    <DateInput
                      label="To"
                      value={form.toDate}
                      min={form.fromDate}
                      onChange={setToDate}
                    />
                  </div>

                  {/* Day count summary */}
                  {dayCount > 0 && (
                    <div className="flex-shrink-0 bg-indigo-50 border border-indigo-100 rounded-xl px-5 py-3 min-w-[220px]">
                      <div className="flex items-center gap-2 mb-1">
                        <CalendarDays size={14} className="text-indigo-500" />
                        <span className="text-[13px] font-semibold text-indigo-700">
                          {dayCount} {dayCount === 1 ? "day" : "days"} selected
                        </span>
                      </div>
                      <p className="text-[11.5px] text-indigo-500">
                        {fmtDate(form.fromDate)} – {fmtDate(form.toDate)}
                      </p>
                      <p className="text-[11px] text-indigo-400 mt-1">
                        You will be able to select a seat for all days in the next step.
                      </p>
                    </div>
                  )}
                </div>
              </section>

              {/* 3. Preferences */}
              <section>
                <SectionHeader
                  icon={<Settings2 size={15} />}
                  title="3. Preferences"
                  subtitle="Choose features that are important to you"
                />
                <div className="flex gap-3 flex-wrap">
                  {PREFERENCES.map(({ key, label, icon }) => {
                    const checked = form.preferences.includes(key);
                    return (
                      <button
                        key={key}
                        onClick={() => togglePreference(key)}
                        className={cn(
                          "flex flex-col items-center gap-2 px-5 py-4 rounded-xl border transition-all duration-150 w-[140px]",
                          checked
                            ? "border-indigo-300 bg-indigo-50 shadow-sm"
                            : "border-[#EBEBF5] bg-white hover:border-gray-300 hover:bg-gray-50"
                        )}
                      >
                        {icon}
                        <span className="text-[12.5px] font-medium text-[#1A1A2E]">{label}</span>
                        <Checkbox
                          checked={checked}
                          onCheckedChange={() => togglePreference(key)}
                          className="pointer-events-none"
                        />
                      </button>
                    );
                  })}

                  {/* Tip card */}
                  <div className="flex-1 min-w-[180px] bg-amber-50 border border-amber-100 rounded-xl px-4 py-3 flex flex-col gap-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-base">💡</span>
                      <span className="text-[12px] font-semibold text-amber-700">Tip</span>
                    </div>
                    <p className="text-[11.5px] text-amber-600 leading-relaxed">
                      Selecting more preferences helps us show seats that match your needs better.
                    </p>
                  </div>
                </div>
              </section>

              {/* Actions */}
              <div className="flex justify-between items-center pt-1 border-t border-[#EBEBF5]">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearAll}
                  className="gap-1.5 text-[12.5px] text-gray-500"
                >
                  <RefreshCw size={12} />
                  Clear All
                </Button>
                <Button
                  onClick={findAvailableSeats}
                  disabled={!step1Valid || loadingSeats}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 gap-2 text-[13px] font-semibold"
                >
                  {loadingSeats ? "Finding seats…" : "Find Available Seats"}
                  {!loadingSeats && <ChevronRight size={15} />}
                </Button>
              </div>

              {/* What happens next */}
              <div className="bg-[#F7F8FC] border border-[#EBEBF5] rounded-xl px-5 py-3 flex items-start gap-3">
                <div className="w-5 h-5 rounded-full bg-indigo-100 flex items-center justify-center shrink-0 mt-0.5">
                  <span className="text-indigo-600 text-[10px] font-bold">i</span>
                </div>
                <div>
                  <p className="text-[12.5px] font-semibold text-[#1A1A2E]">What happens next?</p>
                  <p className="text-[12px] text-gray-400 mt-0.5">
                    You'll be taken to the floor map to view and select your preferred seats based on availability and your preferences.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════════
              STEP 2 – Select a Seat (Floor Map)
          ════════════════════════════════════════════════════ */}
          {step === 2 && (
            <div className="bg-white border border-[#EBEBF5] rounded-xl p-6 flex flex-col gap-5">

              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[15px] font-bold text-[#1A1A2E]">Select a Seat</p>
                  <p className="text-[12px] text-gray-400 mt-0.5">
                    {selectedSite?.name} · {selectedBuilding?.name} · {selectedFloor?.name}
                  </p>
                </div>
                <div className="flex gap-2.5 items-center">
                  {/* Legend */}
                  <div className="flex gap-3 items-center text-[11px] text-gray-500">
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 rounded bg-indigo-600 inline-block" /> Selected
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 rounded bg-indigo-50 border border-indigo-200 inline-block" /> Matches prefs
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 rounded bg-white border border-[#EBEBF5] inline-block" /> Available
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-3 h-3 rounded bg-gray-100 inline-block" /> Booked
                    </span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Floor map */}
              <div className="bg-[#F7F8FC] border border-[#EBEBF5] rounded-xl p-6 overflow-x-auto">
                <div className="flex flex-col gap-3 min-w-max">
                  {Object.entries(seatRows).sort(([a], [b]) => Number(a) - Number(b)).map(([row, rowSeats]) => (
                    <div key={row} className="flex gap-2 items-center">
                      <span className="text-[10px] font-semibold text-gray-300 w-5 text-right mr-1">
                        {String.fromCharCode(64 + Number(row))}
                      </span>
                      <div className="flex gap-2">
                        {rowSeats.sort((a, b) => a.col - b.col).map((seat) => (
                          <SeatTile
                            key={seat.id}
                            seat={seat}
                            selected={form.selectedSeatId === seat.id}
                            onSelect={() => selectSeat(seat.id)}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Selected seat info */}
              {selectedSeat && (
                <div className="bg-indigo-50 border border-indigo-100 rounded-xl px-5 py-3 flex items-center justify-between">
                  <div>
                    <p className="text-[13px] font-semibold text-indigo-700">
                      Seat {selectedSeat.label} selected
                    </p>
                    <div className="flex gap-1.5 mt-1.5">
                      {selectedSeat.amenities.map((a) => {
                        const pref = PREFERENCES.find((p) => p.key === a);
                        return pref ? (
                          <Badge
                            key={a}
                            variant="secondary"
                            className="text-[10px] px-2 py-0.5 bg-white border border-indigo-100 text-indigo-600"
                          >
                            {pref.label}
                          </Badge>
                        ) : null;
                      })}
                    </div>
                  </div>
                  <CheckCircle2 size={20} className="text-indigo-500 shrink-0" />
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-between pt-1 border-t border-[#EBEBF5]">
                <Button variant="outline" size="sm" onClick={goBack} className="text-[12.5px]">
                  ← Back
                </Button>
                <Button
                  onClick={goToReview}
                  disabled={!form.selectedSeatId}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 gap-2 text-[13px] font-semibold"
                >
                  Review Booking <ChevronRight size={15} />
                </Button>
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════════
              STEP 3 – Review & Confirm
          ════════════════════════════════════════════════════ */}
          {step === 3 && !confirmation && (
            <div className="bg-white border border-[#EBEBF5] rounded-xl p-6 flex flex-col gap-5 max-w-xl">
              <div>
                <p className="text-[15px] font-bold text-[#1A1A2E]">Review & Confirm</p>
                <p className="text-[12px] text-gray-400 mt-0.5">Please review your booking details before confirming</p>
              </div>

              <Separator />

              <div>
                <SummaryRow label="Location"  value={selectedSite?.name ?? "—"} />
                <SummaryRow label="Building"  value={selectedBuilding?.name ?? "—"} />
                <SummaryRow label="Floor"     value={selectedFloor?.name ?? "—"} />
                <SummaryRow label="Seat"      value={`Seat ${selectedSeat?.label ?? "—"}`} />
                <SummaryRow label="From"      value={fmtDate(form.fromDate)} />
                <SummaryRow label="To"        value={fmtDate(form.toDate)} />
                <SummaryRow label="Duration"  value={`${dayCount} ${dayCount === 1 ? "day" : "days"}`} />
                <div className="py-3 flex justify-between items-center">
                  <span className="text-[12.5px] text-gray-500">Preferences</span>
                  <div className="flex gap-1.5 flex-wrap justify-end">
                    {form.preferences.length > 0
                      ? form.preferences.map((p) => {
                          const pref = PREFERENCES.find((x) => x.key === p);
                          return pref ? (
                            <Badge key={p} variant="secondary" className="text-[11px]">
                              {pref.label}
                            </Badge>
                          ) : null;
                        })
                      : <span className="text-[12.5px] font-semibold text-[#1A1A2E]">None selected</span>
                    }
                  </div>
                </div>
              </div>

              <div className="flex justify-between pt-1 border-t border-[#EBEBF5]">
                <Button variant="outline" size="sm" onClick={goBack} className="text-[12.5px]">
                  ← Back
                </Button>
                <Button
                  onClick={confirmBooking}
                  disabled={submitting}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-6 text-[13px] font-semibold"
                >
                  {submitting ? "Confirming…" : "Confirm Booking"}
                </Button>
              </div>
            </div>
          )}

          {/* ════════════════════════════════════════════════════
              Confirmation success
          ════════════════════════════════════════════════════ */}
          {confirmation && (
            <div className="bg-white border border-[#EBEBF5] rounded-xl p-8 flex flex-col items-center gap-4 max-w-md mx-auto text-center">
              <div className="w-14 h-14 rounded-full bg-emerald-50 flex items-center justify-center">
                <CheckCircle2 size={28} className="text-emerald-500" />
              </div>
              <div>
                <p className="text-[18px] font-bold text-[#1A1A2E]">Booking Confirmed!</p>
                <p className="text-[12.5px] text-gray-400 mt-1">
                  Your seat has been reserved successfully.
                </p>
              </div>
              <div className="bg-[#F7F8FC] border border-[#EBEBF5] rounded-xl px-6 py-4 w-full text-left">
                <p className="text-[11px] font-semibold tracking-widest uppercase text-gray-400 mb-3">
                  Booking Details
                </p>
                <SummaryRow label="Confirmation" value={confirmation.confirmationCode} />
                <SummaryRow label="Location"     value={confirmation.location} />
                <SummaryRow label="Floor"        value={confirmation.floor} />
                <SummaryRow label="Seat"         value={confirmation.seat} />
                <SummaryRow label="From"         value={fmtDate(confirmation.fromDate)} />
                <SummaryRow label="To"           value={fmtDate(confirmation.toDate)} />
              </div>
              <Button
                onClick={resetForm}
                variant="outline"
                className="text-[13px] font-medium w-full"
              >
                Book another seat
              </Button>
            </div>
          )}

        </main>
      </div>
    </SidebarProvider>
  );
};

export default BookASeatPage;