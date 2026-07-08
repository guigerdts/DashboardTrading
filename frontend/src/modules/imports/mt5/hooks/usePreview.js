import { useMutation } from '@tanstack/react-query';
import { importApi } from '../api/importApi';

export function usePreview() {
  return useMutation({
    mutationFn: (file) => importApi.preview(file),
  });
}
