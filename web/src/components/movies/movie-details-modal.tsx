"use client";

import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Star,
  Calendar,
  Clock,
  Film,
  Plus,
  Check,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { createPortal } from "react-dom";
import { useEffect, useState } from "react";

interface MovieDetailsModalProps {
  movie: any | null;
  onClose: () => void;
  onAdd?: (movie: any) => void;
  isAdding?: boolean;
  isTracked?: boolean;
}

export function MovieDetailsModal({
  movie,
  onClose,
  onAdd,
  isAdding,
  isTracked,
}: MovieDetailsModalProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    if (movie) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "unset";
    }
    return () => {
      document.body.style.overflow = "unset";
    };
  }, [movie]);

  if (!mounted) return null;

  const modalContent = (
    <AnimatePresence>
      {movie && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 md:p-8">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="absolute inset-0 bg-background/80 backdrop-blur-xl"
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 20 }}
            className="relative w-full max-w-4xl bg-card/60 backdrop-blur-2xl border border-border/50 rounded-[3rem] overflow-hidden shadow-2xl flex flex-col md:flex-row max-h-[90vh]"
          >
            {/* Close Button */}
            <button
              onClick={onClose}
              className="absolute top-6 right-6 z-20 p-3 bg-background/50 backdrop-blur-md rounded-2xl text-muted-foreground hover:text-foreground hover:scale-110 transition-all border border-border/20 shadow-lg"
            >
              <X className="w-6 h-6" />
            </button>

            {/* Poster Section */}
            <div className="w-full md:w-[40%] relative aspect-[2/3] md:aspect-auto shrink-0">
              {movie.poster_url ? (
                <img
                  src={
                    movie.poster_url ||
                    `https://images.placeholders.dev/?width=500&height=750&text=${encodeURIComponent(movie.title)}&bgColor=%2318181b&textColor=%2371717a`
                  }
                  alt={movie.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full bg-accent flex items-center justify-center">
                  <Film className="w-20 h-20 text-muted-foreground opacity-20" />
                </div>
              )}
              <div className="absolute inset-0 bg-gradient-to-t from-background/90 via-transparent to-transparent md:bg-gradient-to-r md:from-transparent md:to-transparent" />
            </div>

            {/* Content Section */}
            <div className="flex-1 p-8 md:p-12 flex flex-col gap-8 overflow-y-auto">
              <div className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="px-3 py-1 bg-primary/20 text-primary text-[10px] font-black uppercase tracking-[0.2em] rounded-full border border-primary/20">
                    {movie.media_type || "Movie"}
                  </span>
                  <div className="flex items-center gap-1 text-yellow-500 font-black text-sm">
                    <Star className="w-4 h-4 fill-yellow-500" />
                    <span>{movie.vote_average || movie.rating || "0.0"}</span>
                  </div>
                </div>

                <h2 className="text-4xl md:text-5xl font-black tracking-tighter text-foreground leading-tight">
                  {movie.title}
                </h2>

                <div className="flex flex-wrap items-center gap-6 text-sm text-muted-foreground font-bold">
                  <div className="flex items-center gap-2">
                    <Calendar className="w-4 h-4 text-primary" />
                    <span>
                      {movie.release_date?.split("-")[0] ||
                        movie.release_year ||
                        "Unknown"}
                    </span>
                  </div>
                  {movie.runtime && (
                    <div className="flex items-center gap-2">
                      <Clock className="w-4 h-4 text-primary" />
                      <span>{movie.runtime} min</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-4">
                <h3 className="text-xs font-black uppercase tracking-widest text-primary">
                  Overview
                </h3>
                <p className="text-muted-foreground leading-relaxed text-base font-medium">
                  {movie.overview || "No description available for this title."}
                </p>
              </div>

              {(movie.genre_ids || movie.genres) && (
                <div className="flex flex-wrap gap-2">
                  {(movie.genre_ids
                    ? typeof movie.genre_ids === "string"
                      ? movie.genre_ids.split(",")
                      : movie.genre_ids
                    : movie.genres || []
                  ).map((genre: any, i: number) => (
                    <span
                      key={i}
                      className="px-4 py-2 bg-accent/50 text-muted-foreground text-xs font-bold rounded-xl border border-border/50"
                    >
                      {typeof genre === "string" ? genre : genre.name}
                    </span>
                  ))}
                </div>
              )}

              <div className="mt-auto pt-8 flex flex-col sm:flex-row gap-4">
                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    onAdd?.(movie);
                  }}
                  disabled={isAdding || isTracked}
                  className={`flex-1 h-14 rounded-2xl font-black text-sm uppercase tracking-widest transition-all shadow-xl ${isTracked ? "bg-primary/10 text-primary border border-primary/20 cursor-default" : "bg-primary text-primary-foreground hover:scale-[1.02] active:scale-[0.98]"}`}
                >
                  {isAdding ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                  ) : isTracked ? (
                    <span className="flex items-center gap-2">
                      <Check className="w-5 h-5" /> Tracked
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      <Plus className="w-5 h-5" /> Add to Library
                    </span>
                  )}
                </Button>

                <Button
                  variant="outline"
                  className="h-14 rounded-2xl font-black text-sm uppercase tracking-widest border-border hover:bg-accent transition-all px-8"
                  onClick={onClose}
                >
                  Close
                </Button>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );

  return createPortal(modalContent, document.body);
}
