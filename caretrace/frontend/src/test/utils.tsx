import { QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";

/**
 * Test QueryClient: retries off and no caching between tests so query state is
 * deterministic. Mirrors the production reliability settings (no window-focus
 * refetch) without the spammy retry loop. The no-op QueryCache onError marks
 * expected query failures as handled so intentional error-path tests don't trip
 * Vitest's unhandled-rejection guard.
 */
export function makeTestQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({ onError: () => {} }),
    defaultOptions: {
      queries: { retry: false, staleTime: 0, refetchOnWindowFocus: false },
      mutations: { retry: false },
    },
  });
}

export function renderWithClient(
  ui: ReactElement,
  { client = makeTestQueryClient(), ...options }: { client?: QueryClient } & RenderOptions = {}
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { client, ...render(ui, { wrapper: Wrapper, ...options }) };
}
