/**
 * Colour-coded stability badge for an edge's confidence level.
 *
 * @param {{ stability: number, confidenceLevel: string }} props
 */
export function EdgeStabilityIndicator({ stability, confidenceLevel }) {
  const config = {
    high: {
      label: 'High',
      dot: 'bg-green-500',
      bg: 'bg-green-50',
      text: 'text-green-700',
      border: 'border-green-200',
    },
    medium: {
      label: 'Medium',
      dot: 'bg-yellow-400',
      bg: 'bg-yellow-50',
      text: 'text-yellow-700',
      border: 'border-yellow-200',
    },
    low: {
      label: 'Low',
      dot: 'bg-gray-400',
      bg: 'bg-gray-50',
      text: 'text-gray-600',
      border: 'border-gray-200',
    },
    insufficient: {
      label: 'Insufficient',
      dot: 'bg-red-400',
      bg: 'bg-red-50',
      text: 'text-red-700',
      border: 'border-red-200',
    },
  };

  const c = config[confidenceLevel] || config.insufficient;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${c.bg} ${c.border} ${c.text}`}
      title={`Stability: ${(stability * 100).toFixed(0)}%`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${c.dot}`} aria-hidden="true" />
      {c.label}
    </span>
  );
}
