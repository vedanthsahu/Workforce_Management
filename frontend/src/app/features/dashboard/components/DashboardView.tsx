"use client";

import {
  Building2,
  MapPin,
  Calendar as CalendarIcon,
  ArrowRight,
  Users,
  AlertCircle,
  Loader2,
} from "lucide-react";
import { motion } from "motion/react";
import { format } from "date-fns";
import { UseFormReturn } from "react-hook-form";
import {
  BookingFormData,
  DashboardStats,
  Floor,
  NextBooking,
  Office,
} from "../schemas/dashboard.schema";
import { useRouter } from "next/navigation";

type Props = {
  form: UseFormReturn<BookingFormData>;
  onSubmit: (data: BookingFormData) => void;
  offices: Office[];
  floors: Floor[];
  selectedOffice: string;
  stats: DashboardStats;
  nextBooking: NextBooking;
  submitting: boolean;
  apiError: string;
};

const statConfig = [
  { label: "Your Bookings", key: "bookings" as const, icon: CalendarIcon, color: "from-[#3D45AA] to-[#5B63D1]" },
  { label: "Available Seats", key: "availableSeats" as const, icon: MapPin, color: "from-[#F8843F] to-[#DA3D20]" },
  { label: "Team Members", key: "teamMembers" as const, icon: Users, color: "from-[#DA3D20] to-[#F8843F]" },
];

export default function DashboardView({
  form,
  onSubmit,
  offices,
  floors,
  selectedOffice,
  stats,
  nextBooking,
  submitting,
  apiError,
}: Props) {
  const router = useRouter();

  const {
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isValid },
  } = form;

  // const selectedOffice = watch("office");
  const selectedFloor = watch("floor");
  const selectedDate = watch("date");


