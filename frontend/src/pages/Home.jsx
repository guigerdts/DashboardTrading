import { Link } from 'react-router-dom';

const modules = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Trading Journal', path: '/trading-journal' },
  { name: 'Analytics', path: '/analytics' },
  { name: 'Risk Management', path: '/risk-management' },
  { name: 'Psychology', path: '/psychology' },
  { name: 'Strategies', path: '/strategies' },
  { name: 'Setups', path: '/setups' },
  { name: 'Screenshot Library', path: '/screenshot-library' },
  { name: 'Error Management', path: '/error-management' },
  { name: 'MT5 Import', path: '/imports/mt5' },
  { name: 'Settings', path: '/settings' },
];

function Home() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">
            Trade Intelligence Platform
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Select a module to get started.
          </p>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <nav className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((mod) => (
            <Link
              key={mod.path}
              to={mod.path}
              className="rounded-lg border border-gray-200 bg-white px-6 py-5 shadow-sm transition hover:border-blue-300 hover:shadow-md"
            >
              <h2 className="text-lg font-semibold text-gray-900">
                {mod.name}
              </h2>
              <p className="mt-1 text-sm text-gray-500">Open {mod.name} &rarr;</p>
            </Link>
          ))}
        </nav>
      </main>
    </div>
  );
}

export default Home;
