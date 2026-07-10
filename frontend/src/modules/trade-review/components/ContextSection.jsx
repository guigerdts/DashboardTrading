import { useState, useEffect } from 'react';
import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { useCatalogList } from '../../catalogs/hooks/useCatalog';
import {
  useUpdateTradeStrategy,
  useUpdateTradeSetup,
  useSyncTradeTags,
  useSyncTradeMistakes,
} from '../../catalogs/hooks/useTradeContext';

function MultiSelect({ options, selectedIds, onChange, placeholder, isLoading }) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedLabels = options
    .filter((o) => selectedIds.includes(o.id))
    .map((o) => o.name);

  const toggle = (id) => {
    const next = selectedIds.includes(id)
      ? selectedIds.filter((i) => i !== id)
      : [...selectedIds, id];
    onChange(next);
  };

  if (isLoading) {
    return <Skeleton variant="text" width="100%" />;
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex min-h-[2.25rem] w-full flex-wrap items-center gap-1 rounded border border-gray-300 px-2 py-1.5 text-left text-sm hover:border-gray-400"
      >
        {selectedLabels.length > 0 ? (
          selectedLabels.map((label) => (
            <span
              key={label}
              className="inline-flex items-center rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700"
            >
              {label}
            </span>
          ))
        ) : (
          <span className="text-gray-400">{placeholder}</span>
        )}
      </button>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute left-0 right-0 z-20 mt-1 max-h-48 overflow-y-auto rounded border border-gray-200 bg-white shadow-lg">
            {options.length === 0 ? (
              <p className="p-3 text-sm text-gray-400">No options available</p>
            ) : (
              options.map((opt) => (
                <label
                  key={opt.id}
                  className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-gray-50"
                >
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(opt.id)}
                    onChange={() => toggle(opt.id)}
                    className="rounded border-gray-300"
                  />
                  <span>{opt.name}</span>
                </label>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

function SingleSelect({ options, value, onChange, placeholder, isLoading }) {
  if (isLoading) {
    return <Skeleton variant="text" width="100%" />;
  }

  return (
    <select
      value={value ?? ''}
      onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
      className="w-full rounded border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
    >
      <option value="">{placeholder}</option>
      {options.map((opt) => (
        <option key={opt.id} value={opt.id}>
          {opt.name}
        </option>
      ))}
    </select>
  );
}

export function ContextSection({ data, isLoading: isTradeLoading }) {
  const tradeId = data?.id;
  const [strategyId, setStrategyId] = useState(data?.strategy_id ?? null);
  const [setupId, setSetupId] = useState(data?.setup_id ?? null);
  const [tagIds, setTagIds] = useState(data?.tags?.map((t) => t.id) ?? []);
  const [mistakeIds, setMistakeIds] = useState(data?.mistakes?.map((m) => m.id) ?? []);
  const [dirty, setDirty] = useState(false);
  const [syncError, setSyncError] = useState(null);

  const { data: strategies, isLoading: stratLoading } = useCatalogList('strategies');
  const { data: setups, isLoading: setupLoading } = useCatalogList('setups');
  const { data: tags, isLoading: tagsLoading } = useCatalogList('tags');
  const { data: mistakes, isLoading: mistakesLoading } = useCatalogList('mistakes');

  const updateStrategy = useUpdateTradeStrategy(tradeId);
  const updateSetup = useUpdateTradeSetup(tradeId);
  const syncTags = useSyncTradeTags(tradeId);
  const syncMistakes = useSyncTradeMistakes(tradeId);

  useEffect(() => {
    if (data) {
      setStrategyId(data.strategy_id ?? null);
      setSetupId(data.setup_id ?? null);
      setTagIds(data.tags?.map((t) => t.id) ?? []);
      setMistakeIds(data.mistakes?.map((m) => m.id) ?? []);
    }
  }, [data]);

  const handleSave = async () => {
    setSyncError(null);
    try {
      if (strategyId !== (data?.strategy_id ?? null)) {
        await updateStrategy.mutateAsync(strategyId);
      }
      if (setupId !== (data?.setup_id ?? null)) {
        await updateSetup.mutateAsync(setupId);
      }
      const origTagIds = data?.tags?.map((t) => t.id) ?? [];
      if (JSON.stringify(tagIds.sort()) !== JSON.stringify(origTagIds.sort())) {
        await syncTags.mutateAsync(tagIds);
      }
      const origMistakeIds = data?.mistakes?.map((m) => m.id) ?? [];
      if (JSON.stringify(mistakeIds.sort()) !== JSON.stringify(origMistakeIds.sort())) {
        await syncMistakes.mutateAsync(mistakeIds.map((id) => ({ id })));
      }
      setDirty(false);
    } catch (err) {
      setSyncError(err?.data?.detail || err.message || 'Failed to save context');
    }
  };

  const hasChanges =
    strategyId !== (data?.strategy_id ?? null) ||
    setupId !== (data?.setup_id ?? null) ||
    JSON.stringify(tagIds.sort()) !== JSON.stringify((data?.tags?.map((t) => t.id) ?? []).sort()) ||
    JSON.stringify(mistakeIds.sort()) !== JSON.stringify((data?.mistakes?.map((m) => m.id) ?? []).sort());

  const isSaving =
    updateStrategy.isPending ||
    updateSetup.isPending ||
    syncTags.isPending ||
    syncMistakes.isPending;

  if (isTradeLoading) {
    return (
      <Card title="Context">
        <div className="space-y-3">
          <Skeleton variant="text" width="50%" />
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="100%" />
        </div>
      </Card>
    );
  }

  if (!data) return null;

  return (
    <Card title="Context">
      <div className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Strategy</label>
            <SingleSelect
              options={strategies || []}
              value={strategyId}
              onChange={(val) => {
                setStrategyId(val);
                setDirty(true);
              }}
              placeholder="Select strategy..."
              isLoading={stratLoading}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-500">Setup</label>
            <SingleSelect
              options={setups || []}
              value={setupId}
              onChange={(val) => {
                setSetupId(val);
                setDirty(true);
              }}
              placeholder="Select setup..."
              isLoading={setupLoading}
            />
          </div>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">Tags</label>
          <MultiSelect
            options={tags || []}
            selectedIds={tagIds}
            onChange={(ids) => {
              setTagIds(ids);
              setDirty(true);
            }}
            placeholder="Select tags..."
            isLoading={tagsLoading}
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">Mistakes</label>
          <MultiSelect
            options={mistakes || []}
            selectedIds={mistakeIds}
            onChange={(ids) => {
              setMistakeIds(ids);
              setDirty(true);
            }}
            placeholder="Select mistakes..."
            isLoading={mistakesLoading}
          />
        </div>

        {syncError && (
          <p className="text-sm text-red-600">{syncError}</p>
        )}

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save Context'}
          </button>
        </div>
      </div>
    </Card>
  );
}
