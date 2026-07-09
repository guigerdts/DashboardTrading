import { useState } from 'react';
import { Card } from '../../../shared/ui/Card';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';

export function ReviewEditor({ review, isLoading, onSave, isSaving, isError, error, reset }) {
  const [content, setContent] = useState(review?.content || '');
  const [lesson, setLesson] = useState(review?.lesson_learned || '');

  const handleSave = () => {
    onSave({ content: content || null, lesson_learned: lesson || null });
  };

  if (isError) {
    return (
      <Card title="Review">
        <ErrorFallback message={error?.message || 'Failed to save review'} onRetry={reset} />
      </Card>
    );
  }

  if (isLoading) {
    return (
      <Card title="Review">
        <div className="space-y-3">
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="100%" />
          <Skeleton variant="text" width="30%" />
        </div>
      </Card>
    );
  }

  return (
    <Card title="Review">
      <div className="space-y-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">Notes / Analysis</label>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={4}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="Write your trade analysis here..."
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-gray-500">Lesson Learned</label>
          <textarea
            value={lesson}
            onChange={(e) => setLesson(e.target.value)}
            rows={2}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            placeholder="What did you learn from this trade?"
          />
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="rounded bg-blue-600 px-4 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
          {isError && (
            <span className="text-sm text-red-600">Failed to save. Check console for details.</span>
          )}
        </div>
      </div>
    </Card>
  );
}
