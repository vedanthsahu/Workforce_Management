"use client";

import { SidebarProvider } from "@/components/ui/sidebar";
import MyBookingsPage from "@/features/bookings/components/MyBookingsPage";

export default function MyBookings() {
  return (
    <SidebarProvider>
      <MyBookingsPage />
    </SidebarProvider>
  );
}