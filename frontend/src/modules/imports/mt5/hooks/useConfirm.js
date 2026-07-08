import { useMutation } from '@tanstack/react-query';
import { importApi } from '../api/importApi';

export function useConfirm() {
  return useMutation({
    mutationFn: (file) => importApi.confirm(file),
  });
}
