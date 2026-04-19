"use client";

import { useState } from "react";
import { useAuthStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authApi } from "@/lib/api";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";
import { GoogleLogin } from "@react-oauth/google";

export function AuthForm() {
    const [mode, setMode] = useState<'login' | 'register'>('login');
    const [isLoading, setIsLoading] = useState(false);
    const login = useAuthStore((state) => state.login);
    const googleLogin = useAuthStore((state) => state.googleLogin);

    const handleGoogleSuccess = async (credentialResponse: any) => {
        setIsLoading(true);
        try {
            await googleLogin(credentialResponse.credential);
            toast.success("Welcome back to CineWave");
        } catch (err) {
            toast.error("Google Login failed");
        } finally {
            setIsLoading(false);
        }
    };

    const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsLoading(true);
        const formData = new FormData(e.currentTarget);
        const data = Object.fromEntries(formData);
        try {
            await login(data);
            toast.success("Welcome back to CineWave");
        } catch (err) {
            toast.error("Invalid credentials. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleRegister = async (e: React.FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setIsLoading(true);
        const formData = new FormData(e.currentTarget);
        const data = Object.fromEntries(formData);
        try {
            await authApi.register(data);
            toast.success("Account created! You can now login.");
            setMode('login');
        } catch (err: any) {
            toast.error(err.response?.data?.detail || "Registration failed");
        } finally {
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

                            <div className="mt-8 flex justify-center w-full overflow-hidden">
                                <GoogleLogin
                                    onSuccess={handleGoogleSuccess}
                                    onError={() => toast.error("Google Login Failed")}
                                    theme="filled_black"
                                    shape="pill"
                                    text="continue_with"
                                    size="large"
                                    width="100%"
                                />
                            </div>

                            <div className="my-6 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                                <hr className="border-zinc-800 border-dashed" />
                                <span className="text-zinc-500 text-[11px] font-medium uppercase tracking-wider">Or continue With</span>
                                <hr className="border-zinc-800 border-dashed" />
                            </div>

                            <div className="space-y-5">
                                <div className="space-y-2">
                                    <Label htmlFor="username" className="block text-sm font-medium text-zinc-300">
                                        Username
                                    </Label>
                                    <Input
                                        type="text"
                                        required
                                        name="username"
                                        id="username"
                                        className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 px-4"
                                    />
                                </div>
                                
                                <div className="space-y-2">
                                    <Label htmlFor="password" className="block text-sm font-medium text-zinc-300">
                                        Password
                                    </Label>
                                    <Input
                                        type="password"
                                        required
                                        name="password"
                                        id="password"
                                        className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 px-4"
                                    />
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

                            <div className="mt-8 flex justify-center w-full overflow-hidden">
                                <GoogleLogin
                                    onSuccess={handleGoogleSuccess}
                                    onError={() => toast.error("Google Login Failed")}
                                    theme="filled_black"
                                    shape="pill"
                                    text="continue_with"
                                    size="large"
                                    width="100%"
                                />
                            </div>

                            <div className="my-6 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                                <hr className="border-zinc-800 border-dashed" />
                                <span className="text-zinc-500 text-[11px] font-medium uppercase tracking-wider">Or continue With</span>
                                <hr className="border-zinc-800 border-dashed" />
                            </div>

                            <div className="space-y-5">
                                <div className="space-y-2">
                                    <Label htmlFor="reg-username" className="block text-sm font-medium text-zinc-300">
                                        Username
                                    </Label>
                                    <Input
                                        type="text"
                                        required
                                        name="username"
                                        id="reg-username"
                                        className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 px-4"
                                    />
                                </div>

                                <div className="space-y-2">
                                    <Label htmlFor="reg-email" className="block text-sm font-medium text-zinc-300">
                                        Email
                                    </Label>
                                    <Input
                                        type="email"
                                        required
                                        name="email"
                                        id="reg-email"
                                        className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 px-4"
                                    />
                                </div>
                                
                                <div className="space-y-2">
                                    <Label htmlFor="reg-password" className="block text-sm font-medium text-zinc-300">
                                        Password
                                    </Label>
                                    <Input
                                        type="password"
                                        required
                                        name="password"
                                        id="reg-password"
                                        className="bg-zinc-900/50 border-zinc-800 text-white placeholder:text-zinc-600 focus-visible:ring-zinc-700 h-11 px-4"
                                    />
                                </div>

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
