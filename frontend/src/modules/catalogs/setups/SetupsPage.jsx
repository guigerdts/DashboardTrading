import { useCatalogList, useCatalogCreate, useCatalogUpdate, useCatalogArchive } from '../hooks/useCatalog';
import { CatalogAdmin } from '../shared/CatalogAdmin';

const SETUP_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'actions', label: 'Actions' },
];

export default function SetupsPage() {
  return (
    <CatalogAdmin
      entity="setup"
      title="Setups"
      description="Define your trade setups with entry and exit criteria."
      columns={SETUP_COLUMNS}
      listQuery={useCatalogList('setups')}
      createMutation={useCatalogCreate('setups')}
      updateMutation={useCatalogUpdate('setups')}
      archiveMutation={useCatalogArchive('setups')}
    />
  );
}
