import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

import Home from './pages/Home';
import TradingJournal from './pages/TradingJournal';
import Analytics from './pages/Analytics';
import RiskManagement from './pages/RiskManagement';
import Psychology from './pages/Psychology';
import Strategies from './pages/Strategies';
import Setups from './pages/Setups';
import ScreenshotLibrary from './pages/ScreenshotLibrary';
import ErrorManagement from './pages/ErrorManagement';
import Settings from './pages/Settings';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ImportPage = lazy(() => import('./modules/imports/mt5/pages/ImportPage'));

function App() {
  return (
    <Suspense fallback={<div className="p-6">Loading...</div>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/imports/mt5" element={<ImportPage />} />
        <Route path="/trading-journal" element={<TradingJournal />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/risk-management" element={<RiskManagement />} />
        <Route path="/psychology" element={<Psychology />} />
        <Route path="/strategies" element={<Strategies />} />
        <Route path="/setups" element={<Setups />} />
        <Route path="/screenshot-library" element={<ScreenshotLibrary />} />
        <Route path="/error-management" element={<ErrorManagement />} />
        <Route path="/settings" element={<Settings />} />
      </Routes>
    </Suspense>
  );
}

export default App;
