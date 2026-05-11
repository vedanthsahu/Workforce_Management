// "use client";

// import { createContext, useContext, useEffect, useState } from "react";
// import { useRouter, usePathname } from "next/navigation";
// import { authService } from "../services/auth.service";
// import type { AuthContextType, User } from "../types/auth.types";

// const AuthContext = createContext<AuthContextType | null>(null);

// const PUBLIC_ROUTES = ["/login", "/auth/callback"];
// const ROOT_ROUTE = "/";

// export function AuthProvider({ children }: { children: React.ReactNode }) {
//   const router = useRouter();
//   const pathname = usePathname();
//   const [user, setUser] = useState<User | null>(null);
//   const [isLoading, setIsLoading] = useState(true);

//   // Step 1 — On every route change, check if user is authenticated
//   useEffect(() => {
//     // Skip auth check on public routes — no cookie expected here
//     if (PUBLIC_ROUTES.includes(pathname)) {
//       setIsLoading(false);
//       return;
//     }

//     authService
//       .getMe()
//       .then(setUser)
//       .catch(() => setUser(null))
//       .finally(() => setIsLoading(false));
//   }, [pathname]);

//   // Step 2 — Once auth check is done, redirect based on result
//   useEffect(() => {
//     if (isLoading) return; // wait until auth check completes

//     // Root route — redirect based on auth status
//     if (pathname === ROOT_ROUTE) {
//       if (user) {
//         router.replace("/dashboard"); //  logged in → dashboard
//       } else {
//         router.replace("/login");     //  not logged in → login
//       }
//       return;
//     }

//     // Already logged in and trying to access login → go to dashboard
//     if (user && PUBLIC_ROUTES.includes(pathname)) {
//       router.replace("/dashboard");
//       return;
//     }

//     // Not logged in and trying to access protected route → go to login
//     if (!user && !PUBLIC_ROUTES.includes(pathname)) {
//       router.replace("/login");
//       return;
//     }
//   }, [isLoading, user, pathname]);

//   const logout = async () => {
//     await authService.logout();
//     setUser(null);
//     router.replace("/login");
//   };

//   return (
//     <AuthContext.Provider
//       value={{
//         user,
//         isLoading,
//         isAuthenticated: !!user,
//         logout,
//       }}
//     >
//       {children}
//     </AuthContext.Provider>
//   );
// }

// export function useAuthContext() {
//   const ctx = useContext(AuthContext);
//   if (!ctx) throw new Error("useAuthContext must be used inside AuthProvider");
//   return ctx;
// }

"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { authService } from "../services/auth.service";
import type { AuthContextType, User } from "../types/auth.types";

const AuthContext = createContext<AuthContextType | null>(null);

const PUBLIC_ROUTES = ["/login", "/auth/callback"];
const ROOT_ROUTE = "/";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Step 1 — On every route change, check if user is authenticated
  useEffect(() => {
    // Skip auth check on public routes — no cookie expected here
    if (PUBLIC_ROUTES.includes(pathname)) {
      setIsLoading(false);
      return;
    }

    authService
      .getMe()
      .then(setUser)
      .catch((err) => {
        const status = err?.response?.status;
        const isNetworkError = !err?.response;

        if (isNetworkError) {
          // Server unreachable — don't clear user, let dashboard
          // handle it via FatalErrorScreen (network_error)
          setUser((prev) => prev);
        } else if (status === 401 || status === 403) {
          // Genuine auth failure — clear user so Step 2 redirects to login
          setUser(null);
        } else {
          // Other HTTP errors (500, 503 etc) — stay put, don't redirect
          setUser((prev) => prev);
        }
      })
      .finally(() => setIsLoading(false));
  }, [pathname]);

  // Step 2 — Once auth check is done, redirect based on result
  useEffect(() => {
    if (isLoading) return;

    // Root route — redirect based on auth status
    if (pathname === ROOT_ROUTE) {
      if (user) {
        router.replace("/dashboard");
      } else {
        router.replace("/login");
      }
      return;
    }

    // Already logged in and trying to access login → go to dashboard
    if (user && PUBLIC_ROUTES.includes(pathname)) {
      router.replace("/dashboard");
      return;
    }

    // Only redirect to login on confirmed auth failure (user explicitly null)
    // not on network errors where user state is preserved
    if (user === null && !PUBLIC_ROUTES.includes(pathname)) {
      router.replace("/login");
      return;
    }
  }, [isLoading, user, pathname]);

  const logout = async () => {
    await authService.logout();
    setUser(null);
    router.replace("/login");
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuthContext must be used inside AuthProvider");
  return ctx;
}