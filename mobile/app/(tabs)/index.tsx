import { useEffect, useState, useRef, useCallback, memo, useMemo } from "react";
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  Dimensions,
  TouchableOpacity,
  ActivityIndicator,
  FlatList,
  Animated,
  RefreshControl,
  Alert,
} from "react-native";
import { SafeAreaView, useSafeAreaInsets } from "react-native-safe-area-context";
import { LinearGradient } from "expo-linear-gradient";
import { Star, Plus, Info, Check, CheckCircle2, RefreshCw, Sparkles, Bell } from "lucide-react-native";
import { useFocusEffect, useRouter } from "expo-router";
import { useAuthStore } from "../../lib/store";
import { movieApi, aiApi, notificationApi } from "../../lib/api";
import { BlurView } from "expo-blur";

const { width } = Dimensions.get("window");
const ITEM_WIDTH = width * 0.4;

// ─── MovieCard defined OUTSIDE HomeScreen so memo() actually works ───────────
const MovieCard = memo(({
  movie,
  isAdded,
  isToggling,
  onToggle,
  onPress,
}: {
  movie: any;
  isAdded: boolean;
  isToggling: boolean;
  onToggle: (movie: any) => void;
  onPress: (movie: any) => void;
}) => (
  <TouchableOpacity
    style={styles.movieCard}
    activeOpacity={0.85}
    onPress={() => onPress(movie)}
  >
    <Image
      source={{ uri: movie.poster_url || "https://images.placeholders.dev/?width=500&height=750&text=No+Poster" }}
      style={styles.poster}
    />
    <View style={styles.ratingBadge}>
      <Star size={10} color="#FFD700" fill="#FFD700" />
      <Text style={styles.ratingText}>{Number(movie.vote_average || 0).toFixed(1)}</Text>
    </View>
    <TouchableOpacity
      style={[styles.cardAddButton, isAdded && styles.cardAddedButton]}
      onPress={() => onToggle(movie)}
      disabled={isToggling}
    >
      {isAdded ? (
        <Check size={16} color="white" />
      ) : (
        <Plus size={16} color="white" />
      )}
    </TouchableOpacity>
    <Text style={styles.movieTitle} numberOfLines={1}>
      {movie.title}
    </Text>
  </TouchableOpacity>
));

const SkeletonCard = () => (
  <View style={styles.skeletonCard}>
    <View style={styles.skeletonPoster} />
    <View style={styles.skeletonTitle} />
  </View>
);

const SkeletonLoader = () => (
  <View style={styles.skeletonContainer}>
    <View style={styles.skeletonHero} />
    <View style={styles.skeletonSection}>
      <View style={styles.skeletonSectionHeader} />
      <View style={{ flexDirection: "row", paddingHorizontal: 16 }}>
        {[1, 2, 3].map(i => <SkeletonCard key={i} />)}
      </View>
    </View>
  </View>
);
// ─────────────────────────────────────────────────────────────────────────────

