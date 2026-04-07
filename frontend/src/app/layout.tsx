import type { Metadata } from "next";
import "../styles/index.css";
import "./globals.css"; 
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "SeatBook - Office Workspace Booking System",
  description: "Modern seat booking system for enterprise workspace management",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}
        <Toaster richColors position="bottom-right" />
      </body>
    </html>
  );
}
