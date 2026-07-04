import { useEffect, useRef, useState } from "react";

/**
 * Interroge périodiquement une fonction asynchrone et expose son résultat.
 * Utilisé pour tout ce qui doit rester "vivant" à l'écran (score du
 * scanner, santé système...) sans dépendre d'un WebSocket pour cette V1.
 */
export function usePolling(fetchFn, { intervalMs = 5000, enabled = true } = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;

  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;

    async function run() {
      try {
        const result = await fetchFnRef.current();
        if (!cancelled) {
          setData(result);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    run();
    const id = setInterval(run, intervalMs);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [intervalMs, enabled]);

  return { data, error, isLoading };
}
