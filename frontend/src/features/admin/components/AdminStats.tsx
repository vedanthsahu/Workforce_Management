import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";

import {
  Building2,
  Layers,
  Armchair,
  CalendarCheck,
  Ban,
} from "lucide-react";

const stats = [
  {
    title: "Total Offices",
    value: "4",
    subtitle: "All locations",
    icon: Building2,
    color: "bg-blue-100 text-blue-600",
  },
  {
    title: "Total Floors",
    value: "18",
    subtitle: "Across all offices",
    icon: Layers,
    color: "bg-green-100 text-green-600",
  },
  {
    title: "Total Seats",
    value: "1,248",
    subtitle: "Active seats",
    icon: Armchair,
    color: "bg-orange-100 text-orange-600",
  },
  {
    title: "Booked Today",
    value: "342",
    subtitle: "27.4% occupancy",
    icon: CalendarCheck,
    color: "bg-blue-100 text-blue-600",
  },
  {
    title: "Blocked Seats",
    value: "56",
    subtitle: "Maintenance / Other",
    icon: Ban,
    color: "bg-purple-100 text-purple-600",
  },
];

export default function AdminStats() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
      {stats.map((item, index) => {
        const Icon = item.icon;

        return (
          <Card key={index}>

            {/* HEADER */}
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle>{item.title}</CardTitle>

              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center ${item.color}`}
              >
                <Icon className="w-5 h-5" />
              </div>
            </CardHeader>

            {/* CONTENT */}
            <CardContent>
              <div className="text-2xl font-semibold">
                {item.value}
              </div>

              <CardDescription>
                {item.subtitle}
              </CardDescription>
            </CardContent>

          </Card>
        );
      })}
    </div>
  );
}