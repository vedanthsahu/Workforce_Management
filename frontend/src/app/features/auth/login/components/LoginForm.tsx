"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Building2,
  Mail,
  Lock,
  Eye,
  EyeOff,
  AlertCircle,
} from "lucide-react";
import { motion } from "framer-motion";
import { ImageWithFallback } from "@/app/components/common/ImageWithFallback";

type Props = {
  register: any;
  handleSubmit: any;
  errors: any;
  isValid: boolean;
  loading: boolean;
  onSubmit: (data: any) => void;
  apiError?: string;
};

export default function LoginForm({
  register,
  handleSubmit,
  errors,
  isValid,
  loading,
  onSubmit,
  apiError, // FIXED
}: Props) {
  const [showPassword, setShowPassword] = useState(false);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-white flex">
      
      {/* LEFT */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="w-full max-w-md"
        >

          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 mb-12">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#3D45AA] to-[#5B63D1] flex items-center justify-center">
              <Building2 className="w-7 h-7 text-white" />
            </div>
            <span className="text-2xl font-semibold">SeatBook</span>
          </Link>

          <h1 className="text-3xl font-semibold mb-6">Welcome back</h1>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

            {/* ✅ API ERROR */}
            {apiError && (
              <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm">
                <AlertCircle className="w-5 h-5 mt-0.5 text-red-500" />
                <span>{apiError}</span>
              </div>
            )}

            {/* EMAIL */}
            <div>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  {...register("email")}
                  placeholder="you@company.com"
                  className={`w-full pl-12 py-3 rounded-xl border outline-none
                    ${errors.email ? "border-red-500" : "border-gray-200"}
                  `}
                  autoComplete="new-email"
                />
              </div>

              {errors.email && (
                <p className="text-red-500 text-sm mt-1">
                  {errors.email.message}
                </p>
              )}
            </div>

            {/* PASSWORD */}
            <div>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />

                <input
                  type={showPassword ? "text" : "password"}
                  {...register("password")}
                  className={`w-full pl-12 pr-12 py-3 rounded-xl border outline-none
                    ${errors.password ? "border-red-500" : "border-gray-200"}
                  `}
                  autoComplete="new-password"
                />

                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400"
                >
                  {showPassword ? (
                    <EyeOff className="w-5 h-5" />
                  ) : (
                    <Eye className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* ✅ Password error OUTSIDE */}
              {errors.password && (
                <p className="text-red-500 text-sm mt-1">
                  {errors.password.message}
                </p>
              )}
            </div>

            {/* BUTTON */}
            <button
              type="submit"
              disabled={!isValid || loading}
              className="w-full py-3 bg-[#3D45AA] text-white rounded-xl disabled:opacity-50"
            >
              {loading ? "Signing in..." : "Sign in"}
            </button>
          </form>
        </motion.div>
      </div>

      {/* RIGHT SIDE */}
      <div className="hidden lg:block lg:w-1/2 relative bg-gradient-to-br from-[#3D45AA] to-[#2E3680] p-12">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="h-full flex flex-col justify-center"
        >
          <div className="mb-12">
            <h2 className="text-4xl font-semibold text-white mb-4">
              Manage Your Workspace <br /> Effortlessly
            </h2>
            <p className="text-xl text-white/90">
              Book seats, manage bookings, and optimize your office space.
            </p>
          </div>

          <div className="relative rounded-2xl overflow-hidden shadow-2xl">
            <ImageWithFallback
              src="https://images.unsplash.com/photo-1722149493669-30098ef78f9f"
              alt="workspace"
              className="w-full h-[400px] object-cover"
            />
          </div>

          <div className="grid grid-cols-3 gap-8 mt-12 text-center text-white">
            <div>
              <div className="text-3xl font-semibold">10K+</div>
              <div className="text-sm text-white/80">Users</div>
            </div>
            <div>
              <div className="text-3xl font-semibold">500+</div>
              <div className="text-sm text-white/80">Companies</div>
            </div>
            <div>
              <div className="text-3xl font-semibold">50K+</div>
              <div className="text-sm text-white/80">Bookings</div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}