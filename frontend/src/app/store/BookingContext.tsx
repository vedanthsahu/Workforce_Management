"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface BookingData {
  office?: string;
  floor?: string;
  date?: string;
  seat?: {
  id: string;
  row: string;
  number: number;
  amenities?: string[];
  nearWindow?: boolean;
  };
}

interface BookingContextType {
  bookingData: BookingData;
  setBookingData: (data: BookingData) => void;
  updateBookingData: (data: Partial<BookingData>) => void;
  clearBookingData: () => void;
}

const BookingContext = createContext<BookingContextType | undefined>(undefined);

export function BookingProvider({ children }: { children: ReactNode }) {
  const [bookingData, setBookingData] = useState<BookingData>({});

  const updateBookingData = (data: Partial<BookingData>) => {
    setBookingData((prev) => ({ ...prev, ...data }));
  };

  const clearBookingData = () => {
    setBookingData({});
  };

  return (
    <BookingContext.Provider
      value={{ bookingData, setBookingData, updateBookingData, clearBookingData }}
    >
      {children}
    </BookingContext.Provider>
  );
}

export function useBooking() {
  const context = useContext(BookingContext);
  if (context === undefined) {
    throw new Error("useBooking must be used within a BookingProvider");
  }
  return context;
}
