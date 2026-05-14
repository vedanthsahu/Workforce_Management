import AdminHeader from "@/features/admin/components/AdminHeader";
import AdminStats from "@/features/admin/components/AdminStats";
import AdminCharts from "@/features/admin/components/AdminCharts";
import { AppSidebar } from "@/features/dashboard/components/AppSidebar";
import { SidebarProvider } from "@/components/ui/sidebar";

export default function AdminPage() {
  return (
    <SidebarProvider>
      <div className="flex h-screen w-full">

        {/* Sidebar */}
        <AppSidebar user={null} />

        {/* Main Content */}
        <main className="flex-1 bg-gray-50 p-6 space-y-6 w-full">

          {/* Header */}
          <AdminHeader />

          {/* Stats */}
          <AdminStats />
          {/* Charts */}
          <AdminCharts />

        </main>
         

      </div>
    </SidebarProvider>
  );
}