"use client";

import { useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  AreaChart,
  Area,
  XAxis,
  YAxis,
} from "recharts";

import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";

import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";

import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";

import { Info } from "lucide-react";

// ✅ TYPE FIX (IMPORTANT)
type WeekType = "this-week" | "last-week";

// ---------- DATA ----------
const totalSeats = 1248;
const booked = 342;
const available = 906;

// ✅ TYPE-SAFE DATA
const weeklyData: Record<
  WeekType,
  { day: string; occupancy: number }[]
> = {
  "this-week": [
    { day: "Mon 11", occupancy: 40 },
    { day: "Tue 12", occupancy: 60 },
    { day: "Wed 13", occupancy: 90 },
    { day: "Thu 14", occupancy: 85 },
    { day: "Fri 15", occupancy: 50 },
    { day: "Sat 16", occupancy: 30 },
    { day: "Sun 17", occupancy: 20 },
  ],
  "last-week": [
    { day: "Mon", occupancy: 20 },
    { day: "Tue", occupancy: 30 },
    { day: "Wed", occupancy: 50 },
    { day: "Thu", occupancy: 70 },
    { day: "Fri", occupancy: 60 },
    { day: "Sat", occupancy: 40 },
    { day: "Sun", occupancy: 25 },
  ],
};

const baseOffices = [
  { name: "Bengaluru (HQ)", value: 78.6 },
  { name: "Hyderabad", value: 54.2 },
  { name: "Pune", value: 32.8 },
  { name: "Chennai", value: 28.1 },
];

const extraOffices = [
  { name: "Mumbai", value: 48.5 },
  { name: "Indore", value: 36.2 },
];

// ---------- COMPONENT ----------
export default function AdminCharts() {
  // ✅ FIXED STATE TYPE
  const [selectedWeek, setSelectedWeek] =
    useState<WeekType>("this-week");

  const [expanded, setExpanded] = useState(false);

  const offices = expanded
    ? [...baseOffices, ...extraOffices]
    : baseOffices;

  return (
    <div className="grid grid-cols-3 gap-4">

      {/* ---------------- DONUT ---------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">
            Today's Overview
          </CardTitle>
        </CardHeader>

        <CardContent className="flex items-center justify-between gap-6">

          <div className="relative w-[160px] h-[160px]">
            <ChartContainer
              config={{
                booked: { label: "Booked", color: "#4F46E5" },
                available: { label: "Available", color: "#E5E7EB" },
              }}
              className="h-full w-full"
            >
              <PieChart>
                <Pie
                  data={[
                    { name: "booked", value: booked },
                    { name: "available", value: available },
                  ]}
                  dataKey="value"
                  innerRadius={55}
                  outerRadius={75}
                  stroke="none"
                >
                  <Cell fill="var(--color-booked)" />
                  <Cell fill="var(--color-available)" />
                </Pie>
              </PieChart>
            </ChartContainer>

            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <p className="text-2xl font-semibold">
                {((booked / totalSeats) * 100).toFixed(1)}%
              </p>
              <p className="text-xs text-muted-foreground">
                Occupancy
              </p>
            </div>
          </div>

          <div className="space-y-4 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">
                Booked Seats
              </p>
              <p className="font-medium">
                {booked} ({((booked / totalSeats) * 100).toFixed(1)}%)
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">
                Available Seats
              </p>
              <p className="font-medium">
                {available} ({((available / totalSeats) * 100).toFixed(1)}%)
              </p>
            </div>

            <div>
              <p className="text-xs text-muted-foreground">
                Total Seats
              </p>
              <p className="font-medium">{totalSeats}</p>
            </div>
          </div>

        </CardContent>

        <div className="mx-6 mb-5 mt-2 flex items-center gap-2 rounded-md bg-blue-50 px-3 py-2 text-xs text-blue-600">
          <Info className="w-4 h-4" />
          Occupancy rate is calculated based on all bookable seats.
        </div>
      </Card>

      {/* ---------------- LINE CHART ---------------- */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-semibold">
            Occupancy Trend
          </CardTitle>

          <Select value={selectedWeek} onValueChange={(value) => {
    if (value) setSelectedWeek(value as WeekType);
  }}
>
            <SelectTrigger className="h-8 w-[120px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="this-week">This Week</SelectItem>
              <SelectItem value="last-week">Last Week</SelectItem>
            </SelectContent>
          </Select>
        </CardHeader>

        <CardContent>
          <ChartContainer
            config={{
              occupancy: {
                label: "Occupancy",
                color: "#4F46E5",
              },
            }}
            className="h-[240px]"
          >
            <AreaChart data={weeklyData[selectedWeek]}>
              <defs>
                <linearGradient id="occGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#4F46E5" stopOpacity={0.35} />
                  <stop offset="95%" stopColor="#4F46E5" stopOpacity={0} />
                </linearGradient>
              </defs>

              <XAxis dataKey="day" axisLine={false} tickLine={false} />
              <YAxis
                domain={[0, 100]}
                tickFormatter={(v) => `${v}%`}
                axisLine={false}
                tickLine={false}
              />

              <ChartTooltip content={<ChartTooltipContent />} />

              <Area
                type="monotone"
                dataKey="occupancy"
                stroke="#4F46E5"
                fill="url(#occGradient)"
              />
            </AreaChart>
          </ChartContainer>
        </CardContent>
      </Card>

      {/* ---------------- TOP OFFICES ---------------- */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-semibold">
            Top Offices by Occupancy
          </CardTitle>
        </CardHeader>

        <CardContent className="space-y-4">
          {offices.map((item, i) => (
            <div key={i}>
              <div className="flex justify-between text-sm">
                <span>{item.name}</span>
                <span className="text-muted-foreground">
                  {item.value}%
                </span>
              </div>

              <div className="w-full h-2 bg-gray-200 rounded-full mt-1">
                <div
                  className="h-2 bg-indigo-500 rounded-full"
                  style={{ width: `${item.value}%` }}
                />
              </div>
            </div>
          ))}

          <button
            onClick={() => setExpanded(!expanded)}
            className="text-sm text-indigo-600"
          >
            {expanded ? "Show less" : "View all offices →"}
          </button>
        </CardContent>
      </Card>

    </div>
  );
}