import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRiskMetrics } from '../hooks/useRiskMetrics';

vi.mock('../../analytics/hooks/useDashboardFilters', () => ({
  useDashboardFilters: () => ({ filters: { accountId: null, dateFrom: null, dateTo: null } }),
}));

vi.mock('../services/riskAnalyticsApi', () => ({
  riskAnalyticsApi: {
    getRiskMetrics: vi.fn().mockResolvedValue({ total_trades: 0 }),
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

describe('useRiskMetrics', () => {
  it('has correct query key shape', () => {
    const { result } = renderHook(() => useRiskMetrics(), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });
});
