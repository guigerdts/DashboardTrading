import { useCatalogList, useCatalogCreate, useCatalogUpdate, useCatalogArchive } from '../hooks/useCatalog';
import { CatalogAdmin } from '../shared/CatalogAdmin';

const MISTAKE_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'actions', label: 'Actions' },
];

export default function MistakesPage() {
  return (
    <CatalogAdmin
      entity="mistake"
      title="Mistakes"
      description="Catalog common trading mistakes for post-trade review."
      columns={MISTAKE_COLUMNS}
      listQuery={useCatalogList('mistakes')}
      createMutation={useCatalogCreate('mistakes')}
      updateMutation={useCatalogUpdate('mistakes')}
      archiveMutation={useCatalogArchive('mistakes')}
    />
  );
}
