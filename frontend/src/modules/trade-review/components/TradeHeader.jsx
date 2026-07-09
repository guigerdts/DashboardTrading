import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency } from '../../analytics/utils/formatters';

export function TradeHeader({ data, isLoading, isError, error, onRetry }) {
  if (isError) {
    return <ErrorFallback message={error?.message || 'Failed to load trade'} onRetry={onRetry} />;
  }

  if (isLoading || !data) {
    return (
      <Card>
        <div className="space-y-3">
          <Skeleton variant="text" width="40%" />
          <div className="flex gap-4">
            <Skeleton variant="text" width="20%" />
            <Skeleton variant="text" width="15%" />
            <Skeleton variant="text" width="25%" />
          </div>
        </div>
      </Card>
    );
  }

  const pnl = data.net_pnl ?? 0;

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold text-gray-900">{data.asset_symbol || '\u2014'}</h2>
          {data.direction === 'long' ? (
            <span className="rounded bg-green-100 px-2 py-0.5 text-sm font-medium text-green-700">Long \u2191</span>
          ) : (
            <span className="rounded bg-red-100 px-2 py-0.5 text-sm font-medium text-red-700">Short \u2193</span>
          )}
          {data.status === 'closed' ? (
            <span className="rounded bg-gray-100 px-2 py-0.5 text-sm font-medium text-gray-600">Closed</span>
          ) : (
            <span className="rounded bg-green-100 px-2 py-0.5 text-sm font-medium text-green-700">Open</span>
          )}
        </div>

        <div className={`text-2xl font-bold ${pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : ''}`}>
          {data.status === 'closed' ? formatCurrency(pnl) : '\u2014'}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-8 gap-y-2 text-sm sm:grid-cols-4">
        <div>
          <span className="text-gray-500">Ticket</span>
          <p className="font-mono font-medium text-gray-900">{data.broker_ticket || '\u2014'}</p>
        </div>
        <div>
          <span className="text-gray-500">Account</span>
          <p className="font-medium text-gray-900">{data.account_name || '\u2014'}</p>
        </div>
        <div>
          <span className="text-gray-500">Return</span>
          <p className={`font-medium ${data.return_pct > 0 ? 'text-green-600' : data.return_pct < 0 ? 'text-red-600' : ''}`}>
            {data.return_pct != null ? `${data.return_pct.toFixed(2)}%` : '\u2014'}
          </p>
        </div>
        <div>
          <span className="text-gray-500">Duration</span>
          <p className="font-medium text-gray-900">
            {data.duration_hours != null ? `${data.duration_hours.toFixed(1)}h` : 'Open'}
          </p>
        </div>
      </div>
    </Card>
  );
}
