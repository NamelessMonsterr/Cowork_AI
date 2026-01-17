import React, { useState, useEffect } from 'react';

const styles = {
  container: {
    padding: '20px',
    color: '#fff',
    maxWidth: '900px',
    margin: '0 auto'
  },
  header: {
    borderBottom: '1px solid #444',
    paddingBottom: '10px',
    marginBottom: '20px'
  },
  statsRow: {
    display: 'flex',
    gap: '20px',
    marginBottom: '30px'
  },
  statCard: {
    flex: 1,
    padding: '20px',
    background: 'linear-gradient(135deg, rgba(33,150,243,0.2), rgba(156,39,176,0.2))',
    borderRadius: '12px',
    textAlign: 'center'
  },
  statValue: {
    fontSize: '2.5em',
    fontWeight: 'bold'
  },
  statLabel: {
    color: '#888',
    marginTop: '5px'
  },
  section: {
    marginBottom: '25px',
    padding: '15px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '8px'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    marginTop: '10px'
  },
  badge: {
    padding: '3px 8px',
    borderRadius: '4px',
    background: '#4CAF50',
    color: '#fff',
    fontSize: '0.85em'
  },
  btnDanger: {
    padding: '8px 16px',
    borderRadius: '4px',
    border: 'none',
    background: '#f44336',
    color: '#fff',
    cursor: 'pointer'
  },
  muted: {
    color: '#888',
    fontSize: '0.9em',
    marginBottom: '10px'
  }
};

/**
 * W20.7 Learning Dashboard
 * Show how Flash Assistant is improving over time.
 */
const LearningDashboard = ({ apiUrl }) => {
  const [stats, setStats] = useState({
    totalExecutions: 0,
    successRate: 0,
    improvements: [],
    appProfiles: []
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLearningStats();
  }, []);

  const fetchLearningStats = async () => {
    try {
      // In real implementation, fetch from /learning/stats
      // Mock data for now
      setStats({
        totalExecutions: 1247,
        successRate: 94.3,
        successRateChange: +2.1,
        improvements: [
          { app: 'Notepad', before: 85, after: 98, strategy: 'UIA' },
          { app: 'Chrome', before: 72, after: 91, strategy: 'Vision' },
          { app: 'VS Code', before: 88, after: 95, strategy: 'UIA' }
        ],
        appProfiles: [
          { name: 'notepad', preferred: 'UIA', rate: 98, samples: 156 },
          { name: 'chrome', preferred: 'Vision', rate: 91, samples: 89 },
          { name: 'explorer', preferred: 'UIA', rate: 95, samples: 234 }
        ]
      });
      setLoading(false);
    } catch (e) {
      console.error('Failed to fetch learning stats:', e);
      setLoading(false);
    }
  };

  const clearLearningData = () => {
    if (window.confirm('Are you sure you want to clear all learning data? This cannot be undone.')) {
      // In real implementation, call /learning/clear
      setStats({
        totalExecutions: 0,
        successRate: 0,
        improvements: [],
        appProfiles: []
      });
      alert('Learning data cleared.');
    }
  };

  if (loading) return <div className="learning-page">Loading Learning Dashboard...</div>;

  return (
    <div className="learning-page" style={styles.container}>
      <h2 style={styles.header}>Learning Dashboard</h2>
      
      {/* Overview Stats */}
      <section style={styles.statsRow}>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{stats.totalExecutions}</div>
          <div style={styles.statLabel}>Total Executions</div>
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{stats.successRate}%</div>
          <div style={styles.statLabel}>Success Rate</div>
          {stats.successRateChange && (
            <div style={{ color: stats.successRateChange > 0 ? '#4CAF50' : '#f44336' }}>
              {stats.successRateChange > 0 ? '+' : ''}{stats.successRateChange}% this week
            </div>
          )}
        </div>
        <div style={styles.statCard}>
          <div style={styles.statValue}>{stats.appProfiles.length}</div>
          <div style={styles.statLabel}>Apps Learned</div>
        </div>
      </section>
      
      {/* Improvements */}
      <section style={styles.section}>
        <h3>Recent Improvements</h3>
        {stats.improvements.length === 0 ? (
          <p style={styles.muted}>No improvements yet. Keep using Flash Assistant!</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Application</th>
                <th>Before</th>
                <th>After</th>
                <th>Best Strategy</th>
              </tr>
            </thead>
            <tbody>
              {stats.improvements.map((imp, i) => (
                <tr key={i}>
                  <td>{imp.app}</td>
                  <td style={{ color: '#f44336' }}>{imp.before}%</td>
                  <td style={{ color: '#4CAF50' }}>{imp.after}%</td>
                  <td>
                    <span style={styles.badge}>{imp.strategy}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      
      {/* App Profiles */}
      <section style={styles.section}>
        <h3>Learned App Profiles</h3>
        <table style={styles.table}>
          <thead>
            <tr>
              <th>App</th>
              <th>Preferred Strategy</th>
              <th>Success Rate</th>
              <th>Samples</th>
            </tr>
          </thead>
          <tbody>
            {stats.appProfiles.map((app, i) => (
              <tr key={i}>
                <td>{app.name}</td>
                <td>
                  <span style={{
                    ...styles.badge,
                    background: app.preferred === 'UIA' ? '#2196F3' : '#9C27B0'
                  }}>
                    {app.preferred}
                  </span>
                </td>
                <td>{app.rate}%</td>
                <td>{app.samples}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      
      {/* Privacy Controls */}
      <section style={styles.section}>
        <h3>Privacy Controls</h3>
        <p style={styles.muted}>
          Learning data is stored locally and never sent to any server.
          Sensitive windows (bank, login, password) are automatically excluded.
        </p>
        <button onClick={clearLearningData} style={styles.btnDanger}>
          Clear All Learning Data
        </button>
      </section>
    </div>
  );
};

// Styles moved to top
export default LearningDashboard;
