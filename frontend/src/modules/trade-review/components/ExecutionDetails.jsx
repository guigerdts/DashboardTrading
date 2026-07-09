import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { formatCurrency, formatDate } from '../../analytics/utils/formatters';

export function ExecutionDetails({ data, isLoading }) {
  if (isLoading || !data) {
    return (
      <Card title="Execution">
        <div className="space-y-2">
          <Skeleton variant="text" width="90%" />
          <Skeleton variant="text" width="70%" />
          <Skeleton variant="text" width="80%" />
        </div>
      </Card>
    );
  }

  return (
    <Card title="Execution">
      <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-3">
        <div>
          <span className="text-gray-500">Entry Price</span>
          <p className="font-medium text-gray-900">{formatCurrency(data.entry_price)}</p>
        </div>
        <div>
          <span className="text-gray-500">Exit Price</span>
          <p className="font-medium text-gray-900">
            {data.exit_price != null ? formatCurrency(data.exit_price) : '\u2014'}
          </p>
        </div>
        <div>
          <span className="text-gray-500">Quantity</span>
          <p className="font-medium text-gray-900">{data.quantity}</p>
        </div>
        <div>
          <span className="text-gray-500">Entry Date</span>
          <p className="font-medium text-gray-900">{formatDate(data.entry_datetime)}</p>
        </div>
        <div>
          <span className="text-gray-500">Exit Date</span>
          <p className="font-medium text-gray-900">
            {data.exit_datetime ? formatDate(data.exit_datetime) : '\u2014'}
          </p>
        </div>
        <div>
          <span className="text-gray-500">Duration</span>
          <p className="font-medium text-gray-900">
            {data.duration_hours != null ? `${data.duration_hours.toFixed(1)} hours` : 'Open'}
          </p>
        </div>
      </div>
    </Card>
  );
}
