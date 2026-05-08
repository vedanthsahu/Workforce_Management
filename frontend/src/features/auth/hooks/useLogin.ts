"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { authService } from "../services/auth.service";
import { emailSchema, type EmailFormValues } from "../schemas/auth.schema";

export function useLogin() {
  const form = useForm<EmailFormValues>({
    resolver: zodResolver(emailSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = (data: EmailFormValues) => {
    authService.loginWithEmail(data.email);
  };

  return {
    register:      form.register,
    handleSubmit:  form.handleSubmit(onSubmit),
    errors:        form.formState.errors,
    isSubmitting:  form.formState.isSubmitting,
  };
}