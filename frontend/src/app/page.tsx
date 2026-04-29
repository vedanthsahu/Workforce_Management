import { cookies } from "next/headers";
import { redirect } from "next/navigation";

export default async function RootPage() {
  const cookieStore = await cookies();
  
  // Check if access_token cookie exists (set by your backend after SSO)
  const accessToken = cookieStore.get("access_token");

  if (accessToken) {
    redirect("/dashboard"); //  logged in → dashboard
  } else {
    redirect("/login");     //  not logged in → login
  }
}