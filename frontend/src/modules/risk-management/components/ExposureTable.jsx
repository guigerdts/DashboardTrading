import { useState } from 'react';
import { Skeleton } from '../../../shared/components/Skeleton';
import { ErrorFallback } from '../../../shared/components/ErrorFallback';
import { formatCurrency, formatNumber } from '../../analytics/utils/formatters';

const TABS = ['By Asset', 'By Session', 'By Strategy'];

/**
 * Exposure breakdown table with tabs for asset / session / strategy dimensions.
 *
 * @param {{
 *   byAssetData, bySessionData, byStrategyData,
 *   isLoading, isError, error, onRetry?: () => void
 * }} props
 */
export function ExposureTable({
  byAssetData,
  bySessionData,
  byStrategyData,
  isLoading,
  isError,
  error,
  onRetry,
}) {
  const [activeTab, setActiveTab] = useState('By Asset');

  if (isError) {
    return (
      <ErrorFallback
        message={error?.message || 'Failed to load exposure data'}
        onRetry={onRetry}
      />
    );
  }

  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <Skeleton variant="text" width="140px" className="mb-4" />
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="mb-3 flex gap-4">
            <Skeleton variant="rect" height={24} width="20%" />
            <Skeleton variant="rect" height={24} width="16%" />
            <Skeleton variant="rect" height={24} width="14%" />
            <Skeleton variant="rect" height={24} width="14%" />
          </div>
        ))}
      </div>
    );
  }

  const renderAssetSection = () => {
    const records = byAssetData?.records;
    if (!records || records.length === 0) {
      return (
        <div className="flex h-[200px] items-center justify-center">
          <p className="text-gray-400">No asset exposure data</p>
        </div>
      );
    }
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Asset</th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Notional</th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Trades</th>
              <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">Total P&amp;L</th>
            </tr>
          </thead>
          <tbody>
            {records.map((rec, idx) => {
              const pnl = rec.total_pnl ?? 0;
              return (
                <tr
                  key={rec.asset_id ?? idx}
                  className="border-b border-gray-100 last:border-0"
                >
                  <td className="py-2 pr-2 font-medium text-gray-900">{rec.symbol || `Asset #${rec.asset_id}`}</td>
                  <td className="py-2 pr-2 text-gray-700">{formatCurrency(rec.notional)}</td>
                  <td className="py-2 pr-2 text-gray-700">{formatNumber(rec.trade_count)}</td>
                  <td
                    className={`py-2 ${
                      pnl > 0 ? 'text-green-600' : pnl < 0 ? 'text-red-600' : 'text-gray-700'
                    }`}
                  >
                    {formatCurrency(pnl)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  const renderSessionSection = () => {
    const records = bySessionData?.records;
    if (!records || records.length === 0) {
      return (
        <div className="flex h-[200px] items-center justify-center">
          <p className="text-gray-400">No session exposure data</p>
        </div>
      );
    }
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Session</th>
              <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">Trade Count</th>
            </tr>
          </thead>
          <tbody>
            {records.map((rec, idx) => (
              <tr
                key={rec.session_name ?? idx}
                className="border-b border-gray-100 last:border-0"
              >
                <td className="py-2 pr-2 font-medium text-gray-900">{rec.session_name || 'Unknown'}</td>
                <td className="py-2 text-gray-700">{formatNumber(rec.trade_count)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderStrategySection = () => {
    const records = byStrategyData?.records;
    if (!records || records.length === 0) {
      return (
        <div className="flex h-[200px] items-center justify-center">
          <p className="text-gray-400">No strategy exposure data</p>
        </div>
      );
    }
    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Strategy</th>
              <th className="pb-2 pr-2 text-xs font-medium uppercase tracking-wider text-gray-500">Trades</th>
              <th className="pb-2 text-xs font-medium uppercase tracking-wider text-gray-500">Total Risk</th>
            </tr>
          </thead>
          <tbody>
            {records.map((rec, idx) => (
              <tr
                key={rec.strategy_name ?? idx}
                className="border-b border-gray-100 last:border-0"
              >
                <td className="py-2 pr-2 font-medium text-gray-900">{rec.strategy_name || 'Unknown'}</td>
                <td className="py-2 pr-2 text-gray-700">{formatNumber(rec.trade_count)}</td>
                <td className="py-2 text-gray-700">{formatCurrency(rec.total_risk_amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold text-gray-800">Exposure</h2>
      <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        {/* Tabs */}
        <div className="mb-4 flex gap-2 border-b border-gray-200">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`pb-2 text-sm font-medium transition ${
                activeTab === tab
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === 'By Asset' && renderAssetSection()}
        {activeTab === 'By Session' && renderSessionSection()}
        {activeTab === 'By Strategy' && renderStrategySection()}
      </div>
    </div>
  );
}
