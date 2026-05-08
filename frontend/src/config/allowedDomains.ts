const raw = process.env.NEXT_PUBLIC_ALLOWED_EMAIL_DOMAINS ?? "";

export const ALLOWED_EMAIL_DOMAINS = raw
  .split(",")
  .map((d) => d.trim().toLowerCase())
  .filter(Boolean);