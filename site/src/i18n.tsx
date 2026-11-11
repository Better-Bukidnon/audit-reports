import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { LANGS, STRINGS, type Key, type Lang } from './strings';

export type T = (key: Key, params?: Record<string, string | number>) => string;

const STORE_KEY = 'ar-lang';

function saved(): Lang {
  try {
    const v = localStorage.getItem(STORE_KEY);
    if (v && (LANGS as string[]).includes(v)) return v as Lang;
  } catch {
    /* storage blocked */
  }
  return 'en';
}

const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: T } | null>(null);

export function LangProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>(saved);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORE_KEY, l);
    } catch {
      /* storage blocked */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const t = useCallback<T>(
    (key, params) => {
      let s = STRINGS[lang][key] ?? STRINGS.en[key];
      if (params) s = s.replace(/\{(\w+)\}/g, (m, k: string) => (k in params ? String(params[k]) : m));
      return s;
    },
    [lang],
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export function useLang() {
  const v = useContext(LangContext);
  if (!v) throw new Error('useLang outside LangProvider');
  return v;
}

export function useT(): T {
  return useLang().t;
}

/** Sets the document title, "<page> · Bukidnon Audit Reports". */
export function useTitle(page: string | null) {
  useEffect(() => {
    document.title = page ? `${page} · Bukidnon Audit Reports` : 'Bukidnon Audit Reports · Better Bukidnon';
  }, [page]);
}
