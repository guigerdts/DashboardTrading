import { useQuery } from '@tanstack/react-query';
import { edgeDiscoveryApi } from '../services/edge-discovery.service';

/**
 * Fetch detailed edge info + trades for a single group.
 * Disabled when groupId is empty.
 *
 * @param {string} groupId — the edge group_id
 * @returns {{ data, isLoading, isError, error, refetch }}
 */
export function useEdgeDetail(groupId) {
  return useQuery({
    queryKey: ['edge-discovery', 'detail', groupId],
    queryFn: () => edgeDiscoveryApi.getEdge(groupId),
    enabled: !!groupId,
    staleTime: Infinity,
    refetchOnMount: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });
}
