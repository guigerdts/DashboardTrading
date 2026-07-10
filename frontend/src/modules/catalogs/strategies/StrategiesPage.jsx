import { useCatalogList, useCatalogCreate, useCatalogUpdate, useCatalogArchive } from '../hooks/useCatalog';
import { CatalogAdmin } from '../shared/CatalogAdmin';

const STRATEGY_COLUMNS = [
  { key: 'name', label: 'Name' },
  { key: 'description', label: 'Description' },
  { key: 'actions', label: 'Actions' },
];

export default function StrategiesPage() {
  return (
    <CatalogAdmin
      entity="strategy"
      title="Strategies"
      description="Manage your trading strategies — create, edit, or archive them."
      columns={STRATEGY_COLUMNS}
      listQuery={useCatalogList('strategies')}
      createMutation={useCatalogCreate('strategies')}
      updateMutation={useCatalogUpdate('strategies')}
      archiveMutation={useCatalogArchive('strategies')}
    />
  );
}
