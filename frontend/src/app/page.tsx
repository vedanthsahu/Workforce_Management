// "use client";

import LandingView from "./features/home/components/LandingView";

// import Link from "next/link";
// import { ArrowRight, Building2, Calendar, Check, ChevronRight, MapPin, Shield, Zap } from "lucide-react";
// import { motion } from "motion/react";
// import { ImageWithFallback } from "./components/figma/ImageWithFallback";

// export default function Landing() {
//   const features = [
//     {
//       icon: MapPin,
//       title: "Interactive Seat Maps",
//       description: "Visual floor plans with real-time availability"
//     },
//     {
//       icon: Calendar,
//       title: "Smart Scheduling",
//       description: "Book seats in advance or for recurring days"
//     },
//     {
//       icon: Shield,
//       title: "Enterprise Security",
//       description: "Role-based access and secure authentication"
//     },
//     {
//       icon: Zap,
//       title: "Instant Booking",
//       description: "Reserve your seat in seconds with one click"
//     }
//   ];

//   const benefits = [
//     "Real-time seat availability tracking",
//     "Multi-office and floor support",
//     "Mobile-responsive design",
//     "Admin dashboard for management",
//     "Booking history and analytics",
//     "Automated notifications"
//   ];

//   return (
//     <div className="min-h-screen bg-white">
//       {/* Navigation */}
//       <nav className="fixed top-0 left-0 right-0 bg-white/80 backdrop-blur-lg border-b border-gray-100 z-50">
//         <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
//           <div className="flex items-center gap-2">
//             <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#3D45AA] to-[#5B63D1] flex items-center justify-center">
//               <Building2 className="w-6 h-6 text-white" />
//             </div>
//             <span className="text-xl font-semibold text-gray-900">SeatBook</span>
//           </div>
//           <div className="flex items-center gap-4">
//             <Link href="/login" className="text-sm text-gray-600 hover:text-gray-900 transition-colors">
//               Sign In
//             </Link>
//             <Link
//               href="/login"
//               className="px-5 py-2.5 bg-[#3D45AA] text-white rounded-lg hover:bg-[#2E3680] transition-colors text-sm"
//             >
//               Get Started
//             </Link>
//           </div>
//         </div>
//       </nav>

//       {/* Hero Section */}
//       <section className="pt-32 pb-20 px-6">
//         <div className="max-w-7xl mx-auto">
//           <div className="grid lg:grid-cols-2 gap-12 items-center">
//             <motion.div
//               initial={{ opacity: 0, y: 20 }}
//               animate={{ opacity: 1, y: 0 }}
//               transition={{ duration: 0.6 }}
//             >
//               {/* <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#FFF19B]/30 rounded-full mb-6">
//                 <Zap className="w-4 h-4 text-[#F8843F]" />
//                 <span className="text-sm text-gray-700">Smart Workspace Management</span>
//               </div> */}
//               <h1 className="text-5xl lg:text-6xl font-semibold text-gray-900 mb-6 leading-tight">
//                 Book Your Perfect
//                 <span className="block text-transparent bg-clip-text bg-gradient-to-r from-[#3D45AA] to-[#DA3D20]">
//                   Office Seat
//                 </span>
//               </h1>
//               <p className="text-lg text-gray-600 mb-8 leading-relaxed">
//                 Modern, intuitive seat booking system for enterprises. Manage workspaces, coordinate teams, 
//                 and optimize office space utilization with our smart booking platform.
//               </p>
//               <div className="flex flex-wrap gap-4">
//                 <Link
//                   href="/dashboard"
//                   className="group px-8 py-4 bg-[#3D45AA] text-white rounded-xl hover:bg-[#2E3680] transition-all shadow-lg shadow-[#3D45AA]/20 hover:shadow-xl hover:shadow-[#3D45AA]/30 flex items-center gap-2"
//                 >
//                   Book a Seat
//                   <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
//                 </Link>
//                 <Link
//                   href="/login"
//                   className="px-8 py-4 bg-white border-2 border-gray-200 text-gray-700 rounded-xl hover:border-[#3D45AA] hover:text-[#3D45AA] transition-all"
//                 >
//                   Watch Demo
//                 </Link>
//               </div>
//             </motion.div>

//             <motion.div
//               initial={{ opacity: 0, scale: 0.95 }}
//               animate={{ opacity: 1, scale: 1 }}
//               transition={{ duration: 0.6, delay: 0.2 }}
//               className="relative"
//             >
//               <div className="relative rounded-2xl overflow-hidden shadow-2xl">
//                 <ImageWithFallback
//                   src="https://images.unsplash.com/photo-1748346918817-0b1b6b2f9bab?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtb2Rlcm4lMjBvZmZpY2UlMjB3b3Jrc3BhY2UlMjB0ZWFtd29ya3xlbnwxfHx8fDE3NzQ3OTEzODF8MA&ixlib=rb-4.1.0&q=80&w=1080"
//                   alt="Modern office workspace"
//                   className="w-full h-[500px] object-cover"
//                 />
//               </div>
//               <div className="absolute -bottom-6 -left-6 w-48 h-48 bg-gradient-to-br from-[#F8843F] to-[#DA3D20] rounded-2xl opacity-10 blur-3xl" />
//               <div className="absolute -top-6 -right-6 w-48 h-48 bg-gradient-to-br from-[#3D45AA] to-[#5B63D1] rounded-2xl opacity-10 blur-3xl" />
//             </motion.div>
//           </div>
//         </div>
//       </section>

