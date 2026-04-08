"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Building2, Calendar, LayoutDashboard, LogOut, Settings } from "lucide-react";
import { motion } from "motion/react";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const isLandingPage = pathname === "/";
  const isLoginPage = pathname === "/login";
  const isAdminPage = pathname?.startsWith("/admin");

  const handleLogout = () => {
    router.push("/");
  };

  if (isLandingPage || isLoginPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#3D45AA] to-[#5B63D1] flex items-center justify-center">
              <Building2 className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-semibold text-gray-900">SeatBook</span>
          </Link>

          <nav className="flex items-center gap-1">
            <NavLink href="/dashboard" icon={LayoutDashboard} active={pathname === "/dashboard"}>
              Dashboard
            </NavLink>
            <NavLink href="/my-bookings" icon={Calendar} active={pathname === "/my-bookings"}>
              My Bookings
            </NavLink>
            {isAdminPage && (
              <NavLink href="/admin/offices" icon={Settings} active={isAdminPage}>
                Admin
              </NavLink>
            )}
          </nav>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-3 px-4 py-2 bg-gray-50 rounded-xl">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#F8843F] to-[#DA3D20] flex items-center justify-center">
                <span className="text-sm font-semibold text-white">JD</span>
              </div>
              <span className="text-sm text-gray-700">John Doe</span>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main>{children}</main>
    </div>
  );
}

function NavLink({ href, icon: Icon, active, children }: { href: string; icon: any; active: boolean; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors relative ${
        active
          ? "text-[#3D45AA] bg-[#3D45AA]/5"
          : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
      }`}
    >
      <Icon className="w-4 h-4" />
      <span className="text-sm">{children}</span>
      {active && (
        <motion.div
          layoutId="activeNav"
          className="absolute inset-0 bg-[#3D45AA]/5 rounded-lg -z-10"
          transition={{ type: "spring", duration: 0.5 }}
        />
      )}
    </Link>
  );
}
