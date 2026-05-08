import Image from "next/image";

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex">

      {/* ── Left Panel ── */}
      <div className="flex flex-1 flex-col items-center justify-center bg-white px-8 relative">

        {/* Logo — top left */}
        <div className="absolute top-8 left-8 flex items-center gap-2.5">
          <Image
            src="/logo.png"
            alt="Solugenix logo"
            width={36}
            height={36}
            className="rounded-lg"
          />
          <span className="text-lg font-semibold tracking-tight text-gray-900">
            Solugenix Seat Book
          </span>
        </div>

        {/* Form area */}
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-bold text-gray-900 mb-1">{title}</h1>
          <p className="text-sm text-gray-500 mb-8">{subtitle}</p>
          {children}
        </div>
      </div>

      {/* ── Right Panel ── */}
      <div className="hidden lg:flex flex-1 flex-col justify-between bg-[#1e2235] text-white p-12 relative overflow-hidden">

        {/* Decorative blobs */}
        <div className="absolute -top-24 -right-24 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-0 w-72 h-72 bg-blue-500/10 rounded-full blur-2xl pointer-events-none" />

        {/* Heading */}
        <div className="relative z-10 max-w-md">
          <h2 className="text-3xl font-bold leading-tight mb-4">
            Manage Your Workspace Effortlessly
          </h2>
          <p className="text-gray-400 text-sm leading-relaxed">
            Book seats, manage bookings, and optimize your office space with our
            enterprise-grade booking system.
          </p>
        </div>

        {/* Mock UI Card */}
        <div className="relative z-10 bg-white rounded-2xl shadow-2xl p-4 w-full max-w-md mx-auto my-8">
          {/* Window chrome */}
          <div className="flex items-center gap-2 mb-3">
            <div className="flex gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-red-400" />
              <span className="w-2.5 h-2.5 rounded-full bg-yellow-400" />
              <span className="w-2.5 h-2.5 rounded-full bg-green-400" />
            </div>
            <div className="flex-1 mx-2 h-5 bg-gray-100 rounded-full text-[10px] text-gray-400 flex items-center px-3">
              app.seatbook.io/floor-map
            </div>
          </div>

          <div className="flex gap-3">
            {/* Sidebar */}
            <div className="w-28 shrink-0">
              <div className="flex items-center gap-1.5 mb-3">
                <div className="w-5 h-5 bg-indigo-600 rounded flex items-center justify-center">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5">
                    <rect x="2" y="7" width="20" height="14" rx="2" />
                    <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
                  </svg>
                </div>
                <span className="text-[10px] font-semibold text-gray-800">SeatBook</span>
              </div>
              <p className="text-[8px] font-semibold uppercase text-gray-400 mb-1 tracking-wide">Workspace</p>
              {["Floor Map", "My Bookings", "Teams"].map((item, i) => (
                <div
                  key={item}
                  className={`px-2 py-1 rounded text-[9px] mb-0.5 ${
                    i === 0 ? "bg-indigo-50 text-indigo-700 font-medium" : "text-gray-500"
                  }`}
                >
                  {item}
                </div>
              ))}
              <p className="text-[8px] font-semibold uppercase text-gray-400 mb-1 mt-2 tracking-wide">Analytics</p>
              {["Reports", "Settings"].map((item) => (
                <div key={item} className="px-2 py-1 text-[9px] text-gray-500">{item}</div>
              ))}
            </div>

            {/* Floor map */}
            <div className="flex-1 min-w-0">
              <div className="flex justify-between items-center mb-1">
                <span className="text-[10px] font-semibold text-gray-800">Floor 3 — Zone A</span>
                <span className="text-[8px] text-gray-400">Mon, 20 Apr 2026</span>
              </div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-[8px] uppercase tracking-wide text-gray-400 font-medium">Seat Availability</span>
                <span className="text-[8px] font-semibold text-emerald-500">48 of 64 Free</span>
              </div>
              <div className="grid grid-cols-8 gap-1">
                {Array.from({ length: 32 }).map((_, i) => (
                  <div
                    key={i}
                    className={`w-4 h-4 rounded-[3px] ${
                      i === 11            ? "bg-red-500"   :
                      [10,18,19].includes(i) ? "bg-rose-200"  :
                      [24,25,30,31].includes(i) ? "bg-gray-200"  :
                      "bg-emerald-100"
                    }`}
                  />
                ))}
              </div>
              <div className="flex gap-2 mt-2 flex-wrap">
                {[
                  ["bg-emerald-100", "Available"],
                  ["bg-rose-200",    "Occupied"],
                  ["bg-red-500",     "Your Item"],
                  ["bg-gray-200",    "Inactive"],
                ].map(([color, label]) => (
                  <div key={label} className="flex items-center gap-1">
                    <span className={`w-2 h-2 rounded-sm ${color}`} />
                    <span className="text-[7px] text-gray-400">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="relative z-10 flex gap-12">
          {[
            ["10K+", "Active Users"],
            ["500+", "Companies"],
            ["50K+", "Bookings/Month"],
          ].map(([value, label]) => (
            <div key={label}>
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-sm text-gray-400">{label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}