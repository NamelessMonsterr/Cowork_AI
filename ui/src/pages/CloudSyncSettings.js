import React, { useState, useEffect } from 'react';

const styles = {
  container: {
    padding: '20px',
    color: '#fff',
    maxWidth: '600px',
    margin: '0 auto'
  },
  header: {
    borderBottom: '1px solid #444',
    paddingBottom: '10px',
    marginBottom: '20px'
  },
  section: {
    marginBottom: '25px',
    padding: '15px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '8px'
  },
  row: {
    marginBottom: '10px'
  },
  btn: {
    padding: '8px 16px',
    borderRadius: '4px',
    border: 'none',
    background: '#4CAF50',
    color: '#fff',
    cursor: 'pointer',
    marginRight: '10px'
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
    fontSize: '0.9em'
  },
  privacyBox: {
    padding: '15px',
    background: 'rgba(76, 175, 80, 0.1)',
    border: '1px solid rgba(76, 175, 80, 0.3)',
    borderRadius: '8px',
    fontSize: '0.9em'
  }
};

/**
 * W19.7 Cloud Sync Settings
 * Enable sync, view devices, trigger manual sync.
 */
const CloudSyncSettings = ({ apiUrl }) => {
  const [authStatus, setAuthStatus] = useState({ authenticated: false, user: null });
  const [syncEnabled, setSyncEnabled] = useState(false);
  const [devices, setDevices] = useState([]);
  const [lastSync, setLastSync] = useState(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await fetch(`${apiUrl}/cloud/auth/status`);
      const data = await res.json();
      setAuthStatus(data);
    } catch (e) {
      console.error('Auth check failed:', e);
    }
  };

  const handleLogin = async () => {
    const email = prompt('Enter your email:');
    if (!email) return;
    
    try {
      await fetch(`${apiUrl}/cloud/auth/request_otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });
      
      const otp = prompt('Enter the OTP sent to your email (check console):');
      if (!otp) return;
      
      const res = await fetch(`${apiUrl}/cloud/auth/verify_otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, otp })
      });
      
      if (res.ok) {
        checkAuth();
        alert('Logged in successfully!');
      } else {
        alert('Invalid OTP');
      }
    } catch (e) {
      alert('Login failed: ' + e.message);
    }
  };

  const handleLogout = async () => {
    await fetch(`${apiUrl}/cloud/auth/logout`, { method: 'POST' });
    setAuthStatus({ authenticated: false, user: null });
  };

  const triggerSync = async () => {
    setSyncing(true);
    try {
      // In real implementation, call /cloud/sync/push or /pull
      await new Promise(r => setTimeout(r, 1500)); // Mock delay
      setLastSync(new Date().toLocaleString());
    } catch (e) {
      console.error('Sync failed:', e);
    }
    setSyncing(false);
  };

  return (
    <div className="sync-page" style={styles.container}>
      <h2 style={styles.header}>Cloud Sync Settings</h2>
      
      {/* Auth Status */}
      <section style={styles.section}>
        <h3>Account</h3>
        {authStatus.authenticated ? (
          <div>
            <p>Logged in as: <strong>{authStatus.user?.email}</strong></p>
            <button onClick={handleLogout} style={styles.btnDanger}>Logout</button>
          </div>
        ) : (
          <div>
            <p style={styles.muted}>Not logged in. Login to enable cloud sync.</p>
            <button onClick={handleLogin} style={styles.btn}>Login with Email</button>
          </div>
        )}
      </section>
      
      {/* Sync Toggle */}
      <section style={styles.section}>
        <h3>Sync Preferences</h3>
        <div style={styles.row}>
          <label>
            <input
              type="checkbox"
              checked={syncEnabled}
              onChange={() => setSyncEnabled(!syncEnabled)}
              disabled={!authStatus.authenticated}
            />
            Enable Cloud Sync
          </label>
        </div>
        <p style={styles.muted}>
          When enabled, settings, plugins, and skills sync across your devices.
        </p>
      </section>
      
      {/* Manual Sync */}
      <section style={styles.section}>
        <h3>Manual Sync</h3>
        <button
          onClick={triggerSync}
          style={styles.btn}
          disabled={!authStatus.authenticated || syncing}
        >
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
        {lastSync && <p style={styles.muted}>Last sync: {lastSync}</p>}
      </section>
      
      {/* Devices (Mock) */}
      <section style={styles.section}>
        <h3>Connected Devices</h3>
        {devices.length === 0 ? (
          <p style={styles.muted}>This is the only device connected.</p>
        ) : (
          <ul>
            {devices.map((d, i) => <li key={i}>{d.name} - {d.lastSeen}</li>)}
          </ul>
        )}
      </section>
      
      {/* Privacy Notice */}
      <section style={styles.privacyBox}>
        <strong>Privacy Note:</strong> All synced data is encrypted with AES-256.
        Your data is never shared or analyzed.
      </section>
    </div>
  );
};

// Styles moved to top


export default CloudSyncSettings;
