import { Card } from '../../../../shared/ui/Card';

export function ImportResult({ data, onReset, onGoToDashboard }) {
  const { total_rows, imported_rows, skipped_rows, error_rows } = data;

  return (
    <div>
      <h2 className="mb-4 text-xl font-bold text-gray-900">Import Complete</h2>
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <p className="text-2xl font-bold text-gray-900">{total_rows}</p>
          <p className="text-sm text-gray-500">Total rows</p>
        </Card>
        <Card>
          <p className="text-2xl font-bold text-green-600">{imported_rows}</p>
          <p className="text-sm text-gray-500">Imported</p>
        </Card>
        <Card>
          <p className="text-2xl font-bold text-amber-600">{skipped_rows}</p>
          <p className="text-sm text-gray-500">Skipped</p>
        </Card>
        <Card>
          <p className="text-2xl font-bold text-red-600">{error_rows}</p>
          <p className="text-sm text-gray-500">Errors</p>
        </Card>
      </div>
      <div className="flex gap-3">
        <button
          onClick={onReset}
          className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          Import another file
        </button>
        <button
          onClick={onGoToDashboard}
          className="rounded border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
        >
          Go to Dashboard
        </button>
      </div>
    </div>
  );
}