console.log("selectedOffice:", selectedOffice, "floors:", floors);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-6 py-8">

        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">Welcome back, John 👋</h1>
          <p className="text-gray-600">Book your workspace for a productive day</p>
        </motion.div>

        {/* Stats Cards */}
        <div className="grid md:grid-cols-3 gap-6 mb-8">
          {statConfig.map((stat, index) => (
            <motion.div
              key={stat.key}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600 mb-1">{stat.label}</p>
                  <p className="text-3xl font-semibold text-gray-900">{stats[stat.key]}</p>
                </div>
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${stat.color} flex items-center justify-center`}>
                  <stat.icon className="w-7 h-7 text-white" />
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Main Grid */}
        <div className="grid lg:grid-cols-3 gap-6">

          {/* Booking Form */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="lg:col-span-2 bg-white rounded-2xl p-8 shadow-sm border border-gray-100"
          >
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Book a Seat</h2>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">

              {/* API Error */}
              {apiError && (
                <div className="flex items-start gap-3 bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-sm">
                  <AlertCircle className="w-5 h-5 mt-0.5 text-red-500 flex-shrink-0" />
                  <span>{apiError}</span>
                </div>
              )}

              {/* Select Office */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Select Office
                </label>
                <div className="grid md:grid-cols-3 gap-4">
                  {offices.map((office) => (
                    // FIX: motion.div + plain <button type="button">
                    // motion.button can drop the type prop in some Framer Motion
                    // versions, causing a default type="submit" which submits the
                    // form instead of firing onClick.
                    <motion.div key={office.id} whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                      <button
                        type="button"
                        onClick={() => setValue("office", office.id, { shouldValidate: true })}
                        className={`w-full p-4 rounded-xl border-2 text-left transition-all ${
                          selectedOffice === office.id
                            ? "border-[#3D45AA] bg-[#3D45AA]/5"
                            : "border-gray-200 hover:border-gray-300"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                            selectedOffice === office.id
                              ? "bg-gradient-to-br from-[#3D45AA] to-[#5B63D1]"
                              : "bg-gray-100"
                          }`}>
                            <Building2 className={`w-5 h-5 ${selectedOffice === office.id ? "text-white" : "text-gray-600"}`} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-gray-900 mb-1">{office.name}</div>
                            <div className="text-xs text-gray-600 mb-2">{office.address}</div>
                            <span className="px-2 py-1 bg-green-50 text-green-700 rounded-md text-xs">
                              {office.available} available
                            </span>
                          </div>
                        </div>
                      </button>
                    </motion.div>
                  ))}
                </div>
                {errors.office && (
                  <p className="text-red-500 text-sm mt-1">{errors.office.message}</p>
                )}
              </div>

              {/* Select Floor */}
              {selectedOffice && floors.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                  <label className="block text-sm font-medium text-gray-700 mb-3">
                    Select Floor
                  </label>
                  <div className="grid grid-cols-5 gap-3">
                    {floors.map((floor) => (
                      <motion.div key={floor.id} whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                        <button
                          type="button"
                          onClick={() => setValue("floor", floor.id, { shouldValidate: true })}
                          className={`w-full p-4 rounded-xl border-2 transition-all ${
                            selectedFloor === floor.id
                              ? "border-[#3D45AA] bg-[#3D45AA]/5"
                              : "border-gray-200 hover:border-gray-300"
                          }`}
                        >
                          <div className="text-center">
                            <div className={`text-lg font-semibold mb-1 ${
                              selectedFloor === floor.id ? "text-[#3D45AA]" : "text-gray-900"
                            }`}>
                              {floor.name}
                            </div>
                            <div className="text-xs text-gray-600">{floor.available} seats</div>
                          </div>
                        </button>
                      </motion.div>
                    ))}
                  </div>
                  {errors.floor && (
                    <p className="text-red-500 text-sm mt-1">{errors.floor.message}</p>
                  )}
                </motion.div>
              )}

              {/* Select Date */}
              <div>
                <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-3">
                  Select Date
                </label>
                <div className="relative">
                  <CalendarIcon className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    id="date"
                    type="date"
                    value={selectedDate}
                    onChange={(e) => setValue("date", e.target.value, { shouldValidate: true })}
                    min={format(new Date(), "yyyy-MM-dd")}
                    className={`w-full pl-12 pr-4 py-3 bg-gray-50 border rounded-xl focus:ring-2 focus:ring-[#3D45AA] focus:border-transparent outline-none transition-all ${
                      errors.date ? "border-red-500" : "border-gray-200"
                    }`}
                  />
                </div>
                {errors.date && (
                  <p className="text-red-500 text-sm mt-1">{errors.date.message}</p>
                )}
              </div>

              {/* Submit */}
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <button
                  type="submit"
                  disabled={!isValid || submitting}
                  className="w-full py-4 bg-[#3D45AA] text-white rounded-xl hover:bg-[#2E3680] transition-all shadow-lg shadow-[#3D45AA]/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {submitting ? (
                    <><Loader2 className="w-5 h-5 animate-spin" />Processing...</>
                  ) : (
                    <>Continue to Seat Selection<ArrowRight className="w-5 h-5" /></>
                  )}
                </button>
              </motion.div>

            </form>
          </motion.div>

          {/* Sidebar */}
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="space-y-6">

            {/* Quick Actions */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="font-semibold text-gray-900 mb-4">Quick Actions</h3>
              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => router.push("/my-bookings")}
                  className="w-full p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left flex items-center justify-between group"
                >
                  <span className="text-sm text-gray-700">View My Bookings</span>
                  <ArrowRight className="w-4 h-4 text-gray-400 group-hover:translate-x-1 transition-transform" />
                </button>
                <button
                  type="button"
                  onClick={() => router.push("/admin/offices")}
                  className="w-full p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors text-left flex items-center justify-between group"
                >
                  <span className="text-sm text-gray-700">Admin Panel</span>
                  <ArrowRight className="w-4 h-4 text-gray-400 group-hover:translate-x-1 transition-transform" />
                </button>
              </div>
            </div>

            {/* Next Booking */}
            <div className="bg-gradient-to-br from-[#3D45AA] to-[#2E3680] rounded-2xl p-6 text-white">
              <h3 className="font-semibold mb-4">Next Booking</h3>
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <CalendarIcon className="w-4 h-4" />
                  <span className="text-sm">{nextBooking.date}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  <span className="text-sm">{nextBooking.office}</span>
                </div>
                <div className="flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  <span className="text-sm">{nextBooking.seat}</span>
                </div>
              </div>
            </div>

            {/* Pro Tip */}
            <div className="bg-[#FFF19B]/20 rounded-2xl p-6 border border-[#FFF19B]/50">
              <h3 className="font-semibold text-gray-900 mb-2">💡 Pro Tip</h3>
              <p className="text-sm text-gray-700">
                Book seats near windows for better natural lighting and a more productive day!
              </p>
            </div>

          </motion.div>
        </div>
      </div>
    </div>
  );
}