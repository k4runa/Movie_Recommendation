"use client";

import { useState, useRef, useEffect } from "react";
import { Search, Loader2, X, Film, Check, Plus, Star } from "lucide-react";
import { movieApi } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import { useAuthStore } from "@/lib/store";
import { toast } from "sonner";
import { MovieDetailsModal } from "./movie-details-modal";

export function MovieSearch() {
  const { user } = useAuthStore();
  const [query, setQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedMovie, setSelectedMovie] = useState<any | null>(null);
  const [addingId, setAddingId] = useState<number | null>(null);
  const [trackedIds, setTrackedIds] = useState<Set<number>>(new Set());

  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);

    // Initial fetch of tracked movies to show correct status
    const fetchTracked = async () => {
      try {
        const res = await movieApi.getMovies();
        const movies =
          res.data?.data?.watched_movies ||
          res.data?.data?.movies ||
          res.data ||
          [];
        setTrackedIds(new Set(movies.map((m: any) => m.tmdb_id)));
      } catch (err) {
        console.log("Failed to fetch tracked movies for search (Background):", err);
      }
    };
    fetchTracked();

    const handleMovieAdded = (e: any) => {
      // If we have detail in event, add it
      const id = e.detail?.tmdb_id;
      if (id) setTrackedIds((prev) => new Set(prev).add(id));
      else fetchTracked(); // fallback to refetch
    };

    window.addEventListener("movie-added", handleMovieAdded);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      window.removeEventListener("movie-added", handleMovieAdded);
    };
  }, [user]);

  // Auto-search (debounce) when query changes
  useEffect(() => {
    const delayDebounceFn = setTimeout(() => {
      if (query.trim()) {
        handleSearch();
      } else {
        setResults([]);
      }
    }, 500);

    return () => clearTimeout(delayDebounceFn);
  }, [query]);

  const handleSearch = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setShowDropdown(true);
    try {
      const res = await movieApi.searchMovies(query);
      setResults(res.data?.data?.results || []);
    } catch (err) {
      toast.error("Search failed");
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddMovie = async (movie: any) => {
    const tmdbId = movie.tmdb_id;
    if (addingId === tmdbId || trackedIds.has(tmdbId)) return;
    setAddingId(tmdbId);
    try {
      await movieApi.addMovie({ tmdb_id: tmdbId });
      toast.success(`${movie.title} added to library!`);
      setTrackedIds((prev) => new Set(prev).add(tmdbId));
      window.dispatchEvent(
        new CustomEvent("movie-added", { detail: { tmdb_id: tmdbId } }),
      );
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to add movie");
    } finally {
      setAddingId(null);
    }
  };

  return (
    <div className="relative w-full max-w-md" ref={dropdownRef}>
      <form onSubmit={handleSearch} className="relative group">
        <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
          <Search className="h-4 w-4 text-muted-foreground group-focus-within:text-primary transition-colors" />
        </div>
        <input
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (!e.target.value) setShowDropdown(false);
          }}
          onFocus={() => query && setShowDropdown(true)}
          placeholder="Search movies, TV shows, anime..."
          className="w-full bg-accent/30 border border-border/50 rounded-2xl pl-10 pr-10 py-2.5 text-sm text-foreground placeholder-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all font-medium"
        />
        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery("");
              setShowDropdown(false);
            }}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted-foreground hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </form>

      {/* Results Dropdown */}
      <AnimatePresence>
        {showDropdown && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            className="absolute top-full mt-2 w-full bg-card/90 backdrop-blur-2xl border border-border/50 rounded-3xl shadow-2xl overflow-hidden z-[60] max-h-[400px] flex flex-col"
          >
            {isSearching ? (
              <div className="flex flex-col items-center justify-center py-8 gap-3">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
                <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                  Eco is searching...
                </p>
              </div>
            ) : results.length === 0 ? (
              <div className="py-8 text-center px-4">
                <p className="text-sm font-bold text-muted-foreground">
                  No matches found for "{query}"
                </p>
              </div>
            ) : (
              <div className="overflow-y-auto py-2">
                {results.map((movie) => {
                  const isTracked = trackedIds.has(movie.tmdb_id);
                  return (
                    <div
                      key={movie.tmdb_id}
                      onClick={() => setSelectedMovie(movie)}
                      className="flex items-center gap-4 px-4 py-3 hover:bg-primary/10 cursor-pointer transition-colors group"
                    >
                      <div className="w-10 h-14 rounded-lg bg-accent overflow-hidden shrink-0 border border-border/20">
                        {movie.poster_url ? (
                          <img
                            src={movie.poster_url}
                            className="w-full h-full object-cover"
                            alt=""
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <Film className="w-4 h-4 text-muted-foreground" />
                          </div>
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-black text-foreground truncate group-hover:text-primary transition-colors">
                          {movie.title}
                        </h4>
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground font-bold uppercase tracking-wider">
                          <span>
                            {movie.release_date?.split("-")[0] || "N/A"}
                          </span>
                          <span>•</span>
                          <div className="flex items-center gap-0.5 text-yellow-500/80">
                            <Star className="w-2.5 h-2.5 fill-yellow-500/80" />
                            <span>
                              {movie.vote_average || movie.rating || "0.0"}
                            </span>
                          </div>
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleAddMovie(movie);
                        }}
                        className={`p-2 rounded-xl transition-all ${isTracked ? "bg-primary/10 text-primary cursor-default" : "bg-accent text-muted-foreground hover:bg-primary hover:text-primary-foreground"}`}
                      >
                        {addingId === movie.tmdb_id ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : isTracked ? (
                          <Check className="w-4 h-4" />
                        ) : (
                          <Plus className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <MovieDetailsModal
        movie={selectedMovie}
        onClose={() => setSelectedMovie(null)}
        onAdd={handleAddMovie}
        isAdding={addingId === selectedMovie?.tmdb_id}
        isTracked={trackedIds.has(selectedMovie?.tmdb_id)}
      />
    </div>
  );
}
