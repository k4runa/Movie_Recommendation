import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Request interceptor for JWT
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

export const authApi = {
  login: (credentials: any) => api.post('/login', new URLSearchParams(credentials)),
  register: (userData: any) => api.post('/users', userData),
  getMe: () => {
    const token = localStorage.getItem('access_token');
    if (!token) return Promise.reject(new Error("No token"));
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const username = payload.sub;
      return api.get(`/users/${username}`);
    } catch (e) {
      return Promise.reject(e);
    }
  },
  updateUserField: (username: string, data: { field: string; value: any; current_password?: string }) => {
    return api.patch(`/users/${username}`, data);
  },
  logout: () => api.post('/logout')
};

export const movieApi = {
  getMovies: (username: string) => api.get(`/movies/${username}`),
  searchMovies: (query: string) => api.get(`/movies/search?query=${query}`),
  addMovie: (username: string, movieData: any) => api.post(`/movies/${username}`, movieData),
  deleteMovie: (username: string, movieId: number) => api.delete(`/movies/${username}/${movieId}`),
  getRecommendations: (username: string) => api.get(`/movies/recommendations/${username}`),
  getAIInsights: (username: string) => api.get(`/movies/ai-insights/${username}`),
};

export const aiApi = {
  chat: (message: string, history?: { role: string; content: string }[]) =>
    api.post('/ai/chat', { message, history: history || [] }),
  streamChat: async (message: string, history?: { role: string; content: string }[]) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    return fetch(`${API_BASE_URL}/ai/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ message, history: history || [] }),
    });
  },
};

export default api;
