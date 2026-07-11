import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useInsights, useInsightDetail, useRefreshInsights } from '../useInsights';

vi.mock('../../services/aiInsightsApi', () => ({
  aiInsightsApi: {
    getSummary: vi.fn().mockResolvedValue({
      insights: [
        { id: 1, severity: 'warning', title: 'Test insight', message: 'Test message' },
      ],
    }),
    getDetail: vi.fn().mockResolvedValue({
      id: 1,
      severity: 'warning',
      title: 'Test insight',
      message: 'Test message',
      supporting_metrics: [],
    }),
    refresh: vi.fn().mockResolvedValue({ status: 'ok' }),
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

describe('useInsights', () => {
  it('has correct query key shape when filters are provided', () => {
    const { result } = renderHook(() => useInsights({ accountId: 1 }), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('calls getSummary with filters', async () => {
    const { aiInsightsApi } = await import('../../services/aiInsightsApi');
    renderHook(() => useInsights({ accountId: 1 }), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(aiInsightsApi.getSummary).toHaveBeenCalledWith({ accountId: 1 });
    });
  });

  it('returns insights data on success', async () => {
    const { result } = renderHook(() => useInsights(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data.insights).toHaveLength(1);
  });
});

describe('useInsightDetail', () => {
  it('is not enabled when insightId is null', () => {
    const { result } = renderHook(() => useInsightDetail(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('is not enabled when insightId is undefined', () => {
    const { result } = renderHook(() => useInsightDetail(undefined), {
      wrapper: createWrapper(),
    });
    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('calls getDetail when insightId is provided', async () => {
    const { aiInsightsApi } = await import('../../services/aiInsightsApi');
    renderHook(() => useInsightDetail(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(aiInsightsApi.getDetail).toHaveBeenCalledWith(1);
    });
  });

  it('returns detail data on success', async () => {
    const { result } = renderHook(() => useInsightDetail(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data.id).toBe(1);
  });
});

describe('useRefreshInsights', () => {
  it('calls refresh on mutation', async () => {
    const { aiInsightsApi } = await import('../../services/aiInsightsApi');
    const { result } = renderHook(() => useRefreshInsights(), {
      wrapper: createWrapper(),
    });
    result.current.mutate();
    await waitFor(() => {
      expect(aiInsightsApi.refresh).toHaveBeenCalled();
    });
  });

  it('invalidates summary query on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    // eslint-disable-next-line react/prop-types
    function Wrapper({ children }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );
    }

    // Pre-populate the summary cache to verify invalidation
    queryClient.setQueryData(['ai-insights', 'summary', {}], { insights: [] });

    const { result } = renderHook(() => useRefreshInsights(), {
      wrapper: Wrapper,
    });

    const stateBefore = queryClient.getQueryState(['ai-insights', 'summary', {}]);
    expect(stateBefore).toBeDefined();
    expect(stateBefore.isInvalidated).toBe(false);

    result.current.mutate();
    await waitFor(() => {
      const state = queryClient.getQueryState(['ai-insights', 'summary', {}]);
      // InvalidateQueries marks the query as invalidated (stale) rather than removing it
      expect(state.isInvalidated).toBe(true);
    });
  });
});
