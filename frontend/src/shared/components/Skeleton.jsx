const variantStyles = {
  text: 'rounded',
  rect: 'rounded-lg',
  circle: 'rounded-full',
};

export function Skeleton({ className = '', variant = 'text', width, height }) {
  const resolvedHeight = height ?? (variant === 'text' ? '1rem' : undefined);
  const resolvedWidth = width ?? (variant === 'circle' ? (height || '2.5rem') : undefined);

  return (
    <div
      className={`animate-pulse bg-gray-200 ${variantStyles[variant] || variantStyles.text} ${className}`}
      style={{ width: resolvedWidth, height: resolvedHeight }}
      aria-hidden="true"
    />
  );
}
