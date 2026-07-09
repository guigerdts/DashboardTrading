import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { formatCurrency } from '../../analytics/utils/formatters';

export function RiskDetails({ data, isLoading }) {
  if (isLoading || !data) {
    return (
      <Card title="Risk">
        <div className="space-y-2">
          <Skeleton variant="text" width="80%" />
          <Skeleton variant="text" width="60%" />
          <Skeleton variant="text" width="70%" />
        </div>
      </Card>
    );
  }

  return (
    <Card title="Risk">
      <div className="grid grid-cols-2 gap-x-8 gap-y-3 text-sm sm:grid-cols-3">
        <div>
          <span className="text-gray-500">Stop Loss</span>
          <p className="font-medium text-gray-900">
            {data.stop_loss != null ? formatCurrency(data.stop_loss) : '\u2014'}
          </p>
        </div>
        <div>
          <span className="text-gray-500">Take Profit</span>
          <p className="font-medium text-gray-900">
            {data.take_profit != null ? formatCurrency(data.take_profit) : '\u2014'}
          </p>
        </div>
        <div>
          <span className="text-gray-500">Position Size</span>
          <p className="font-medium text-gray-900">
            {data.position_size != null ? data.position_size : '\u2014'}
          </p>
        </div>
        <div>
          <span className="text-gray-500">Commission</span>
          <p className="font-medium text-gray-900">{formatCurrency(data.commission)}</p>
        </div>
        <div>
          <span className="text-gray-500">Swap Fees</span>
          <p className="font-medium text-gray-900">{formatCurrency(data.swap_fees)}</p>
        </div>
        <div>
          <span className="text-gray-500">Risk Amount</span>
          <p className="font-medium text-gray-900">
            {data.risk_amount != null ? formatCurrency(data.risk_amount) : '\u2014'}
          </p>
        </div>
      </div>
    </Card>
  );
}
