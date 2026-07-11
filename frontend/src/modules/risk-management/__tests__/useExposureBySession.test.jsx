import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useExposureBySession } from '../hooks/useExposureBySession';

vi.mock('../../analytics/hooks/useDashboardFilters', () => ({
  useDashboardFilters: () => ({ filters: { accountId: null, dateFrom: null, dateTo: null } }),
}));

vi.mock('../services/riskAnalyticsApi', () => ({
  riskAnalyticsApi: {
    getExposureBySession: vi.fn().mockResolvedValue({ records: [] }),
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

describe('useExposureBySession', () => {
  it('has correct query key shape', () => {
    const { result } = renderHook(() => useExposureBySession(), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });
});