export default function HomeScreen() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const insets = useSafeAreaInsets();

  const [trending, setTrending] = useState<any[]>([]);
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [aiRecommendations, setAiRecommendations] = useState<any[]>([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Map: tmdb_id -> internal db id (for checking if movie is in library)
  const [addedMovies, setAddedMovies] = useState<Map<number, number>>(new Map());
  const addedMoviesRef = useRef<Map<number, number>>(new Map());
  const [togglingIds, setTogglingIds] = useState<Set<number>>(new Set());
  const togglingIdsRef = useRef<Set<number>>(new Set());

  // Toast
  const [toastVisible, setToastVisible] = useState(false);
  const [toastMessage, setToastMessage] = useState("");
  const toastOffset = insets.top + 10;
  const toastY = useRef(new Animated.Value(-100)).current;

  const showToast = useCallback((message: string) => {
    setToastMessage(message);
    setToastVisible(true);
    Animated.sequence([
      Animated.timing(toastY, { toValue: toastOffset, duration: 350, useNativeDriver: true }),
      Animated.delay(1800),
      Animated.timing(toastY, { toValue: -100, duration: 350, useNativeDriver: true }),
    ]).start(() => setToastVisible(false));
  }, []);

  const fetchLibrary = async () => {
    try {
      const res = await movieApi.getMovies();
      const movies = res.data?.data?.watched_movies || [];
      const map = new Map<number, number>();
      movies.forEach((m: any) => {
        if (m.tmdb_id) map.set(m.tmdb_id, m.id);
      });
      addedMoviesRef.current = map;
      setAddedMovies(new Map(map));
    } catch (e) { }
  };

  const fetchUnreadCount = async () => {
    try {
      const res = await notificationApi.getUnreadCount();
      if (res.data?.success) setUnreadNotifications(res.data.data.count);
    } catch (e) { }
  };

  const fetchData = async (isRefreshing = false) => {
    if (isRefreshing) setRefreshing(true);
    else if (trending.length === 0) setLoading(true);
    try {
      const tasks = [movieApi.getTrending(), movieApi.getRecommendations()];
      if (user?.ai_enabled !== false) tasks.push(aiApi.getRecommendations());
      const [trendRes, recsRes, aiRes] = await Promise.all(tasks);
      if (trendRes.data?.success) setTrending(trendRes.data.data.results || []);
      if (recsRes.data?.success) setRecommendations(recsRes.data.data.recommendations || []);
      if (aiRes?.data?.success) setAiRecommendations(aiRes.data.data || []);
    } catch (_e) {
      // Data fetch failure is handled gracefully by empty state
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      if (!user) return;
      // Only fetch in background if we don't have data, or if specifically refreshing
      if (addedMovies.size === 0) fetchLibrary();
      fetchUnreadCount();
      if (trending.length === 0) fetchData(false);
    }, [user, trending.length, addedMovies.size])
  );

  const onRefresh = useCallback(() => {
    fetchLibrary();
    fetchData(true);
  }, []);

  // ─── Instant optimistic toggle ───────────────────────────────────────────
  const handleToggleMovie = useCallback((movie: any) => {
    const tmdbId = movie.tmdb_id;
    if (!tmdbId) return;
    if (togglingIdsRef.current.has(tmdbId)) return;

    const currentId = addedMoviesRef.current.get(tmdbId);
    const isAdding = currentId === undefined;

    // 0. Lock this tmdbId against concurrent toggles
    togglingIdsRef.current.add(tmdbId);
    setTogglingIds(prev => new Set(prev).add(tmdbId));

    // 1. Update UI instantly
    setAddedMovies(prev => {
      const next = new Map(prev);
      if (isAdding) next.set(tmdbId, -1);
      else next.delete(tmdbId);
      return next;
    });
    addedMoviesRef.current = new Map(addedMoviesRef.current);
    if (isAdding) addedMoviesRef.current.set(tmdbId, -1);
    else addedMoviesRef.current.delete(tmdbId);

    // 2. Toast instantly
    showToast(isAdding ? `${movie.title} added!` : "Removed from library.");

    // 3. Background API sync (legacy tmdb_id flow)
    (async () => {
      try {
        if (!isAdding) {
          await movieApi.deleteMovie(currentId!);
        } else {
          await movieApi.addMovie({
            tmdb_id: tmdbId,
            title: movie.title,
            overview: movie.overview,
            poster_url: movie.poster_url,
            vote_average: typeof movie.vote_average === 'string' ? parseFloat(movie.vote_average) : movie.vote_average,
            release_date: movie.release_date,
            genre_ids: Array.isArray(movie.genre_ids) ? movie.genre_ids.map(String).join(",") : (movie.genre_ids || ""),
            query: movie.title
          });
          const libRes = await movieApi.getMovies();
          const found = (libRes.data?.data?.watched_movies || []).find((m: any) => m.tmdb_id === tmdbId);
          if (found) {
            addedMoviesRef.current.set(tmdbId, found.id);
            setAddedMovies(prev => new Map(prev).set(tmdbId, found.id));
          }
        }
      } catch (e: any) {
        const errorMsg = e.response?.data?.detail || "Could not update library. Try again.";
        Alert.alert("Error", errorMsg);

        setAddedMovies(prev => {
          const next = new Map(prev);
          if (isAdding) next.delete(tmdbId);
          else next.set(tmdbId, currentId!);
          return next;
        });
        if (isAdding) addedMoviesRef.current.delete(tmdbId);
        else addedMoviesRef.current.set(tmdbId, currentId!);
      } finally {
        togglingIdsRef.current.delete(tmdbId);
        setTogglingIds(prev => {
          const next = new Set(prev);
          next.delete(tmdbId);
          return next;
        });
      }
    })();
  }, [showToast]);

  // Stable callbacks passed to MovieCard
  const handlePress = useCallback((m: any) => {
    router.push({ pathname: `/movie/${m.tmdb_id}`, params: { ai_reason: m.ai_reason } });
  }, []);

  if (loading && !refreshing) {
    return (
      <SafeAreaView style={styles.container}>
        <SkeletonLoader />
      </SafeAreaView>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#FF4500" />}
      >
        {/* Header (Now non-sticky) */}
        <SafeAreaView edges={['top']} style={styles.header}>
          <View style={styles.headerContent}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <View style={styles.logoBadge}>
                <Sparkles size={20} color="white" />
              </View>
              <Text style={styles.logoText}>ecofil</Text>
            </View>
            <TouchableOpacity
              style={styles.notificationButton}
              onPress={() => router.push("/notifications")}
            >
              <Bell size={22} color="white" />
              {unreadNotifications > 0 && (
                <View style={styles.badge}>
                  <Text style={styles.badgeText}>{unreadNotifications > 9 ? "9+" : unreadNotifications}</Text>
                </View>
              )}
            </TouchableOpacity>
          </View>
        </SafeAreaView>

        {/* Toast */}
        {toastVisible && (
          <Animated.View style={[styles.toastContainer, { transform: [{ translateY: toastY }] }]}>
            <LinearGradient colors={["#171717", "#0a0a0a"]} style={styles.toastGradient}>
              <CheckCircle2 size={18} color="#4ADE80" />
              <Text style={styles.toastText}>{toastMessage}</Text>
            </LinearGradient>
          </Animated.View>
        )}
        {/* Hero */}
        {trending.length > 0 && (
          <View style={styles.heroSection}>
            <Image source={{ uri: trending[0].poster_url }} style={styles.heroImage} />
            <LinearGradient colors={["transparent", "rgba(10,10,10,0.8)", "#0a0a0a"]} style={styles.heroGradient} />
            <View style={styles.heroContent}>
              <Text style={styles.heroTitle}>{trending[0].title}</Text>
              <View style={styles.heroButtons}>
                <TouchableOpacity
                  style={[styles.primaryButton, addedMovies.has(trending[0].tmdb_id) && styles.heroAddedButton]}
                  onPress={() => handleToggleMovie(trending[0])}
                  disabled={togglingIds.has(trending[0].tmdb_id)}
                >
                  {addedMovies.has(trending[0].tmdb_id)
                    ? <Check size={20} color="#4ADE80" />
                    : <Plus size={20} color="white" />}
                  <Text style={styles.buttonText}>
                    {addedMovies.has(trending[0].tmdb_id) ? "In Library" : "Add to Library"}
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.secondaryButton}
                  onPress={() => router.push({ pathname: `/movie/${trending[0].tmdb_id}`, params: { ai_reason: trending[0].ai_reason } })}
                >
                  <Info size={20} color="white" />
                  <Text style={styles.buttonText}>Details</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}

        {/* Trending */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Trending Now</Text>
          </View>
          <FlatList
            data={trending.slice(1)}
            horizontal
            showsHorizontalScrollIndicator={false}
            renderItem={({ item }) => (
              <MovieCard
                movie={item}
                isAdded={addedMovies.has(item.tmdb_id)}
                isToggling={togglingIds.has(item.tmdb_id)}
                onToggle={handleToggleMovie}
                onPress={handlePress}
              />
            )}
            keyExtractor={(item) => `trending-${item.tmdb_id}`}
            contentContainerStyle={styles.listContent}
          />
        </View>

        {/* Personalized */}
        <View style={styles.section}>
          <View style={styles.sectionHeader}>
            <Text style={styles.sectionTitle}>Personalized Picks</Text>
          </View>
          {recommendations.length > 0 ? (
            <FlatList
              data={recommendations}
              horizontal
              showsHorizontalScrollIndicator={false}
              renderItem={({ item }) => (
                <MovieCard
                  movie={item}
                  isAdded={addedMovies.has(item.tmdb_id)}
                  isToggling={togglingIds.has(item.tmdb_id)}
                  onToggle={handleToggleMovie}
                  onPress={handlePress}
                />
              )}
              keyExtractor={(item) => `rec-${item.tmdb_id}`}
              contentContainerStyle={styles.listContent}
            />
          ) : (
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateText}>Add movies to refine AI picks!</Text>
            </View>
          )}
        </View>

        {/* AI Recommendations */}
        {user?.ai_enabled !== false && aiRecommendations.length > 0 && (
          <View style={[styles.section, styles.aiSection]}>
            <View style={styles.sectionHeader}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <Sparkles size={18} color="#FF4500" />
                <Text style={styles.sectionTitle}>Eco Recommendations</Text>
              </View>
            </View>
            <FlatList
              data={aiRecommendations}
              horizontal
              showsHorizontalScrollIndicator={false}
              renderItem={({ item }) => (
                <MovieCard
                  movie={item}
                  isAdded={addedMovies.has(item.tmdb_id)}
                  isToggling={togglingIds.has(item.tmdb_id)}
                  onToggle={handleToggleMovie}
                  onPress={handlePress}
                />
              )}
              keyExtractor={(item) => `ai-rec-${item.tmdb_id}`}
              contentContainerStyle={styles.listContent}
            />
          </View>
        )}

        <View style={{ height: 40 }} />
      </ScrollView>

      {/* Floating Refresh */}
      <TouchableOpacity style={styles.floatingRefresh} onPress={onRefresh} activeOpacity={0.8}>
        <RefreshCw size={22} color="white" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  skeletonContainer: { flex: 1, backgroundColor: "#0a0a0a" },
  skeletonHero: { height: 450, backgroundColor: "#171717", marginBottom: 30 },
  skeletonSection: { marginBottom: 30 },
  skeletonSectionHeader: { width: 150, height: 20, backgroundColor: "#171717", marginLeft: 24, marginBottom: 15, borderRadius: 4 },
  skeletonCard: { width: ITEM_WIDTH, marginRight: 16 },
  skeletonPoster: { width: "100%", height: ITEM_WIDTH * 1.5, borderRadius: 12, backgroundColor: "#171717" },
  skeletonTitle: { width: "70%", height: 14, backgroundColor: "#171717", marginTop: 10, borderRadius: 4 },
  container: { flex: 1, backgroundColor: "#0a0a0a" },
  badgeText: { color: "white", fontSize: 10, fontWeight: "900" },
  header: {
    backgroundColor: "#0a0a0a",
  },
  headerContent: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 24,
    height: 60,
  },
  notificationButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "rgba(255,255,255,0.05)",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
  },
  badge: {
    position: "absolute",
    top: 0,
    right: 0,
    backgroundColor: "#FF4500",
    minWidth: 16,
    height: 16,
    borderRadius: 8,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
    borderWidth: 2,
    borderColor: "#0a0a0a",
  },
  logoBadge: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#FF4500',
    alignItems: 'center',
    justifyContent: 'center'
  },
  logoText: {
    color: "white",
    fontSize: 22,
    fontWeight: "900",
    letterSpacing: -0.5
  },
  heroSection: { height: 450, position: "relative" },
  heroImage: { width: "100%", height: "100%" },
  heroGradient: { ...StyleSheet.absoluteFillObject },
  heroContent: { position: "absolute", bottom: 40, left: 24, right: 24 },
  heroTitle: { color: "white", fontSize: 36, fontWeight: "900", marginBottom: 20, letterSpacing: -1 },
  heroButtons: { flexDirection: "row", gap: 12 },
  primaryButton: { flex: 1, backgroundColor: "#FF4500", flexDirection: "row", alignItems: "center", justifyContent: "center", paddingVertical: 14, borderRadius: 10, gap: 8 },
  heroAddedButton: { backgroundColor: "#171717", borderWidth: 1, borderColor: "rgba(74,222,128,0.3)" },
  secondaryButton: { flex: 1, backgroundColor: "rgba(255,255,255,0.1)", flexDirection: "row", alignItems: "center", justifyContent: "center", paddingVertical: 14, borderRadius: 10, gap: 8 },
  buttonText: { color: "white", fontSize: 15, fontWeight: "700" },
  section: { marginTop: 30 },
  aiSection: { paddingVertical: 10, backgroundColor: "rgba(139,92,246,0.03)" },
  sectionHeader: { flexDirection: "row", alignItems: "center", paddingHorizontal: 24, marginBottom: 15, gap: 8 },
  sectionTitle: { color: "white", fontSize: 18, fontWeight: "800" },
  listContent: { paddingHorizontal: 16 },
  movieCard: { width: ITEM_WIDTH, marginHorizontal: 8, position: "relative" },
  poster: { width: "100%", height: ITEM_WIDTH * 1.5, borderRadius: 10, backgroundColor: "#171717" },
  ratingBadge: { position: "absolute", top: 8, left: 8, backgroundColor: "rgba(0,0,0,0.6)", flexDirection: "row", alignItems: "center", paddingHorizontal: 6, paddingVertical: 3, borderRadius: 6, gap: 4 },
  ratingText: { color: "white", fontSize: 10, fontWeight: "800" },
  cardAddButton: { position: "absolute", top: 8, right: 8, width: 32, height: 32, borderRadius: 16, backgroundColor: "#171717", alignItems: "center", justifyContent: "center", borderWidth: 1, borderColor: "rgba(255,255,255,0.1)" },
  cardAddedButton: { backgroundColor: "#4ADE80", borderColor: "#4ADE80" },
  cardTogglingButton: { backgroundColor: "rgba(255, 69, 0, 0.15)", borderColor: "rgba(255, 69, 0, 0.3)" },
  movieTitle: { color: "#E5E5E5", fontSize: 14, fontWeight: "600", marginTop: 8 },
  toastContainer: { position: "absolute", top: 10, left: 24, right: 24, zIndex: 1000 },
  toastGradient: { flexDirection: "row", alignItems: "center", paddingHorizontal: 20, paddingVertical: 14, borderRadius: 10, gap: 12, borderWidth: 1, borderColor: "rgba(255,255,255,0.05)" },
  toastText: { color: "white", fontSize: 14, fontWeight: "600" },
  emptyState: { marginHorizontal: 24, padding: 30, backgroundColor: "#111", borderRadius: 10, alignItems: "center" },
  emptyStateText: { color: "#525252", fontSize: 14, fontWeight: "600" },
  floatingRefresh: {
    position: "absolute", bottom: 20, right: 20,
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: "#FF4500",
    alignItems: "center", justifyContent: "center",
    shadowColor: "#FF4500",
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4, shadowRadius: 12, elevation: 8,
  },
  sectionSubtitle: { color: "#A1A1AA", fontSize: 13, paddingHorizontal: 24, marginBottom: 8 },
});
