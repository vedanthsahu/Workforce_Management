import { AuthLayout } from "@/features/auth/components/AuthLayout";
import { LoginForm }  from "@/features/auth/components/LoginForm";

export default function LoginPage() {
  return (
    <AuthLayout
      title="Welcome back"
      subtitle="Enter your work email to sign in."
    >
      <LoginForm />
    </AuthLayout>
  );
}