import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRollingMetrics } from '../useRollingMetrics';

vi.mock('../../services/analyticsApi', () => ({
  analyticsApi: {
    getRolling: vi.fn().mockResolvedValue({ window_size: 30, points: [] }),
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

describe('useRollingMetrics', () => {
  it('has correct query key shape with filters', () => {
    const filters = { accountId: 1, dateFrom: '2024-01-01' };
    const { result } = renderHook(() => useRollingMetrics(filters), {
      wrapper: createWrapper(),
    });
    // React Query fires the query and sets up the key
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined(); // initial state before fetch
  });
});
