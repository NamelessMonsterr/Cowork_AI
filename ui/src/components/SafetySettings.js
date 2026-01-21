import React, { useState, useEffect } from 'react';
import './SafetySettings.css';

const API_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8765';

export function SafetySettings() {
    const [trustedApps, setTrustedApps] = useState([]);
    const [appAliases, setAppAliases] = useState({});
    const [trustedDomains, setTrustedDomains] = useState([]);
    const [restrictedShell, setRestrictedShell] = useState(null);
    const [newApp, setNewApp] = useState('');
    const [newDomain, setNewDomain] = useState('');
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState('');

    // Load trusted apps and domains
    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            setLoading(true);
            
            // Load apps
            const appsRes = await fetch(`${API_URL}/safety/trusted_apps`);
            if (appsRes.ok) {
                const data = await appsRes.json();
                setTrustedApps(data.trusted_apps || []);
                setAppAliases(data.app_aliases || {});
            }
            
            // Load domains
            const domainsRes = await fetch(`${API_URL}/safety/trusted_domains`);
            if (domainsRes.ok) {
                const data = await domainsRes.json();
                setTrustedDomains(data.trusted_domains || []);
            }
            
            // Load restricted shell config
            const shellRes = await fetch(`${API_URL}/safety/restricted_shell`);
            if (shellRes.ok) {
                const data = await shellRes.json();
                setRestrictedShell(data);
            }
            
            setLoading(false);
        } catch (error) {
            console.error('Failed to load settings:', error);
            setMessage('❌ Failed to load settings');
            setLoading(false);
        }
    };

    const saveApps = async () => {
        try {
            setSaving(true);
            const response = await fetch(`${API_URL}/safety/trusted_apps`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    trusted_apps: trustedApps,
                    app_aliases: appAliases
                })
            });

            if (response.ok) {
                setMessage('✅ Trusted apps saved successfully');
                setTimeout(() => setMessage(''), 3000);
            } else {
                setMessage('❌ Failed to save apps');
            }
            setSaving(false);
        } catch (error) {
            console.error('Failed to save apps:', error);
            setMessage('❌ Failed to save apps');
            setSaving(false);
        }
    };

    const saveDomains = async () => {
        try {
            setSaving(true);
            const response = await fetch(`${API_URL}/safety/trusted_domains`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    trusted_domains: trustedDomains
                })
            });

            if (response.ok) {
                setMessage('✅ Trusted domains saved successfully');
                setTimeout(() => setMessage(''), 3000);
            } else {
                setMessage('❌ Failed to save domains');
            }
            setSaving(false);
        } catch (error) {
            console.error('Failed to save domains:', error);
            setMessage('❌ Failed to save domains');
            setSaving(false);
        }
    };

    const addApp = () => {
        if (newApp.trim() && !trustedApps.includes(newApp.trim().toLowerCase())) {
            setTrustedApps([...trustedApps, newApp.trim().toLowerCase()]);
            setNewApp('');
        }
    };

    const removeApp = (app) => {
        setTrustedApps(trustedApps.filter(a => a !== app));
    };

    const addDomain = () => {
        if (newDomain.trim() && !trustedDomains.includes(newDomain.trim().toLowerCase())) {
            setTrustedDomains([...trustedDomains, newDomain.trim().toLowerCase()]);
            setNewDomain('');
        }
    };

    const removeDomain = (domain) => {
        setTrustedDomains(trustedDomains.filter(d => d !== domain));
    };

    if (loading) {
        return <div className="safety-settings">Loading...</div>;
    }

    return (
        <div className="safety-settings">
            <h2>🛡️ Safety Settings</h2>
            
            {message && <div className="message">{message}</div>}

            {/* Trusted Apps Section */}
            <div className="section">
                <h3>Trusted Applications</h3>
                <p className="description">
                    Applications that can be opened via voice commands. Only add apps you trust.
                </p>
                
                <div className="add-item">
                    <input
                        type="text"
                        id="new-app-input"
                        name="newApp"
                        value={newApp}
                        onChange={(e) => setNewApp(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && addApp()}
                        placeholder="e.g., chrome, code, notepad"
                        autoComplete="off"
                    />
                    <button onClick={addApp} className="btn-add">➕ Add App</button>
                </div>

                <div className="items-list">
                    {trustedApps.map(app => (
                        <div key={app} className="item">
                            <span>{app}</span>
                            <button onClick={() => removeApp(app)} className="btn-remove">❌</button>
                        </div>
                    ))}
                </div>

                <button
                    onClick={saveApps}
                    disabled={saving}
                    className="btn-save"
                >
                    {saving ? 'Saving...' : '💾 Save Apps'}
                </button>
            </div>

            {/* Trusted Domains Section */}
            <div className="section">
                <h3>Trusted Domains</h3>
                <p className="description">
                    Domains that can be opened via URL commands. Only add domains you trust.
                </p>
                
                <div className="add-item">
                    <input
                        type="text"
                        id="new-domain-input"
                        name="newDomain"
                        value={newDomain}
                        onChange={(e) => setNewDomain(e.target.value)}
                        onKeyPress={(e) => e.key === 'Enter' && addDomain()}
                        placeholder="e.g., github.com, google.com"
                        autoComplete="off"
                    />
                    <button onClick={addDomain} className="btn-add">➕ Add Domain</button>
                </div>

                <div className="items-list">
                    {trustedDomains.map(domain => (
                        <div key={domain} className="item">
                            <span>{domain}</span>
                            <button onClick={() => removeDomain(domain)} className="btn-remove">❌</button>
                        </div>
                    ))}
                </div>

                <button
                    onClick={saveDomains}
                    disabled={saving}
                    className="btn-save"
                >
                    {saving ? 'Saving...' : '💾 Save Domains'}
                </button>
            </div>

            {/* Restricted Shell Section */}
            <div className="section">
                <h3>🔧 Diagnostic Shell Commands (Advanced)</h3>
                <p className="description">
                    Allow safe diagnostic commands like ipconfig, whoami, Get-Process. Disabled by default for security.
                </p>
                
                {restrictedShell ? (
                    <>
                        <div style={{ marginBottom: '16px', padding: '12px', background: 'rgba(255,215,0,0.1)', borderRadius: '6px' }}>
                            <strong>Status:</strong> {restrictedShell.enabled ? '✅ Enabled' : '❌ Disabled'}
                            {restrictedShell.enabled && restrictedShell.allow_admin && (
                                <span style={{ marginLeft: '12px', color: '#ff8800' }}>⚠️ Admin mode enabled</span>
                            )}
                        </div>
                        
                        {restrictedShell.enabled && (
                            <>
                                <div style={{ marginBottom: '12px' }}>
                                    <strong style={{ color: '#ffd700' }}>Allowed CMD Commands:</strong>
                                    <div className="items-list" style={{ maxHeight: '150px' }}>
                                        {(restrictedShell.allowed_cmd || []).map(cmd => (
                                            <div key={cmd} className="item" style={{ fontSize: '0.9rem' }}>
                                                <code>{cmd}</code>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                
                                <div style={{ marginBottom: '12px' }}>
                                    <strong style={{ color: '#ffd700' }}>Allowed PowerShell Commands:</strong>
                                    <div className="items-list" style={{ maxHeight: '150px' }}>
                                        {(restrictedShell.allowed_powershell || []).map(cmd => (
                                            <div key={cmd} className="item" style={{ fontSize: '0.9rem' }}>
                                                <code>{cmd}</code>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </>
                        )}
                        
                        <div style={{ marginTop: '16px', padding: '12px', background: 'rgba(100,100,100,0.2)', borderRadius: '6px', fontSize: '0.9rem' }}>
                            📝 To enable/disable: Edit <code>assistant/config/restricted_shell.json</code> and restart backend
                        </div>
                    </>
                ) : (
                    <div>Loading configuration...</div>
                )}
            </div>

            <div className="warning-box">
                ⚠️ <strong>Security Warning:</strong> Only add applications and domains you trust.
                Changes take effect immediately for new commands.
            </div>
        </div>
    );
}

export default SafetySettings;
