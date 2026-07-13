import { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';

import Home from './pages/Home';
import TradingJournal from './pages/TradingJournal';
import TradeDetail from './pages/TradeDetail';
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
const StrategiesAdmin = lazy(() => import('./modules/catalogs/strategies/StrategiesPage'));
const SetupsAdmin = lazy(() => import('./modules/catalogs/setups/SetupsPage'));
const TagsAdmin = lazy(() => import('./modules/catalogs/tags/TagsPage'));
const MistakesAdmin = lazy(() => import('./modules/catalogs/mistakes/MistakesPage'));
const EdgeDiscoveryPage = lazy(() => import('./modules/edge-discovery/pages/EdgeDiscoveryPage'));
const EdgeDetailPage = lazy(() => import('./modules/edge-discovery/pages/EdgeDetailPage'));
const AIInsightsPage = lazy(() => import('./modules/ai-insights/pages/AIInsightsPage'));
const StrategyLabPage = lazy(() => import('./modules/strategy-lab/pages/StrategyLabPage'));
const ExperimentDetailPage = lazy(() => import('./modules/strategy-lab/pages/ExperimentDetailPage'));

function App() {
  return (
    <Suspense fallback={<div className="p-6">Loading...</div>}>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/imports/mt5" element={<ImportPage />} />
        <Route path="/trading-journal" element={<TradingJournal />} />
        <Route path="/trades/:id" element={<TradeDetail />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/risk-management" element={<RiskManagement />} />
        <Route path="/psychology" element={<Psychology />} />
        <Route path="/strategies" element={<Strategies />} />
        <Route path="/setups" element={<Setups />} />
        <Route path="/screenshot-library" element={<ScreenshotLibrary />} />
        <Route path="/error-management" element={<ErrorManagement />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/settings/strategies" element={<StrategiesAdmin />} />
        <Route path="/settings/setups" element={<SetupsAdmin />} />
        <Route path="/settings/tags" element={<TagsAdmin />} />
        <Route path="/settings/mistakes" element={<MistakesAdmin />} />
        <Route path="/analytics/edges" element={<EdgeDiscoveryPage />} />
        <Route path="/analytics/edges/:group_id" element={<EdgeDetailPage />} />
        <Route path="/analytics/insights" element={<AIInsightsPage />} />
        <Route path="/lab/experiments" element={<StrategyLabPage />} />
        <Route path="/lab/experiments/:id" element={<ExperimentDetailPage />} />
      </Routes>
    </Suspense>
  );
}

export default App;
