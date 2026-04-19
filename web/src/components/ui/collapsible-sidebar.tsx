"use client"
import React, { useState } from "react";
import {
  Film,
  Compass,
  Settings,
  LogOut,
  ChevronDown,
  ChevronsRight,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

export const CollapsibleSidebar = ({ 
  activeTab, 
  setActiveTab, 
  logout,
  user
}: { 
  activeTab: string, 
  setActiveTab: (tab: any) => void,
  logout: () => void,
  user: any
}) => {
  const [open, setOpen] = useState(true);

  return (
    <nav
      className={cn(
        "sticky top-0 md:top-6 md:m-6 md:mb-6 h-screen md:h-[calc(100vh-3rem)] shrink-0 transition-all duration-300 ease-in-out z-50",
        open ? "w-64" : "w-20",
        "border-border bg-background md:rounded-2xl p-4 shadow-sm flex flex-col md:border"
      )}
    >
      <TitleSection open={open} user={user} />

      <div className="space-y-1 flex-1">
        <Option
          Icon={Film}
          title="My collections"
          id="movies"
          selected={activeTab}
          setSelected={setActiveTab}
          open={open}
        />
        <Option
          Icon={Compass}
          title="Discover"
          id="recommendations"
          selected={activeTab}
          setSelected={setActiveTab}
          open={open}
        />
        <Option
          Icon={Settings}
          title="Settings"
          id="settings"
          selected={activeTab}
          setSelected={setActiveTab}
          open={open}
        />
      </div>

      <div className="border-t border-border pt-4 pb-16 space-y-1">
        <button
          onClick={logout}
          className={cn(
            "relative flex h-11 w-full items-center rounded-lg transition-all duration-200",
            "text-muted-foreground hover:bg-accent hover:text-destructive"
          )}
        >
          <div className="grid h-full w-14 place-content-center">
            <LogOut className="h-4 w-4" />
          </div>
          {open && <span className="text-xs font-black uppercase tracking-widest">Logout</span>}
        </button>
      </div>

      <ToggleClose open={open} setOpen={setOpen} />
    </nav>
  );
};

const Option = ({ Icon, title, id, selected, setSelected, open }: any) => {
  const isSelected = selected === id;
  
  return (
    <button
      onClick={() => setSelected(id)}
      className={cn(
        "relative flex h-11 w-full items-center rounded-lg transition-all duration-200 mb-1",
        isSelected 
          ? "bg-card text-foreground border border-border shadow-md" 
          : "text-muted-foreground hover:bg-card hover:text-foreground"
      )}
    >
      <div className="grid h-full w-14 place-content-center">
        <Icon className={cn("h-4 w-4", isSelected ? "text-foreground" : "text-muted-foreground")} />
      </div>
      
      {open && (
        <span className="text-xs font-black uppercase tracking-widest">
          {title}
        </span>
      )}

      {isSelected && (
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-4 bg-foreground rounded-r-full" />
      )}
    </button>
  );
};

const TitleSection = ({ open, user }: any) => {
  return (
    <div className="mb-8 border-b border-border pb-6 pt-2">
      <div className="flex items-center gap-3 px-2">
        <Logo />
        {open && (
          <div className="flex flex-col">
            <span className="block text-sm font-black tracking-tighter text-foreground">
              CINEWAVE
            </span>
            <span className="block text-[10px] text-muted-foreground font-bold uppercase tracking-widest">
              {user?.username || 'Guest'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

const Logo = () => {
  return (
    <div className="grid size-10 shrink-0 place-content-center rounded-xl bg-foreground shadow-lg">
      <Film className="w-5 h-5 text-background" strokeWidth={3} />
    </div>
  );
};

const ToggleClose = ({ open, setOpen }: any) => {
  return (
    <button
      onClick={() => setOpen(!open)}
      className="absolute bottom-0 left-0 right-0 border-t border-border transition-colors bg-background hover:bg-card rounded-b-2xl"
    >
      <div className="flex items-center p-2.5">
        <div className="grid size-8 place-content-center">
          <ChevronsRight
            className={cn(
              "h-3.5 w-3.5 transition-transform duration-500 text-muted-foreground",
              open ? "rotate-180" : ""
            )}
          />
        </div>
        {open && (
          <span className="text-[9px] font-black uppercase tracking-widest text-muted-foreground">
            Collapse
          </span>
        )}
      </div>
    </button>
  );
};
