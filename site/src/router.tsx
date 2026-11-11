// A small path router: the site has five kinds of page, so it doesn't need a library.
// Cloudflare serves index.html for any path (single-page-application handling), and so
// does Vite's dev server.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type AnchorHTMLAttributes, type MouseEvent } from 'react';

type Router = {
  path: string;
  query: URLSearchParams;
  navigate: (to: string, opts?: { replace?: boolean; keepScroll?: boolean }) => void;
};

const RouterContext = createContext<Router | null>(null);

function current() {
  return {
    path: window.location.pathname.replace(/\/+$/, '') || '/',
    search: window.location.search,
    hash: window.location.hash,
  };
}

export function RouterProvider({ children }: { children: React.ReactNode }) {
  const [loc, setLoc] = useState(current);

  useEffect(() => {
    const onPop = () => setLoc(current());
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  // After a page with an #anchor renders, scroll to the anchor. Pages that load data show
  // "Loading…" first, so keep looking for the anchor for about two seconds.
  useEffect(() => {
    if (!loc.hash) return;
    const id = decodeURIComponent(loc.hash.slice(1));
    let frame = 0;
    let tries = 0;
    const find = () => {
      const el = document.getElementById(id);
      if (el) el.scrollIntoView();
      else if (tries++ < 120) frame = requestAnimationFrame(find);
    };
    find();
    return () => cancelAnimationFrame(frame);
  }, [loc]);

  const navigate = useCallback<Router['navigate']>((to, opts) => {
    if (opts?.replace) window.history.replaceState(null, '', to);
    else window.history.pushState(null, '', to);
    setLoc(current());
    if (!opts?.keepScroll && !to.includes('#')) window.scrollTo(0, 0);
  }, []);

  const value = useMemo(() => ({ path: loc.path, query: new URLSearchParams(loc.search), navigate }), [loc, navigate]);
  return <RouterContext.Provider value={value}>{children}</RouterContext.Provider>;
}

export function useRouter(): Router {
  const r = useContext(RouterContext);
  if (!r) throw new Error('useRouter outside RouterProvider');
  return r;
}

type LinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & { to: string };

/** An in-site link. Modified clicks (new tab, etc.) are left to the browser. */
export function Link({ to, onClick, ...rest }: LinkProps) {
  const { navigate } = useRouter();
  function handle(e: MouseEvent<HTMLAnchorElement>) {
    onClick?.(e);
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    navigate(to);
  }
  return <a href={to} onClick={handle} {...rest} />;
}
