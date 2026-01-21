import React, { useState, useEffect } from 'react';
import '../App.css';

const API_URL = 'http://127.0.0.1:8765';

export function PluginsPanel({ onClose }) {
  const [activeTab, setActiveTab] = useState('installed'); // 'installed', 'store'
  
  // Installed State
  const [plugins, setPlugins] = useState([]);
  
  // Store State
  const [storePlugins, setStorePlugins] = useState([]);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- Actions ---

  const fetchInstalled = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/plugins/list`); // Local Plugins
      const data = await res.json();
      setPlugins(data);
    } catch (err) {
      setError("Failed to load plugins.");
    } finally {
      setLoading(false);
    }
  };

  const fetchStore = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/marketplace/list`); // Marketplace Registry
      const data = await res.json();
      setStorePlugins(data.plugins || []);
    } catch (err) {
      setError("Failed to load marketplace.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'installed') fetchInstalled();
    if (activeTab === 'store') fetchStore();
  }, [activeTab]);

  const handleToggle = async (plugin) => {
    const action = plugin.state === 'enabled' ? 'disable' : 'enable';
    try {
      await fetch(`${API_URL}/plugins/${action}/${plugin.id}`, { method: 'POST' });
      fetchInstalled(); 
    } catch (err) {
      console.error("Toggle failed", err);
    }
  };

  const handleInstallFile = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    
    setLoading(true);
    try {
      // Determines if legacy zip install or new package install logic needed?
      // API currently maps /plugins/install to zip install.
      const res = await fetch(`${API_URL}/plugins/install`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Install failed");
      
      alert(`Plugin ${data.id} Installed!`);
      fetchInstalled();
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStoreInstall = async (pluginId) => {
      if(!window.confirm(`Install plugin ${pluginId}?`)) return;
      setLoading(true);
      try {
          const res = await fetch(`${API_URL}/marketplace/install/${pluginId}`, { method: 'POST' });
          const data = await res.json();
          if(!res.ok) throw new Error(data.detail || "Install failed");
          
          alert("Installation Successful!");
          setActiveTab('installed'); // Switch back to see it
      } catch (err) {
          alert(`Store Install Failed: ${err.message}`);
      } finally {
          setLoading(false);
      }
  };

  return (
    <div className="panel-overlay" onClick={onClose}>
      <div className="panel" onClick={(e) => e.stopPropagation()} style={{ width: '700px', height: '600px', display: 'flex', flexDirection: 'column' }}>
        <div className="panel-header">
          <h2>🧩 PLUGINS</h2>
          <button className="panel-close" onClick={onClose}>✕</button>
        </div>
        
        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #333' }}>
            <div 
                className={`tab ${activeTab === 'installed' ? 'active' : ''}`}
                style={{ flex: 1, padding: '10px', textAlign: 'center', cursor: 'pointer', background: activeTab === 'installed' ? 'rgba(0, 255, 255, 0.1)' : 'transparent', color: activeTab === 'installed' ? '#0ff' : '#888' }}
                onClick={() => setActiveTab('installed')}
            >
                INSTALLED
            </div>
            <div 
                className={`tab ${activeTab === 'store' ? 'active' : ''}`}
                style={{ flex: 1, padding: '10px', textAlign: 'center', cursor: 'pointer', background: activeTab === 'store' ? 'rgba(0, 255, 255, 0.1)' : 'transparent', color: activeTab === 'store' ? '#0ff' : '#888' }}
                onClick={() => setActiveTab('store')}
            >
                MARKETPLACE 🛒
            </div>
        </div>
        
        <div className="panel-content" style={{ flex: 1, overflowY: 'auto', padding: '15px' }}>
            
            {loading && <div style={{ textAlign: 'center', padding: '20px' }}>Loading...</div>}
            {error && <div style={{ color: 'red', textAlign: 'center' }}>{error}</div>}

            {/* INSTALLED VIEW */}
            {activeTab === 'installed' && !loading && (
                <>
                    <div style={{ marginBottom: '15px', display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                        <label className="footer-btn" style={{ cursor: 'pointer', fontSize: '0.8em' }}>
                            📂 LOAD LOCAL .ZIP
                            <input 
                                type="file" 
                                id="plugin-file-upload" 
                                name="pluginFile" 
                                accept=".zip,.cowork-plugin" 
                                style={{ display: 'none' }} 
                                onChange={handleInstallFile} 
                            />
                        </label>
                    </div>

                    {plugins.length === 0 ? (
                         <div style={{ textAlign: 'center', color: '#666', marginTop: '50px' }}>No plugins installed. Check the Marketplace!</div>
                    ) : (
                        <ul className="history-list">
                            {plugins.map(p => (
                                <li key={p.id} className="history-item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '5px' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                                        <span style={{ fontWeight: 'bold', color: '#0ff' }}>{p.name} <span style={{fontSize:'0.8em', color:'#666'}}>v{p.version}</span></span>
                                        <span style={{ 
                                            color: p.state === 'enabled' ? '#0f0' : '#888',
                                            border: `1px solid ${p.state === 'enabled' ? '#0f0' : '#888'}`,
                                            padding: '2px 6px',
                                            fontSize: '0.8em',
                                            borderRadius: '4px'
                                        }}>
                                            {p.state.toUpperCase()}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: '0.9em', color: '#ccc' }}>{p.description}</div>
                                    <div style={{ fontSize: '0.8em', color: '#888' }}>Publisher: {p.publisher || "Unknown"}</div>
                                    <div style={{ marginTop: '5px' }}>
                                        <button 
                                            className="footer-btn" 
                                            style={{ padding: '2px 8px', fontSize: '0.8em', borderColor: p.state === 'enabled' ? '#ff4444' : '#0f0', color: p.state === 'enabled' ? '#ff4444' : '#0f0' }}
                                            onClick={() => handleToggle(p)}
                                        >
                                            {p.state === 'enabled' ? 'DISABLE' : 'ENABLE'}
                                        </button>
                                    </div>
                                </li>
                            ))}
                        </ul>
                    )}
                </>
            )}

            {/* MARKETPLACE VIEW */}
            {activeTab === 'store' && !loading && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '15px' }}>
                    {storePlugins.map(p => (
                        <div key={p.id} className="hex-frame" style={{ padding: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            <div style={{ fontWeight: 'bold', color: '#0ff', fontSize: '1.1em' }}>{p.name}</div>
                            <div style={{ fontSize: '0.8em', color: '#888' }}>v{p.version} by {p.author}</div>
                            <div style={{ fontSize: '0.9em', color: '#ccc', flex: 1 }}>{p.description}</div>
                            {p.verified && <div style={{ color: '#0f0', fontSize: '0.8em' }}>✅ Verified Publisher</div>}
                            
                            <button 
                                className="footer-btn active" 
                                style={{ marginTop: 'auto', width: '100%' }}
                                onClick={() => handleStoreInstall(p.id)}
                            >
                                INSTALL
                            </button>
                        </div>
                    ))}
                    {storePlugins.length === 0 && <div style={{ gridColumn: '1/-1', textAlign: 'center', color: '#666' }}>No plugins found in registry.</div>}
                </div>
            )}

        </div>
      </div>
    </div>
  );
}
