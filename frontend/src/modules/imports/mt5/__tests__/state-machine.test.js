import { describe, it, expect } from 'vitest';
import { importReducer } from '../hooks/useImportFlow';

// Helper to create a valid mock File
function validFile(name = 'test.csv') {
  return new File(['content'], name, { type: 'text/csv' });
}

describe('importReducer — state machine', () => {
  describe('initial state', () => {
    it('starts as idle', () => {
      const state = importReducer(undefined, { type: '@@INIT' });
      expect(state.state).toBe('idle');
      expect(state.file).toBeNull();
      expect(state.validationError).toBeNull();
      expect(state.previewData).toBeNull();
      expect(state.confirmData).toBeNull();
    });
  });

  describe('SET_FILE transitions', () => {
    it('idle → file-selected with valid file', () => {
      const initial = importReducer(undefined, { type: '@@INIT' });
      const file = validFile();
      const next = importReducer(initial, { type: 'SET_FILE', file });
      expect(next.state).toBe('file-selected');
      expect(next.file).toBe(file);
      expect(next.validationError).toBeNull();
    });

    it('stays in current state on invalid file and reports error', () => {
      const initial = importReducer(undefined, { type: '@@INIT' });
      const badFile = new File(['content'], 'bad.xlsx', { type: 'application/vnd.ms-excel' });
      const next = importReducer(initial, { type: 'SET_FILE', file: badFile });
      // State unchanged
      expect(next.state).toBe('idle');
      expect(next.validationError).toBe('File must be a .csv');
      expect(next.file).toBeNull();
    });
  });

  describe('happy path transitions', () => {
    it('file-selected → previewLoading (on PREVIEW)', () => {
      const file = validFile();
      const fileSelected = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(fileSelected, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      expect(loading.state).toBe('previewLoading');
      expect(loading.previewError).toBeNull();
    });

    it('previewLoading → previewReady (on PREVIEW_SUCCESS)', () => {
      const previewData = { total_rows: 5, valid_rows: 5, invalid_rows: 0, rows: [] };
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: previewData });
      expect(ready.state).toBe('previewReady');
      expect(ready.previewData).toEqual(previewData);
    });

    it('previewLoading → previewError (on PREVIEW_ERROR)', () => {
      const error = new Error('Server error');
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const errState = importReducer(loading, { type: 'PREVIEW_ERROR', error });
      expect(errState.state).toBe('previewError');
      expect(errState.previewError).toBe(error);
    });

    it('previewReady → confirmLoading (on CONFIRM)', () => {
      const previewData = { total_rows: 5, valid_rows: 5, invalid_rows: 0, rows: [] };
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: previewData });
      const confirmLoading = importReducer(ready, { type: 'CONFIRM' });
      expect(confirmLoading.state).toBe('confirmLoading');
      expect(confirmLoading.confirmError).toBeNull();
    });

    it('confirmLoading → confirmSuccess (on CONFIRM_SUCCESS)', () => {
      const confirmData = { total_rows: 5, imported_rows: 5, skipped_rows: 0, error_rows: 0, rows: [] };
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 5, valid_rows: 5, invalid_rows: 0, rows: [] } });
      const confirmLoading = importReducer(ready, { type: 'CONFIRM' });
      const success = importReducer(confirmLoading, { type: 'CONFIRM_SUCCESS', data: confirmData });
      expect(success.state).toBe('confirmSuccess');
      expect(success.confirmData).toEqual(confirmData);
    });

    it('confirmLoading → confirmError (on CONFIRM_ERROR)', () => {
      const error = new Error('Server error');
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 5, valid_rows: 5, invalid_rows: 0, rows: [] } });
      const confirmLoading = importReducer(ready, { type: 'CONFIRM' });
      const errState = importReducer(confirmLoading, { type: 'CONFIRM_ERROR', error });
      expect(errState.state).toBe('confirmError');
      expect(errState.confirmError).toBe(error);
    });
  });

  describe('retry transitions', () => {
    it('previewError → previewLoading (retry)', () => {
      const error = new Error('Server error');
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const errState = importReducer(loading, { type: 'PREVIEW_ERROR', error });
      const retry = importReducer(errState, { type: 'PREVIEW' });
      expect(retry.state).toBe('previewLoading');
      expect(retry.previewError).toBeNull();
    });

    it('confirmError → confirmLoading (retry)', () => {
      const error = new Error('Server error');
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 5, valid_rows: 5, invalid_rows: 0, rows: [] } });
      const confirmLoading = importReducer(ready, { type: 'CONFIRM' });
      const errState = importReducer(confirmLoading, { type: 'CONFIRM_ERROR', error });
      const retry = importReducer(errState, { type: 'CONFIRM' });
      expect(retry.state).toBe('confirmLoading');
      expect(retry.confirmError).toBeNull();
    });
  });

  describe('forbidden transitions are no-ops', () => {
    it('idle → CONFIRM is a no-op', () => {
      const initial = importReducer(undefined, { type: '@@INIT' });
      const result = importReducer(initial, { type: 'CONFIRM' });
      expect(result.state).toBe('idle');
    });

    it('previewLoading → CONFIRM is a no-op', () => {
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const result = importReducer(loading, { type: 'CONFIRM' });
      expect(result.state).toBe('previewLoading');
    });

    it('previewLoading → CONFIRM_SUCCESS is a no-op', () => {
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const result = importReducer(loading, { type: 'CONFIRM_SUCCESS', data: {} });
      expect(result.state).toBe('previewLoading');
    });

    it('previewReady → CONFIRM_SUCCESS is a no-op', () => {
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 1, valid_rows: 1, invalid_rows: 0, rows: [] } });
      const result = importReducer(ready, { type: 'CONFIRM_SUCCESS', data: {} });
      expect(result.state).toBe('previewReady');
    });

    it('confirmSuccess → PREVIEW is a no-op', () => {
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 1, valid_rows: 1, invalid_rows: 0, rows: [] } });
      const confirmLoading = importReducer(ready, { type: 'CONFIRM' });
      const success = importReducer(confirmLoading, { type: 'CONFIRM_SUCCESS', data: { total_rows: 1, imported_rows: 1, skipped_rows: 0, error_rows: 0, rows: [] } });
      const result = importReducer(success, { type: 'PREVIEW' });
      expect(result.state).toBe('confirmSuccess');
    });

    it('unknown action type is a no-op', () => {
      const initial = importReducer(undefined, { type: '@@INIT' });
      const result = importReducer(initial, { type: 'UNKNOWN' });
      expect(result.state).toBe('idle');
    });
  });

  describe('file change from previewReady', () => {
    it('resets to file-selected and clears preview/confirm data', () => {
      const file1 = validFile('first.csv');
      const file2 = validFile('second.csv');
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile1 = importReducer(base, { type: 'SET_FILE', file: file1 });
      const loading = importReducer(withFile1, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 5, valid_rows: 5, invalid_rows: 0, rows: [] } });
      const changed = importReducer(ready, { type: 'SET_FILE', file: file2 });
      expect(changed.state).toBe('file-selected');
      expect(changed.file).toBe(file2);
      expect(changed.previewData).toBeNull();
      expect(changed.confirmData).toBeNull();
      expect(changed.previewError).toBeNull();
      expect(changed.confirmError).toBeNull();
    });
  });

  describe('RESET', () => {
    it('resets from previewReady to idle', () => {
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 5, valid_rows: 5, invalid_rows: 0, rows: [] } });
      const reset = importReducer(ready, { type: 'RESET' });
      expect(reset.state).toBe('idle');
      expect(reset.file).toBeNull();
      expect(reset.previewData).toBeNull();
      expect(reset.confirmData).toBeNull();
    });

    it('resets from confirmSuccess to idle', () => {
      const file = validFile();
      const base = importReducer(undefined, { type: '@@INIT' });
      const withFile = importReducer(base, { type: 'SET_FILE', file });
      const loading = importReducer(withFile, { type: 'PREVIEW' });
      const ready = importReducer(loading, { type: 'PREVIEW_SUCCESS', data: { total_rows: 1, valid_rows: 1, invalid_rows: 0, rows: [] } });
      const confirmLoading = importReducer(ready, { type: 'CONFIRM' });
      const success = importReducer(confirmLoading, { type: 'CONFIRM_SUCCESS', data: { total_rows: 1, imported_rows: 1, skipped_rows: 0, error_rows: 0, rows: [] } });
      const reset = importReducer(success, { type: 'RESET' });
      expect(reset.state).toBe('idle');
      expect(reset.file).toBeNull();
    });
  });
});
