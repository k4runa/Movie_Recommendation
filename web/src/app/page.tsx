"use client";

import { useEffect, useState } from "react";
import { useAuthStore, useDashboardStore } from "@/lib/store";
import { AuthForm } from "@/components/auth/auth-form";
import { VercelV0Chat } from "@/components/chat/v0-ai-chat";
import { MovieDashboard } from "@/components/movies/dashboard";
import { MovieSearch } from "@/components/movies/movie-search";
import { RecommendationsDashboard } from "@/components/movies/recommendations";
import { FavoritesDashboard } from "@/components/movies/favorites-dashboard";
import { SimilarMindsDashboard } from "@/components/social/similar-minds-dashboard";
import { MessagesDashboard } from "@/components/social/messages-dashboard";
import { Button } from "@/components/ui/button";
import {
  LogOut,
  User as UserIcon,
  Sparkles,
  X,
  Settings,
  Film,
  Compass,
  Menu,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import { SettingsDashboard } from "@/components/settings/dashboard";
import { Header } from "@/components/ui/header-2";
import { CollapsibleSidebar } from "@/components/ui/collapsible-sidebar";


export default function Home() {
  const { isAuthenticated, user, isLoading, checkAuth, logout } =
    useAuthStore();
  const [isChatOpen, setIsChatOpen] = useState(false);
  const { activeTab, setActiveTab } = useDashboardStore();
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [selectedSocialUser, setSelectedSocialUser] = useState<any | null>(null);
  const [chatPlaceholder, setChatPlaceholder] = useState("Ask Eco anything...");

  const placeholders = [
    "Ask Eco anything...",
    "Whisper to the cinematic oracle...",
    "Which movie should we explore today?",
    "Tell me your favorite genre...",
    "Searching for a hidden gem?",
  ];

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  useEffect(() => {
    if (isChatOpen) {
      const random = placeholders[Math.floor(Math.random() * placeholders.length)];
      setChatPlaceholder(random);
    }
  }, [isChatOpen]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-2xl font-black tracking-widest text-primary">
          ecofil...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen space-y-8 p-6 animate-in fade-in zoom-in duration-500">
        <div className="text-center space-y-2">
          <h1 className="text-7xl font-black tracking-tighter text-foreground drop-shadow-[0_0_15px_rgba(16,185,129,0.2)]">
            ecofil
          </h1>
          <p className="text-muted-foreground font-medium tracking-wide">
            Your AI Cinematic Expert
          </p>
        </div>
        <AuthForm />
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full overflow-hidden text-foreground selection:bg-primary/30 selection:text-foreground">
      {/* Mobile Backdrop */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsSidebarOpen(false)}
            className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 md:hidden"
          />
        )}
      </AnimatePresence>

      {/* Mobile Sidebar Navigation */}
      <AnimatePresence>
        {isSidebarOpen && (
          <motion.div
            initial={{ x: "-100%" }}
            animate={{ x: 0 }}
            exit={{ x: "-100%" }}
            transition={{ type: "spring", damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 left-0 z-[60] w-72 md:hidden"
          >
            <CollapsibleSidebar 
              activeTab={activeTab} 
              setActiveTab={(tab) => { setActiveTab(tab); setIsSidebarOpen(false); }}
              logout={logout}
              user={user}
              onSelectUser={setSelectedSocialUser}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Desktop Collapsible Sidebar */}
      <div className="hidden md:block">
        <CollapsibleSidebar 
          activeTab={activeTab} 
          setActiveTab={setActiveTab}
          logout={logout}
          user={user}
          onSelectUser={setSelectedSocialUser}
        />
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative bg-transparent">
        {/* Top Header */}
        <Header 
          user={user} 
          onOpenSidebar={() => setIsSidebarOpen(true)} 
          onOpenSettings={() => setActiveTab("settings")} 
        />

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto px-6 md:px-12 py-10 scroll-smooth relative">
          <div className="max-w-6xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-700">
            <main className="pb-32">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -15 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  {activeTab === "movies" && (
                    <div className="space-y-8">
                      <div className="flex flex-col gap-2">
                        <h3 className="text-4xl font-black tracking-tighter">
                          Your Library
                        </h3>
                        <p className="text-muted-foreground font-medium">
                          Manage and track your cinematic journey.
                        </p>
                      </div>
                      <MovieDashboard />
                    </div>
                  )}

                  {activeTab === "recommendations" && (
                    <div className="space-y-8">
                      <div className="flex flex-col gap-2">
                        <h3 className="text-4xl font-black tracking-tighter">
                          Daily Picks
                        </h3>
                        <p className="text-muted-foreground font-medium">
                          Curated by your personal Eco AI Assistant.
                        </p>
                      </div>
                      <RecommendationsDashboard />
                    </div>
                  )}

                  {activeTab === "social" && (
                    <div className="space-y-8">
                      <div className="flex flex-col gap-2">
                        <h3 className="text-4xl font-black tracking-tighter">
                          Similar Minds
                        </h3>
                        <p className="text-muted-foreground font-medium">
                          Discover users with cinematic tastes identical to yours.
                        </p>
                      </div>
                      <SimilarMindsDashboard onTabChange={setActiveTab} />
                    </div>
                  )}

                  {activeTab === "messages" && (
                    <div className="space-y-8 h-full">
                      <div className="flex flex-col gap-2">
                        <h3 className="text-4xl font-black tracking-tighter">
                          Messages
                        </h3>
                        <p className="text-muted-foreground font-medium">
                          Connect with your cinematic kindred spirits.
                        </p>
                      </div>
                      <MessagesDashboard />
                    </div>
                  )}

                  {activeTab === "favorites" && (
                    <div className="space-y-8">
                      <FavoritesDashboard />
                    </div>
                  )}

                  {activeTab === "settings" && (
                    <div className="space-y-8 w-full max-w-4xl">
                      <div className="flex flex-col gap-2">
                        <h3 className="text-4xl font-black tracking-tighter">
                          Preferences
                        </h3>
                        <p className="text-muted-foreground font-medium">
                          Customize your ecofil experience.
                        </p>
                      </div>
                      <SettingsDashboard />
                    </div>
                  )}
                </motion.div>
              </AnimatePresence>
            </main>
          </div>
        </div>
      </div>


      {/* Floating AI Oracle Toggle */}
      <AnimatePresence>
        {!isChatOpen && (
          <motion.button
            initial={{ scale: 0, opacity: 0, y: 20 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0, opacity: 0, y: 20 }}
            whileHover={{ y: -4, scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setIsChatOpen(true)}
            className="fixed bottom-8 right-8 z-40 w-12 h-12 bg-[#171717] border border-[#262626] text-white rounded-xl flex items-center justify-center shadow-xl transition-all hover:shadow-white/5 hover:border-white/20 group"
          >
            <Sparkles className="w-5 h-5 transition-transform" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Slide-out AI Oracle Drawer */}
      <>
        <motion.div
          initial={false}
          animate={{ opacity: isChatOpen ? 1 : 0 }}
          onClick={() => setIsChatOpen(false)}
          className="fixed inset-0 bg-background/60 backdrop-blur-sm z-40"
          style={{ pointerEvents: isChatOpen ? "auto" : "none" }}
        />

        <motion.div
          initial={false}
          animate={{ x: isChatOpen ? 0 : "110%" }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed inset-y-0 right-0 sm:right-6 sm:top-6 sm:bottom-6 w-full sm:max-w-[450px] lg:max-w-[500px] bg-[#171717] border-l sm:border border-[#262626] sm:rounded-2xl shadow-2xl z-50 flex flex-col overflow-hidden"
          style={{ pointerEvents: isChatOpen ? "auto" : "none" }}
        >
          <div className="flex items-center justify-between p-5 border-b border-[#262626]">
            <div className="flex items-center gap-4">
              <div className="bg-[#262626] p-2.5 rounded-xl text-white border border-white/5 shadow-inner">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-black text-xl tracking-tight leading-none mb-1">
                  Eco AI Assistant
                </h3>
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                  Cinematic Expert
                </p>
              </div>
            </div>
            <button
              onClick={() => setIsChatOpen(false)}
              className="p-3 text-muted-foreground hover:text-foreground hover:bg-accent rounded-full transition-colors"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          <div className="flex-1 overflow-hidden relative">
            <div className="absolute inset-0">
              <VercelV0Chat placeholder={chatPlaceholder} />
            </div>
          </div>
        </motion.div>
      </>
    </div>
  );
}
