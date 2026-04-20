"use client";

import { useEffect, useState } from "react";
import { movieApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { useMovieStore } from "@/lib/movie-store";
import { Card } from "@/components/ui/card";
import {
  Loader2,
  Film,
  Star,
  Calendar,
  Sparkles,
  Plus,
  Check,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { MovieDetailsModal } from "./movie-details-modal";
import { EcoLoading } from "./eco-loading";

// Helper function
function cn(...classes: any[]) {
  return classes.filter(Boolean).join(" ");
}

export function RecommendationsDashboard() {
  const { user } = useAuthStore();
  const { recommendations, isRecsLoading, fetchRecommendations } =
    useMovieStore();
  const [trackingId, setTrackingId] = useState<number | null>(null);
  const [trackedIds, setTrackedIds] = useState<Set<number>>(new Set());
  const [selectedMovie, setSelectedMovie] = useState<any | null>(null);

  useEffect(() => {
    if (user?.username) {
      fetchRecommendations(user.username);
    }
  }, [user, fetchRecommendations]);

  const handleRefresh = () => {
    if (user?.username) {
      fetchRecommendations(user.username, true);
      toast.success("Refreshing recommendations with Eco...", {
        icon: <Sparkles className="w-4 h-4 text-primary" />,
      });
    }
  };

  const handleTrackMovie = async (movie: any) => {
    if (!user?.username) return;
    const tmdbId = movie.tmdb_id || movie.id;
    if (trackingId === tmdbId || trackedIds.has(tmdbId)) return;
    setTrackingId(tmdbId);
    try {
      await movieApi.addMovie(user.username, { tmdb_id: tmdbId });
      toast.success(`${movie.title} added to your library!`);

      // Remove from recommendations list immediately
      useMovieStore.setState((state) => ({
        recommendations: state.recommendations.filter(
          (m: any) => (m.tmdb_id || m.id) !== tmdbId,
        ),
      }));

      setTrackedIds((prev) => new Set(prev).add(tmdbId));
      window.dispatchEvent(new CustomEvent("movie-added"));
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add movie");
    } finally {
      setTrackingId(null);
    }
  };

  if (isRecsLoading && recommendations.length === 0) {
    return <EcoLoading />;
  }

  if (recommendations.length === 0) {
    return (
      <div className="p-16 border-2 border-dashed border-border/50 rounded-2xl flex flex-col items-center justify-center text-center space-y-6 bg-card/20 md:backdrop-blur-xl">
        <div className="w-20 h-20 rounded-3xl bg-primary/10 flex items-center justify-center border border-primary/20">
          <Sparkles className="w-10 h-10 text-primary" />
        </div>
        <div className="space-y-2">
          <h4 className="text-2xl font-black tracking-tighter text-foreground">
            Not Enough Data
          </h4>
          <p className="text-muted-foreground max-w-sm font-medium">
            Add more movies to your library so the AI can understand your taste
            and generate personalized recommendations.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header / Refresh */}
      <div className="flex justify-end">
        <button
          onClick={handleRefresh}
          disabled={isRecsLoading}
          className="group flex items-center gap-2 px-6 py-3 bg-card/40 border border-border/50 rounded-2xl text-muted-foreground hover:text-primary hover:bg-accent transition-all disabled:opacity-50 font-bold text-sm shadow-lg"
        >
          <RefreshCw
            className={cn(
              "w-4 h-4 transition-transform duration-700",
              isRecsLoading ? "animate-spin" : "group-hover:rotate-180",
            )}
          />
          <span>Refresh</span>
        </button>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
        {recommendations.map((movie: any, idx: number) => {
          const tmdbId = movie.tmdb_id || movie.id;
          const isTracked = trackedIds.has(tmdbId);

          return (
            <Card
              key={idx}
              onClick={() => setSelectedMovie(movie)}
              className="bg-card/40 md:backdrop-blur-md border border-border/50 p-4 rounded-2xl flex flex-col gap-4 hover:bg-card/60 transition-all hover:-translate-y-1 hover:border-primary/50 overflow-hidden group cursor-pointer"
            >
              {/* Image Section */}
              <div className="w-full aspect-[2/3] bg-accent/30 rounded-xl overflow-hidden relative border border-border/10">
                <img
                  src={
                    movie.poster_url ||
                    `https://images.placeholders.dev/?width=500&height=750&text=${encodeURIComponent(movie.title)}&bgColor=%2318181b&textColor=%2371717a`
                  }
                  alt={movie.title}
                  className="w-full h-full object-cover transition-all"
                />

                <div className="absolute top-3 right-3 bg-background/60 md:backdrop-blur-xl border border-border/20 px-3 py-1.5 rounded-xl flex items-center gap-1.5 text-xs font-black text-yellow-500 shadow-xl">
                  <Star className="w-3.5 h-3.5 fill-yellow-500" />
                  {movie.vote_average || movie.rating || "0.0"}
                </div>

                <div className="absolute bottom-3 right-3">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTrackMovie(movie);
                    }}
                    disabled={trackingId === tmdbId || isTracked}
                    className={cn(
                      "backdrop-blur-xl px-4 py-2.5 rounded-2xl flex items-center justify-center font-black text-xs uppercase tracking-widest transition-all shadow-2xl",
                      isTracked
                        ? "bg-primary/20 text-primary border border-primary/30"
                        : "bg-primary text-primary-foreground hover:scale-105 active:scale-95",
                    )}
                  >
                    {trackingId === tmdbId ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : isTracked ? (
                      <Check className="w-4 h-4" />
                    ) : (
                      <span className="flex items-center gap-1.5">
                        <Plus className="w-4 h-4" /> Track
                      </span>
                    )}
                  </button>
                </div>
              </div>

              {/* Content Section */}
              <div className="flex-1 flex flex-col px-1">
                <h3 className="font-black text-xl text-foreground line-clamp-1 group-hover:text-primary transition-colors tracking-tight">
                  {movie.title}
                </h3>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-black uppercase tracking-widest mt-1 mb-3">
                  <Calendar className="w-3 h-3" />
                  <span>
                    {movie.release_date || movie.release_year || "Unknown"}
                  </span>
                </div>

                <p className="text-xs text-muted-foreground line-clamp-2 font-medium leading-relaxed mb-4">
                  {movie.overview}
                </p>

                {movie.ai_reason && movie.ai_reason !== "N/A" && (
                  <div className="mt-auto bg-primary/10 border border-primary/20 p-4 rounded-2xl shadow-inner group-hover:bg-primary/20 transition-colors">
                    <p className="text-[11px] text-primary line-clamp-2 italic font-black flex items-start gap-2 leading-snug">
                      <Sparkles className="w-4 h-4 shrink-0" />
                      <span>{movie.ai_reason}</span>
                    </p>
                  </div>
                )}
              </div>

              {/* Genres */}
              {(movie.genre_ids || movie.genres) && (
                <div className="flex flex-wrap gap-2 pt-4 border-t border-border/10">
                  {(movie.genre_ids || movie.genres || [])
                    .slice(0, 3)
                    .map((g: string, i: number) => (
                      <span
                        key={i}
                        className="text-[10px] uppercase font-black tracking-widest bg-accent text-muted-foreground px-3 py-1 rounded-full border border-border/50"
                      >
                        {g}
                      </span>
                    ))}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      <MovieDetailsModal
        movie={selectedMovie}
        onClose={() => setSelectedMovie(null)}
        onAdd={handleTrackMovie}
        isAdding={trackingId === (selectedMovie?.tmdb_id || selectedMovie?.id)}
        isTracked={trackedIds.has(selectedMovie?.tmdb_id || selectedMovie?.id)}
      />
    </div>
  );
}
