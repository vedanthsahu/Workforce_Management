import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const refreshToken = req.cookies.get("refresh_token")?.value;

  // Tell backend to invalidate the refresh token
  if (refreshToken) {
    await fetch(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/auth/logout`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }
    ).catch(() => {}); // don't block logout if backend is down
  }

  const res = NextResponse.json({ ok: true });
  res.cookies.delete("refresh_token");
  return res;
}