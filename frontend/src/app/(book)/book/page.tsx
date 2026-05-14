"use client";

import { SidebarProvider } from "@/components/ui/sidebar";
import BookASeatPage from "@/features/book/components/Bookaseatpage";


export default function Book() {
  return (
    <SidebarProvider>
      <BookASeatPage/>
    </SidebarProvider>
  );
}