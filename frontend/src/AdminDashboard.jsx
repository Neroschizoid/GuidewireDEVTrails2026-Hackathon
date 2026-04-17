import React, { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { apiGet, apiPost } from './api';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const INITIAL_STATS = {
  total_workers_protected: 0,
  active_weekly_coverage: 0,
  protected_earnings_estimate: 0,
  claims_premium_ratio: 0,
  loss_ratio_percent: 0,
  fraud_savings: 0,
  avg_payout_time: 'No payouts yet',
  predicted_next_week_claims: 0,
  predicted_next_week_loss: 0,
  highest_risk_day: null,
  forecast_location: null,
  weather_unavailable: false,
};

const currency = (value) => `Rs ${Number(value || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState('predictions');
  const [stats, setStats] = useState(INITIAL_STATS);
  const [threshold, setThreshold] = useState(50);
  const [forecastData, setForecastData] = useState([]);
  const [forecastLocation, setForecastLocation] = useState('');
  const [flaggedClaims, setFlaggedClaims] = useState([]);
  const [selectedFlags, setSelectedFlags] = useState(new Set());
  const [liveClaims, setLiveClaims] = useState([]);

  useEffect(() => {
    const fetchAll = () => {
      fetchStats();
      fetchForecast(threshold);
      fetchFlagged();
      fetchLiveClaims();
    };

    fetchAll();
    const intervalId = setInterval(fetchAll, 5000);
    return () => clearInterval(intervalId);
  }, [threshold]);

  const fetchStats = async () => {
    try {
      setStats(await apiGet('/api/v1/admin/stats'));
    } catch {
      setStats(INITIAL_STATS);
    }
  };

  const fetchForecast = async (thr) => {
    try {
      const data = await apiPost('/api/v1/admin/forecast', { threshold: thr });
      setForecastData(data || []);
      setForecastLocation(data?.[0]?.location || '');
    } catch {
      setForecastData([]);
      setForecastLocation('');
    }
  };

  const fetchFlagged = async () => {
    try {
      setFlaggedClaims(await apiGet('/api/v1/admin/flagged_claims'));
    } catch {
      setFlaggedClaims([]);
    }
  };

  const fetchLiveClaims = async () => {
    try {
      setLiveClaims(await apiGet('/api/v1/admin/live_claims'));
    } catch {
      setLiveClaims([]);
    }
  };

  const handleThresholdChange = (e) => {
    const val = Number(e.target.value);
    setThreshold(val);
  };

  const toggleSelect = (id) => {
    const next = new Set(selectedFlags);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedFlags(next);
  };

  const toggleSelectAll = () => {
    if (selectedFlags.size === flaggedClaims.length && flaggedClaims.length > 0) {
      setSelectedFlags(new Set());
      return;
    }
    setSelectedFlags(new Set(flaggedClaims.map((claim) => claim.payout_id)));
  };

  const bulkResolve = async () => {
    if (selectedFlags.size === 0) return;
    try {
      await apiPost('/api/v1/admin/bulk_resolve', { payout_ids: Array.from(selectedFlags) });
      setSelectedFlags(new Set());
      fetchFlagged();
      fetchStats();
    } catch {
      // keep current state on failure
    }
  };

  const forecastSummary = useMemo(() => {
    if (!forecastData.length) return null;
    const likelyDays = forecastData.filter((item) => item.workers_at_risk > 0).length;
    const totalWorkers = forecastData.reduce((sum, item) => sum + Number(item.workers_at_risk || 0), 0);
    return {
      likelyDays,
      totalWorkers,
    };
  }, [forecastData]);

  return (
    <div className="gwContainer gwAdminBg">
      <div className="gwCard gwAdminBg">
        <div className="gwCardHead">
          <div className="gwCardTitle gwNeonText">Mission Control: Intelligent Dashboard</div>
        </div>

        <div className="gwInlineStats gwAdminStatGridWide">
          <div className="gwStat">
            <div className="gwStatLabel gwNeonAccent">Workers Protected</div>
            <div className="gwStatValue">{stats.total_workers_protected.toLocaleString()}</div>
            <div className="gwMuted">{stats.active_weekly_coverage} active weekly covers</div>
          </div>
          <div className="gwStat">
            <div className="gwStatLabel gwNeonAccent">Protected Earnings</div>
            <div className="gwStatValue">{currency(stats.protected_earnings_estimate)}</div>
            <div className="gwMuted">Estimated income protected this week</div>
          </div>
          <div className="gwStat">
            <div className="gwStatLabel gwNeonAccent">Loss Ratio</div>
            <div className="gwStatValue">{stats.loss_ratio_percent.toFixed(1)}%</div>
            <div className="gwMuted">Claims/Premium ratio {stats.claims_premium_ratio.toFixed(2)}x</div>
          </div>
          <div className="gwStat">
            <div className="gwStatLabel gwNeonText">Avg Payout Time</div>
            <div className="gwStatValue">{stats.avg_payout_time}</div>
            <div className="gwMuted">Fraud savings {currency(stats.fraud_savings)}</div>
          </div>
        </div>

        <div className="gwInlineStats gwAdminStatGrid">
          <div className="gwStat">
            <div className="gwStatLabel gwNeonAccent">Next Week Claims</div>
            <div className="gwStatValue">{stats.predicted_next_week_claims}</div>
            <div className="gwMuted">Projected weather/disruption affected workers</div>
          </div>
          <div className="gwStat">
            <div className="gwStatLabel gwNeonAccent">Next Week Loss</div>
            <div className="gwStatValue">{currency(stats.predicted_next_week_loss)}</div>
            <div className="gwMuted">{stats.forecast_location || 'Primary zone'} predictive exposure</div>
          </div>
          <div className="gwStat">
            <div className="gwStatLabel gwNeonText">Highest Risk Day</div>
            <div className="gwStatValue">{stats.highest_risk_day || 'N/A'}</div>
            <div className="gwMuted">{stats.weather_unavailable ? 'Weather feed unavailable' : 'Based on live 7-day forecast'}</div>
          </div>
        </div>

        <div className="gwTabGroup" style={{ maxWidth: '420px', margin: '0 auto 24px' }}>
          {['predictions', 'fraud', 'live'].map((tab) => (
            <button
              key={tab}
              className={`gwTabMotionBtn ${activeTab === tab ? 'gwTabMotionBtnActive' : ''}`}
              onClick={() => setActiveTab(tab)}
              style={{ flex: 1, justifyContent: 'center' }}
            >
              {activeTab === tab && (
                <motion.div layoutId="adminTabBg" className="gwTabActiveBg" transition={{ type: 'spring', stiffness: 100, damping: 20 }}>
                  <div className="gwTabActiveLine" />
                </motion.div>
              )}
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
              {tab === 'fraud' && flaggedClaims.length > 0 ? <span className="gwMicroCounter" style={{ marginLeft: 6 }}>{flaggedClaims.length}</span> : null}
            </button>
          ))}
        </div>

        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            {activeTab === 'predictions' ? (
              <div className="gwCardInner">
                <div className="gwAdminTopBar">
                  <div>
                    <div className="gwCardTitle">Predictive Claim Analytics</div>
                    <div className="gwMuted">
                      {stats.weather_unavailable
                        ? 'Live weather feed is unavailable right now.'
                        : `Forecast zone: ${forecastLocation || stats.forecast_location || 'Primary active worker location'}`}
                    </div>
                  </div>
                  <div className="gwSliderWrap">
                    <span className="gwSliderLabel">Trigger Threshold ({threshold}mm)</span>
                    <input
                      type="range"
                      min="10"
                      max="100"
                      step="5"
                      value={threshold}
                      onChange={handleThresholdChange}
                      style={{ accentColor: '#24d6ff' }}
                    />
                  </div>
                </div>

                <div className="gwInlineStats gwAdminStatGridWide">
                  <div className="gwStat">
                    <div className="gwStatLabel">Likely Claim Days</div>
                    <div className="gwStatValue">{forecastSummary?.likelyDays || 0}</div>
                  </div>
                  <div className="gwStat">
                    <div className="gwStatLabel">Workers at Risk</div>
                    <div className="gwStatValue">{forecastSummary?.totalWorkers || 0}</div>
                  </div>
                  <div className="gwStat">
                    <div className="gwStatLabel">Projected Loss</div>
                    <div className="gwStatValue">{currency(stats.predicted_next_week_loss)}</div>
                  </div>
                </div>

                <div className="gwGlowChart" style={{ height: '300px', marginBottom: '16px' }}>
                  <ResponsiveContainer width="99%" height="100%">
                    <AreaChart data={forecastData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorLoss" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ff4d8d" stopOpacity={0.8} />
                          <stop offset="95%" stopColor="#ff4d8d" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <XAxis dataKey="day" stroke="#8B949E" />
                      <YAxis stroke="#8B949E" />
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1C2128', borderColor: '#30363D' }}
                        formatter={(value, name) => {
                          if (name === 'expected_loss') return [currency(value), 'Expected Loss'];
                          if (name === 'workers_at_risk') return [value, 'Workers at Risk'];
                          return [value, name];
                        }}
                        labelFormatter={(label, payload) => {
                          const point = payload?.[0]?.payload;
                          if (!point) return label;
                          return `${label} • Rain ${point.rainfall}mm • AQI ${point.aqi}`;
                        }}
                      />
                      <Area type="monotone" dataKey="expected_loss" stroke="#ff4d8d" fillOpacity={1} fill="url(#colorLoss)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>

                {forecastData.length ? (
                  <div className="gwTableWrap">
                    <table className="gwTable">
                      <thead>
                        <tr>
                          <th>Day</th>
                          <th>Workers at Risk</th>
                          <th>Expected Loss</th>
                          <th>Rainfall</th>
                          <th>AQI</th>
                        </tr>
                      </thead>
                      <tbody>
                        {forecastData.map((point) => (
                          <tr key={point.day} className="gwTableRow">
                            <td>{point.day}</td>
                            <td>{point.workers_at_risk}</td>
                            <td>{currency(point.expected_loss)}</td>
                            <td>{point.rainfall} mm</td>
                            <td>{point.aqi}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="gwMuted" style={{ textAlign: 'center', padding: '24px' }}>
                    No live forecast points are available right now.
                  </div>
                )}
              </div>
            ) : null}

            {activeTab === 'fraud' ? (
              <div className="gwCardInner">
                <div className="gwAdminTopBar">
                  <div className="gwCardTitle">Flagged Claims Protocol</div>
                  <button className="gwPrimaryBtnSmall" onClick={bulkResolve} disabled={selectedFlags.size === 0}>
                    Bulk Approve Selected ({selectedFlags.size})
                  </button>
                </div>

                {flaggedClaims.length === 0 ? (
                  <div className="gwMuted" style={{ textAlign: 'center', padding: '24px' }}>No flagged claims awaiting review.</div>
                ) : (
                  <div className="gwTableWrap">
                    <table className="gwTable">
                      <thead>
                        <tr>
                          <th>
                            <input
                              type="checkbox"
                              className="gwCheckbox"
                              checked={selectedFlags.size === flaggedClaims.length && flaggedClaims.length > 0}
                              onChange={toggleSelectAll}
                            />
                          </th>
                          <th>Worker ID</th>
                          <th>Worker Name</th>
                          <th>Amount</th>
                          <th>Fraud Score</th>
                          <th>Reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {flaggedClaims.map((claim) => (
                          <tr key={claim.payout_id} className="gwTableRow">
                            <td>
                              <input
                                type="checkbox"
                                className="gwCheckbox"
                                checked={selectedFlags.has(claim.payout_id)}
                                onChange={() => toggleSelect(claim.payout_id)}
                              />
                            </td>
                            <td>{claim.worker_id.substring(0, 8)}...</td>
                            <td>{claim.worker_name}</td>
                            <td>{currency(claim.amount)}</td>
                            <td className="gwNeonAccent">{claim.fraud_score}</td>
                            <td>{claim.fraud_reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : null}

            {activeTab === 'live' ? (
              <div className="gwCardInner">
                <div className="gwCardTitle" style={{ marginBottom: '16px' }}>Live Payouts Stream</div>
                {liveClaims.length === 0 ? (
                  <div className="gwMuted" style={{ textAlign: 'center', padding: '24px' }}>No recent claims found.</div>
                ) : (
                  <div className="gwTableWrap">
                    <table className="gwTable">
                      <thead>
                        <tr>
                          <th>Payout ID</th>
                          <th>Worker ID</th>
                          <th>Amount</th>
                          <th>Status</th>
                          <th>Timestamp</th>
                        </tr>
                      </thead>
                      <tbody>
                        {liveClaims.map((claim) => (
                          <tr key={claim.payout_id} className="gwTableRow">
                            <td>{claim.payout_id.substring(0, 8)}...</td>
                            <td>{claim.worker_id.substring(0, 8)}...</td>
                            <td>{currency(claim.amount)}</td>
                            <td style={{ color: '#2EA043' }}>{claim.status}</td>
                            <td>{new Date(claim.timestamp).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ) : null}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

export default AdminDashboard;
