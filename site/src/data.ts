import { useEffect, useState } from 'react';
import type { Government, Index } from './types';

const cache = new Map<string, Promise<unknown>>();

function load<T>(path: string): Promise<T> {
  let p = cache.get(path);
  if (!p) {
    p = fetch(path).then((r) => {
      if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
      return r.json();
    });
    p.catch(() => cache.delete(path));
    cache.set(path, p);
  }
  return p as Promise<T>;
}

type State<T> = { data: T | null; error: Error | null };

function useJson<T>(path: string | null): State<T> {
  const [state, setState] = useState<State<T> & { path: string | null }>({ data: null, error: null, path: null });
  useEffect(() => {
    if (!path) return;
    let live = true;
    load<T>(path).then(
      (data) => live && setState({ data, error: null, path }),
      (error: Error) => live && setState({ data: null, error, path }),
    );
    return () => {
      live = false;
    };
  }, [path]);
  // Don't show the last government's data while the next one loads.
  return state.path === path ? state : { data: null, error: null };
}

export const useIndex = () => useJson<Index>('/data/index.json');
export const useGovernment = (slug: string | null) => useJson<Government>(slug ? `/data/gov/${slug}.json` : null);
