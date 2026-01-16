import React, { useState, useEffect } from 'react';

/**
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
    background: 'rgba(255,255,255,0.05)',
    padding: '15px',
    borderRadius: '8px'
  },
  warning: {
    background: 'rgba(255, 100, 100, 0.2)',
    border: '1px solid #ff4444',
    color: '#ffcccc',
    padding: '10px',
    borderRadius: '4px',
    marginBottom: '10px',
    fontSize: '0.9em'
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    cursor: 'pointer',
    userSelect: 'none'
  },
  on: { color: '#0f0', fontWeight: 'bold' },
  off: { color: '#888' },
  muted: {
    color: '#888',
    fontSize: '0.9em',
    marginBottom: '10px'
  },
  addRow: {
    display: 'flex',
    gap: '10px',
    marginBottom: '10px'
  },
  input: {
    flex: 1,
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #555',
    background: '#333',
    color: '#fff'
  },
  addBtn: {
    padding: '8px 20px',
    background: '#4CAF50',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '0.9em'
  },
  list: {
    listStyle: 'none',
    padding: 0
  },
  allowed: { color: '#0f0' },
  blocked: { color: '#f44' },
  smallBtn: {
    padding: '4px 8px',
    fontSize: '0.8em',
    marginRight: '5px',
    background: '#444',
    color: '#fff',
    border: 'none',
    borderRadius: '3px',
    cursor: 'pointer'
  },
  removeBtn: {
    padding: '4px 8px',
    fontSize: '0.8em',
    background: 'rgba(255,0,0,0.3)',
    color: '#ffcccc',
    border: 'none',
    borderRadius: '3px',
    cursor: 'pointer'
  },
  footer: {
    marginTop: '20px',
    textAlign: 'right'
  },
  saveBtn: {
    padding: '12px 30px',
    borderRadius: '6px',
    border: 'none',
    background: '#4CAF50',
    color: '#fff',
    fontSize: '16px',
    cursor: 'pointer'
  }
};

export default function PermissionsPage({ apiUrl }) {
  const [permissions, setPermissions] = useState({
    apps: [],
    folders: [],
    network: [],
    autopilot: false
  });
  const [newApp, setNewApp] = useState('');
  const [newFolder, setNewFolder] = useState('');
  const [newDomain, setNewDomain] = useState('');

  useEffect(() => {
    fetchPermissions();
  }, []);

  async function fetchPermissions() {
    try {
      const res = await fetch(`${apiUrl}/permissions`);
      if (res.ok) {
        setPermissions(await res.json());
      }
    } catch (e) {
      console.error('Failed to fetch permissions:', e);
    }
  }

  async function savePermissions() {
    try {
      await fetch(`${apiUrl}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(permissions)
      });
      alert('Permissions saved!');
    } catch (e) {
      console.error('Failed to save:', e);
    }
  }

  function addApp() {
    if (newApp && !permissions.apps.find(a => a.name === newApp)) {
      setPermissions({
        ...permissions,
        apps: [...permissions.apps, { name: newApp, allowed: true }]
      });
      setNewApp('');
    }
  }

  function toggleApp(name) {
    setPermissions({
      ...permissions,
      apps: permissions.apps.map(a => 
        a.name === name ? { ...a, allowed: !a.allowed } : a
      )
    });
  }

  function removeApp(name) {
    setPermissions({
      ...permissions,
      apps: permissions.apps.filter(a => a.name !== name)
    });
  }

  function addFolder() {
    if (newFolder && !permissions.folders.find(f => f.path === newFolder)) {
      setPermissions({
        ...permissions,
        folders: [...permissions.folders, { path: newFolder, allowed: true }]
      });
      setNewFolder('');
    }
  }

  function addDomain() {
    if (newDomain && !permissions.network.find(n => n.domain === newDomain)) {
      setPermissions({
        ...permissions,
        network: [...permissions.network, { domain: newDomain, allowed: true }]
      });
      setNewDomain('');
    }
  }

  return (
    <div style={styles.container}>
      <h2 style={styles.header}>Permissions</h2>
      
      {/* Autopilot Toggle */}
      <section style={styles.section}>
        <h3>Autopilot Mode</h3>
        <div style={styles.warning}>
          <strong>WARNING:</strong> Autopilot allows Flash Assistant to execute actions without confirmation.
          Only enable if you fully trust the current task.
        </div>
        <label style={styles.toggle}>
          <input
            type="checkbox"
            checked={permissions.autopilot}
            onChange={(e) => setPermissions({...permissions, autopilot: e.target.checked})}
          />
          <span style={permissions.autopilot ? styles.on : styles.off}>
            {permissions.autopilot ? 'ENABLED' : 'DISABLED'}
          </span>
        </label>
      </section>
      
      {/* Apps */}
      <section style={styles.section}>
        <h3>Applications</h3>
        <p style={styles.muted}>Control which applications Flash Assistant can interact with.</p>
        <div style={styles.addRow}>
          <input
            type="text"
            placeholder="e.g., notepad.exe"
            value={newApp}
            onChange={(e) => setNewApp(e.target.value)}
            style={styles.input}
          />
          <button onClick={addApp} style={styles.addBtn}>Add</button>
        </div>
        <table style={styles.table}>
          <thead>
            <tr>
              <th>Application</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {permissions.apps.map(app => (
              <tr key={app.name}>
                <td>{app.name}</td>
                <td>
                  <span style={app.allowed ? styles.allowed : styles.blocked}>
                    {app.allowed ? 'Allowed' : 'Blocked'}
                  </span>
                </td>
                <td>
                  <button onClick={() => toggleApp(app.name)} style={styles.smallBtn}>
                    {app.allowed ? 'Block' : 'Allow'}
                  </button>
                  <button onClick={() => removeApp(app.name)} style={styles.removeBtn}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      
      {/* Folders */}
      <section style={styles.section}>
        <h3>Folder Access</h3>
        <p style={styles.muted}>Restrict which folders Flash Assistant can access.</p>
        <div style={styles.addRow}>
          <input
            type="text"
            placeholder="e.g., C:\\Users\\Documents"
            value={newFolder}
            onChange={(e) => setNewFolder(e.target.value)}
            style={styles.input}
          />
          <button onClick={addFolder} style={styles.addBtn}>Add</button>
        </div>
        <ul style={styles.list}>
          {permissions.folders.map(folder => (
            <li key={folder.path}>
              <span>{folder.path}</span>
              <span style={folder.allowed ? styles.allowed : styles.blocked}>
                {folder.allowed ? 'Allowed' : 'Blocked'}
              </span>
            </li>
          ))}
        </ul>
      </section>
      
      {/* Network */}
      <section style={styles.section}>
        <h3>Network Access</h3>
        <p style={styles.muted}>Control which domains plugins can access.</p>
        <div style={styles.addRow}>
          <input
            type="text"
            placeholder="e.g., api.openai.com"
            value={newDomain}
            onChange={(e) => setNewDomain(e.target.value)}
            style={styles.input}
          />
          <button onClick={addDomain} style={styles.addBtn}>Add</button>
        </div>
        <ul style={styles.list}>
          {permissions.network.map(net => (
            <li key={net.domain}>
              <span>{net.domain}</span>
              <span style={net.allowed ? styles.allowed : styles.blocked}>
                {net.allowed ? 'Allowed' : 'Blocked'}
              </span>
            </li>
          ))}
        </ul>
      </section>
      
      {/* Save */}
      <div style={styles.footer}>
        <button onClick={savePermissions} style={styles.saveBtn}>
          Save Permissions
        </button>
      </div>
    </div>
  );
}

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
  warning: {
    padding: '10px',
    background: 'rgba(244, 67, 54, 0.2)',
    border: '1px solid rgba(244, 67, 54, 0.5)',
    borderRadius: '4px',
    marginBottom: '10px',
    fontSize: '0.9em'
  },
  toggle: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    cursor: 'pointer'
  },
  on: { color: '#4CAF50', fontWeight: 'bold' },
  off: { color: '#888' },
  muted: { color: '#888', fontSize: '0.9em', marginBottom: '10px' },
  addRow: {
    display: 'flex',
    gap: '10px',
    marginBottom: '15px'
  },
  input: {
    flex: 1,
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #555',
    background: '#333',
    color: '#fff'
  },
  addBtn: {
    padding: '8px 16px',
    borderRadius: '4px',
    border: 'none',
    background: '#2196F3',
    color: '#fff',
    cursor: 'pointer'
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse'
  },
  smallBtn: {
    padding: '4px 8px',
    borderRadius: '4px',
    border: 'none',
    background: '#555',
    color: '#fff',
    cursor: 'pointer',
    marginRight: '5px'
  },
  removeBtn: {
    padding: '4px 8px',
    borderRadius: '4px',
    border: 'none',
    background: '#f44336',
    color: '#fff',
    cursor: 'pointer'
  },
  list: {
    listStyle: 'none',
    padding: 0
  },
  allowed: { color: '#4CAF50' },
  blocked: { color: '#f44336' },
  footer: {
    marginTop: '20px',
    textAlign: 'right'
  },
  saveBtn: {
    padding: '12px 30px',
    borderRadius: '6px',
    border: 'none',
    background: '#4CAF50',
    color: '#fff',
    fontSize: '16px',
    cursor: 'pointer'
  }
};


