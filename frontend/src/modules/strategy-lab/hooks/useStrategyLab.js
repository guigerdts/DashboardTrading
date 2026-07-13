import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { strategyLabApi } from '../services/strategyLabApi';

// Strategy Versions
export function useStrategyVersions(strategyId) {
  return useQuery({
    queryKey: ['strategy-lab', 'versions', strategyId],
    queryFn: ({ signal }) => strategyLabApi.getStrategyVersions(strategyId),
    enabled: !!strategyId,
  });
}

export function useStrategyVersion(id) {
  return useQuery({
    queryKey: ['strategy-lab', 'version', id],
    queryFn: ({ signal }) => strategyLabApi.getStrategyVersion(id),
    enabled: !!id,
  });
}

// Experiments
export function useExperiments() {
  return useQuery({
    queryKey: ['strategy-lab', 'experiments'],
    queryFn: ({ signal }) => strategyLabApi.getExperiments(),
  });
}

export function useExperiment(id) {
  return useQuery({
    queryKey: ['strategy-lab', 'experiment', id],
    queryFn: ({ signal }) => strategyLabApi.getExperiment(id),
    enabled: !!id,
  });
}

// Runs
export function useRuns() {
  return useQuery({
    queryKey: ['strategy-lab', 'runs'],
    queryFn: ({ signal }) => strategyLabApi.getRuns(),
  });
}

export function useRun(id) {
  return useQuery({
    queryKey: ['strategy-lab', 'run', id],
    queryFn: ({ signal }) => strategyLabApi.getRun(id),
    enabled: !!id,
  });
}

export function useRunComparison(runId, baselineId) {
  return useQuery({
    queryKey: ['strategy-lab', 'comparison', runId, baselineId],
    queryFn: ({ signal }) => strategyLabApi.compareRuns(runId, baselineId),
    enabled: !!runId && !!baselineId,
  });
}

// Mutations
export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => strategyLabApi.createExperiment(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategy-lab', 'experiments'] }),
  });
}

export function useCreateRun() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => strategyLabApi.createRun(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['strategy-lab', 'runs'] });
      queryClient.invalidateQueries({ queryKey: ['strategy-lab', 'experiment'] });
    },
  });
}

export function useCreateStrategyVersion() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data) => strategyLabApi.createStrategyVersion(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['strategy-lab', 'versions'] }),
  });
}
