"use client";

import { AuthProvider } from "@/features/auth/context/AuthContext";

// Simply wrap the app with AuthProvider
// No axios injection needed — cookies are handled by the browser automatically
export function Providers({ children }: { children: React.ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}