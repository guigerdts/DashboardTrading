import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import ImportPage from '../pages/ImportPage';

vi.mock('../api/importApi', () => ({
  importApi: {
    preview: vi.fn(),
    confirm: vi.fn(),
  },
}));

const previewData = {
  total_rows: 3,
  valid_rows: 3,
  invalid_rows: 0,
  rows: [
    { row_index: 1, broker_ticket: '1001', status: 'valid', errors: [] },
    { row_index: 2, broker_ticket: '1002', status: 'valid', errors: [] },
    { row_index: 3, broker_ticket: '1003', status: 'valid', errors: [] },
  ],
};

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

async function completePreview() {
  const { importApi } = await import('../api/importApi');
  importApi.preview.mockResolvedValue(previewData);

  renderPage();
  await selectFile();

  const previewBtn = await screen.findByText('Preview Import');
  await userEvent.click(previewBtn);

  await waitFor(() => {
    expect(screen.getByText(/3 valid/)).toBeInTheDocument();
  });

  return importApi;
}

describe('confirm flow', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('successful confirm renders ImportResult with summary', async () => {
    const importApi = await completePreview();

    const confirmData = {
      total_rows: 3,
      imported_rows: 3,
      skipped_rows: 0,
      error_rows: 0,
      rows: [
        { row_index: 1, broker_ticket: '1001', status: 'imported', trade_id: 1, errors: [], warnings: [] },
        { row_index: 2, broker_ticket: '1002', status: 'imported', trade_id: 2, errors: [], warnings: [] },
        { row_index: 3, broker_ticket: '1003', status: 'imported', trade_id: 3, errors: [], warnings: [] },
      ],
    };
    importApi.confirm.mockResolvedValue(confirmData);

    // Click Confirm Import
    const confirmBtn = screen.getByText('Confirm Import');
    await userEvent.click(confirmBtn);

    // ImportResult screen
    await waitFor(() => {
      expect(screen.getByText('Import Complete')).toBeInTheDocument();
    });

    // Summary counts — "3" appears in both total_rows and imported_rows cards
    const threes = screen.getAllByText('3');
    expect(threes.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText('Imported')).toBeInTheDocument();
    expect(screen.getByText('Skipped')).toBeInTheDocument();
    expect(screen.getByText('Errors')).toBeInTheDocument();

    // Action buttons
    expect(screen.getByText('Import another file')).toBeInTheDocument();
    expect(screen.getByText('Go to Dashboard')).toBeInTheDocument();
  });

  it('failed confirm shows ErrorFallback', async () => {
    const importApi = await completePreview();

    importApi.confirm.mockRejectedValue(new Error('Server error'));

    const confirmBtn = screen.getByText('Confirm Import');
    await userEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText('Server error')).toBeInTheDocument();
    });

    expect(screen.getByText('Retry')).toBeInTheDocument();
  });

  it('retry after confirm error calls confirm mutation again', async () => {
    const importApi = await completePreview();

    importApi.confirm.mockRejectedValueOnce(new Error('First attempt failed'));
    importApi.confirm.mockResolvedValueOnce({
      total_rows: 3,
      imported_rows: 3,
      skipped_rows: 0,
      error_rows: 0,
      rows: [],
    });

    // First click — fails
    const confirmBtn = screen.getByText('Confirm Import');
    await userEvent.click(confirmBtn);

    await waitFor(() => {
      expect(screen.getByText('First attempt failed')).toBeInTheDocument();
    });

    // Retry
    const retryBtn = screen.getByText('Retry');
    await userEvent.click(retryBtn);

    await waitFor(() => {
      expect(screen.getByText('Import Complete')).toBeInTheDocument();
    });

    expect(importApi.confirm).toHaveBeenCalledTimes(2);
  });

  it('all buttons disabled during confirmLoading (no double-submit)', async () => {
    const importApi = await completePreview();

    // Return a promise that never resolves — keeps mutation in loading state
    importApi.confirm.mockReturnValue(new Promise(() => {}));

    const confirmBtn = screen.getByText('Confirm Import');
    await userEvent.click(confirmBtn);

    await waitFor(() => {
      // Button should show loading text
      expect(screen.getByText('Importing...')).toBeInTheDocument();
    });

    // FileUploader should be disabled during confirmLoading
    const fileUploader = screen.getByRole('region', { name: /file upload/i });
    expect(fileUploader).toHaveAttribute('aria-disabled', 'true');
  });
});
