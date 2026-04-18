import { create } from 'zustand';
import { movieApi } from '@/lib/api';

interface MovieState {
  recommendations: any[];
  isRecsLoading: boolean;
  lastFetched: number | null;
  fetchRecommendations: (username: string, force?: boolean) => Promise<void>;
  clearRecommendations: () => void;
}

export const useMovieStore = create<MovieState>((set, get) => ({
  recommendations: [],
  isRecsLoading: false,
  lastFetched: null,

  fetchRecommendations: async (username, force = false) => {
    const { recommendations, lastFetched } = get();
    
    // Cache logic: don't fetch if we have recs and it's been less than 30 mins, unless forced
    const now = Date.now();
    const isStale = !lastFetched || now - lastFetched > 30 * 60 * 1000;
    
    if (recommendations.length > 0 && !isStale && !force) {
      return;
    }

    set({ isRecsLoading: true });
    try {
      const res = await movieApi.getRecommendations(username);
      const recs = res.data?.data?.recommendations || res.data?.recommendations || res.data || [];
      set({ 
        recommendations: Array.isArray(recs) ? recs : [], 
        lastFetched: now,
        isRecsLoading: false 
      });
    } catch (err) {
      console.error("Failed to fetch recommendations in store", err);
      set({ isRecsLoading: false });
    }
  },

  clearRecommendations: () => {
    set({ recommendations: [], lastFetched: null });
  }
}));
