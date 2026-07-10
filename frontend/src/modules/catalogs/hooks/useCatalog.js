import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../../api/client';

export function useCatalogList(entity) {
  return useQuery({
    queryKey: [entity],
    queryFn: ({ signal }) => api.get(`/${entity}`, { signal }),
  });
}

export function useCatalogGet(entity, id) {
  return useQuery({
    queryKey: [entity, id],
    queryFn: ({ signal }) => api.get(`/${entity}/${id}`, { signal }),
    enabled: !!id,
  });
}

export function useCatalogCreate(entity) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => api.post(`/${entity}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [entity] }),
  });
}

export function useCatalogUpdate(entity) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, ...data }) => api.patch(`/${entity}/${id}`, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [entity] }),
  });
}

export function useCatalogArchive(entity) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id) => api.delete(`/${entity}/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: [entity] }),
  });
}
