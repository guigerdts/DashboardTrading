import { useMutation, useQueryClient } from '@tanstack/react-query';
import { tradeReviewApi } from '../api/tradeReviewApi';

export function useTradeReview(tradeId) {
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: (data) => tradeReviewApi.saveReview(tradeId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trades', 'detail', tradeId] });
    },
  });

  return {
    save: mutation.mutate,
    isSaving: mutation.isPending,
    isSuccess: mutation.isSuccess,
    error: mutation.error,
    isError: mutation.isError,
    reset: mutation.reset,
  };
}
