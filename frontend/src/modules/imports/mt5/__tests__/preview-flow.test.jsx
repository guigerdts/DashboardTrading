import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ImportPage from '../pages/ImportPage';

// Mock the importApi module so no real HTTP calls are made
vi.mock('../api/importApi', () => ({
  importApi: {
    preview: vi.fn(),
    confirm: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

function renderPage() {
  return render(<ImportPage />, { wrapper: createWrapper() });
}

async function selectFile() {
  const file = new File(['content'], 'test.csv', { type: 'text/csv' });
  const fileInput = document.querySelector('input[type="file"]');
  await userEvent.upload(fileInput, file);
}

describe('preview flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('successful preview renders PreviewTable with rows', async () => {
    const { importApi } = await import('../api/importApi');
    const previewData = {
      total_rows: 3,
      valid_rows: 2,
      invalid_rows: 1,
      rows: [
        { row_index: 1, broker_ticket: '1001', status: 'valid', errors: [] },
        { row_index: 2, broker_ticket: '1002', status: 'valid', errors: [] },
        { row_index: 3, broker_ticket: '1003', status: 'invalid', errors: ['Bad volume'] },
      ],
    };
    importApi.preview.mockResolvedValue(previewData);

    renderPage();
    await selectFile();

    // Click Preview Import
    const previewBtn = await screen.findByText('Preview Import');
    await userEvent.click(previewBtn);

    // Wait for PreviewTable to appear
    await waitFor(() => {
      expect(screen.getByText(/2 valid/)).toBeInTheDocument();
      expect(screen.getByText(/1 invalid/)).toBeInTheDocument();
      expect(screen.getByText(/3 total/)).toBeInTheDocument();
    });

    // Rows rendered
    expect(screen.getByText('1001')).toBeInTheDocument();
    expect(screen.getByText('1002')).toBeInTheDocument();
    expect(screen.getByText('1003')).toBeInTheDocument();
    // Badge text — "valid" appears in summary bar too, use getAllByText
    const validBadges = screen.getAllByText('valid');
    expect(validBadges.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('invalid')).toBeInTheDocument();
  });

  it('failed preview shows ErrorFallback', async () => {
    const { importApi } = await import('../api/importApi');
    // Use a distinct error message — 'Failed to load data' is filtered
    // by getErrorMessage guard and falls through to 'Server error'
    importApi.preview.mockRejectedValue(new Error('Bad gateway'));

    renderPage();
    await selectFile();

    const previewBtn = await screen.findByText('Preview Import');
    await userEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText('Bad gateway')).toBeInTheDocument();
    });

    // Retry button visible
    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('retry after preview error calls preview mutation again', async () => {
    const { importApi } = await import('../api/importApi');
    importApi.preview.mockRejectedValueOnce(new Error('First attempt failed'));
    importApi.preview.mockResolvedValueOnce({
      total_rows: 1,
      valid_rows: 1,
      invalid_rows: 0,
      rows: [{ row_index: 1, broker_ticket: '2001', status: 'valid', errors: [] }],
    });

    renderPage();
    await selectFile();

    // First click — fails
    const previewBtn = await screen.findByText('Preview Import');
    await userEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText('First attempt failed')).toBeInTheDocument();
    });

    // Retry
    const retryBtn = screen.getByText('Retry');
    await userEvent.click(retryBtn);

    // Now succeeds
    await waitFor(() => {
      expect(screen.getByText(/1 valid/)).toBeInTheDocument();
    });

    expect(importApi.preview).toHaveBeenCalledTimes(2);
  });

  it('preview with 0 valid rows shows table but Confirm disabled', async () => {
    const { importApi } = await import('../api/importApi');
    const previewData = {
      total_rows: 2,
      valid_rows: 0,
      invalid_rows: 2,
      rows: [
        { row_index: 1, broker_ticket: '3001', status: 'invalid', errors: ['Bad volume'] },
        { row_index: 2, broker_ticket: '3002', status: 'invalid', errors: ['Missing ticket'] },
      ],
    };
    importApi.preview.mockResolvedValue(previewData);

    renderPage();
    await selectFile();

    const previewBtn = await screen.findByText('Preview Import');
    await userEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText(/0 valid/)).toBeInTheDocument();
    });

    // Confirm button should be rendered but disabled (canConfirm requires valid_rows > 0)
    const confirmBtn = screen.getByText('Confirm Import');
    expect(confirmBtn).toBeDisabled();
  });

  it('preview with 0 total rows shows "No rows found"', async () => {
    const { importApi } = await import('../api/importApi');
    const previewData = {
      total_rows: 0,
      valid_rows: 0,
      invalid_rows: 0,
      rows: [],
    };
    importApi.preview.mockResolvedValue(previewData);

    renderPage();
    await selectFile();

    const previewBtn = await screen.findByText('Preview Import');
    await userEvent.click(previewBtn);

    await waitFor(() => {
      expect(screen.getByText('No rows found in the CSV file')).toBeInTheDocument();
    });

    // Confirm button is rendered but disabled (valid_rows is 0)
    const confirmBtn = screen.getByText('Confirm Import');
    expect(confirmBtn).toBeDisabled();
  });
});
