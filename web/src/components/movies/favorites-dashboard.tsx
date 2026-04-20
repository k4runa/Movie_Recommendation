"use client";

import React, { useEffect, useState } from "react";
import { movieApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Star, Trash2, Loader2, Plus, Film } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

export const FavoritesDashboard = () => {
  const { user } = useAuthStore();
  const [favorites, setFavorites] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchFavorites = async () => {
    setLoading(true);
    try {
      const res = await movieApi.getMovies();
      const allMovies = res.data?.data?.watched_movies || [];
      const favs = allMovies.filter((m: any) => m.is_favorite);
      setFavorites(favs);
    } catch (err) {
      toast.error("Failed to load favorites.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFavorites();
  }, [user]);

  const removeFavorite = async (movieId: number) => {
    try {
      await movieApi.toggleFavorite(movieId);
      toast.success("Removed from favorites.");
      fetchFavorites();
    } catch (err) {
      toast.error("Failed to remove favorite.");
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-10 h-10 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-12">
      <div className="bg-card border border-border rounded-2xl p-8 md:p-12 relative overflow-hidden">
        <div className="absolute top-0 right-0 p-8 text-primary/5">
          <Star className="w-48 h-48 rotate-12" fill="currentColor" />
        </div>

        <div className="relative z-10 space-y-4 max-w-2xl">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 p-2 rounded-xl">
              <Star className="w-5 h-5 text-primary" fill="currentColor" />
            </div>
            <span className="text-[10px] font-black uppercase tracking-widest text-primary">Limited Edition Selection</span>
          </div>
          <h2 className="text-4xl md:text-5xl font-black tracking-tighter">Your All-Time Top 3</h2>
          <p className="text-muted-foreground font-medium text-lg leading-relaxed">
            These are the films that define your cinematic identity. Choose wisely—you can only showcase three at a time.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {[0, 1, 2].map((index) => {
          const fav = favorites[index];
          return (
            <div key={index} className="space-y-4">
              <div
                className={`aspect-[2/3] rounded-2xl border-2 border-dashed transition-all duration-500 overflow-hidden relative group
                  ${fav ? "border-transparent" : "border-border bg-accent/20 hover:bg-accent/40"}`}
              >
                {fav ? (
                  <>
                    {fav.poster_url ? (
                      <img
                        src={fav.poster_url}
                        alt={fav.title}
                        className="w-full h-full object-cover transition-all"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center p-6 text-center bg-card">
                        <span className="text-xl font-black tracking-tighter">{fav.title}</span>
                      </div>
                    )}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-6">
                      <button
                        onClick={() => removeFavorite(fav.id)}
                        className="bg-destructive text-destructive-foreground p-4 rounded-2xl flex items-center justify-center gap-2 font-black text-[10px] uppercase tracking-widest shadow-xl"
                      >
                        <Trash2 className="w-4 h-4" />
                        Remove Spot
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center space-y-4">
                    <div className="bg-accent size-14 rounded-2xl flex items-center justify-center mb-2">
                      <Plus className="w-6 h-6 text-muted-foreground" />
                    </div>
                    <div>
                      <h5 className="font-bold text-muted-foreground">Spot #{index + 1} Empty</h5>
                      <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest mt-1">Add from library</p>
                    </div>
                  </div>
                )}
              </div>
              {fav && (
                <div className="px-2">
                  <h4 className="font-black text-xl tracking-tighter truncate">{fav.title}</h4>
                  <p className="text-xs text-muted-foreground font-bold uppercase tracking-widest">{fav.release_date?.split("-")[0] || "Unknown"}</p>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="bg-accent/30 rounded-3xl p-6 border border-border flex items-center gap-4">
        <div className="bg-card p-3 rounded-2xl border border-border">
          <Film className="w-6 h-6 text-muted-foreground" />
        </div>
        <div>
          <h6 className="font-bold text-sm">How to add favorites?</h6>
          <p className="text-xs text-muted-foreground">Go to your main library and click the star icon on any movie card to pin it here.</p>
        </div>
      </div>
    </div>
  );
};
