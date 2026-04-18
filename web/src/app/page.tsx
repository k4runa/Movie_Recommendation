"use client";

import { useEffect, useState } from "react";
import { useAuthStore } from "@/lib/store";
import { AuthForm } from "@/components/auth/auth-form";
import { VercelV0Chat } from "@/components/chat/v0-ai-chat";
import { MovieDashboard } from "@/components/movies/dashboard";
import { MovieSearch } from "@/components/movies/movie-search";
import { RecommendationsDashboard } from "@/components/movies/recommendations";
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

export default function Home() {
  const { isAuthenticated, user, isLoading, checkAuth, logout } =
    useAuthStore();
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<
    "movies" | "recommendations" | "settings"
  >("movies");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-pulse text-2xl font-black tracking-widest text-primary">
          CINEWAVE...
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen space-y-8 p-6 animate-in fade-in zoom-in duration-500">
        <div className="text-center space-y-2">
          <h1 className="text-7xl font-black tracking-tighter text-foreground drop-shadow-[0_0_15px_rgba(16,185,129,0.2)]">
            CINEWAVE
          </h1>
          <p className="text-muted-foreground font-medium tracking-wide">
            Your AI Cinematic Oracle
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

      {/* Sidebar Navigation */}
      <aside
        className={`
        fixed inset-y-0 left-0 z-50 w-72 bg-card/70 backdrop-blur-xl border-r border-border transition-transform duration-300 md:relative md:translate-x-0
        ${isSidebarOpen ? "translate-x-0" : "-translate-x-full"}
      `}
      >
        <div className="flex flex-col h-full">
          <div className="p-8">
            <div className="flex items-center justify-between mb-12">
              <h1 className="text-3xl font-black tracking-tighter text-primary">
                CINEWAVE
              </h1>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="md:hidden p-2 text-muted-foreground hover:text-foreground"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="mb-8 md:hidden">
              <MovieSearch />
            </div>

            <nav className="space-y-2">
              {[
                { id: "movies", label: "My Movies", icon: Film },
                { id: "recommendations", label: "Discover", icon: Compass },
                { id: "settings", label: "Settings", icon: Settings },
              ].map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id as any);
                    setIsSidebarOpen(false);
                  }}
                  className={`w-full flex items-center gap-4 px-5 py-4 rounded-2xl transition-all font-bold ${activeTab === item.id ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20 scale-[1.02]" : "text-muted-foreground hover:text-foreground hover:bg-accent/50"}`}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </button>
              ))}
            </nav>
          </div>
          <div className="mt-auto p-8 border-t border-border/50">
            <button
              onClick={logout}
              className="w-full flex items-center gap-4 px-5 py-4 rounded-2xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all font-bold"
            >
              <LogOut className="w-5 h-5" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative bg-transparent">
        {/* Top Header */}
        <header className="sticky top-0 flex items-center justify-between px-6 py-4 border-b border-border/20 bg-background/40 backdrop-blur-md z-50 shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="md:hidden p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-xl"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center">
                <UserIcon className="w-5 h-5 text-primary" />
              </div>
              <div className="hidden sm:block">
                <h2 className="text-sm font-black tracking-tight leading-none mb-1">
                  Welcome, {user?.username}
                </h2>
                <p className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest">
                  Enthusiast Member
                </p>
              </div>
            </div>
          </div>

          <div className="hidden md:flex flex-1 justify-center px-8">
            <MovieSearch />
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("settings")}
              className="p-2.5 text-muted-foreground hover:text-foreground hover:bg-accent rounded-xl transition-colors"
            >
              <Settings className="w-5 h-5" />
            </button>
          </div>
        </header>

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
                          Curated by your personal AI Oracle.
                        </p>
                      </div>
                      <RecommendationsDashboard />
                    </div>
                  )}

                  {activeTab === "settings" && (
                    <div className="space-y-8 w-full max-w-4xl">
                      <div className="flex flex-col gap-2">
                        <h3 className="text-4xl font-black tracking-tighter">
                          Preferences
                        </h3>
                        <p className="text-muted-foreground font-medium">
                          Customize your CineWave experience.
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
            whileHover={{ scale: 1.1, rotate: 5 }}
            whileTap={{ scale: 0.9 }}
            onClick={() => setIsChatOpen(true)}
            className="fixed bottom-8 right-8 z-40 w-16 h-16 bg-primary text-primary-foreground rounded-2xl flex items-center justify-center shadow-[0_0_30px_rgba(var(--primary),0.3)] border border-primary/20 transition-all group"
          >
            <Sparkles className="w-8 h-8 transition-transform" />
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
          animate={{ x: isChatOpen ? 0 : "100%" }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed right-0 top-0 bottom-0 w-full sm:w-[450px] lg:w-[550px] bg-card/90 backdrop-blur-3xl border-l border-border shadow-2xl z-50 flex flex-col"
          style={{ pointerEvents: isChatOpen ? "auto" : "none" }}
        >
          <div className="flex items-center justify-between p-6 border-b border-border/50">
            <div className="flex items-center gap-4">
              <div className="bg-primary/10 p-3 rounded-2xl text-primary border border-primary/20 shadow-inner">
                <Sparkles className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-black text-xl tracking-tight leading-none mb-1">
                  Oracle Chat
                </h3>
                <p className="text-xs font-bold text-muted-foreground uppercase tracking-widest">
                  Conversational AI
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
              <VercelV0Chat />
            </div>
          </div>
        </motion.div>
      </>
    </div>
  );
}
