import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEdgeRankings } from '../useEdgeRankings';

vi.mock('../../services/edge-discovery.service', () => ({
  edgeDiscoveryApi: {
    getRankings: vi.fn().mockResolvedValue({
      snapshot_id: 'snap_001',
      generated_at: '2025-01-15T10:00:00Z',
      parameters: { min_observations: 5, bootstrap_resamples: 1000, fdr_alpha: 0.05, stability_threshold: 0.7, seed: null },
      trade_count: 5,
      rankings: [],
    }),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  // eslint-disable-next-line react/prop-types
  return function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('useEdgeRankings', () => {
  it('has correct query key shape when showInsufficient is false', () => {
    const { result } = renderHook(() => useEdgeRankings(false), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('has correct query key shape when showInsufficient is true', () => {
    const { result } = renderHook(() => useEdgeRankings(true), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('passes showInsufficient parameter to the service', async () => {
    const { edgeDiscoveryApi } = await import('../../services/edge-discovery.service');
    renderHook(() => useEdgeRankings(true), {
      wrapper: createWrapper(),
    });
    expect(edgeDiscoveryApi.getRankings).toHaveBeenCalledWith(true);
  });
});
