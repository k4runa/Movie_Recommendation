"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { useGoogleLogin } from "@react-oauth/google";
import { Eye, EyeOff, ShieldCheck, Lock, User, Mail, Info } from "lucide-react";
import { Checkbox } from "@/components/ui/checkbox";
import { cn } from "@/lib/utils";

export function AuthForm() {
    const [mode, setMode] = useState<'login' | 'register'>('login');
    const [isLoading, setIsLoading] = useState(false);
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const login = useAuthStore((state) => state.login);
    const googleLogin = useAuthStore((state) => state.googleLogin);

    const handleGoogleLogin = useGoogleLogin({
        onSuccess: async (tokenResponse) => {
            setIsLoading(true);
            try {
                await googleLogin(tokenResponse.access_token);
                toast.success("Welcome back to ecofil");
            } catch (err: any) {
                setError(err.response?.data?.detail || "Google Login failed");
            } finally {
                setIsLoading(false);
            }
        },
        onError: () => toast.error("Google Login failed")
    });

    const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsLoading(true);
        const formData = new FormData(e.currentTarget);
        const data = Object.fromEntries(formData);
        setError(null);
        try {
            await login(data);
            if (rememberMe) {
                localStorage.setItem("remembered_username", String(data.username));
            } else {
                localStorage.removeItem("remembered_username");
            }
            toast.success("Welcome back to ecofil");
        } catch (err: any) {
            const errorData = err.response?.data?.detail;
            let errorMessage = "Invalid credentials. Please try again.";
            
            if (Array.isArray(errorData)) {
                errorMessage = errorData[0]?.msg || errorMessage;
            } else if (typeof errorData === 'string') {
                errorMessage = errorData;
            }
            
            setError(errorMessage);
        } finally {
            setIsLoading(false);
        }
    };

    const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsLoading(true);
        const formData = new FormData(e.currentTarget);
        const data = Object.fromEntries(formData);
        setError(null);
        try {
            await authApi.register(data);
            toast.success("Account created! Logging you in...");

            // Auto-login after successful registration
            await login({
                username: data.username,
                password: data.password
            });
        } catch (err: any) {
            const errorData = err.response?.data?.detail;
            let errorMessage = "Registration failed";
            
            if (Array.isArray(errorData)) {
                errorMessage = errorData[0]?.msg || errorMessage;
            } else if (typeof errorData === 'string') {
                errorMessage = errorData;
            }
            
            setError(errorMessage);
            setIsLoading(false);
        }
    };

    const GoogleIcon = () => (
        <svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" viewBox="0 0 256 262">
            <path fill="#4285f4" d="M255.878 133.451c0-10.734-.871-18.567-2.756-26.69H130.55v48.448h71.947c-1.45 12.04-9.283 30.172-26.69 42.356l-.244 1.622l38.755 30.023l2.685.268c24.659-22.774 38.875-56.282 38.875-96.027"></path>
            <path fill="#34a853" d="M130.55 261.1c35.248 0 64.839-11.605 86.453-31.622l-41.196-31.913c-11.024 7.688-25.82 13.055-45.257 13.055c-34.523 0-63.824-22.773-74.269-54.25l-1.531.13l-40.298 31.187l-.527 1.465C35.393 231.798 79.49 261.1 130.55 261.1"></path>
            <path fill="#fbbc05" d="M56.281 156.37c-2.756-8.123-4.351-16.827-4.351-25.82c0-8.994 1.595-17.697 4.206-25.82l-.073-1.73L15.26 71.312l-1.335.635C5.077 89.644 0 109.517 0 130.55s5.077 40.905 13.925 58.602z"></path>
            <path fill="#eb4335" d="M130.55 50.479c24.514 0 41.05 10.589 50.479 19.438l36.844-35.974C195.245 12.91 165.798 0 130.55 0C79.49 0 35.393 29.301 13.925 71.947l42.211 32.783c10.59-31.477 39.891-54.251 74.414-54.251"></path>
        </svg>
    );

    return (
        <section className="flex w-full px-4 py-8 bg-transparent">
            <AnimatePresence mode="wait">
                <motion.div
                    key={mode}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -20 }}
                    transition={{ duration: 0.3 }}
                    className="m-auto h-fit w-full max-w-md bg-zinc-950/80 backdrop-blur-xl border border-zinc-800 rounded-2xl shadow-2xl p-6 sm:p-8"
                >
                    {mode === 'login' ? (
                        <form onSubmit={handleLogin}>
                            <div>
                                <h1 className="mb-1 mt-2 text-2xl font-semibold text-white tracking-tight">Welcome back</h1>
                                <p className="text-zinc-400 text-sm">Enter your credentials to access your account</p>
                            </div>

                            <div className="mt-8">
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="w-full flex items-center justify-center gap-3 bg-zinc-900 border-zinc-800 text-white hover:bg-zinc-800 hover:text-white transition-colors h-11"
                                    onClick={() => handleGoogleLogin()}
                                >
                                    <GoogleIcon />
                                    <span className="font-semibold text-sm">Continue with Google</span>
                                </Button>
                            </div>

                            <div className="my-6 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                                <hr className="border-zinc-800 border-dashed" />
                                <span className="text-zinc-500 text-[11px] font-medium uppercase tracking-wider">Or continue with</span>
                                <hr className="border-zinc-800 border-dashed" />
                            </div>

                            <div className="space-y-5">
                                <div className="space-y-2">
                                    <Label htmlFor="username" className="block text-sm font-medium text-zinc-300">
                                        Username
                                    </Label>
                                    <div className="relative group">
                                        <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-white transition-colors" />
                                        <Input
                                            type="text"
                                            required
                                            name="username"
                                            id="username"
                                            placeholder="Enter username"
                                            className={cn(
                                                "bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 pl-11 transition-all",
                                                error && "border-red-500/50 focus-visible:ring-red-500/20"
                                            )}
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <div className="flex items-center justify-between">
                                        <Label htmlFor="password" className="text-sm font-medium text-zinc-300">
                                            Password
                                        </Label>
                                        <button type="button" className="text-[10px] text-zinc-500 hover:text-white transition-colors font-bold uppercase tracking-widest">
                                            Forgot?
                                        </button>
                                    </div>
                                    <div className="relative group">
                                        <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-white transition-colors" />
                                        <Input
                                            type={showPassword ? "text" : "password"}
                                            required
                                            name="password"
                                            id="password"
                                            className={cn(
                                                "bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 pl-11 pr-12 transition-all",
                                                error && "border-red-500/50 focus-visible:ring-red-500/20"
                                            )}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-white transition-all"
                                        >
                                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                        </button>
                                    </div>
                                </div>

                                {error && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex items-start gap-3"
                                    >
                                        <Info className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                                        <p className="text-xs font-medium text-red-200 leading-tight">{error}</p>
                                    </motion.div>
                                )}

                                <div className="flex items-center space-x-2 py-1">
                                    <Checkbox
                                        id="remember"
                                        checked={rememberMe}
                                        onCheckedChange={(checked) => setRememberMe(!!checked)}
                                        className="border-zinc-800 data-[state=checked]:bg-white data-[state=checked]:text-black"
                                    />
                                    <label htmlFor="remember" className="text-xs font-medium text-zinc-500 cursor-pointer select-none">
                                        Remember me
                                    </label>
                                </div>

                                <Button type="submit" disabled={isLoading} className="w-full h-11 bg-white text-black hover:bg-zinc-200 font-bold mt-2 text-sm">
                                    {isLoading ? "Signing in..." : "Continue"}
                                </Button>
                            </div>

                            <p className="mt-8 text-zinc-400 text-center text-sm">
                                Don't have an account?
                                <Button
                                    type="button"
                                    onClick={() => setMode('register')}
                                    variant="link"
                                    className="px-2 text-white hover:text-zinc-300 font-semibold"
                                >
                                    Sign Up
                                </Button>
                            </p>
                        </form>
                    ) : (
                        <form onSubmit={handleRegister}>
                            <div>
                                <h1 className="mb-1 mt-2 text-2xl font-semibold text-white tracking-tight">Create an Account</h1>
                                <p className="text-zinc-400 text-sm">Welcome! Create an account to get started</p>
                            </div>

                            <div className="mt-8">
                                <Button
                                    type="button"
                                    variant="outline"
                                    className="w-full flex items-center justify-center gap-3 bg-zinc-900 border-zinc-800 text-white hover:bg-zinc-800 hover:text-white transition-colors h-11"
                                    onClick={() => handleGoogleLogin()}
                                >
                                    <GoogleIcon />
                                    <span className="font-semibold text-sm">Continue with Google</span>
                                </Button>
                            </div>

                            <div className="my-6 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                                <hr className="border-zinc-800 border-dashed" />
                                <span className="text-zinc-500 text-[11px] font-medium uppercase tracking-wider">Or continue with</span>
                                <hr className="border-zinc-800 border-dashed" />
                            </div>

                            <div className="space-y-5">
                                <div className="space-y-2">
                                    <Label htmlFor="reg-username" className="block text-sm font-medium text-zinc-300">
                                        Username
                                    </Label>
                                    <div className="relative group">
                                        <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-white transition-colors" />
                                        <Input
                                            type="text"
                                            required
                                            name="username"
                                            id="reg-username"
                                            placeholder="Enter username"
                                            className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 pl-11 transition-all"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="reg-email" className="block text-sm font-medium text-zinc-300">
                                        Email
                                    </Label>
                                    <div className="relative group">
                                        <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-white transition-colors" />
                                        <Input
                                            type="email"
                                            required
                                            name="email"
                                            id="reg-email"
                                            placeholder="Enter email"
                                            className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 pl-11 transition-all"
                                        />
                                    </div>
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="reg-password" className="text-sm font-medium text-zinc-300">
                                        Password
                                    </Label>
                                    <div className="relative group">
                                        <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-600 group-focus-within:text-white transition-colors" />
                                        <Input
                                            type={showPassword ? "text" : "password"}
                                            required
                                            name="password"
                                            id="reg-password"
                                            placeholder="Min. 8 characters"
                                            className={cn(
                                                "bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 pl-11 pr-12 transition-all",
                                                error && "border-red-500/50 focus-visible:ring-red-500/20"
                                            )}
                                        />
                                        <button
                                            type="button"
                                            onClick={() => setShowPassword(!showPassword)}
                                            className="absolute right-3 top-1/2 -translate-y-1/2 p-1.5 hover:bg-zinc-800 rounded-lg text-zinc-500 hover:text-white transition-all"
                                        >
                                            {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                        </button>
                                    </div>
                                    <div className="flex items-start gap-2 pt-1">
                                        <Info className="w-3 h-3 text-zinc-500 mt-0.5" />
                                        <p className="text-[10px] text-zinc-500 leading-tight">
                                            At least 8 characters, one uppercase and one digit.
                                        </p>
                                    </div>
                                </div>

                                {error && (
                                    <motion.div
                                        initial={{ opacity: 0, y: -10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 flex items-start gap-3"
                                    >
                                        <Info className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                                        <p className="text-xs font-medium text-red-200 leading-tight">{error}</p>
                                    </motion.div>
                                )}

                                <Button type="submit" disabled={isLoading} className="w-full h-11 bg-white text-black hover:bg-zinc-200 font-bold mt-2 text-sm">
                                    {isLoading ? "Creating account..." : "Continue"}
                                </Button>
                            </div>

                            <p className="mt-8 text-zinc-400 text-center text-sm">
                                Have an account?
                                <Button
                                    type="button"
                                    onClick={() => setMode('login')}
                                    variant="link"
                                    className="px-2 text-white hover:text-zinc-300 font-semibold"
                                >
                                    Sign In
                                </Button>
                            </p>
                        </form>
                    )}
                </motion.div>
            </AnimatePresence>
        </section>
    );
}
