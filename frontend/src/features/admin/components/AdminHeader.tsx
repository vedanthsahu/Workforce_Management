"use client";

import { Calendar } from "lucide-react";

export default function AdminHeader() {
  return (
    <div className="flex items-center justify-between">

      {/* LEFT */}
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-sm text-muted-foreground">
          Overview of your workspace
        </p>
      </div>

      {/* RIGHT FILTERS */}
      <div className="flex items-center gap-3">

        {/* Offices Dropdown */}
        <select className="h-9 px-3 rounded-md border bg-white text-sm">
          <option>All Offices</option>
        </select>

        {/* Floors Dropdown */}
        <select className="h-9 px-3 rounded-md border bg-white text-sm">
          <option>All Floors</option>
        </select>

        {/* Date */}
        <div className="flex items-center gap-2 h-9 px-3 rounded-md border bg-white text-sm">
          <Calendar className="w-4 h-4 text-muted-foreground" />
          May 17, 2026
        </div>

      </div>
    </div>
  );
}