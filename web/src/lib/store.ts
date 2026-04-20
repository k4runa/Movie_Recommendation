import { create } from 'zustand';
import { authApi } from '@/lib/api';

export interface User {
  id?: number;
  username: string;
  nickname?: string;
  email?: string;
  role?: string;
  device?: string;
  os?: string;
  country?: string;
  city?: string;
  created_at?: string;
  last_seen?: string;
  ai_enabled?: boolean;
  max_toasts?: number;
  dm_notifications?: boolean;
  is_private?: boolean;
  avatar_url?: string;
  bio?: string;
  gender?: string;
  age?: number;
  location?: string;
  show_age?: boolean;
  show_gender?: boolean;
  show_location?: boolean;
  show_bio?: boolean;
  show_favorites?: boolean;
  ip?: string;
  device_name?: string;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: any) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  checkAuth: (isSilent?: boolean) => Promise<void>;
  updateUser: (data: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (credentials) => {
    set({ isLoading: true });
    try {
      const res = await authApi.login(credentials);
      const { username, role } = res.data;
      
      try {
        const userRes = await authApi.getMe();
        set({ 
          user: userRes.data?.data?.user || userRes.data, 
          isAuthenticated: true, 
          isLoading: false 
        });
      } catch (err) {
        console.warn("Profile fetch failed, using login response data", err);
        set({ 
          user: { username, role }, 
          isAuthenticated: true, 
          isLoading: false 
        });
      }
    } catch (err) {
      set({ isLoading: false });
      throw err;
    }
  },

  googleLogin: async (credential) => {
    set({ isLoading: true });
    try {
      const res = await authApi.googleLogin(credential);
      const { username, role } = res.data;
      
      try {
        const userRes = await authApi.getMe();
        set({ 
          user: userRes.data?.data?.user || userRes.data, 
          isAuthenticated: true, 
          isLoading: false 
        });
      } catch (err) {
        console.warn("Profile fetch failed, using login response data", err);
        set({ 
          user: { username, role }, 
          isAuthenticated: true, 
          isLoading: false 
        });
      }
    } catch (err) {
      set({ isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.warn("Logout request failed, continuing local logout", err);
    }
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  updateUser: (data: Partial<User>) => {
    const currentUser = get().user;
    if (currentUser) {
      set({ user: { ...currentUser, ...data } });
    }
  },

  checkAuth: async (isSilent = false) => {
    if (!isSilent) set({ isLoading: true });
    try {
      const res = await authApi.getMe();
      set({ user: res.data?.data?.user || res.data, isAuthenticated: true, isLoading: false });
    } catch (err) {
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));


interface SocialState {
  activeChatId: number | null;
  setActiveChatId: (id: number | null) => void;
  unreadTotal: number;
  setUnreadTotal: (count: number) => void;
}

export const useSocialUIStore = create<SocialState>((set) => ({
  activeChatId: null,
  setActiveChatId: (id) => set({ activeChatId: id }),
  unreadTotal: 0,
  setUnreadTotal: (count) => set({ unreadTotal: count }),
}));

// Auto-logout when the API interceptor detects a 401
if (typeof window !== 'undefined') {
  window.addEventListener('auth-expired', () => {
    useAuthStore.getState().logout();
  });
}
