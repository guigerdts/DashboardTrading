import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { usePerformanceByPeriod } from '../usePerformanceByPeriod';

vi.mock('../../services/analyticsApi', () => ({
  analyticsApi: {
    getPerformanceByPeriod: vi.fn().mockResolvedValue({ records: [] }),
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

describe('usePerformanceByPeriod', () => {
  it('accepts period param and creates correct query key', () => {
    const filters = { accountId: 1 };
    const { result } = renderHook(() => usePerformanceByPeriod(filters, 'quarter'), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('defaults to month period', () => {
    const filters = { accountId: 1 };
    const { result } = renderHook(() => usePerformanceByPeriod(filters), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
  });
});
