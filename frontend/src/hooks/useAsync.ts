import { useEffect, useState } from "react";

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

  const execute = async () => {
    setState({ data: null, error: null, isLoading: true });
    try {
      const result = await asyncFunction();
      setState({ data: result, error: null, isLoading: false });
      return result;
    } catch (error) {
      setState({
        data: null,
        error: error instanceof Error ? error : new Error(String(error)),
        isLoading: false,
      });
    }
  };

  useEffect(() => {
    if (immediate) {
      execute();
    }
  }, []);

  return state;
}
