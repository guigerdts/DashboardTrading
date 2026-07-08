import { useReducer, useCallback, useRef } from 'react';
import { useMutation } from '@tanstack/react-query';
import { importApi } from '../api/importApi';

const initialState = {
  state: 'idle',
  file: null,
  validationError: null,
  previewData: null,
  confirmData: null,
  previewError: null,
  confirmError: null,
};

function validateFile(file) {
  if (!file) return 'Please select a file';
  const name = file.name.toLowerCase();
  if (!name.endsWith('.csv')) return 'File must be a .csv';
  if (file.size > 5 * 1024 * 1024) return 'File must be ≤ 5 MB';
  return null;
}

function importReducer(state, action) {
  switch (action.type) {
    case 'SET_FILE': {
      const validationError = validateFile(action.file);

      // Invalid file — show error, stay in current state
      if (validationError) {
        return { ...state, validationError };
      }

      // File change when a file was already selected — clear preview/confirm data
      if (state.file !== null) {
        return {
          ...state,
          file: action.file,
          validationError: null,
          state: 'file-selected',
          previewData: null,
          confirmData: null,
          previewError: null,
          confirmError: null,
        };
      }

      // Fresh valid file
      return {
        ...state,
        file: action.file,
        validationError: null,
        state: 'file-selected',
      };
    }

    case 'CLEAR_FILE':
      return { ...initialState };

    case 'PREVIEW':
      if (state.state !== 'file-selected' && state.state !== 'previewError') {
        return state;
      }
      return { ...state, state: 'previewLoading', previewError: null };

    case 'PREVIEW_SUCCESS':
      if (state.state !== 'previewLoading') return state;
      return { ...state, state: 'previewReady', previewData: action.data };

    case 'PREVIEW_ERROR':
      if (state.state !== 'previewLoading') return state;
      return { ...state, state: 'previewError', previewError: action.error };

    case 'CONFIRM':
      if (state.state !== 'previewReady' && state.state !== 'confirmError') {
        return state;
      }
      return { ...state, state: 'confirmLoading', confirmError: null };

    case 'CONFIRM_SUCCESS':
      if (state.state !== 'confirmLoading') return state;
      return { ...state, state: 'confirmSuccess', confirmData: action.data };

    case 'CONFIRM_ERROR':
      if (state.state !== 'confirmLoading') return state;
      return { ...state, state: 'confirmError', confirmError: action.error };

    case 'RESET':
      return { ...initialState };

    default:
      return state;
  }
}

export function useImportFlow() {
  const [store, dispatch] = useReducer(importReducer, initialState);

  // Keep a ref to the current file to avoid stale closures in callbacks
  const fileRef = useRef(store.file);
  fileRef.current = store.file;

  const previewMutation = useMutation({
    mutationFn: (file) => importApi.preview(file),
    onSuccess: (data) => dispatch({ type: 'PREVIEW_SUCCESS', data }),
    onError: (error) => dispatch({ type: 'PREVIEW_ERROR', error }),
  });

  const confirmMutation = useMutation({
    mutationFn: (file) => importApi.confirm(file),
    onSuccess: (data) => dispatch({ type: 'CONFIRM_SUCCESS', data }),
    onError: (error) => dispatch({ type: 'CONFIRM_ERROR', error }),
  });

  const setFile = useCallback(
    (file) => dispatch({ type: 'SET_FILE', file }),
    [],
  );

  const preview = useCallback(() => {
    dispatch({ type: 'PREVIEW' });
    previewMutation.mutate(fileRef.current);
  }, [previewMutation]);

  const confirm = useCallback(() => {
    dispatch({ type: 'CONFIRM' });
    confirmMutation.mutate(fileRef.current);
  }, [confirmMutation]);

  const reset = useCallback(() => dispatch({ type: 'RESET' }), []);

  const canConfirm = store.state === 'previewReady';
  const isPreviewing = store.state === 'previewLoading';
  const isConfirming = store.state === 'confirmLoading';

  return {
    state: store.state,
    file: store.file,
    validationError: store.validationError,
    previewData: store.previewData,
    confirmData: store.confirmData,
    previewError: store.previewError,
    confirmError: store.confirmError,
    isPreviewing,
    isConfirming,
    canConfirm,
    setFile,
    preview,
    confirm,
    reset,
  };
}
