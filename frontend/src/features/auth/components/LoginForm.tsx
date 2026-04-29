"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLogin } from "../hooks/useLogin";


export function LoginForm() {
  const { register, handleSubmit, errors, isSubmitting } = useLogin();

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="email" className="text-sm font-medium text-gray-700">
          Work email address
        </Label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
              <rect x="2" y="4" width="20" height="16" rx="2" />
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
            </svg>
          </span>
          <Input
            id="email"
            type="email"
            placeholder="abc@solugenix.com"
            className="pl-9 h-11 text-sm border-gray-200 focus-visible:ring-indigo-500"
            {...register("email")}
          />
        </div>
        {errors.email && (
          <p className="text-xs text-red-500">{errors.email.message}</p>
        )}
      </div>

      <Button
        type="submit"
        disabled={isSubmitting}
        className="w-full h-11 bg-indigo-600 hover:bg-indigo-700 text-white font-medium text-sm rounded-lg"
      >
        {isSubmitting ? (
          <span className="flex items-center gap-2">
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
            </svg>
            Redirecting...
          </span>
        ) : (
          "Continue"
        )}
      </Button>

      {/* SSO hint */}
      <div className="pt-2 flex items-center gap-2 text-xs text-gray-400">
        <svg width="14" height="14" viewBox="0 0 21 21" fill="none">
          <rect x="0"  y="0"  width="9" height="9" fill="#F25022"/>
          <rect x="11" y="0"  width="9" height="9" fill="#7FBA00"/>
          <rect x="0"  y="11" width="9" height="9" fill="#00A4EF"/>
          <rect x="11" y="11" width="9" height="9" fill="#FFB900"/>
        </svg>
        You'll be redirected to Microsoft to complete sign in.
      </div>
    </form>
  );
}