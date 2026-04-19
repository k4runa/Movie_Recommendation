import React from 'react';
import { Button, buttonVariants } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { MenuToggleIcon } from '@/components/ui/menu-toggle-icon';
import { useScroll } from '@/components/ui/use-scroll';
import { MovieSearch } from '@/components/movies/movie-search';
import { User as UserIcon, Settings, Menu } from 'lucide-react';

export function Header({ 
  user, 
  onOpenSidebar, 
  onOpenSettings 
}: { 
  user: any, 
  onOpenSidebar: () => void, 
  onOpenSettings: () => void 
}) {
	const [open, setOpen] = React.useState(false);
	const scrolled = useScroll(10);

	const links = [
		{
			label: 'Features',
			href: '#',
		},
		{
			label: 'Pricing',
			href: '#',
		},
		{
			label: 'About',
			href: '#',
		},
	];

	React.useEffect(() => {
		if (open) {
			// Disable scroll
			document.body.style.overflow = 'hidden';
		} else {
			// Re-enable scroll
			document.body.style.overflow = '';
		}

		// Cleanup when component unmounts
		return () => {
			document.body.style.overflow = '';
		};
	}, [open]);

	return (
		<header
			className={cn(
				'sticky top-0 z-50 mx-auto w-full max-w-5xl border-b border-transparent md:rounded-md md:border md:transition-all md:ease-out',
				{
					'bg-background/95 supports-[backdrop-filter]:bg-background/50 border-border backdrop-blur-lg md:top-6 md:max-w-4xl md:shadow':
						scrolled && !open,
					'bg-background/90': open,
				},
			)}
		>
			<nav
				className={cn(
					'flex h-14 w-full items-center justify-between px-4 md:h-12 md:transition-all md:ease-out',
					{
						'md:px-2': scrolled,
					},
				)}
			>
				<div className="flex items-center gap-2">
					<button
						onClick={onOpenSidebar}
						className="md:hidden p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-xl transition-colors"
					>
						<Menu className="w-5 h-5" />
					</button>
					<h1 className="text-lg font-black tracking-tighter text-primary md:hidden">CINEWAVE</h1>
					<h1 className="text-xl font-black tracking-tighter text-primary hidden md:block">CINEWAVE</h1>
				</div>

				<div className="hidden md:flex flex-1 justify-center max-w-md mx-4">
					<MovieSearch />
				</div>

				<div className="flex items-center gap-3">
					<div className="hidden sm:flex items-center gap-3 text-right">
						<div>
							<p className="text-[10px] font-black tracking-tight leading-none text-foreground uppercase">
								{user?.username}
							</p>
							<p className="text-[8px] text-muted-foreground font-bold uppercase tracking-widest mt-0.5">
								Enthusiast
							</p>
						</div>
						<div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
							<UserIcon className="w-4 h-4 text-primary" />
						</div>
					</div>

					<button
						onClick={onOpenSettings}
						className="p-2 text-muted-foreground hover:text-foreground hover:bg-accent rounded-xl transition-colors"
					>
						<Settings className="w-4 h-4" />
					</button>

					<Button size="icon" variant="ghost" onClick={() => setOpen(!open)} className="md:hidden">
						<MenuToggleIcon open={open} className="size-5" duration={300} />
					</Button>
				</div>
			</nav>

			<div
				className={cn(
					'bg-background/95 backdrop-blur-xl fixed top-14 right-0 bottom-0 left-0 z-50 flex flex-col overflow-hidden border-y md:hidden',
					open ? 'block' : 'hidden',
				)}
			>
				<div
					data-slot={open ? 'open' : 'closed'}
					className={cn(
						'data-[slot=open]:animate-in data-[slot=open]:zoom-in-95 data-[slot=closed]:animate-out data-[slot=closed]:zoom-out-95 ease-out',
						'flex h-full w-full flex-col p-6 space-y-8',
					)}
				>
					<div className="space-y-4">
						<label className="text-[10px] font-black uppercase tracking-widest text-muted-foreground">Quick Search</label>
						<MovieSearch />
					</div>
					
					<div className="pt-4 border-t border-border/50">
						<div className="flex items-center gap-4 mb-6">
							<div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
								<UserIcon className="w-6 h-6 text-primary" />
							</div>
							<div>
								<p className="font-black text-lg text-foreground">{user?.username}</p>
								<p className="text-xs text-muted-foreground font-bold uppercase tracking-widest">Enthusiast Member</p>
							</div>
						</div>
						<Button variant="outline" className="w-full rounded-xl h-12 font-black text-xs uppercase tracking-widest" onClick={() => { onOpenSettings(); setOpen(false); }}>
							Settings
						</Button>
					</div>
				</div>
			</div>
		</header>
	);
}
