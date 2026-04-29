import axios from "axios";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const axiosInstance = axios.create({
  baseURL: BACKEND_URL,
  withCredentials: true, // browser sends httpOnly cookies automatically
  headers: {
    "Content-Type": "application/json",
  },
});

let _refreshing: Promise<boolean> | null = null;

axiosInstance.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    // Only attempt refresh once per request
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      // Deduplicate — if refresh already in flight, wait for it
      if (!_refreshing) {
        _refreshing = axios
          .post(
            `${BACKEND_URL}/auth/refresh`,
            {},
            { withCredentials: true }
          )
          .then(() => true)
          .catch(() => false)
          .finally(() => (_refreshing = null));
      }

      const refreshed = await _refreshing;

      if (refreshed) {
        // Retry original request with new cookies
        return axiosInstance(original);
      }

      // Refresh failed — send to login only if not already there
      if (
        typeof window !== "undefined" &&
        !window.location.pathname.includes("/login")
      ) {
        window.location.href = "/login";
      }
    }

    return Promise.reject(error);
  }
);