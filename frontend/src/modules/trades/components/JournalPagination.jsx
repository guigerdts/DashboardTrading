/**
 * Pagination controls for the Trading Journal.
 * Simple prev/next with page indicator and total record count.
 *
 * @param {{ page: number, pages: number, total: number, onPageChange: (page: number) => void }} props
 */
export function JournalPagination({ page, pages, total, onPageChange }) {
  if (total === 0) return null;

  return (
    <div className="flex items-center justify-between border-t border-gray-200 bg-white px-4 py-3">
      <div className="text-sm text-gray-700">
        Page <span className="font-medium">{page}</span> of{' '}
        <span className="font-medium">{pages}</span> ({total} records)
      </div>
      <div className="flex gap-2">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page <= 1}
          className="rounded border border-gray-300 bg-white px-3 py-1 text-sm disabled:opacity-50"
        >
          Previous
        </button>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pages}
          className="rounded border border-gray-300 bg-white px-3 py-1 text-sm disabled:opacity-50"
        >
          Next
        </button>
      </div>
    </div>
  );
}
