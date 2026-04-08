const BASE_URL = "http://127.0.0.1:8000";

export const loginUser = async (payload: {
  email: string;
  password: string;
}) => {
  const res = await fetch(`${BASE_URL}/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    const error: any = new Error("Request failed");
    error.status = res.status;
    throw error;
  }

  return res.json();
};