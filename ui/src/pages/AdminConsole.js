import React, { useState, useEffect } from 'react';

/**
 * W17.4 Admin Console
 * Manage team policies, roles, and peer visibility.
 */
const AdminConsole = ({ apiUrl }) => {
  const [peers, setPeers] = useState([]);
  const [policies, setPolicies] = useState({
    allowDelegation: true,
    maxConcurrentTasks: 5,
    trustedPeers: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchPeers();
    fetchPolicies();
  }, []);

  const fetchPeers = async () => {
    try {
      const res = await fetch(`${apiUrl}/team/peers`);
      const data = await res.json();
      setPeers(data.peers || []);
    } catch (e) {
      console.error('Failed to fetch peers:', e);
    }
  };

  const fetchPolicies = async () => {
    try {
      // Mock policies for now - would be fetched from API
      setLoading(false);
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  const toggleDelegation = () => {
    setPolicies(prev => ({ ...prev, allowDelegation: !prev.allowDelegation }));
  };

  const addTrustedPeer = (peerId) => {
    setPolicies(prev => ({
      ...prev,
      trustedPeers: [...prev.trustedPeers, peerId]
    }));
  };

  if (loading) return <div className="admin-page">Loading Admin Console...</div>;
  if (error) return <div className="admin-page error">Error: {error}</div>;

  return (
    <div className="admin-page" style={styles.container}>
      <h2 style={styles.header}>Admin Console</h2>
      
      {/* Team Policies */}
      <section style={styles.section}>
        <h3>Team Policies</h3>
        <div style={styles.policyRow}>
          <label>
            <input
              type="checkbox"
              checked={policies.allowDelegation}
              onChange={toggleDelegation}
            />
            Allow Task Delegation
          </label>
        </div>
        <div style={styles.policyRow}>
          <label>Max Concurrent Tasks:</label>
          <input
            type="number"
            value={policies.maxConcurrentTasks}
            onChange={(e) => setPolicies(prev => ({ ...prev, maxConcurrentTasks: parseInt(e.target.value) }))}
            style={styles.input}
          />
        </div>
      </section>
      
      {/* Discovered Peers */}
      <section style={styles.section}>
        <h3>Discovered Peers ({peers.length})</h3>
        {peers.length === 0 ? (
          <p style={styles.muted}>No peers discovered on local network.</p>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th>Name</th>
                <th>IP</th>
                <th>Role</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {peers.map(peer => (
                <tr key={peer.agent_id}>
                  <td>{peer.name}</td>
                  <td>{peer.ip}:{peer.port}</td>
                  <td>{peer.role || 'Worker'}</td>
                  <td style={{ color: '#4CAF50' }}>Online</td>
                  <td>
                    <button
                      onClick={() => addTrustedPeer(peer.agent_id)}
                      style={styles.btn}
                      disabled={policies.trustedPeers.includes(peer.agent_id)}
                    >
                      {policies.trustedPeers.includes(peer.agent_id) ? 'Trusted' : 'Trust'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
      
      {/* Audit Log (Placeholder) */}
      <section style={styles.section}>
        <h3>Recent Activity</h3>
        <p style={styles.muted}>No recent delegations.</p>
      </section>
    </div>
  );
};

const styles = {
  container: {
    padding: '20px',
    color: '#fff',
    maxWidth: '800px',
    margin: '0 auto'
  },
  header: {
    borderBottom: '1px solid #444',
    paddingBottom: '10px',
    marginBottom: '20px'
  },
  section: {
    marginBottom: '30px',
    padding: '15px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '8px'
  },
  policyRow: {
    marginBottom: '10px'
  },
  input: {
    marginLeft: '10px',
    padding: '5px',
    borderRadius: '4px',
    border: '1px solid #555',
    background: '#333',
    color: '#fff',
    width: '80px'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse'
  },
  btn: {
    padding: '5px 10px',
    borderRadius: '4px',
    border: 'none',
    background: '#2196F3',
    color: '#fff',
    cursor: 'pointer'
  },
  muted: {
    color: '#888'
  }
};

export default AdminConsole;
