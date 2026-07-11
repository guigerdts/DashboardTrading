import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { RiskDashboard } from '../components/RiskDashboard';

// Mock all hooks
vi.mock('../../analytics/hooks/useDashboardFilters', () => ({
  useDashboardFilters: () => ({ filters: { accountId: null, dateFrom: null, dateTo: null } }),
}));

vi.mock('../hooks/useRiskMetrics', () => ({
  useRiskMetrics: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../hooks/useExposureByAsset', () => ({
  useExposureByAsset: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../hooks/useExposureBySession', () => ({
  useExposureBySession: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../hooks/useExposureByStrategy', () => ({
  useExposureByStrategy: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

vi.mock('../hooks/useCorrelation', () => ({
  useCorrelation: () => ({
    data: null,
    isLoading: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

describe('RiskDashboard', () => {
  it('renders all child section titles', () => {
    render(
      <RiskDashboard filters={{}} />,
      { wrapper: createWrapper() },
    );
    expect(screen.getByText('Risk Metrics')).toBeInTheDocument();
    expect(screen.getByText('Exposure')).toBeInTheDocument();
    expect(screen.getByText('Asset Correlation')).toBeInTheDocument();
  });
});
