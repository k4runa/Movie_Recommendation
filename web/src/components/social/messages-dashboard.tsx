"use client";

import React, { useEffect, useState, useRef } from "react";
import { socialApi, getFullUrl } from "@/lib/api";
import { useAuthStore, useSocialUIStore } from "@/lib/store";
import {
  Search,
  Send,
  MoreVertical,
  Trash2,
  MessageSquare,
  Loader2,
  ChevronLeft,
  Info,
  Clock,
  Check,
  X,
  Pencil,
  User as UserIcon
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { UserProfileModal } from "./similar-minds-dashboard";

const getTimeAgo = (dateString: string) => {
  const date = new Date(dateString);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h`;
  return `${Math.floor(diffInSeconds / 86400)}d`;
};

const isUserOnline = (lastSeen: string | null) => {
  if (!lastSeen) return false;
  const date = new Date(lastSeen);
  const now = new Date();
  // We consider online if active in last 1 minutes
  return (now.getTime() - date.getTime()) < 1 * 60 * 1000;
};

export const MessagesDashboard = () => {
  const { user } = useAuthStore();
  const { activeChatId, setActiveChatId, setUnreadTotal } = useSocialUIStore();
  const [conversations, setConversations] = useState<any[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [newMessage, setNewMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [activeStatus, setActiveStatus] = useState<"ACCEPTED" | "PENDING">("ACCEPTED");
  const [requestCount, setRequestCount] = useState(0);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [activeUser, setActiveUser] = useState<any>(null);
  const [contextMenu, setContextMenu] = useState<{ x: number, y: number, messageId: number, content: string } | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = () => setContextMenu(null);
    window.addEventListener('click', handleClick);
    return () => window.removeEventListener('click', handleClick);
  }, []);

  const fetchConversations = async (statusOverride?: "ACCEPTED" | "PENDING") => {
    const targetStatus = statusOverride || activeStatus;
    try {
      const res = await socialApi.getConversations(targetStatus);

      // Safety: only update state if we are still looking at the same status
      if (targetStatus === activeStatus || statusOverride) {
        const convs = res.data?.data?.conversations || [];
        setConversations(convs);

        // Calculate total unread
        const total = convs.reduce((acc: number, curr: any) => acc + curr.unread_count, 0);
        setUnreadTotal(total);

        // Check for requests if we are in inbox
        if (targetStatus === "ACCEPTED") {
          const reqRes = await socialApi.getConversations("PENDING");
          setRequestCount(reqRes.data?.data?.conversations?.length || 0);
        }
      }
    } catch (err) {
      console.log("Failed to fetch conversations (Background):", err);
    } finally {
      // Only disable first-load spinner
      if (loading) setLoading(false);
    }
  };

  const fetchMessages = async (otherId: number) => {
    try {
      const res = await socialApi.getMessages(otherId);
      const newMessages = res.data?.data?.messages || [];

      setMessages(prev => {
        // Simple optimization: only update if lengths differ or last message ID differs
        if (prev.length === newMessages.length &&
          (prev.length === 0 || prev[prev.length - 1].id === newMessages[newMessages.length - 1].id)) {
          return prev;
        }
        return newMessages;
      });

      // Mark as read
      await socialApi.markAsRead(otherId);
      fetchConversations(); // Refresh unread badges
    } catch (err) {
      console.log("Failed to fetch messages (Background):", err);
    }
  };

  useEffect(() => {
    fetchConversations(activeStatus);
    // Poll for new messages/requests every 10 seconds
    const interval = setInterval(() => fetchConversations(activeStatus), 10000);
    return () => clearInterval(interval);
  }, [activeStatus]);

  useEffect(() => {
    if (activeChatId) {
      // Find in existing conversations first
      const conv = conversations.find(c => c.participant.id === activeChatId);
      if (conv) {
        setActiveUser(conv.participant);
      } else if (!activeUser || activeUser.id !== activeChatId) {
        // Fetch user info for a NEW chat initiator
        socialApi.getProfile(activeChatId).then(res => {
          setActiveUser(res.data?.data);
        }).catch(() => setActiveUser(null));
      }

      fetchMessages(activeChatId);
      // Poll active chat every 5 seconds
      const interval = setInterval(() => fetchMessages(activeChatId), 5000);
      return () => clearInterval(interval);
    } else {
      setActiveUser(null);
    }
  }, [activeChatId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeChatId || sending) return;

    setSending(true);
    try {
      await socialApi.sendMessage(activeChatId, newMessage);
      setNewMessage("");
      fetchMessages(activeChatId);
    } catch (err) {
      toast.error("Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const handleEditMessage = async (messageId: number) => {
    if (!editContent.trim()) return;
    try {
      await socialApi.editMessage(messageId, editContent);
      setEditingId(null);
      if (activeChatId) fetchMessages(activeChatId);
    } catch (err) {
      toast.error("Failed to edit message");
    }
  };

  const handleDeleteMessage = async (messageId: number) => {
    try {
      await socialApi.deleteMessage(messageId);
      setDeleteTargetId(null);
      if (activeChatId) fetchMessages(activeChatId);
      toast.success("Message deleted");
    } catch (err) {
      toast.error("Failed to delete message");
    }
  };

  const handleConversationRequest = async (otherId: number, action: "accept" | "decline") => {
    try {
      await socialApi.handleRequest(otherId, action);
      toast.success(action === "accept" ? "Request accepted" : "Request declined");
      setActiveChatId(action === "accept" ? otherId : null);
      if (action === "accept") {
        setActiveStatus("ACCEPTED"); // The useEffect will handle fetchConversations
      } else {
        fetchConversations("PENDING");
      }
    } catch (err) {
      toast.error("Failed to handle request");
    }
  };

  const handleDeleteConversation = async (otherId: number) => {
    try {
      await socialApi.deleteConversation(otherId);
      setActiveChatId(null);
      fetchConversations();
      toast.success("Conversation deleted");
    } catch (err) {
      toast.error("Failed to delete conversation");
    }
  };

  const filteredConversations = conversations.filter(c =>
    c.participant.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (c.participant.nickname && c.participant.nickname.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const selectedConv = conversations.find(c => c.participant.id === activeChatId);

  if (loading && conversations.length === 0) {
    return (
      <div className="flex h-[600px] items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex flex-col md:flex-row h-[600px] border border-border rounded-2xl bg-card overflow-hidden relative">

      {/* Sidebar - Conversation List */}
      <div className={cn(
        "w-full md:w-80 border-r border-border flex flex-col bg-accent/10",
        activeChatId ? "hidden md:flex" : "flex"
      )}>
        <div className="p-6 border-b border-border space-y-4">
          {/* Status Tabs */}
          <div className="flex border-b border-border gap-6 px-2">
            <button
              onClick={() => {
                if (activeStatus === "ACCEPTED") return;
                setActiveStatus("ACCEPTED");
                setActiveChatId(null);
                setConversations([]);
                setLoading(true); // Trigger spinner for clean state on explicit switch
              }}
              className={cn(
                "pb-4 text-[10px] font-black uppercase tracking-[0.2em] transition-all relative",
                activeStatus === "ACCEPTED" ? "text-primary" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Inbox
              {activeStatus === "ACCEPTED" && <motion.div layoutId="tab-underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
            </button>
            <button
              onClick={() => {
                if (activeStatus === "PENDING") return;
                setActiveStatus("PENDING");
                setActiveChatId(null);
                setConversations([]);
                setLoading(true);
              }}
              className={cn(
                "pb-4 text-[10px] font-black uppercase tracking-[0.2em] transition-all relative",
                activeStatus === "PENDING" ? "text-primary" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Requests
              {activeStatus === "PENDING" && <motion.div layoutId="tab-underline" className="absolute bottom-0 left-0 right-0 h-0.5 bg-primary" />}
              {requestCount > 0 && (
                <span className="absolute -top-1 -right-4 size-4 bg-primary text-primary-foreground text-[8px] flex items-center justify-center rounded-full">
                  {requestCount}
                </span>
              )}
            </button>
          </div>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-background border border-border rounded-2xl text-xs font-medium focus:ring-2 focus:ring-primary/20 outline-none transition-all"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-2 space-y-1">
          {filteredConversations.length === 0 ? (
            <div className="text-center py-10 px-6">
              <MessageSquare className="w-8 h-8 text-muted-foreground mx-auto mb-2 opacity-20" />
              <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">
                {activeStatus === "PENDING" ? "No message requests" : "No conversations"}
              </p>
            </div>
          ) : (
            filteredConversations.map((conv) => (
              <div
                key={conv.participant.id}
                onClick={() => setActiveChatId(conv.participant.id)}
                className={cn(
                  "p-4 cursor-pointer transition-all border border-transparent",
                  activeChatId === conv.participant.id
                    ? "bg-accent/50 border-border"
                    : "hover:bg-accent/30 hover:border-border/50 hover:-translate-y-0.5"
                )}
              >
                <div className="relative">
                  <div className="size-12 rounded bg-gradient-to-br from-primary/20 to-primary/5 border border-border overflow-hidden flex items-center justify-center text-primary font-black uppercase">
                    {conv.participant.avatar_url ? (
                      <img src={getFullUrl(conv.participant.avatar_url)} alt="Avatar" className="w-full h-full object-cover" />
                    ) : (
                      conv.participant.username[0]
                    )}
                  </div>
                  {conv.unread_count > 0 && (
                    <div className="absolute -top-1 -right-1 size-5 bg-primary text-white text-[10px] font-black flex items-center justify-center rounded-full border-2 border-card animate-in zoom-in">
                      {conv.unread_count}
                    </div>
                  )}
                </div>
                <div className="flex-1 text-left min-w-0">
                  <div className="flex justify-between items-start mb-0.5">
                    <span className="text-xs font-black tracking-tight truncate">
                      {conv.participant.nickname || conv.participant.username}
                    </span>
                    <span className="text-[9px] font-medium text-muted-foreground whitespace-nowrap ml-2">
                      {conv.last_message && getTimeAgo(conv.last_message.created_at)}
                    </span>
                  </div>
                  <p className={cn(
                    "text-[10px] truncate",
                    conv.unread_count > 0 ? "text-foreground font-bold" : "text-muted-foreground font-medium"
                  )}>
                    {conv.last_message ? (
                      <>
                        {conv.last_message.sender_id === user?.id ? "You: " : ""}
                        {conv.last_message.content}
                      </>
                    ) : "No messages yet"}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className={cn(
        "flex-1 flex flex-col bg-background relative",
        !activeChatId && "hidden md:flex"
      )}>
        {activeChatId && (activeUser || selectedConv) ? (
          <>
            {/* Chat Header */}
            <div className="h-20 border-b border-border px-6 flex items-center justify-between bg-card/50 backdrop-blur-md sticky top-0 z-10">
              <div
                className="flex items-center gap-4 cursor-pointer group"
                onClick={() => setIsProfileOpen(true)}
              >
                <button
                  onClick={(e) => { e.stopPropagation(); setActiveChatId(null); }}
                  className="md:hidden p-2 hover:bg-accent rounded-xl"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <div className="size-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 border border-border overflow-hidden flex items-center justify-center text-primary font-black uppercase group-hover:scale-110 transition-transform">
                  {(activeUser?.avatar_url || selectedConv?.participant?.avatar_url) ? (
                    <img src={getFullUrl(activeUser?.avatar_url || selectedConv?.participant?.avatar_url)} alt="Avatar" className="w-full h-full object-cover" />
                  ) : (
                    (activeUser?.username || selectedConv?.participant?.username || "?")[0]
                  )}
                </div>
                <div className="flex flex-col">
                  <span className="text-sm font-black tracking-tighter group-hover:text-primary transition-colors">
                    {activeUser?.nickname || activeUser?.username || selectedConv?.participant?.nickname || selectedConv?.participant?.username}
                  </span>
                  <div className="flex items-center gap-1.5">
                    <div className={cn(
                      "size-1.5 rounded-full shadow-sm",
                      isUserOnline(activeUser?.last_seen || selectedConv?.participant?.last_seen) ? "bg-emerald-500" : "bg-muted-foreground/30"
                    )} />
                    <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">
                      {isUserOnline(activeUser?.last_seen || selectedConv?.participant?.last_seen) ? "Active now" : `Last seen ${getTimeAgo(activeUser?.last_seen || selectedConv?.participant?.last_seen || "")}`}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleDeleteConversation(activeChatId)}
                  className="p-2.5 hover:bg-destructive/10 hover:text-destructive rounded-xl transition-all group"
                  title="Delete History"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                <button className="p-2.5 hover:bg-accent rounded-xl">
                  <MoreVertical className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Messages List */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar bg-accent/[0.02]">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
                  <div className="size-16 rounded-3xl bg-accent flex items-center justify-center">
                    <MessageSquare className="w-8 h-8 text-muted-foreground opacity-50" />
                  </div>
                  <div>
                    <h4 className="text-sm font-black uppercase tracking-widest">No messages yet</h4>
                    <p className="text-[10px] font-medium text-muted-foreground mt-1">Start a conversation with {activeUser?.nickname || activeUser?.username || selectedConv?.participant?.nickname || selectedConv?.participant?.username}!</p>
                  </div>
                </div>
              ) : (
                messages.map((msg, idx) => {
                  const isOwn = msg.sender_id === user?.id;
                  const prevMsg = idx > 0 ? messages[idx - 1] : null;
                  const isSequence = prevMsg && prevMsg.sender_id === msg.sender_id;
                  const isEditing = editingId === msg.id;

                  return (
                    <div
                      key={msg.id}
                      className={cn(
                        "flex flex-col max-w-[80%]",
                        isOwn ? "ml-auto items-end" : "mr-auto items-start",
                        isSequence ? "mt-1" : "mt-6"
                      )}
                    >
                      {!isSequence && (
                        <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground mb-2 px-1">
                          {isOwn ? "You" : activeUser?.nickname || activeUser?.username || selectedConv?.participant?.nickname || selectedConv?.participant?.username} • {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          {msg.is_edited && <span className="ml-1 opacity-50">(edited)</span>}
                        </span>
                      )}
                      <motion.div
                        initial={{ scale: 0.9, opacity: 0, y: 10 }}
                        animate={{ scale: 1, opacity: 1, y: 0 }}
                        onContextMenu={(e) => {
                          if (isOwn && !isEditing) {
                            e.preventDefault();
                            setContextMenu({ x: e.clientX, y: e.clientY, messageId: msg.id, content: msg.content });
                          }
                        }}
                        className={cn(
                          "px-4 py-2.5 rounded-2xl text-xs font-medium shadow-sm relative group cursor-default transition-all",
                          isOwn
                            ? "bg-primary text-primary-foreground rounded-tr-none hover:brightness-110"
                            : "bg-card border border-border text-foreground rounded-tl-none"
                        )}
                      >
                        {isEditing ? (
                          <div className="flex flex-col gap-2 min-w-[150px]">
                            <textarea
                              value={editContent}
                              onChange={(e) => setEditContent(e.target.value)}
                              className="bg-transparent border-none outline-none text-xs w-full resize-none p-0 text-primary-foreground placeholder:text-primary-foreground/50 leading-relaxed font-medium"
                              rows={Math.max(1, editContent.split('\n').length)}
                              autoFocus
                            />
                            <div className="flex justify-end gap-1 mt-1 pt-1 border-t border-primary-foreground/20">
                              <button onClick={() => setEditingId(null)} className="p-1 hover:bg-black/10 rounded-md transition-colors">
                                <X className="size-3" />
                              </button>
                              <button onClick={() => handleEditMessage(msg.id)} className="p-1 hover:bg-black/10 rounded-md transition-colors">
                                <Check className="size-3" />
                              </button>
                            </div>
                          </div>
                        ) : (
                          <>
                            {msg.content}
                          </>
                        )}

                        {isOwn && idx === messages.length - 1 && (
                          <div className="absolute -bottom-5 right-1 flex items-center gap-1 opacity-50">
                            <span className="text-[8px] font-black uppercase tracking-widest">
                              {msg.is_read ? "Read" : "Sent"}
                            </span>
                          </div>
                        )}
                      </motion.div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input or Request Banner */}
            {selectedConv?.status === "PENDING" && selectedConv?.last_message?.receiver_id === user?.id ? (
              <div className="p-8 border-t border-border bg-accent/30 backdrop-blur-md text-center space-y-6">
                <div className="max-w-md mx-auto space-y-2">
                  <h4 className="text-lg font-black tracking-tight">Message Request</h4>
                  <p className="text-xs text-muted-foreground font-medium">
                    {activeUser?.nickname || activeUser?.username || selectedConv?.participant?.nickname || selectedConv?.participant?.username} wants to chat.
                    They can only see if you've read the message once you accept.
                  </p>
                </div>
                <div className="flex items-center justify-center gap-4">
                  <button
                    onClick={() => handleConversationRequest(activeChatId, "decline")}
                    className="px-8 py-3 bg-card border border-border rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-destructive/10 hover:text-destructive transition-all"
                  >
                    Decline
                  </button>
                  <button
                    onClick={() => handleConversationRequest(activeChatId, "accept")}
                    className="px-10 py-3 bg-primary text-primary-foreground rounded-2xl text-[10px] font-black uppercase tracking-widest shadow-xl hover:scale-105 active:scale-95 transition-all"
                  >
                    Accept
                  </button>
                </div>
              </div>
            ) : (
              <div className="p-6 border-t border-border bg-card/50 backdrop-blur-md">
                {(selectedConv?.status === "PENDING" || selectedConv?.status === "PENDING_SENT") && (
                  <div className="mb-4 text-center">
                    <p className="text-[10px] font-black uppercase tracking-widest text-muted-foreground opacity-50">
                      Waiting for acceptance...
                    </p>
                  </div>
                )}
                <form onSubmit={handleSendMessage} className="flex items-center gap-3">
                  <div className="flex-1 relative">
                    <input
                      type="text"
                      placeholder={(selectedConv?.status === "PENDING" || selectedConv?.status === "PENDING_SENT") ? "You must be accepted to send more..." : "Write a message..."}
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      disabled={selectedConv?.status === "PENDING" || selectedConv?.status === "PENDING_SENT"}
                      className="w-full bg-background border border-border rounded-2xl px-5 py-3.5 text-xs font-medium focus:ring-2 focus:ring-primary/20 outline-none transition-all shadow-inner disabled:opacity-50"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={!newMessage.trim() || sending || selectedConv?.status === "PENDING" || selectedConv?.status === "PENDING_SENT"}
                    className={cn(
                      "size-12 rounded-2xl flex items-center justify-center transition-all shadow-lg active:scale-95",
                      newMessage.trim() && selectedConv?.status !== "PENDING" && selectedConv?.status !== "PENDING_SENT"
                        ? "bg-primary text-primary-foreground shadow-primary/20 hover:scale-105"
                        : "bg-accent text-muted-foreground grayscale cursor-not-allowed"
                    )}
                  >
                    {sending ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
                  </button>
                </form>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
            <div className="relative mb-8">
              <div className="relative size-20 rounded-2xl bg-card border border-border flex items-center justify-center text-primary">
                <MessageSquare className="w-8 h-8" />
              </div>
            </div>
            <h3 className="text-2xl font-black tracking-tighter mb-3">Your Messages</h3>
            <p className="text-muted-foreground font-medium max-w-xs mx-auto text-sm">
              Select a conversation from the list to start chatting with your cinematic kindred spirits.
            </p>
            <div className="mt-8 flex gap-4">
              <div className="flex flex-col items-center gap-1">
                <div className="size-10 rounded-xl bg-accent/50 flex items-center justify-center">
                  <Info className="w-4 h-4 text-muted-foreground" />
                </div>
                <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">Private</span>
              </div>
              <div className="flex flex-col items-center gap-1">
                <div className="size-10 rounded-xl bg-accent/50 flex items-center justify-center">
                  <Clock className="w-4 h-4 text-muted-foreground" />
                </div>
                <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">Real-time</span>
              </div>
            </div>
          </div>
        )}
      </div>

      <AnimatePresence>
        {isProfileOpen && activeChatId && (
          <UserProfileModal
            userId={activeChatId}
            onClose={() => setIsProfileOpen(false)}
            setActiveChatId={setActiveChatId}
          />
        )}
      </AnimatePresence>

      {/* Context Menu */}
      <AnimatePresence>
        {contextMenu && (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            style={{ top: contextMenu.y, left: contextMenu.x }}
            className="fixed z-[100] min-w-[140px] bg-card/95 backdrop-blur-xl border border-border rounded-2xl shadow-2xl overflow-hidden p-1.5"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              onClick={() => {
                setEditingId(contextMenu.messageId);
                setEditContent(contextMenu.content);
                setContextMenu(null);
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-primary hover:text-primary-foreground rounded-xl transition-all text-xs font-black uppercase tracking-widest group"
            >
              <Pencil className="size-3.5" />
              Edit
            </button>
            <button
              onClick={() => {
                setDeleteTargetId(contextMenu.messageId);
                setContextMenu(null);
              }}
              className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-destructive hover:text-destructive-foreground rounded-xl transition-all text-xs font-black uppercase tracking-widest group"
            >
              <Trash2 className="size-3.5" />
              Delete
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Custom Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteTargetId && (
          <div className="fixed inset-0 z-[110] flex items-center justify-center p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="absolute inset-0 bg-background/80 backdrop-blur-sm"
              onClick={() => setDeleteTargetId(null)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-[340px] bg-card border border-border rounded-[2rem] shadow-2xl overflow-hidden p-8 text-center space-y-6"
            >
              <div className="size-16 bg-destructive/10 text-destructive rounded-3xl flex items-center justify-center mx-auto">
                <Trash2 className="size-8" />
              </div>
              <div className="space-y-2">
                <h4 className="text-lg font-black tracking-tight">Delete Message?</h4>
                <p className="text-xs text-muted-foreground font-medium">This action cannot be undone. The message will be removed for everyone.</p>
              </div>
              <div className="flex flex-col gap-2">
                <button
                  onClick={() => handleDeleteMessage(deleteTargetId)}
                  className="w-full py-4 bg-destructive text-destructive-foreground rounded-2xl text-[10px] font-black uppercase tracking-widest hover:brightness-110 active:scale-95 transition-all shadow-lg shadow-destructive/20"
                >
                  Delete Message
                </button>
                <button
                  onClick={() => setDeleteTargetId(null)}
                  className="w-full py-4 bg-accent/50 text-foreground rounded-2xl text-[10px] font-black uppercase tracking-widest hover:bg-accent active:scale-95 transition-all"
                >
                  Cancel
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};
