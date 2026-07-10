import { useState } from 'react';
import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';

function defaultFieldRenderer(item, field) {
  return item[field] ?? '\u2014';
}

function defaultFormFields({ formData, extraFields, handleChange, entity }) {
  return (
    <>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">Name</label>
        <input
          type="text"
          name="name"
          value={formData.name || ''}
          onChange={handleChange}
          required
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          placeholder={`Enter ${entity} name...`}
        />
      </div>
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-500">Description</label>
        <textarea
          name="description"
          value={formData.description || ''}
          onChange={handleChange}
          rows={2}
          className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          placeholder={`Optional description...`}
        />
      </div>
      {extraFields}
    </>
  );
}

export function CatalogAdmin({
  entity,
  title,
  description,
  columns,
  listQuery,
  createMutation,
  updateMutation,
  archiveMutation,
  extraFields,
  fieldRenderer,
}) {
  const [showForm, setShowForm] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [error, setError] = useState(null);
  const [archiveError, setArchiveError] = useState(null);
  const [showArchived, setShowArchived] = useState(false);

  const { data: items, isLoading, isError, error: queryError, refetch } = listQuery;
  const create = createMutation;
  const update = updateMutation;
  const archive = archiveMutation;

  const displayed = showArchived
    ? (items || [])
    : (items || []).filter((item) => item.is_active !== false);

  const resetForm = () => {
    setFormData({ name: '', description: '' });
    setEditingItem(null);
    setShowForm(false);
    setError(null);
  };

  const openCreate = () => {
    resetForm();
    setShowForm(true);
  };

  const openEdit = (item) => {
    const base = {
      name: item.name || '',
      description: item.description || '',
    };
    // Only include category/color for tag entities that have them
    if (item.category !== undefined || item.color !== undefined) {
      base.category = item.category || '';
      base.color = item.color || '';
    }
    setFormData(base);
    setEditingItem(item);
    setShowForm(true);
    setError(null);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    const payload = { name: formData.name, description: formData.description || null };
    if ('category' in formData) payload.category = formData.category || null;
    if ('color' in formData) payload.color = formData.color || null;

    try {
      if (editingItem) {
        await update.mutateAsync({ id: editingItem.id, ...payload });
      } else {
        await create.mutateAsync(payload);
      }
      resetForm();
    } catch (err) {
      setError(err?.data?.detail?.[0]?.msg || err?.data?.detail || err.message || 'Operation failed');
    }
  };

  const handleArchive = async (item) => {
    try {
      await archive.mutateAsync(item.id);
      setArchiveError(null);
    } catch (err) {
      setArchiveError(err?.data?.detail || err.message || 'Failed to archive');
    }
  };

  const renderRow = columns.map((col) => {
    if (col.key === 'actions') {
      return { key: 'actions', render: (item) => (
        <div className="flex gap-2">
          <button
            onClick={() => openEdit(item)}
            className="text-xs text-blue-600 hover:text-blue-700"
          >
            Edit
          </button>
          <button
            onClick={() => handleArchive(item)}
            className="text-xs text-red-600 hover:text-red-700"
          >
            {item.is_active === false ? 'Restore' : 'Archive'}
          </button>
        </div>
      )};
    }
    return {
      key: col.key,
      render: (item) => {
        const renderer = fieldRenderer || defaultFieldRenderer;
        return renderer(item, col.key);
      },
    };
  });

  const render = fieldRenderer || defaultFieldRenderer;

  return (
    <div>
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-900">{title}</h2>
            {description && <p className="mt-1 text-sm text-gray-500">{description}</p>}
          </div>
          <button
            onClick={openCreate}
            className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700"
          >
            + New {entity}
          </button>
        </div>
      </div>

      {showForm && (
        <Card className="mb-6">
          <h3 className="mb-4 text-sm font-medium text-gray-700">
            {editingItem ? `Edit ${entity}` : `Create ${entity}`}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            {defaultFormFields({ formData, extraFields, handleChange, entity })}
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={create.isPending || update.isPending}
                className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {create.isPending || update.isPending
                  ? 'Saving...'
                  : editingItem
                    ? 'Update'
                    : 'Create'}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="rounded border border-gray-300 px-4 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        </Card>
      )}

      {archiveError && (
        <div className="mb-4 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {archiveError}
        </div>
      )}

      {isError && (
        <ErrorFallback message={queryError?.message || `Failed to load ${entity}s`} onRetry={refetch} />
      )}

      {isLoading && (
        <Card>
          <div className="space-y-3">
            <Skeleton variant="text" width="60%" />
            <Skeleton variant="text" width="100%" />
            <Skeleton variant="text" width="100%" />
          </div>
        </Card>
      )}

      {!isLoading && !isError && (
        <>
          <div className="mb-4 flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={showArchived}
                onChange={(e) => setShowArchived(e.target.checked)}
                className="rounded border-gray-300"
              />
              Show archived items
            </label>
            <span className="text-xs text-gray-400">
              {items ? items.length : 0} total
              {!showArchived && ` (${displayed.length} active)`}
            </span>
          </div>

          {displayed.length === 0 ? (
            <Card>
              <p className="py-4 text-center text-sm text-gray-400">
                No {title?.toLowerCase() || entity} found. Create one to get started.
              </p>
            </Card>
          ) : (
            <Card className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    {columns.map((col) => (
                      <th key={col.key} className="px-3 py-2">
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {displayed.map((item) => (
                    <tr
                      key={item.id}
                      className={`hover:bg-gray-50 ${item.is_active === false ? 'opacity-50' : ''}`}
                    >
                      {columns.map((col) => (
                        <td key={col.key} className="px-3 py-2.5 text-gray-900">
                          {col.key === 'actions'
                            ? (() => {
                                const colDef = renderRow.find((r) => r.key === 'actions');
                                return colDef ? colDef.render(item) : null;
                              })()
                            : render(item, col.key)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
