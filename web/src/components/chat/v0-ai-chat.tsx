import { useEffect, useRef, useCallback, useState, memo } from "react";
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

const MemoizedMarkdown = memo(({ content }: { content: string }) => {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc ml-4 mb-2">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal ml-4 mb-2">{children}</ol>,
        li: ({ children }) => <li className="mb-1">{children}</li>,
        code: ({ children }) => (
          <code className="bg-[#262626] px-1 py-0.5 rounded text-[10px] font-mono">
            {children}
          </code>
        ),
        strong: ({ children }) => (
          <strong className="font-black text-white">{children}</strong>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
});

const MessageItem = memo(({ msg }: { msg: Message }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      className={cn(
        "flex w-full gap-3",
        msg.role === "user" ? "flex-row-reverse" : "flex-row"
      )}
    >
      <div
        className={cn(
          "w-8 h-8 rounded-lg shrink-0 flex items-center justify-center border",
          msg.role === "user"
            ? "bg-[#262626] border-white/10"
            : "bg-[#171717] border-[#262626]"
        )}
      >
        {msg.role === "user" ? (
          <User className="w-4 h-4 text-white" />
        ) : (
          <Sparkles className="w-4 h-4 text-white" />
        )}
      </div>
      <div
        className={cn(
          "max-w-[85%] p-4 rounded-xl text-xs leading-relaxed shadow-sm",
          msg.role === "user"
            ? "bg-white text-[#0a0a0a] font-bold rounded-tr-none"
            : "bg-[#171717] border border-[#262626] text-white rounded-tl-none prose prose-invert prose-sm max-w-none"
        )}
      >
        {msg.role === "assistant" ? (
          <MemoizedMarkdown content={msg.content} />
        ) : (
          msg.content
        )}
      </div>
    </motion.div>
  );
});

export function VercelV0Chat({ placeholder = "Ask Eco anything..." }: { placeholder?: string }) {
  const [value, setValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState<string | null>(null);

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
  }, [messages, streamingContent]);

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
      let fullContent = "";
      setStreamingContent("");

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        fullContent += chunk;
        setStreamingContent(fullContent);
      }

      setMessages((prev) => [...prev, { role: "assistant", content: fullContent }]);
      setStreamingContent(null);
    } catch (err) {
      console.log("Chat error (User Action):", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I'm sorry, I'm having trouble connecting right now. Please try again later.",
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
    <div className="flex flex-col w-full h-full bg-[#0a0a0a] overflow-hidden">
      {/* Chat History */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-hide"
      >
        {messages.length === 0 && !streamingContent && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-6 animate-in fade-in zoom-in duration-500">
            <div className="w-16 h-16 rounded-2xl bg-[#171717] flex items-center justify-center border border-[#262626] shadow-xl">
              <Sparkles className="w-8 h-8 text-white" />
            </div>
            <div className="space-y-2">
              <h2 className="text-2xl font-black tracking-tighter text-white">Eco</h2>
              <p className="text-muted-foreground text-xs font-medium max-w-[280px]">
                Ask me anything about movies, directors, or personalized recommendations.
              </p>
            </div>
            <div className="grid grid-cols-1 gap-2 w-full max-w-[300px]">
              <button
                onClick={() => setValue("Recommend me an action movie")}
                className="text-[10px] font-black uppercase tracking-widest py-3 px-4 rounded-xl border border-[#262626] bg-[#171717] text-muted-foreground hover:text-white hover:border-white/20 transition-all"
              >
                "Recommend an action movie"
              </button>
              <button
                onClick={() => setValue("What are my favorite movies?")}
                className="text-[10px] font-black uppercase tracking-widest py-3 px-4 rounded-xl border border-[#262626] bg-[#171717] text-muted-foreground hover:text-white hover:border-white/20 transition-all"
              >
                "What are my favorites?"
              </button>
            </div>
          </div>
        )}

        <div className="space-y-8">
          {messages.map((msg, i) => (
            <MessageItem key={i} msg={msg} />
          ))}
          {streamingContent !== null && (
            <MessageItem msg={{ role: "assistant", content: streamingContent }} />
          )}
        </div>

        {isLoading && streamingContent === null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start gap-3"
          >
            <div className="w-8 h-8 rounded-lg shrink-0 flex items-center justify-center bg-[#171717] border border-[#262626]">
              <Sparkles className="w-4 h-4 text-white animate-pulse" />
            </div>
            <div className="bg-[#171717] border border-[#262626] p-4 rounded-xl rounded-tl-none">
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            </div>
          </motion.div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-6 bg-[#0a0a0a] border-t border-[#262626]">
        <div className="relative group bg-[#050505] rounded-2xl border border-[#262626] shadow-inner transition-all focus-within:border-white/10">
          <Textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
              adjustHeight();
            }}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            className="w-full px-5 py-5 resize-none bg-transparent border-none text-white text-xs font-medium leading-relaxed focus:outline-none focus-visible:ring-0 focus-visible:ring-offset-0 placeholder:text-muted-foreground/40 min-h-[60px] max-h-[200px] overflow-hidden"
          />

          <div className="flex items-center justify-between px-4 pb-4">
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-black uppercase tracking-widest text-muted-foreground/30">
                Press Enter to whisper
              </span>
            </div>
            <button
              onClick={handleSend}
              disabled={!value.trim() || isLoading}
              className={cn(
                "p-2.5 rounded-xl transition-all duration-300 active:scale-95",
                value.trim() && !isLoading
                  ? "bg-white text-[#0a0a0a] scale-105 shadow-lg shadow-white/5"
                  : "bg-[#171717] text-muted-foreground opacity-50 cursor-not-allowed"
              )}
            >
              <ArrowUpIcon className="w-4 h-4" strokeWidth={4} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
