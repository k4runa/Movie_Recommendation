"use client";

import React, { useEffect, useState } from "react";
import { socialApi, getFullUrl } from "@/lib/api";
import { Users, Info, MessageSquare, Loader2, Sparkles, Send } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";
import { useSocialStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const getTimeAgo = (dateString: string) => {
  if (!dateString) return "";
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h`;
  return `${Math.floor(diffInSeconds / 86400)}d`;
};

const isUserOnline = (lastSeen: string | null) => {
  if (!lastSeen) return false;
  const date = new Date(lastSeen);
  const now = new Date();
  return (now.getTime() - date.getTime()) < 3 * 60 * 1000;
};

interface SimilarUser {
  target_user: {
    id: number;
    username: string;
    nickname?: string;
    avatar_url?: string;
    last_seen: string;
  };
  score: number;
  reasons: string;
}

export const SimilarMindsDashboard = ({ onTabChange }: { onTabChange?: (tab: "movies" | "recommendations" | "settings" | "social" | "favorites" | "messages") => void }) => {
  const { setActiveChatId } = useSocialStore();
  const [matches, setMatches] = useState<SimilarUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedUser, setSelectedUser] = useState<number | null>(null);

  const fetchMatches = async () => {
    setLoading(true);
    try {
      const res = await socialApi.getSimilarMinds();
      setMatches(res.data?.data?.matches || []);
    } catch (err) {
      console.error(err);
      toast.error("Failed to load similar minds.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatches();
  }, []);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
        <p className="text-muted-foreground font-medium">Scanning the multiverse for your cinematic twins...</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {matches.length === 0 ? (
        <div className="text-center py-20 border-2 border-dashed border-border rounded-3xl space-y-4">
          <div className="bg-accent w-16 h-16 rounded-2xl flex items-center justify-center mx-auto">
            <Users className="w-8 h-8 text-muted-foreground" />
          </div>
          <h4 className="text-xl font-bold">No twins found yet</h4>
          <p className="text-muted-foreground max-w-md mx-auto">
            Keep adding movies to your library! Once we know your taste better, we'll find people who share your passion.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {matches.map((match) => (
            <motion.div
              key={match.target_user.id}
              whileHover={{ y: -5 }}
              className="bg-card border border-border rounded-2xl p-6 transition-all cursor-pointer group relative overflow-hidden hover:border-primary/50 hover:-translate-y-1"
              onClick={() => setSelectedUser(match.target_user.id)}
            >
              <div className="absolute top-0 right-0 p-4">
                <div className="bg-primary/10 text-primary text-[10px] font-black uppercase tracking-widest px-2 py-1 rounded-full">
                  {Math.round(match.score * 100)}% Match
                </div>
              </div>

              <div className="flex items-center gap-4 mb-6 pr-16">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary to-primary-foreground flex items-center justify-center text-white font-black text-xl overflow-hidden border border-border">
                  {match.target_user.avatar_url ? (
                    <img src={getFullUrl(match.target_user.avatar_url)} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                    (match.target_user.nickname || match.target_user.username)[0].toUpperCase()
                  )}
                </div>
                <div className="flex flex-col">
                  <h4 className="font-bold text-lg leading-none mb-1 group-hover:text-primary transition-colors">
                    {match.target_user.nickname || match.target_user.username}
                  </h4>
                  <div className="flex items-center gap-1.5">
                    <div className={cn(
                      "size-1.5 rounded-full shadow-sm",
                      isUserOnline(match.target_user.last_seen) ? "bg-emerald-500" : "bg-muted-foreground/30"
                    )} />
                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                      {isUserOnline(match.target_user.last_seen) ? "Active now" : `Last seen ${getTimeAgo(match.target_user.last_seen)}`}
                    </span>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="bg-accent/50 rounded-2xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Info className="w-3.5 h-3.5 text-primary" />
                    <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Why we matched</span>
                  </div>
                  <p className="text-xs font-medium italic">"{match.reasons}"</p>
                </div>

                <div className="flex gap-2">
                  <button className="flex-1 bg-foreground text-background text-[10px] font-black uppercase tracking-widest py-3 rounded-xl hover:opacity-90 transition-opacity">
                    View Profile
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* Profile Modal */}
      <AnimatePresence>
        {selectedUser && (
          <UserProfileModal 
            userId={selectedUser} 
            onClose={() => setSelectedUser(null)} 
            onTabChange={onTabChange}
            setActiveChatId={setActiveChatId}
          />
        )}
      </AnimatePresence>
    </div>
  );
};

export const UserProfileModal = ({ 
  userId, 
  onClose, 
  onTabChange, 
  setActiveChatId 
}: { 
  userId: number; 
  onClose: () => void;
  onTabChange?: (tab: any) => void;
  setActiveChatId: (id: number | null) => void;
}) => {
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const res = await socialApi.getProfile(userId);
        setProfile(res.data?.data);
      } catch (err) {
        toast.error("Failed to load user profile.");
        onClose();
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [userId]);

  if (loading) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
        className="absolute inset-0 bg-background/80 backdrop-blur-md"
      />
      <motion.div
        initial={{ scale: 0.9, opacity: 0, y: 20 }}
        animate={{ scale: 1, opacity: 1, y: 0 }}
        exit={{ scale: 0.9, opacity: 0, y: 20 }}
        className="relative bg-card border border-border w-full max-w-2xl rounded-2xl shadow-xl overflow-hidden"
      >
        {/* New Message Button in Modal Header */}
        <div className="absolute top-6 right-6 z-10">
          <button
            onClick={() => {
              setActiveChatId(profile.id);
              if (onTabChange) onTabChange("messages");
              onClose();
            }}
            className="flex items-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground rounded-xl font-black text-[10px] uppercase tracking-widest transition-all hover:-translate-y-0.5 active:scale-95"
          >
            <Send className="w-3 h-3" />
            Send Message
          </button>
        </div>

        <div className="h-32 bg-gradient-to-r from-primary/20 via-primary/5 to-transparent border-b border-border" />
        
        <div className="px-8 pb-8 -mt-12">
          <div className="flex flex-col md:flex-row md:items-end gap-6 mb-8">
            <div className="size-24 rounded-2xl bg-gradient-to-br from-primary to-primary-foreground border-4 border-card flex items-center justify-center text-white font-black text-4xl overflow-hidden">
              {profile.avatar_url ? (
                <img src={getFullUrl(profile.avatar_url)} alt="Avatar" className="w-full h-full object-cover" />
              ) : (
                (profile.nickname || profile.username)[0].toUpperCase()
              )}
            </div>
            <div className="flex-1">
              <h3 className="text-3xl font-black tracking-tighter mb-1">{profile.nickname || profile.username}</h3>
              <div className="flex items-center gap-1.5 mb-2">
                <div className={cn(
                  "size-1.5 rounded-full shadow-sm",
                  isUserOnline(profile.last_seen) ? "bg-emerald-500" : "bg-muted-foreground/30"
                )} />
                <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                  {isUserOnline(profile.last_seen) ? "Active now" : `Last seen ${getTimeAgo(profile.last_seen || "")}`}
                </span>
              </div>
              {profile.nickname && <p className="text-[10px] text-muted-foreground font-black uppercase tracking-widest mb-1">@{profile.username}</p>}
              <div className="flex flex-wrap gap-2 mb-2">
                {profile.top_genres.map((gid: number) => (
                  <span key={gid} className="text-[9px] font-black uppercase tracking-widest bg-accent px-2 py-1 rounded-md text-muted-foreground">
                    Genre #{gid}
                  </span>
                ))}
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                {profile.age && <span>Age: {profile.age}</span>}
                {profile.gender && <span>Gender: {profile.gender}</span>}
                {profile.location && <span>Location: {profile.location}</span>}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="space-y-6">
              {profile.bio && (
                <div className="bg-accent/30 rounded-2xl p-4 border border-border/50">
                  <h5 className="text-[9px] font-black uppercase tracking-widest text-muted-foreground mb-2">Biography</h5>
                  <p className="text-xs font-medium leading-relaxed">{profile.bio}</p>
                </div>
              )}
              
              <div>
                <h5 className="text-[10px] font-black uppercase tracking-widest text-primary mb-4">Top 3 Favorites</h5>
                <div className="flex gap-3">
                  {profile.favorites.length > 0 ? (
                    profile.favorites.map((fav: any) => (
                      <div key={fav.id} className="group relative aspect-[2/3] w-full rounded-2xl overflow-hidden border border-border bg-accent">
                        {fav.poster_url ? (
                          <img src={fav.poster_url} alt={fav.title} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-[8px] text-center p-2 font-bold uppercase">
                            {fav.title}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <div className="w-full py-10 bg-accent/50 rounded-2xl border border-dashed border-border flex items-center justify-center text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                      No favorites set
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="space-y-6">
              <div className="bg-accent/50 rounded-3xl p-6 border border-border">
                <div className="flex items-center gap-2 mb-4">
                  <div className="bg-primary p-1.5 rounded-lg">
                    <Sparkles className="w-3.5 h-3.5 text-white" />
                  </div>
                  <h5 className="text-[10px] font-black uppercase tracking-widest">Eco's Impression</h5>
                </div>
                <p className="text-sm font-medium leading-relaxed italic text-muted-foreground">
                  {generateImpression(profile)}
                </p>
              </div>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

const generateImpression = (profile: any) => {
  const genres = profile.top_genres || [];
  const favCount = profile.favorites?.length || 0;
  const username = profile.nickname || profile.username;
  const bio = profile.bio;

  const intros = [
    `Eco notes that ${username} has a specialized focus.`,
    `A fascinating profile, ${username} seems to value cinematic depth.`,
    `My analysis of ${username} reveals a pattern of discovery.`,
    `${username}'s collection is a journey through genres.`
  ];

  const content = [];
  if (bio) {
    content.push(`Their personal bio suggests a deep connection to their interests.`);
  }

  if (favCount > 0) {
    content.push(`With ${favCount} curated favorites, their taste is quite defined.`);
  } else {
    content.push("They are still exploring the vast ocean of cinema.");
  }

  if (genres.length > 0) {
    content.push(`The profile suggests a love for diverse narratives.`);
  }

  const conclusions = [
    "A perfect match for shared discussions.",
    "A true kindred spirit for your journey.",
    "Definitely someone to keep an eye on in the discovery feed.",
    "Their taste mirrors the sophisticated side of CineWave."
  ];

  const intro = intros[Math.floor((username.length + favCount) + (bio?.length || 0) % intros.length)];
  const conclusion = conclusions[Math.floor((username.length * 3) % conclusions.length)];

  return `"${intro} ${content.join(" ")} ${conclusion}"`;
};
