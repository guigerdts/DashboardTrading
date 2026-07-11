import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { edgeDiscoveryApi } from '../services/edge-discovery.service';

/**
 * Fetch edge rankings.
 * Auto-refetch is disabled — edge snapshots are point-in-time data.
 *
 * @param {boolean} [showInsufficient] — include edges with confidence_level 'insufficient'
 * @returns {{ data, isLoading, isError, error, refetch }}
 */
export function useEdgeRankings(showInsufficient) {
  return useQuery({
    queryKey: ['edge-discovery', 'rankings', showInsufficient],
    queryFn: () => edgeDiscoveryApi.getRankings(showInsufficient),
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}

/**
 * Mutation to generate a new edge snapshot.
 * Invalidates the rankings query on success.
 *
 * @returns {{ mutate, isPending, isError, error, data }}
 */
export function useGenerateEdge() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => edgeDiscoveryApi.generate(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['edge-discovery', 'rankings'] });
      queryClient.invalidateQueries({ queryKey: ['edge-discovery', 'snapshots'] });
    },
  });
}
