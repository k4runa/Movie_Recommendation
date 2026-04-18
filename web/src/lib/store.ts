import { create } from 'zustand';
import { authApi } from '@/lib/api';

interface AuthState {
  user: any | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: any) => Promise<void>;
  logout: () => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (credentials) => {
    const res = await authApi.login(credentials);
    const { access_token } = res.data;
    localStorage.setItem('access_token', access_token);
    const userRes = await authApi.getMe();
    // getMe returns { success: true, data: { user: {...} } }
    set({ user: userRes.data?.data?.user || userRes.data, isAuthenticated: true, isLoading: false });
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.warn("Logout request failed, continuing local logout", err);
    }
    localStorage.removeItem('access_token');
    set({ user: null, isAuthenticated: false, isLoading: false });
  },

  checkAuth: async () => {
    set({ isLoading: true });
    try {
      const token = localStorage.getItem('access_token');
      if (!token) throw new Error('No token');
      const res = await authApi.getMe();
      set({ user: res.data?.data?.user || res.data, isAuthenticated: true, isLoading: false });
    } catch (err) {
      localStorage.removeItem('access_token');
      set({ user: null, isAuthenticated: false, isLoading: false });
    }
  },
}));
