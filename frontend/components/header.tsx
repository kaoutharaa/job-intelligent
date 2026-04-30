'use client';

import { Briefcase, Moon, Sun } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useTheme } from 'next-themes';
import { useEffect, useState } from 'react';

interface HeaderProps {
  onSavedClick?: () => void;
  showSavedOnly?: boolean;
  onGetStartedClick?: () => void;
}

export function Header({ onSavedClick, showSavedOnly, onGetStartedClick }: HeaderProps = {}) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  return (
    <header className="border-b border-border/40 sticky top-0 bg-background/95 backdrop-blur-sm z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg">
            <Briefcase className="text-primary" size={24} />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-foreground">JobFit</h1>
            <p className="text-xs text-muted-foreground">Find opportunities that fit you</p>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {mounted && (
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="text-foreground hover:text-primary rounded-full mr-2"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </Button>
          )}
          <Button 
            variant={showSavedOnly ? "secondary" : "ghost"} 
            className="text-foreground hover:text-primary"
            onClick={onSavedClick}
          >
            Saved Jobs
          </Button>
          <Button 
            className="bg-primary hover:bg-primary/90 text-white dark:text-black rounded-lg"
            onClick={onGetStartedClick}
          >
            Get Started
          </Button>
        </div>
      </div>
    </header>
  );
}
