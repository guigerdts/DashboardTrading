function ModuleTemplate({ name, description }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold tracking-tight text-gray-900">
              {name}
            </h1>
            <span className="inline-flex items-center rounded-full bg-yellow-100 px-3 py-0.5 text-sm font-medium text-yellow-800">
              Scaffold
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="rounded-lg border border-gray-200 bg-white p-8 text-center shadow-sm">
          {description && (
            <p className="text-lg text-gray-600">{description}</p>
          )}
          <p className="mt-4 text-sm text-gray-400">
            This module is not yet implemented.
          </p>
        </div>
      </main>
    </div>
  );
}

export default ModuleTemplate;
