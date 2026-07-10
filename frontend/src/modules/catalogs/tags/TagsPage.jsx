import { useCatalogList, useCatalogCreate, useCatalogUpdate, useCatalogArchive } from '../hooks/useCatalog';
import { CatalogAdmin } from '../shared/CatalogAdmin';

const TAG_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'category', label: 'Category' },
  { key: 'color', label: 'Color' },
  { key: 'description', label: 'Description' },
  { key: 'actions', label: 'Actions' },
];

function tagFieldRenderer(item, field) {
  if (field === 'color') {
    return item.color ? (
      <span className="inline-flex items-center gap-1.5">
        <span
          className="inline-block h-3 w-3 rounded-full"
          style={{ backgroundColor: item.color }}
        />
        <span className="text-xs text-gray-500">{item.color}</span>
      </span>
    ) : (
      '\u2014'
    );
  }
  return item[field] ?? '\u2014';
}

const tagExtraFields = (
  <>
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-500">Category</label>
      <input
        type="text"
        name="category"
        className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
        placeholder="Optional category..."
      />
    </div>
    <div>
      <label className="mb-1 block text-xs font-medium text-gray-500">Color</label>
      <div className="flex gap-2">
        <input
          type="color"
          name="color"
          className="h-9 w-9 cursor-pointer rounded border border-gray-300"
        />
        <input
          type="text"
          name="color"
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          placeholder="#hex or CSS color name..."
        />
      </div>
    </div>
  </>
);

export default function TagsPage() {
  return (
    <CatalogAdmin
      entity="tag"
      title="Tags"
      description="Manage tags for trade classification — create, edit, or archive them."
      columns={TAG_COLUMNS}
      listQuery={useCatalogList('tags')}
      createMutation={useCatalogCreate('tags')}
      updateMutation={useCatalogUpdate('tags')}
      archiveMutation={useCatalogArchive('tags')}
      extraFields={tagExtraFields}
      fieldRenderer={tagFieldRenderer}
    />
  );
}
