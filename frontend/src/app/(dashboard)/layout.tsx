// app/(dashboard)/layout.tsx

import { BookingProvider } from "../store/BookingContext";


export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <BookingProvider>{children}</BookingProvider>;
}