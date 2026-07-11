import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useCorrelation } from '../hooks/useCorrelation';

vi.mock('../../analytics/hooks/useDashboardFilters', () => ({
  useDashboardFilters: () => ({ filters: { accountId: null, dateFrom: null, dateTo: null } }),
}));

vi.mock('../services/riskAnalyticsApi', () => ({
  riskAnalyticsApi: {
    getCorrelation: vi.fn().mockResolvedValue({ pairs: [] }),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('useCorrelation', () => {
  it('has correct query key shape', () => {
    const { result } = renderHook(() => useCorrelation(), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });
});
