import { useEffect, useRef, useState } from "react";

interface UseAsyncState<T> {
  data: T | null;
  error: Error | null;
  isLoading: boolean;
}

export function useAsync<T>(
  asyncFunction: () => Promise<T>,
  immediate = true
): UseAsyncState<T> {
  const [state, setState] = useState<UseAsyncState<T>>({
    data: null,
    error: null,
    isLoading: immediate,
  });

  // The caller may pass a new inline function each render. Keep the latest
  // function without making each render cause another request.
  const taskRef = useRef(asyncFunction);
  useEffect(() => {
    taskRef.current = asyncFunction;
  }, [asyncFunction]);

  useEffect(() => {
    let active = true;
    if (immediate) {
      setState({ data: null, error: null, isLoading: true });
      const load = async () => {
        try {
          const data = await taskRef.current();
          if (active) setState({ data, error: null, isLoading: false });
        } catch (error) {
          if (active) setState({
            data: null,
            error: error instanceof Error ? error : new Error(String(error)),
            isLoading: false,
          });
        }
      };
      void load();
    } else {
      setState((previous) => ({ ...previous, isLoading: false }));
    }
    return () => { active = false; };
  }, [immediate]);

  return state;
}
