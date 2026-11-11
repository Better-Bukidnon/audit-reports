import { useCallback, useEffect, useState } from 'react';

// Light or dark. The reader's choice is kept in localStorage; until they choose, the site
// follows the device's setting and changes with it. index.html runs the same check before
// the first paint (keep STORE_KEY in step with it), so the page never flashes the wrong theme.

export type Theme = 'light' | 'dark';
export const THEMES: Theme[] = ['light', 'dark'];

const STORE_KEY = 'ar-theme';
const darkQuery = typeof window.matchMedia === 'function' ? window.matchMedia('(prefers-color-scheme: dark)') : null;

function saved(): Theme | null {
  try {
    const v = localStorage.getItem(STORE_KEY);
    if (v === 'light' || v === 'dark') return v;
  } catch {
    /* storage blocked */
  }
  return null;
}

const device = (): Theme => (darkQuery?.matches ? 'dark' : 'light');

export function useTheme() {
  const [choice, setChoice] = useState<Theme | null>(saved);
  const [system, setSystem] = useState<Theme>(device);

  useEffect(() => {
    if (!darkQuery) return;
    const onChange = () => setSystem(device());
    darkQuery.addEventListener('change', onChange);
    return () => darkQuery.removeEventListener('change', onChange);
  }, []);

  const theme = choice ?? system;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  const setTheme = useCallback((t: Theme) => {
    setChoice(t);
    try {
      localStorage.setItem(STORE_KEY, t);
    } catch {
      /* storage blocked */
    }
  }, []);

  return { theme, setTheme };
}
