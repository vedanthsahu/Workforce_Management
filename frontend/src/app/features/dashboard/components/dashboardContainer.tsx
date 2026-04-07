"use client";


import { AppLayout } from "@/app/components/layout/AppLayout";
import { useDashboard } from "../hooks/useDashboard";
import DashboardView from "./DashboardView";

export default function DashboardContainer() {
  const {
    form,
    onSubmit,
    offices,
    floors,
    selectedOffice, 
    stats,
    nextBooking,
    submitting,
    apiError,
  } = useDashboard();

  return (
    <AppLayout>
      <DashboardView
        form={form}
        onSubmit={onSubmit}
        offices={offices}
        floors={floors}
        selectedOffice={selectedOffice}
        stats={stats}
        nextBooking={nextBooking}
        submitting={submitting}
        apiError={apiError}
      />
    </AppLayout>
  );
}