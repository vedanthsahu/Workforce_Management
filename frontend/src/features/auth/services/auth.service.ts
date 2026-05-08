import { axiosInstance } from "@/lib/http/axios";
import type { User } from "../types/auth.types";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const authService = {
  // Redirects browser → backend → Microsoft login page
  // After Microsoft auth, backend redirects to FRONTEND_URL (http://localhost:3000/)
  // AuthContext then sees "/" and redirects to /dashboard
  loginWithEmail(_email: string): void {
    window.location.href = `${BACKEND_URL}/auth/login`;
  },

  // Backend reads httpOnly cookie and returns user
  async getMe(): Promise<User> {
    const { data } = await axiosInstance.get<User>("/auth/me");
    return data;
  },

  // Backend clears access_token + refresh_token cookies
  async logout(): Promise<void> {
    await axiosInstance.post("/auth/logout");
  },
};