//       {/* Features Section */}
//       <section className="py-20 px-6 bg-gray-50">
//         <div className="max-w-7xl mx-auto">
//           <div className="text-center mb-16">
//             <h2 className="text-4xl font-semibold text-gray-900 mb-4">
//               Everything You Need to Manage Workspaces
//             </h2>
//             <p className="text-lg text-gray-600 max-w-2xl mx-auto">
//               Powerful features designed for modern hybrid work environments
//             </p>
//           </div>

//           <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
//             {features.map((feature, index) => (
//               <motion.div
//                 key={index}
//                 initial={{ opacity: 0, y: 20 }}
//                 whileInView={{ opacity: 1, y: 0 }}
//                 transition={{ duration: 0.5, delay: index * 0.1 }}
//                 viewport={{ once: true }}
//                 className="bg-white p-8 rounded-2xl shadow-sm hover:shadow-xl transition-all border border-gray-100"
//               >
//                 <div className="w-14 h-14 bg-gradient-to-br from-[#3D45AA] to-[#5B63D1] rounded-xl flex items-center justify-center mb-5">
//                   <feature.icon className="w-7 h-7 text-white" />
//                 </div>
//                 <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
//                 <p className="text-gray-600">{feature.description}</p>
//               </motion.div>
//             ))}
//           </div>
//         </div>
//       </section>

//       {/* Benefits Section */}
//       <section className="py-20 px-6">
//         <div className="max-w-7xl mx-auto">
//           <div className="grid lg:grid-cols-2 gap-12 items-center">
//             <motion.div
//               initial={{ opacity: 0, x: -20 }}
//               whileInView={{ opacity: 1, x: 0 }}
//               transition={{ duration: 0.6 }}
//               viewport={{ once: true }}
//             >
//               <div className="relative rounded-2xl overflow-hidden shadow-xl">
//                 <ImageWithFallback
//                   src="https://images.unsplash.com/photo-1523634806482-b93fe271431a?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxtaW5pbWFsJTIwb2ZmaWNlJTIwaW50ZXJpb3IlMjBkZXNrfGVufDF8fHx8MTc3NDgwMTk4NHww&ixlib=rb-4.1.0&q=80&w=1080"
//                   alt="Office interior"
//                   className="w-full h-[450px] object-cover"
//                 />
//               </div>
//             </motion.div>

//             <motion.div
//               initial={{ opacity: 0, x: 20 }}
//               whileInView={{ opacity: 1, x: 0 }}
//               transition={{ duration: 0.6 }}
//               viewport={{ once: true }}
//             >
//               <h2 className="text-4xl font-semibold text-gray-900 mb-6">
//                 Built for Enterprise Teams
//               </h2>
//               <p className="text-lg text-gray-600 mb-8">
//                 Streamline your office space management with intelligent features 
//                 designed for modern hybrid work environments.
//               </p>
//               <div className="space-y-4">
//                 {benefits.map((benefit, index) => (
//                   <div key={index} className="flex items-start gap-3">
//                     <div className="w-6 h-6 bg-[#3D45AA]/10 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5">
//                       <Check className="w-4 h-4 text-[#3D45AA]" />
//                     </div>
//                     <span className="text-gray-700">{benefit}</span>
//                   </div>
//                 ))}
//               </div>
//             </motion.div>
//           </div>
//         </div>
//       </section>

//       {/* CTA Section */}
//       <section className="py-20 px-6 bg-gradient-to-br from-[#3D45AA] to-[#2E3680]">
//         <div className="max-w-4xl mx-auto text-center">
//           <motion.div
//             initial={{ opacity: 0, y: 20 }}
//             whileInView={{ opacity: 1, y: 0 }}
//             transition={{ duration: 0.6 }}
//             viewport={{ once: true }}
//           >
//             <h2 className="text-4xl font-semibold text-white mb-6">
//               Ready to Transform Your Workspace?
//             </h2>
//             <p className="text-xl text-white/90 mb-8">
//               Join leading enterprises using SeatBook to optimize their office spaces
//             </p>
//             <Link
//               href="/dashboard"
//               className="inline-flex items-center gap-2 px-8 py-4 bg-white text-[#3D45AA] rounded-xl hover:shadow-2xl transition-all group"
//             >
//               Get Started Now
//               <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
//             </Link>
//           </motion.div>
//         </div>
//       </section>

//       {/* Footer */}
//       <footer className="py-12 px-6 bg-gray-50 border-t border-gray-200">
//         <div className="max-w-7xl mx-auto text-center">
//           <div className="flex items-center justify-center gap-2 mb-4">
//             <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#3D45AA] to-[#5B63D1] flex items-center justify-center">
//               <Building2 className="w-5 h-5 text-white" />
//             </div>
//             <span className="text-lg font-semibold text-gray-900">SeatBook</span>
//           </div>
//           <p className="text-gray-600">© 2026 SeatBook. All rights reserved.</p>
//         </div>
//       </footer>
//     </div>
//   );
// }
// src/app/page.tsx



export default function Page() {
  return <LandingView />;
}