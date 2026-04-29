export interface User {
  user_id: string;   // ← was "id"
  name: string;
  email: string;
  location?: string | null;
  project?: string | null;
  role?: string | null;
  created_at?: string | null;
  avatar?: string;
}

export interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  logout: () => Promise<void>;
}

export function getInitials(name: string): string {
  return name
    .split(" ")
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}