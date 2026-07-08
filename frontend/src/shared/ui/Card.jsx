export function Card({ title, children, className = '' }) {
  return (
    <div className={`rounded-lg border border-gray-200 bg-white p-4 shadow-sm ${className}`}>
      {title && <h3 className="mb-2 text-sm font-medium text-gray-500">{title}</h3>}
      {children}
    </div>
  );
}
