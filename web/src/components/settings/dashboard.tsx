"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, User, Palette, Sparkles, Bell } from "lucide-react";

export function SettingsDashboard() {
  const { user, checkAuth } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  
  const [isEditingUsername, setIsEditingUsername] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const [aiEnabled, setAiEnabled] = useState(user?.ai_enabled ?? true);
  const [toastLimit, setToastLimit] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('toastLimit') || "3";
    }
    return "3";
  });

  useEffect(() => {
    setMounted(true);
  }, []);

  const handleUpdateUsername = async () => {
    if (!newUsername || !currentPassword) {
      toast.error("Please provide new username and current password");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await authApi.updateUserField(user.username, {
        field: "username",
        value: newUsername,
        current_password: currentPassword
      });
      if (res.data.new_token) {
        localStorage.setItem("access_token", res.data.new_token);
        await checkAuth();
        toast.success("Username updated successfully!");
        setIsEditingUsername(false);
        setNewUsername("");
        setCurrentPassword("");
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update username");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggleAi = async () => {
    const newValue = !aiEnabled;
    setAiEnabled(newValue);
    try {
      await authApi.updateUserField(user.username, {
        field: "ai_enabled",
        value: newValue
      });
      toast.success(newValue ? "AI Features Enabled" : "AI Features Disabled");
    } catch (err: any) {
      setAiEnabled(!newValue); // revert
      toast.error("Failed to update AI preference");
    }
  };

  const handleToastLimitChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const limit = e.target.value;
    setToastLimit(limit);
    if (typeof window !== 'undefined') {
      localStorage.setItem('toastLimit', limit);
      toast.success(`Max notifications set to ${limit}`);
    }
  };

  if (!mounted) return null;

  return (
    <div className="bg-card/40 backdrop-blur-md border border-border/50 rounded-[2.5rem] p-6 md:p-10 space-y-10 shadow-xl">
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <User className="w-5 h-5 text-primary" />
          <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">Profile Management</label>
        </div>
        
        <div className="flex flex-col gap-4 p-6 bg-background/50 rounded-[2rem] border border-border/40 shadow-inner group transition-all hover:bg-background/80">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="font-black text-xl tracking-tight">{user?.username}</p>
              <p className="text-sm text-muted-foreground font-medium">Public Identity</p>
            </div>
            <Button 
              variant="outline" 
              className={`rounded-2xl px-6 font-bold transition-all ${isEditingUsername ? "bg-destructive/10 text-destructive border-destructive/20 hover:bg-destructive/20" : "border-border hover:bg-accent"}`}
              onClick={() => setIsEditingUsername(!isEditingUsername)}
            >
              {isEditingUsername ? "Cancel" : "Edit Name"}
            </Button>
          </div>
          
          {isEditingUsername && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="pt-6 border-t border-border/20 space-y-5"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest ml-1">New Username</label>
                  <input 
                    type="text" 
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    className="w-full bg-accent/50 border border-border/50 rounded-2xl px-4 py-3 text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest ml-1">Current Password</label>
                  <input 
                    type="password" 
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full bg-accent/50 border border-border/50 rounded-2xl px-4 py-3 text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all font-medium"
                  />
                </div>
              </div>
              <Button 
                onClick={handleUpdateUsername} 
                disabled={isSubmitting || !newUsername || !currentPassword}
                className="w-full bg-primary text-primary-foreground hover:shadow-lg hover:shadow-primary/20 rounded-2xl h-14 font-black text-lg transition-all"
              >
                {isSubmitting ? <Loader2 className="w-5 h-5 animate-spin" /> : "Save Changes"}
              </Button>
            </motion.div>
          )}
        </div>
      </div>
      
      <div className="space-y-6">
        <div className="flex items-center gap-3 mb-2">
          <Palette className="w-5 h-5 text-primary" />
          <label className="text-xs font-black uppercase tracking-widest text-muted-foreground">App Preferences</label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          
          {/* Theme Toggle */}
          <div className="flex flex-col justify-between p-6 bg-background/50 rounded-[2rem] border border-border/40 hover:bg-background/80 transition-all group">
            <div className="mb-6">
              <p className="font-black text-lg tracking-tight group-hover:text-primary transition-colors">Theme Mode</p>
              <p className="text-xs text-muted-foreground font-medium leading-relaxed mt-1">Switch between dark & light cinematic modes.</p>
            </div>
            <div 
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className={`w-full h-12 rounded-2xl relative cursor-pointer transition-all border border-border/50 overflow-hidden flex items-center px-2 ${theme === 'dark' ? 'bg-zinc-900' : 'bg-zinc-100'}`}
            >
              <div className={`absolute inset-0 bg-primary/10 transition-transform duration-500 ${theme === 'dark' ? 'translate-x-0' : '-translate-x-full'}`} />
              <div className={`w-8 h-8 rounded-xl shadow-md transition-all duration-300 z-10 flex items-center justify-center ${theme === 'dark' ? 'translate-x-full bg-primary text-primary-foreground' : 'translate-x-0 bg-white text-zinc-900'}`}>
                {theme === 'dark' ? <Palette className="w-4 h-4" /> : <Palette className="w-4 h-4" />}
              </div>
              <span className={`ml-3 text-xs font-black uppercase tracking-widest z-10 ${theme === 'dark' ? 'text-primary' : 'text-muted-foreground'}`}>
                {theme === 'dark' ? 'Dark Mode' : 'Light Mode'}
              </span>
            </div>
          </div>

          {/* AI Toggle */}
          <div className="flex flex-col justify-between p-6 bg-background/50 rounded-[2rem] border border-border/40 hover:bg-background/80 transition-all group">
            <div className="mb-6">
              <div className="flex items-center gap-2">
                <p className="font-black text-lg tracking-tight group-hover:text-primary transition-colors">AI Eco</p>
                <Sparkles className="w-4 h-4 text-primary animate-pulse" />
              </div>
              <p className="text-xs text-muted-foreground font-medium leading-relaxed mt-1">Enable deep cinematic analysis & chat memory.</p>
            </div>
            <button 
              onClick={handleToggleAi}
              className={`w-full h-12 rounded-2xl relative transition-all border border-border/50 overflow-hidden flex items-center justify-center gap-2 font-black text-xs uppercase tracking-widest ${aiEnabled ? 'bg-primary/10 text-primary border-primary/30' : 'bg-accent/50 text-muted-foreground hover:bg-accent'}`}
            >
              {aiEnabled ? "Eco Active" : "Enable Eco"}
            </button>
          </div>

          {/* Toast Limit */}
          <div className="flex flex-col justify-between p-6 bg-background/50 rounded-[2rem] border border-border/40 hover:bg-background/80 transition-all group">
            <div className="mb-6">
              <div className="flex items-center gap-2">
                <p className="font-black text-lg tracking-tight group-hover:text-primary transition-colors">Feedback</p>
                <Bell className="w-4 h-4 text-primary" />
              </div>
              <p className="text-xs text-muted-foreground font-medium leading-relaxed mt-1">Control the number of toast notifications.</p>
            </div>
            <select 
              value={toastLimit} 
              onChange={handleToastLimitChange}
              className="w-full h-12 bg-accent/50 border border-border/50 rounded-2xl px-4 text-foreground font-black text-xs uppercase tracking-widest focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all appearance-none cursor-pointer"
            >
              <option value="1">1 Alert Only</option>
              <option value="3">3 Alerts Max</option>
              <option value="5">5 Alerts Max</option>
            </select>
          </div>

        </div>
      </div>
    </div>
  );
}
