"use client";

import { useState, useEffect } from "react";
import { useAuthStore } from "@/lib/store";
import { authApi, getFullUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Loader2, 
  User, 
  Palette, 
  Sparkles, 
  Bell, 
  Moon, 
  Sun, 
  Camera, 
  Shield, 
  Fingerprint, 
  Globe, 
  Mail,
  Smartphone,
  Server,
  Check
} from "lucide-react";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

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
  const [isUploading, setIsUploading] = useState(false);
  
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileValues, setProfileValues] = useState({
    nickname: user?.nickname || "",
    bio: user?.bio || "",
    gender: user?.gender || "",
    age: user?.age?.toString() || "",
    location: user?.location || ""
  });

  const handleAvatarUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    setIsUploading(true);
    try {
      await authApi.uploadAvatar(formData);
      await checkAuth(true);
      toast.success("Profile picture updated!");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setIsUploading(false);
    }
  };

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (user) {
      setProfileValues({
        nickname: user.nickname || "",
        bio: user.bio || "",
        gender: user.gender || "",
        age: user.age?.toString() || "",
        location: user.location || ""
      });
    }
  }, [user]);

  const handleUpdateProfile = async () => {
    setIsSubmitting(true);
    try {
      await authApi.updateProfile({
        nickname: profileValues.nickname,
        bio: profileValues.bio,
        gender: profileValues.gender,
        age: profileValues.age ? parseInt(profileValues.age) : null,
        location: profileValues.location
      });
      await checkAuth(true);
      toast.success("Profile updated successfully!");
      setIsEditingProfile(false);
    } catch (err: any) {
      toast.error("Failed to update profile");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUpdateUsername = async () => {
    if (!newUsername || !currentPassword) {
      toast.error("Please provide new username and current password");
      return;
    }
    setIsSubmitting(true);
    try {
      const res = await authApi.updateUserField({
        field: "username",
        value: newUsername,
        current_password: currentPassword
      });
      if (res.data.new_token) {
        localStorage.setItem("access_token", res.data.new_token);
        await checkAuth(true);
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
      await authApi.updateUserField({
        field: "ai_enabled",
        value: newValue
      });
      await checkAuth(true); // Sync the global store so the state persists across tab changes
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
    <div className="bg-transparent space-y-8 max-w-4xl mx-auto">
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <User className="w-4 h-4 text-foreground/70" />
          <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/80">Profile Management</label>
        </div>
        
        <div className="flex flex-col sm:flex-row gap-6 p-4 sm:p-6 bg-card rounded-xl border border-border shadow-sm group transition-all items-center sm:items-start text-center sm:text-left">
          <div className="relative group/avatar">
            <div className="size-20 sm:size-24 rounded-[2rem] bg-gradient-to-br from-primary to-primary-foreground flex items-center justify-center text-white font-black text-2xl sm:text-3xl shadow-xl overflow-hidden border-2 border-border">
              {user?.avatar_url ? (
                <img src={getFullUrl(user.avatar_url)} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                user?.username?.[0]?.toUpperCase()
              )}
              
              {isUploading && (
                <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                  <Loader2 className="w-6 h-6 animate-spin text-white" />
                </div>
              )}
            </div>
            
            <label className="absolute -bottom-1 -right-1 size-8 bg-card border border-border rounded-xl flex items-center justify-center cursor-pointer shadow-lg hover:bg-accent transition-colors group-hover/avatar:scale-110 active:scale-95">
              <Camera className="w-3.5 h-3.5 text-foreground" />
              <input type="file" className="hidden" accept="image/*" onChange={handleAvatarUpload} disabled={isUploading} />
            </label>
          </div>

          <div className="flex-1 w-full flex flex-col sm:flex-row items-center sm:items-end justify-between gap-4">
            <div className="space-y-1">
              <p className="font-bold text-xl sm:text-2xl tracking-tight text-foreground">{user?.username}</p>
              <p className="text-xs text-muted-foreground font-medium">Public Account Identity</p>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button 
                variant="outline" 
                className="w-full sm:w-auto rounded-lg px-4 font-bold text-[10px] uppercase tracking-widest transition-all h-8 border-border hover:bg-accent text-foreground"
                onClick={() => setIsEditingUsername(!isEditingUsername)}
              >
                {isEditingUsername ? "Cancel" : "Change Username"}
              </Button>
            </div>
          </div>
        </div>
          
          {isEditingUsername && (
            <motion.div 
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              className="pt-6 border-t border-border space-y-4"
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <Label className="text-[9px] font-black text-muted-foreground uppercase tracking-[0.15em] ml-1">New Username</Label>
                  <input 
                    type="text" 
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                    className="w-full h-10 bg-accent border border-transparent rounded-lg px-3 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-all font-medium"
                    placeholder="Enter new username"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[9px] font-black text-muted-foreground uppercase tracking-[0.15em] ml-1">Current Password</Label>
                  <input 
                    type="password" 
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    className="w-full h-10 bg-accent border border-transparent rounded-lg px-3 text-xs text-foreground placeholder-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-all font-medium"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <Button 
                onClick={handleUpdateUsername} 
                disabled={isSubmitting || !newUsername || !currentPassword}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg h-10 font-black text-[10px] uppercase tracking-widest transition-all"
              >
                {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Commit Changes"}
              </Button>
            </motion.div>
          )}

          <div className="pt-6 border-t border-border space-y-8">
            <div className="flex items-center justify-between px-1">
              <div className="space-y-0.5">
                <h4 className="text-sm font-bold tracking-tight text-foreground">Identity Details</h4>
                <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest">Public Persona & Biography</p>
              </div>
              {!isEditingProfile && (
                <Button 
                  variant="ghost" 
                  size="sm"
                  onClick={() => setIsEditingProfile(true)}
                  className="h-8 px-4 text-[10px] font-black uppercase tracking-widest text-primary hover:bg-primary/10 rounded-lg transition-all"
                >
                  Edit Profile
                </Button>
              )}
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-12">
              <div className="lg:col-span-7 space-y-6">
                {/* Nickname & Bio Field */}
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold text-foreground ml-0.5">Display Name (Nickname)</Label>
                    {isEditingProfile ? (
                      <input 
                        type="text" 
                        value={profileValues.nickname}
                        onChange={(e) => setProfileValues({...profileValues, nickname: e.target.value})}
                        className="w-full h-11 bg-accent/50 border border-border rounded-xl px-4 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-medium"
                        placeholder="e.g. CinemaLover"
                      />
                    ) : (
                      <div className="w-full h-11 bg-accent/20 border border-border/50 rounded-xl px-4 flex items-center text-sm text-foreground/80 font-medium">
                        {user?.nickname || user?.username}
                      </div>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label className="text-xs font-semibold text-foreground ml-0.5">Biography</Label>
                    {isEditingProfile ? (
                      <textarea 
                        value={profileValues.bio}
                        onChange={(e) => setProfileValues({...profileValues, bio: e.target.value})}
                        className="w-full min-h-[120px] bg-accent/50 border border-border rounded-xl p-4 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-medium resize-none"
                        placeholder="Tell us about your cinematic journey..."
                      />
                    ) : (
                      <div className="w-full min-h-[60px] bg-accent/20 border border-border/50 rounded-xl px-4 py-3 text-sm text-foreground/80 font-medium leading-relaxed italic">
                        {user?.bio || "No biography provided yet."}
                      </div>
                    )}
                    <p className="text-[10px] text-muted-foreground/60 font-medium ml-1 uppercase tracking-wider">Visible to other cinephiles</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label className="text-xs font-semibold text-foreground ml-0.5">Location</Label>
                    {isEditingProfile ? (
                      <input 
                        type="text" 
                        value={profileValues.location}
                        onChange={(e) => setProfileValues({...profileValues, location: e.target.value})}
                        className="w-full h-11 bg-accent/50 border border-border rounded-xl px-4 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-medium"
                        placeholder="e.g. Istanbul, TR"
                      />
                    ) : (
                      <div className="w-full h-11 bg-accent/20 border border-border/50 rounded-xl px-4 flex items-center text-sm text-foreground/80 font-medium">
                        {user?.location || "Unknown Node"}
                      </div>
                    )}
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-xs font-semibold text-foreground ml-0.5">Age</Label>
                      {isEditingProfile ? (
                        <input 
                          type="number" 
                          value={profileValues.age}
                          onChange={(e) => setProfileValues({...profileValues, age: e.target.value})}
                          className="w-full h-11 bg-accent/50 border border-border rounded-xl px-4 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-medium"
                          placeholder="25"
                        />
                      ) : (
                        <div className="w-full h-11 bg-accent/20 border border-border/50 rounded-xl px-4 flex items-center text-sm text-foreground/80 font-medium">
                          {user?.age || "Secret"}
                        </div>
                      )}
                    </div>
                    <div className="space-y-2">
                      <Label className="text-xs font-semibold text-foreground ml-0.5">Gender</Label>
                      {isEditingProfile ? (
                        <input 
                          type="text" 
                          value={profileValues.gender}
                          onChange={(e) => setProfileValues({...profileValues, gender: e.target.value})}
                          className="w-full h-11 bg-accent/50 border border-border rounded-xl px-4 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all font-medium"
                          placeholder="Identify"
                        />
                      ) : (
                        <div className="w-full h-11 bg-accent/20 border border-border/50 rounded-xl px-4 flex items-center text-sm text-foreground/80 font-medium">
                          {user?.gender || "Not specified"}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="lg:col-span-5">
                <div className="bg-accent/30 border border-border/50 rounded-2xl p-6 space-y-4">
                  <h5 className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">Discovery Guide</h5>
                  <p className="text-xs leading-relaxed text-muted-foreground font-medium">
                    Your profile details help Eco match you with kindred spirits. A complete bio increases your visibility in the Social Discovery feed.
                  </p>
                  <Separator className="bg-border/50" />
                  <ul className="space-y-3">
                    {["Detailed Bio", "Current Location", "Film Preferences"].map((item, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-foreground/70">
                        <Check className="w-3 h-3 text-primary" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {isEditingProfile && (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-end gap-3 pt-6 border-t border-border"
              >
                <Button 
                  variant="ghost" 
                  onClick={() => setIsEditingProfile(false)}
                  className="h-10 px-6 text-[10px] font-black uppercase tracking-widest text-muted-foreground hover:bg-accent rounded-xl"
                >
                  Discard
                </Button>
                <Button 
                  onClick={handleUpdateProfile}
                  disabled={isSubmitting}
                  className="h-10 px-8 bg-primary text-primary-foreground rounded-xl font-black text-[10px] uppercase tracking-widest shadow-lg hover:shadow-primary/20 transition-all active:scale-[0.98]"
                >
                  {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : "Commit Changes"}
                </Button>
              </motion.div>
            )}
          </div>
        </div>
      
      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Palette className="w-4 h-4 text-foreground/70" />
          <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/80">App Preferences</label>
        </div>

        <div className="w-full rounded-xl border border-border bg-card p-6 shadow-sm space-y-6">
          <div>
            <h3 className="text-lg font-bold tracking-tight text-foreground">Interface & Features</h3>
            <p className="text-muted-foreground text-xs font-medium mt-0.5">Personalize your cinematic experience.</p>
          </div>
          
          <div className="space-y-4">
            {/* Theme Toggle */}
            <div className="flex items-center justify-between p-4 bg-accent/50 rounded-lg border border-transparent hover:border-border transition-all group">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Label htmlFor="theme-mode" className="text-sm font-bold cursor-pointer text-foreground">Theme Mode</Label>
                  {theme === 'dark' ? <Moon className="w-3.5 h-3.5 text-foreground" /> : <Sun className="w-3.5 h-3.5 text-foreground" />}
                </div>
                <p className="text-[10px] text-muted-foreground font-medium">Switch between dark & light cinematic modes.</p>
              </div>
              <Switch 
                id="theme-mode"
                checked={theme === 'dark'}
                onCheckedChange={(checked) => setTheme(checked ? 'dark' : 'light')}
              />
            </div>

            {/* AI Toggle */}
            <div className="flex items-center justify-between p-4 bg-accent/50 rounded-lg border border-transparent hover:border-border transition-all group">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Label htmlFor="ai-toggle" className="text-sm font-bold cursor-pointer text-foreground">AI Eco Assistant</Label>
                  <Sparkles className="w-3.5 h-3.5 text-foreground" />
                </div>
                <p className="text-[10px] text-muted-foreground font-medium">Enable deep cinematic analysis & chat memory.</p>
              </div>
              <Switch 
                id="ai-toggle"
                checked={aiEnabled}
                onCheckedChange={handleToggleAi}
              />
            </div>

            {/* Toast Limit */}
            <div className="flex items-center justify-between p-4 bg-accent/50 rounded-lg border border-transparent hover:border-border transition-all group">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <Label htmlFor="toast-limit" className="text-sm font-bold cursor-pointer text-foreground">Feedback Frequency</Label>
                  <Bell className="w-3.5 h-3.5 text-foreground" />
                </div>
                <p className="text-[10px] text-muted-foreground font-medium">Control the number of notification alerts.</p>
              </div>
              <div className="relative">
                <select 
                  id="toast-limit"
                  value={toastLimit} 
                  onChange={handleToastLimitChange}
                  className="bg-accent border border-transparent rounded-lg px-3 py-1.5 text-foreground font-bold text-[9px] uppercase tracking-widest focus:outline-none focus:ring-1 focus:ring-ring transition-all appearance-none cursor-pointer pr-7"
                >
                  <option value="1">1 Alert</option>
                  <option value="3">3 Max</option>
                  <option value="5">5 Max</option>
                </select>
                <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground">
                  <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M19 9l-7 7-7-7" /></svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-2 mb-1">
          <Shield className="w-4 h-4 text-foreground/70" />
          <label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground/80">Privacy & Identity</label>
        </div>

        <div className="w-full rounded-xl border border-border bg-card p-6 shadow-sm space-y-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-4">
              <h4 className="text-[10px] font-black uppercase tracking-widest text-primary">Core Information</h4>
              
              <div className="space-y-3">
                <InfoRow Icon={Mail} label="Email Address" value={user?.email || "N/A"} />
                <InfoRow Icon={User} label="Unique Username" value={user?.username || "N/A"} />
                <InfoRow Icon={Fingerprint} label="Account ID" value={`#${user?.id || "0"}`} />
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-[10px] font-black uppercase tracking-widest text-primary">Digital Trace (Current Node)</h4>
              
              <div className="space-y-3">
                <InfoRow Icon={Globe} label="Geo Location" value={`${user?.city || "Unknown"}, ${user?.country || "Earth"}`} />
                <InfoRow Icon={Server} label="IP Signature" value={user?.ip || "0.0.0.0"} />
                <InfoRow Icon={Smartphone} label="Host OS" value={user?.os || "Unknown Platform"} />
              </div>
            </div>
          </div>
          
          <div className="pt-6 border-t border-border space-y-4">
            <h4 className="text-[10px] font-black uppercase tracking-widest text-primary">Public Visibility</h4>
            <p className="text-[10px] text-muted-foreground font-medium">Control what other users see on your public profile.</p>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <PrivacyToggle 
                label="Show Bio" 
                checked={user?.show_bio ?? true} 
                onToggle={async (val) => {
                  await authApi.updateUserField({ field: "show_bio", value: val });
                  await checkAuth(true);
                }}
              />
              <PrivacyToggle 
                label="Show Favorites" 
                checked={user?.show_favorites ?? true} 
                onToggle={async (val) => {
                  await authApi.updateUserField({ field: "show_favorites", value: val });
                  await checkAuth(true);
                }}
              />
              <PrivacyToggle 
                label="Show Age" 
                checked={user?.show_age ?? true} 
                onToggle={async (val) => {
                  await authApi.updateUserField({ field: "show_age", value: val });
                  await checkAuth(true);
                }}
              />
              <PrivacyToggle 
                label="Show Gender" 
                checked={user?.show_gender ?? true} 
                onToggle={async (val) => {
                  await authApi.updateUserField({ field: "show_gender", value: val });
                  await checkAuth(true);
                }}
              />
              <PrivacyToggle 
                label="Show Location" 
                checked={user?.show_location ?? true} 
                onToggle={async (val) => {
                  await authApi.updateUserField({ field: "show_location", value: val });
                  await checkAuth(true);
                }}
              />
              <PrivacyToggle 
                label="Public Discovery" 
                checked={!(user?.is_private ?? false)} 
                onToggle={async (val) => {
                  await authApi.updateUserField({ field: "is_private", value: !val });
                  await checkAuth(true);
                }}
              />
            </div>
          </div>

          <div className="pt-6 border-t border-border">
            <div className="bg-accent/30 rounded-2xl p-4 flex items-start gap-3">
              <div className="mt-0.5">
                <Shield className="w-3.5 h-3.5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-[10px] font-bold text-muted-foreground leading-relaxed">
                  Your privacy is our priority. Metadata is encrypted and used only for security auditing and personalized AI analysis. CineWave never sells your digital signature.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

const InfoRow = ({ Icon, label, value }: { Icon: any, label: string, value: string }) => (
  <div className="flex items-center gap-3">
    <div className="size-8 rounded-lg bg-accent/50 flex items-center justify-center text-muted-foreground">
      <Icon className="w-4 h-4" />
    </div>
    <div className="flex-1">
      <p className="text-[9px] font-black uppercase tracking-widest text-muted-foreground/60 leading-none mb-1">{label}</p>
      <p className="text-sm font-bold tracking-tight text-foreground">{value}</p>
    </div>
  </div>
);

const PrivacyToggle = ({ label, checked, onToggle }: { label: string, checked: boolean, onToggle: (val: boolean) => Promise<void> }) => {
  const [loading, setLoading] = useState(false);

  const handleToggle = async () => {
    setLoading(true);
    try {
      await onToggle(!checked);
      toast.success(`${label} updated!`);
    } catch (err) {
      toast.error(`Failed to update ${label}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-between p-3 bg-accent/30 rounded-xl border border-transparent hover:border-border transition-all">
      <span className="text-[10px] font-bold text-foreground uppercase tracking-widest">{label}</span>
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin text-muted-foreground" />
      ) : (
        <Switch checked={checked} onCheckedChange={handleToggle} />
      )}
    </div>
  );
};
