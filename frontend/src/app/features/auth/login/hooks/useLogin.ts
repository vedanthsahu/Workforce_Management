import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoginFormData, loginSchema } from "../schemas/login.schema";
import { loginUser } from "../services/auth.service";

export const useLogin = () => {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState("");

  const form = useForm({
    resolver: zodResolver(loginSchema),
    mode: "onChange",
  });

//   const onSubmit = async (data: any) => {
//     setLoading(true);

//     try {
//       console.log(data);
//       await new Promise((r) => setTimeout(r, 1000));
//       router.push("/dashboard");
//     } finally {
//       setLoading(false);
//     }
//   };

//   return { ...form, onSubmit, loading };
// };


const onSubmit = async (data: LoginFormData) => {
  setLoading(true);
  setApiError("");
  
  try {
  await loginUser(data); 
  setTimeout(() => { 
  router.push("/dashboard");
 }, 800);
 } catch (err: any) {
const status = err?.response?.status || err?.status || err?.response?.data?.status; 
if (status === 401) {
   setApiError("Invalid email or password");
   } else if (status === 500) {
     setApiError("Server error. Please try again later."); 
    } else if (err?.message === "Network Error") {
       setApiError("Network error. Check your internet connection."); 
      } else { setApiError("Something went wrong. Please try again."); } 
    } finally { setLoading(false); } 
  };
    return { ...form, onSubmit, loading, apiError };
}