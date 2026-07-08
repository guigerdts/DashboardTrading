import { useNavigate } from 'react-router-dom';
import { useImportFlow } from '../hooks/useImportFlow';
import { FileUploader } from '../components/FileUploader';
import { PreviewTable } from '../components/PreviewTable';
import { ImportResult } from '../components/ImportResult';
import { ErrorBoundary } from '../../../../shared/components/ErrorBoundary';
import { ErrorFallback } from '../../../../shared/components/ErrorFallback';
import { Skeleton } from '../../../../shared/components/Skeleton';

function getErrorMessage(error) {
  if (error?.data?.detail) {
    const detail = error.data.detail;
    if (Array.isArray(detail)) {
      return detail.map((d) => d.msg).join('; ');
    }
    return String(detail);
  }
  if (error?.message && error.message !== 'Failed to load data') {
    return error.message;
  }
  return 'Server error';
}

export default function ImportPage() {
  const navigate = useNavigate();
  const flow = useImportFlow();

  const handleGoToDashboard = () => navigate('/dashboard');

  const renderContent = () => {
    switch (flow.state) {
      case 'idle':
        return (
          <FileUploader
            file={flow.file}
            onFileSelect={flow.setFile}
            disabled={false}
            error={flow.validationError}
          />
        );

      case 'file-selected':
        return (
          <div className="space-y-4">
            <FileUploader
              file={flow.file}
              onFileSelect={flow.setFile}
              disabled={false}
              error={flow.validationError}
            />
            <button
              onClick={flow.preview}
              disabled={!!flow.validationError}
              className="rounded bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Preview Import
            </button>
          </div>
        );

      case 'previewLoading':
        return (
          <div className="space-y-4">
            <FileUploader
              file={flow.file}
              onFileSelect={flow.setFile}
              disabled
              error={null}
            />
            <div className="space-y-3 rounded-lg border border-gray-200 bg-white p-4">
              <Skeleton variant="rect" height="2rem" width="40%" />
              <Skeleton variant="rect" height="1rem" />
              <Skeleton variant="rect" height="1rem" />
              <Skeleton variant="rect" height="1rem" />
            </div>
          </div>
        );

      case 'previewReady':
        return (
          <div className="space-y-4">
            <FileUploader
              file={flow.file}
              onFileSelect={flow.setFile}
              disabled={false}
              error={null}
            />
            <PreviewTable data={flow.previewData} />
            <button
              onClick={flow.confirm}
              disabled={!flow.canConfirm}
              className="rounded bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Confirm Import
            </button>
          </div>
        );

      case 'previewError':
        return (
          <div className="space-y-4">
            <FileUploader
              file={flow.file}
              onFileSelect={flow.setFile}
              disabled={false}
              error={null}
            />
            <ErrorFallback
              message={getErrorMessage(flow.previewError)}
              onRetry={flow.preview}
            />
          </div>
        );

      case 'confirmLoading':
        return (
          <div className="space-y-4">
            <FileUploader
              file={flow.file}
              onFileSelect={flow.setFile}
              disabled
              error={null}
            />
            <PreviewTable data={flow.previewData} />
            <button
              disabled
              className="cursor-not-allowed rounded bg-green-600 px-4 py-2 text-sm font-medium text-white opacity-50"
            >
              Importing...
            </button>
          </div>
        );

      case 'confirmSuccess':
        return (
          <ImportResult
            data={flow.confirmData}
            onReset={flow.reset}
            onGoToDashboard={handleGoToDashboard}
          />
        );

      case 'confirmError':
        return (
          <div className="space-y-4">
            <FileUploader
              file={flow.file}
              onFileSelect={flow.setFile}
              disabled
              error={null}
            />
            <PreviewTable data={flow.previewData} />
            <ErrorFallback
              message={getErrorMessage(flow.confirmError)}
              onRetry={flow.confirm}
            />
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="p-6">
      <h1 className="mb-6 text-2xl font-bold text-gray-900">MT5 Import</h1>
      <ErrorBoundary>{renderContent()}</ErrorBoundary>
    </div>
  );
}
