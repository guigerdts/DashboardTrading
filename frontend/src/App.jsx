import { Routes, Route } from 'react-router-dom';

import Home from './pages/Home';
import Dashboard from './pages/Dashboard';
import TradingJournal from './pages/TradingJournal';
import Analytics from './pages/Analytics';
import RiskManagement from './pages/RiskManagement';
import Psychology from './pages/Psychology';
import Strategies from './pages/Strategies';
import Setups from './pages/Setups';
import ScreenshotLibrary from './pages/ScreenshotLibrary';
import ErrorManagement from './pages/ErrorManagement';
import Settings from './pages/Settings';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/dashboard" element={<Dashboard />} />
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
  );
}

export default App;
