"use client";

import LoginForm from "./LoginForm";
import { useLogin } from "../hooks/useLogin";

export default function LoginContainer() {
  const { register, handleSubmit, formState, onSubmit, loading ,apiError} = useLogin();

  return (
    <LoginForm
      register={register}
      handleSubmit={handleSubmit}
      errors={formState.errors}
      isValid={formState.isValid}
      loading={loading}
      onSubmit={onSubmit}
      apiError={apiError} 
    />
  );
}