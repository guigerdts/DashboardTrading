import { useState, useRef, useCallback } from 'react';

export function FileUploader({ file, onFileSelect, disabled, error }) {
  const [isDragOver, setIsDragOver] = useState(false);
  const inputRef = useRef(null);

  const handleDragEnter = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragOver(true);
    },
    [disabled],
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      if (!disabled && e.dataTransfer.files?.[0]) {
        onFileSelect(e.dataTransfer.files[0]);
      }
    },
    [disabled, onFileSelect],
  );

  const handleClick = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const handleKeyDown = useCallback(
    (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (!disabled) inputRef.current?.click();
      }
    },
    [disabled],
  );

  const handleFileChange = useCallback(
    (e) => {
      if (e.target.files?.[0]) {
        onFileSelect(e.target.files[0]);
      }
    },
    [onFileSelect],
  );

  return (
    <div
      role="region"
      aria-label="File upload"
      className={[
        'rounded-lg border-2 border-dashed p-8 text-center transition-colors',
        disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer',
        isDragOver ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400',
      ].join(' ')}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv"
        className="hidden"
        onChange={handleFileChange}
        disabled={disabled}
      />
      {file ? (
        <p className="text-sm text-gray-700">
          Selected: <span className="font-medium">{file.name}</span>
        </p>
      ) : (
        <p className="text-sm text-gray-500">
          Drag & drop a CSV file here, or click to select
        </p>
      )}
      {error && (
        <p className="mt-2 text-sm text-red-600" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
