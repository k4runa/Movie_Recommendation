"use client";

import { useEffect, useState } from "react";
import { movieApi } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Card } from "@/components/ui/card";
import { Loader2, Film, Star, Calendar, RefreshCw } from "lucide-react";
import { toast } from "sonner";
import { MovieDetailsModal } from "./movie-details-modal";

export function MovieDashboard() {
  const { user } = useAuthStore();
  const [movies, setMovies] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedMovie, setSelectedMovie] = useState<any | null>(null);

  useEffect(() => {
    loadMovies();

    // Listen for global movie-added event
    const handleMovieAdded = () => loadMovies();
    window.addEventListener("movie-added", handleMovieAdded);
    return () => window.removeEventListener("movie-added", handleMovieAdded);
  }, []);

  const loadMovies = async () => {
    setIsLoading(true);
    try {
      const res = await movieApi.getMovies();
      setMovies(
        res.data?.data?.watched_movies ||
          res.data?.data?.movies ||
          res.data ||
          [],
      );
    } catch (err) {
      console.error("Failed to load movies", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleFavorite = async (movieId: number) => {
    try {
      const res = await movieApi.toggleFavorite(movieId);
      if (res.data?.is_favorite) {
        toast.success("Added to favorites!");
      } else {
        toast.success("Removed from favorites.");
      }
      await loadMovies();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to update favorite");
    }
  };

  const handleRemoveMovie = async (movieId: number) => {
    try {
      await movieApi.deleteMovie(movieId);
      toast.success("Movie removed from your list");
      await loadMovies();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to remove movie");
    }
  };

  return (
    <div className="space-y-10">
      <div className="flex items-center justify-between px-2">
        <div className="flex items-center gap-3">
          <Film className="w-5 h-5 text-primary" />
          <h2 className="text-xs font-black uppercase tracking-[0.2em] text-muted-foreground">
            Your Library
          </h2>
        </div>

        <button
          onClick={loadMovies}
          disabled={isLoading}
          className="p-4 bg-card/40 border border-border/50 rounded-2xl text-muted-foreground hover:text-primary hover:bg-accent transition-all disabled:opacity-50 shadow-lg"
          title="Refresh List"
        >
          <RefreshCw className={`w-5 h-5 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>

      <div className="space-y-6">
        {isLoading && movies.length === 0 ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="w-10 h-10 animate-spin text-primary" />
          </div>
        ) : movies.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-center space-y-6 bg-card/20 rounded-[3rem] border border-border/50">
            <div className="w-16 h-16 rounded-2xl bg-accent flex items-center justify-center">
              <Film className="w-8 h-8 text-muted-foreground opacity-50" />
            </div>
            <div className="space-y-1">
              <h3 className="text-xl font-black tracking-tight text-foreground">
                Library is empty
              </h3>
              <p className="text-xs text-muted-foreground font-medium">
                Use the search bar at the top to track your first movie!
              </p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {movies.map((movie: any, idx: number) => (
              <Card
                key={idx}
                onClick={() => setSelectedMovie(movie)}
                className="bg-card/40 md:backdrop-blur-md border border-border/50 p-4 rounded-[2.5rem] flex flex-col gap-4 hover:bg-card/60 transition-all hover:-translate-y-2 hover:border-zinc-700 overflow-hidden group cursor-pointer"
              >
                <div className="w-full aspect-[2/3] bg-accent/30 rounded-[2rem] overflow-hidden relative border border-border/10">
                  <img
                    src={movie.poster_url || `https://images.placeholders.dev/?width=500&height=750&text=${encodeURIComponent(movie.title)}&bgColor=%2318181b&textColor=%2371717a`}
                    alt={movie.title}
                    className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                  />
                  <div className="absolute top-3 left-3 flex gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleToggleFavorite(movie.id);
                      }}
                      className={`p-2.5 rounded-xl border border-border/20 shadow-xl transition-all hover:scale-110 active:scale-90 md:backdrop-blur-xl ${
                        movie.is_favorite 
                          ? "bg-yellow-500 text-white border-yellow-400" 
                          : "bg-background/60 text-muted-foreground hover:text-yellow-500"
                      }`}
                      title={movie.is_favorite ? "Remove from favorites" : "Add to favorites"}
                    >
                      <Star className={`w-4 h-4 ${movie.is_favorite ? "fill-white" : ""}`} />
                    </button>
                  </div>

                  <div className="absolute top-3 right-3 bg-background/60 md:backdrop-blur-xl border border-border/20 px-3 py-1.5 rounded-xl flex items-center gap-1.5 text-xs font-black text-yellow-500 shadow-xl">
                    <Star className="w-3.5 h-3.5 fill-yellow-500" />
                    {movie.vote_average || movie.rating || "0.0"}
                  </div>

                  <div className="absolute bottom-3 right-3">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveMovie(movie.id);
                      }}
                      className="bg-background/80 hover:bg-destructive text-muted-foreground hover:text-white backdrop-blur-xl px-5 py-2.5 rounded-2xl flex items-center justify-center font-black text-xs uppercase tracking-widest shadow-lg transition-all hover:scale-105 active:scale-95 border border-border/20 hover:border-destructive"
                      title="Remove from list"
                    >
                      Remove
                    </button>
                  </div>
                </div>

                <div className="flex-1 flex flex-col px-1">
                  <h3
                    className="font-black text-xl text-foreground line-clamp-1 group-hover:text-primary transition-colors tracking-tight"
                    title={movie.title}
                  >
                    {movie.title}
                  </h3>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-black uppercase tracking-widest mt-1 mb-3">
                    <Calendar className="w-3 h-3" />
                    <span>
                      {movie.release_date || movie.release_year || "Unknown"}
                    </span>
                  </div>

                  {movie.overview && (
                    <p
                      className="text-xs text-muted-foreground mt-1 line-clamp-2 font-medium leading-relaxed"
                      title={movie.overview}
                    >
                      {movie.overview}
                    </p>
                  )}
                </div>

                {(movie.genre_ids || movie.genres) && (
                  <div className="flex flex-wrap gap-2 mt-auto pt-4 border-t border-border/10">
                    {(movie.genre_ids
                      ? typeof movie.genre_ids === "string"
                        ? movie.genre_ids.split(",")
                        : movie.genre_ids
                      : movie.genres
                    )
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
            ))}
          </div>
        )}
      </div>

      <MovieDetailsModal
        movie={selectedMovie}
        onClose={() => setSelectedMovie(null)}
        isTracked={true}
      />
    </div>
  );
}
