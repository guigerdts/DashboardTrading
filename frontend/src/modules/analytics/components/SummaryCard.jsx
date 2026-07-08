import { Card } from '../../../shared/ui/Card';

/**
 * Single stat card — pure visual component.
 * Receives an already-formatted value and optional color signals.
 *
 * @param {{ title: string, value: string, isPositive?: boolean, isNegative?: boolean }} props
 */
export function SummaryCard({ title, value, isPositive, isNegative }) {
  const colorClass =
    isPositive ? 'text-green-600' : isNegative ? 'text-red-600' : 'text-gray-900';

  return (
    <Card>
      <p className="mb-1 text-xs font-medium text-gray-500">{title}</p>
      <p className={`truncate text-xl font-semibold ${colorClass}`}>{value}</p>
    </Card>
  );
}
