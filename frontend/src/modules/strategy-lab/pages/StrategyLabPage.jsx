import { ExperimentList } from '../components/ExperimentList';
import { ErrorBoundary } from '../../../shared/components/ErrorBoundary';

/**
 * Strategy Lab landing page — lists experiments with create controls.
 */
export default function StrategyLabPage() {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Strategy Lab</h1>
        <p className="mt-1 text-sm text-gray-500">
          Design, run, and compare strategy experiments
        </p>
      </div>

      <ErrorBoundary>
        <ExperimentList />
      </ErrorBoundary>
    </div>
  );
}
