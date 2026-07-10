import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../api/client';

export function useUpdateTradeStrategy(tradeId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (strategyId) => api.patch(`/trades/${tradeId}`, { strategy_id: strategyId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trade', tradeId] }),
  });
}

export function useUpdateTradeSetup(tradeId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (setupId) => api.patch(`/trades/${tradeId}`, { setup_id: setupId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trade', tradeId] }),
  });
}

export function useSyncTradeTags(tradeId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (tagIds) => api.put(`/trades/${tradeId}/tags`, { tag_ids: tagIds }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trade', tradeId] }),
  });
}

export function useSyncTradeMistakes(tradeId) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mistakes) => api.put(`/trades/${tradeId}/mistakes`, { mistakes }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['trade', tradeId] }),
  });
}
