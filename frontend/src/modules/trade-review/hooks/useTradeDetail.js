import { useQuery } from '@tanstack/react-query';
import { tradeReviewApi } from '../api/tradeReviewApi';

export function useTradeDetail(id) {
  const query = useQuery({
    queryKey: ['trades', 'detail', id],
    queryFn: ({ signal }) => tradeReviewApi.getDetail(id, { signal }),
    enabled: !!id,
    retry: false,
  });

  return {
    data: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    isNotFound: query.error?.status === 404,
    refetch: query.refetch,
  };
}
