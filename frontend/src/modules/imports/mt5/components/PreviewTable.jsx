import { Card } from '../../../../shared/ui/Card';

export function PreviewTable({ data }) {
  const { total_rows, valid_rows, invalid_rows, rows } = data;

  if (total_rows === 0) {
    return (
      <Card title="Preview Results">
        <p className="text-sm text-gray-500">No rows found in the CSV file</p>
      </Card>
    );
  }

  return (
    <Card title="Preview Results">
      <p className="mb-3 text-sm text-gray-600">
        {valid_rows} valid / {invalid_rows} invalid / {total_rows} total
      </p>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-3 py-2 text-left font-medium text-gray-500">#</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Ticket</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Status</th>
              <th className="px-3 py-2 text-left font-medium text-gray-500">Errors</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {rows.map((row) => (
              <tr key={row.row_index}>
                <td className="px-3 py-2 text-gray-500">{row.row_index}</td>
                <td className="px-3 py-2 font-mono text-gray-900">{row.broker_ticket}</td>
                <td className="px-3 py-2">
                  {row.status === 'valid' ? (
                    <span className="inline-flex rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                      valid
                    </span>
                  ) : (
                    <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800">
                      invalid
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-gray-600">
                  {row.errors?.length ? row.errors.join(', ') : '\u2014'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
