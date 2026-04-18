"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { ArrowUpIcon, Loader2, Sparkles, User } from "lucide-react";
import { aiApi } from "@/lib/api";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export function VercelV0Chat() {
  const [value, setValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const adjustHeight = useCallback((reset?: boolean) => {
    const textarea = textareaRef.current;
    if (!textarea) return;
    if (reset) {
      textarea.style.height = `60px`;
      return;
    }
    textarea.style.height = `60px`;
    const newHeight = Math.max(60, Math.min(textarea.scrollHeight, 200));
    textarea.style.height = `${newHeight}px`;
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!value.trim() || isLoading) return;

    const userMsg = value.trim();
    setValue("");
    adjustHeight(true);
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);

    try {
      const history = messages.slice(-6).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await aiApi.streamChat(userMsg, history);

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

      let fullContent = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullContent += chunk;

        setMessages((prev) => {
          const newMsgs = [...prev];
          newMsgs[newMsgs.length - 1].content = fullContent;
          return newMsgs;
        });
      }
    } catch (err) {
      console.error("Chat error:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I'm sorry, I'm having trouble connecting right now. Please try again later.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col w-full h-full bg-transparent overflow-hidden">
      {/* Chat History */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-hide"
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
            <div className="w-20 h-20 rounded-3xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-inner">
              <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <div className="space-y-2">
              <h2 className="text-3xl font-black tracking-tighter text-foreground">
                CineWave Eco
              </h2>
              <p className="text-muted-foreground font-medium max-w-[280px]">
                Ask me anything about movies, directors, or personalized
                recommendations.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-[300px]">
              <button
                onClick={() => setValue("Recommend me an action movie")}
                className="text-xs font-bold py-2 px-4 rounded-xl border border-border hover:bg-accent transition-all"
              >
                "Recommend me an action movie"
              </button>
              <button
                onClick={() => setValue("What are my favorite movies?")}
                className="text-xs font-bold py-2 px-4 rounded-xl border border-border hover:bg-accent transition-all"
              >
                "What are my favorite movies?"
              </button>
            </div>
          </div>
        )}

        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className={cn(
                "flex w-full gap-3",
                msg.role === "user" ? "flex-row-reverse" : "flex-row",
              )}
            >
              <div
                className={cn(
                  "w-8 h-8 rounded-full shrink-0 flex items-center justify-center border",
                  msg.role === "user"
                    ? "bg-primary/20 border-primary/30"
                    : "bg-accent border-border",
                )}
              >
                {msg.role === "user" ? (
                  <User className="w-4 h-4 text-primary" />
                ) : (
                  <Sparkles className="w-4 h-4 text-muted-foreground" />
                )}
              </div>
              <div
                className={cn(
                  "max-w-[85%] p-4 rounded-2xl text-sm leading-relaxed shadow-sm",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground font-medium rounded-tr-none"
                    : "bg-card border border-border/50 text-foreground rounded-tl-none prose prose-invert prose-sm max-w-none",
                )}
              >
                {msg.role === "assistant" ? (
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => (
                        <p className="mb-2 last:mb-0">{children}</p>
                      ),
                      ul: ({ children }) => (
                        <ul className="list-disc ml-4 mb-2">{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol className="list-decimal ml-4 mb-2">{children}</ol>
                      ),
                      li: ({ children }) => (
                        <li className="mb-1">{children}</li>
                      ),
                      code: ({ children }) => (
                        <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">
                          {children}
                        </code>
                      ),
                      strong: ({ children }) => (
                        <strong className="font-black text-primary/90">
                          {children}
                        </strong>
                      ),
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  msg.content
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {isLoading && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="flex justify-start gap-3"
          >
            <div className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center bg-accent border border-border">
              <Sparkles className="w-4 h-4 text-muted-foreground" />
            </div>
            <div className="bg-card border border-border/50 p-4 rounded-2xl rounded-tl-none">
              <Loader2 className="w-5 h-5 animate-spin text-primary" />
            </div>
          </motion.div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 bg-background/40 backdrop-blur-xl border-t border-border/30">
        <div className="relative group bg-accent/30 rounded-3xl border border-border/50 shadow-inner transition-all focus-within:ring-2 focus-within:ring-primary/20 focus-within:border-primary/40">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              adjustHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Whisper to Eco..."
            className="w-full px-5 py-5 resize-none bg-transparent border-none text-foreground text-sm font-medium leading-relaxed focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground min-h-[60px] max-h-[200px] overflow-hidden"
          />

          <div className="flex items-center justify-between px-4 pb-4">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-black uppercase tracking-widest text-muted-foreground opacity-50">
                Press Enter to send
              </span>
            </div>
            <button
              onClick={handleSend}
              disabled={!value.trim() || isLoading}
              className={cn(
                "p-3 rounded-2xl transition-all duration-300 active:scale-95 shadow-lg",
                value.trim() && !isLoading
                  ? "bg-primary text-primary-foreground shadow-primary/20 scale-105"
                  : "bg-accent text-muted-foreground opacity-50 cursor-not-allowed",
              )}
            >
              <ArrowUpIcon className="w-5 h-5" strokeWidth={3} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
