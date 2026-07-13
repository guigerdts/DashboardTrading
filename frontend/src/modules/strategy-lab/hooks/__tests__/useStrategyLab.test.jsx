import { describe, it, expect, vi } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useExperiments,
  useExperiment,
  useCreateExperiment,
  useRuns,
  useRun,
  useRunComparison,
  useCreateRun,
  useStrategyVersions,
  useStrategyVersion,
  useCreateStrategyVersion,
} from '../useStrategyLab';

vi.mock('../../services/strategyLabApi', () => ({
  strategyLabApi: {
    getExperiments: vi.fn().mockResolvedValue({
      experiments: [
        { id: 1, name: 'Test Experiment', status: 'draft', hypothesis: 'Test hypothesis' },
      ],
    }),
    getExperiment: vi.fn().mockResolvedValue({
      experiment: { id: 1, name: 'Test Experiment', status: 'draft' },
      runs: [],
    }),
    createExperiment: vi.fn().mockResolvedValue({ id: 2, name: 'New Exp', status: 'draft' }),
    getRuns: vi.fn().mockResolvedValue({
      runs: [{ id: 1, status: 'completed', engine_version: 'v1.0', metrics_count: 10 }],
    }),
    getRun: vi.fn().mockResolvedValue({ id: 1, status: 'completed', engine_version: 'v1.0' }),
    compareRuns: vi.fn().mockResolvedValue({
      comparison: {
        metrics: [{ name: 'Sharpe', run_a: 1.5, run_b: 1.2, delta: 0.3, p_value: 0.02 }],
        summary: { total_metrics: 1, significant_count: 1, insufficient_count: 0 },
      },
    }),
    createRun: vi.fn().mockResolvedValue({ id: 2, status: 'pending' }),
    getStrategyVersions: vi.fn().mockResolvedValue({
      versions: [{ id: 1, label: 'v1.0.0' }],
    }),
    getStrategyVersion: vi.fn().mockResolvedValue({ id: 1, label: 'v1.0.0' }),
    createStrategyVersion: vi.fn().mockResolvedValue({ id: 3, label: 'v2.0.0' }),
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

describe('useExperiments', () => {
  it('has correct query key shape', () => {
    const { result } = renderHook(() => useExperiments(), {
      wrapper: createWrapper(),
    });
    expect(result.current).toBeDefined();
    expect(result.current.data).toBeUndefined();
  });

  it('calls getExperiments', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    renderHook(() => useExperiments(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(strategyLabApi.getExperiments).toHaveBeenCalled();
    });
  });

  it('returns experiments data on success', async () => {
    const { result } = renderHook(() => useExperiments(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data.experiments).toHaveLength(1);
  });
});

describe('useExperiment', () => {
  it('is not enabled when id is null', () => {
    const { result } = renderHook(() => useExperiment(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('is not enabled when id is undefined', () => {
    const { result } = renderHook(() => useExperiment(undefined), {
      wrapper: createWrapper(),
    });
    expect(result.current.data).toBeUndefined();
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('calls getExperiment when id is provided', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    renderHook(() => useExperiment(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(strategyLabApi.getExperiment).toHaveBeenCalledWith(1);
    });
  });

  it('returns experiment data on success', async () => {
    const { result } = renderHook(() => useExperiment(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data.experiment.id).toBe(1);
  });
});

describe('useCreateExperiment', () => {
  it('calls createExperiment on mutation', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    const { result } = renderHook(() => useCreateExperiment(), {
      wrapper: createWrapper(),
    });
    result.current.mutate({ name: 'New Exp', hypothesis: 'Test' });
    await waitFor(() => {
      expect(strategyLabApi.createExperiment).toHaveBeenCalledWith({ name: 'New Exp', hypothesis: 'Test' });
    });
  });

  it('invalidates experiments query on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    // eslint-disable-next-line react/prop-types
    function Wrapper({ children }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );
    }

    queryClient.setQueryData(['strategy-lab', 'experiments'], { experiments: [] });

    const { result } = renderHook(() => useCreateExperiment(), {
      wrapper: Wrapper,
    });

    const stateBefore = queryClient.getQueryState(['strategy-lab', 'experiments']);
    expect(stateBefore).toBeDefined();
    expect(stateBefore.isInvalidated).toBe(false);

    result.current.mutate({ name: 'New Exp', hypothesis: 'Test' });
    await waitFor(() => {
      const state = queryClient.getQueryState(['strategy-lab', 'experiments']);
      expect(state.isInvalidated).toBe(true);
    });
  });
});

describe('useRuns', () => {
  it('calls getRuns', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    renderHook(() => useRuns(), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(strategyLabApi.getRuns).toHaveBeenCalled();
    });
  });
});

describe('useRun', () => {
  it('is not enabled when id is null', () => {
    const { result } = renderHook(() => useRun(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('calls getRun when id is provided', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    renderHook(() => useRun(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(strategyLabApi.getRun).toHaveBeenCalledWith(1);
    });
  });
});

describe('useRunComparison', () => {
  it('is not enabled when either id is null', () => {
    const { result } = renderHook(() => useRunComparison(1, null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe('idle');

    const { result: result2 } = renderHook(() => useRunComparison(null, 1), {
      wrapper: createWrapper(),
    });
    expect(result2.current.fetchStatus).toBe('idle');
  });

  it('calls compareRuns when both ids are provided', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    renderHook(() => useRunComparison(1, 2), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(strategyLabApi.compareRuns).toHaveBeenCalledWith(1, 2);
    });
  });

  it('returns comparison data on success', async () => {
    const { result } = renderHook(() => useRunComparison(1, 2), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(result.current.data.comparison.metrics).toHaveLength(1);
  });
});

describe('useCreateRun', () => {
  it('calls createRun on mutation', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    const { result } = renderHook(() => useCreateRun(), {
      wrapper: createWrapper(),
    });
    result.current.mutate({ experiment_id: 1, strategy_version_id: 1 });
    await waitFor(() => {
      expect(strategyLabApi.createRun).toHaveBeenCalledWith({ experiment_id: 1, strategy_version_id: 1 });
    });
  });

  it('invalidates runs and experiment queries on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    // eslint-disable-next-line react/prop-types
    function Wrapper({ children }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );
    }

    queryClient.setQueryData(['strategy-lab', 'runs'], { runs: [] });
    queryClient.setQueryData(['strategy-lab', 'experiment'], { experiment: {} });

    const { result } = renderHook(() => useCreateRun(), {
      wrapper: Wrapper,
    });

    expect(queryClient.getQueryState(['strategy-lab', 'runs']).isInvalidated).toBe(false);
    expect(queryClient.getQueryState(['strategy-lab', 'experiment']).isInvalidated).toBe(false);

    result.current.mutate({ experiment_id: 1, strategy_version_id: 1 });
    await waitFor(() => {
      expect(queryClient.getQueryState(['strategy-lab', 'runs']).isInvalidated).toBe(true);
      expect(queryClient.getQueryState(['strategy-lab', 'experiment']).isInvalidated).toBe(true);
    });
  });
});

describe('useStrategyVersions', () => {
  it('is not enabled when strategyId is null', () => {
    const { result } = renderHook(() => useStrategyVersions(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe('idle');
  });

  it('calls getStrategyVersions when strategyId is provided', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    renderHook(() => useStrategyVersions(1), {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(strategyLabApi.getStrategyVersions).toHaveBeenCalledWith(1);
    });
  });
});

describe('useStrategyVersion', () => {
  it('is not enabled when id is null', () => {
    const { result } = renderHook(() => useStrategyVersion(null), {
      wrapper: createWrapper(),
    });
    expect(result.current.fetchStatus).toBe('idle');
  });
});

describe('useCreateStrategyVersion', () => {
  it('calls createStrategyVersion on mutation', async () => {
    const { strategyLabApi } = await import('../../services/strategyLabApi');
    const { result } = renderHook(() => useCreateStrategyVersion(), {
      wrapper: createWrapper(),
    });
    result.current.mutate({ label: 'v2.0.0', code: '...' });
    await waitFor(() => {
      expect(strategyLabApi.createStrategyVersion).toHaveBeenCalledWith({ label: 'v2.0.0', code: '...' });
    });
  });

  it('invalidates versions query on success', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    // eslint-disable-next-line react/prop-types
    function Wrapper({ children }) {
      return (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      );
    }

    queryClient.setQueryData(['strategy-lab', 'versions'], { versions: [] });

    const { result } = renderHook(() => useCreateStrategyVersion(), {
      wrapper: Wrapper,
    });

    expect(queryClient.getQueryState(['strategy-lab', 'versions']).isInvalidated).toBe(false);

    result.current.mutate({ label: 'v2.0.0', code: '...' });
    await waitFor(() => {
      expect(queryClient.getQueryState(['strategy-lab', 'versions']).isInvalidated).toBe(true);
    });
  });
});
