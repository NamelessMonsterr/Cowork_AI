import React, { useState, useEffect } from 'react';

/**
 * VoiceSettings Component - V21 Voice Configuration UI
 * 
 * Allows users to configure:
 * - STT engine preference (auto/faster-whisper/openai/mock)
 * - OpenAI API key
 * - Microphone device selection
 * - Recording duration
 */
export function VoiceSettings({ apiUrl }) {
    const [settings, setSettings] = useState({
        engine_preference: 'auto',
        openai_api_key: '',
        mic_device: null,
        record_seconds: 5
    });
    const [devices, setDevices] = useState([]);
    const [health, setHealth] = useState(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [testResult, setTestResult] = useState(null);
    const [error, setError] = useState(null);

    // Fetch devices and settings on mount
    useEffect(() => {
        const fetchData = async () => {
            try {
                // Fetch current settings
                const settingsRes = await fetch(`${apiUrl}/settings`);
                const settingsData = await settingsRes.json();
                if (settingsData.voice) {
                    setSettings(prev => ({
                        ...prev,
                        engine_preference: settingsData.voice.engine_preference || 'auto',
                        openai_api_key: '', // Don't expose key
                        mic_device: settingsData.voice.mic_device,
                        record_seconds: settingsData.voice.record_seconds || 5
                    }));
                }

                // Fetch audio devices
                const devicesRes = await fetch(`${apiUrl}/voice/devices`);
                const devicesData = await devicesRes.json();
                if (devicesData.devices) {
                    setDevices(devicesData.devices);
                }

                // Fetch STT health
                const healthRes = await fetch(`${apiUrl}/voice/health`);
                const healthData = await healthRes.json();
                setHealth(healthData);

            } catch (err) {
                setError('Failed to load settings');
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchData();
    }, [apiUrl]);

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            // Only send non-empty API key
            const payload = {
                voice: {
                    engine_preference: settings.engine_preference,
                    mic_device: settings.mic_device,
                    record_seconds: settings.record_seconds
                }
            };
            if (settings.openai_api_key) {
                payload.voice.openai_api_key = settings.openai_api_key;
            }

            const res = await fetch(`${apiUrl}/settings`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Save failed');
            
            // Refresh health after save
            const healthRes = await fetch(`${apiUrl}/voice/health`);
            const healthData = await healthRes.json();
            setHealth(healthData);

        } catch (err) {
            setError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleTest = async () => {
        setTesting(true);
        setTestResult(null);
        try {
            const res = await fetch(`${apiUrl}/voice/test?seconds=${settings.record_seconds}`);
            const data = await res.json();
            setTestResult(data);
        } catch (err) {
            setTestResult({ success: false, error: err.message });
        } finally {
            setTesting(false);
        }
    };

    const styles = {
        container: {
            padding: '20px',
            color: '#fff'
        },
        section: {
            marginBottom: '24px',
            padding: '16px',
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '12px',
            border: '1px solid rgba(255, 215, 0, 0.2)'
        },
        sectionTitle: {
            color: '#ffd700',
            fontSize: '1.1rem',
            marginBottom: '16px',
            fontWeight: 'bold'
        },
        field: {
            marginBottom: '16px'
        },
        label: {
            display: 'block',
            color: '#aaa',
            fontSize: '0.9rem',
            marginBottom: '6px'
        },
        select: {
            width: '100%',
            padding: '10px 12px',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '1rem'
        },
        input: {
            width: '100%',
            padding: '10px 12px',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '8px',
            color: '#fff',
            fontSize: '1rem',
            boxSizing: 'border-box'
        },
        slider: {
            width: '100%',
            accentColor: '#ffd700'
        },
        healthBadge: {
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 14px',
            borderRadius: '20px',
            fontSize: '0.9rem'
        },
        healthGood: {
            background: 'rgba(0, 255, 0, 0.2)',
            color: '#00ff00'
        },
        healthBad: {
            background: 'rgba(255, 0, 0, 0.2)',
            color: '#ff4444'
        },
        button: {
            padding: '12px 24px',
            border: 'none',
            borderRadius: '8px',
            fontSize: '1rem',
            fontWeight: 'bold',
            cursor: 'pointer',
            marginRight: '12px',
            transition: 'all 0.2s'
        },
        saveBtn: {
            background: 'linear-gradient(135deg, #ffd700 0%, #ffaa00 100%)',
            color: '#000'
        },
        testBtn: {
            background: 'rgba(255,255,255,0.1)',
            color: '#fff',
            border: '1px solid rgba(255,255,255,0.3)'
        },
        testResult: {
            marginTop: '16px',
            padding: '12px',
            borderRadius: '8px',
            fontSize: '0.9rem'
        },
        error: {
            color: '#ff4444',
            padding: '12px',
            background: 'rgba(255, 0, 0, 0.1)',
            borderRadius: '8px',
            marginBottom: '16px'
        }
    };

    if (loading) {
        return <div style={styles.container}>Loading voice settings...</div>;
    }

    return (
        <div style={styles.container}>
            {error && <div style={styles.error}>⚠️ {error}</div>}

            {/* Engine Status */}
            <div style={styles.section}>
                <div style={styles.sectionTitle}>🎙️ STT Engine Status</div>
                {health && (
                    <div style={{
                        ...styles.healthBadge,
                        ...(health.available ? styles.healthGood : styles.healthBad)
                    }}>
                        {health.available ? '✓' : '✗'} {health.stt_engine}
                        {health.error && <span style={{opacity: 0.7, marginLeft: '8px'}}>({health.error})</span>}
                    </div>
                )}
            </div>

            {/* Engine Preference */}
            <div style={styles.section}>
                <div style={styles.sectionTitle}>⚙️ Engine Configuration</div>
                
                <div style={styles.field}>
                    <label style={styles.label}>STT Engine Preference</label>
                    <select 
                        style={styles.select}
                        value={settings.engine_preference}
                        onChange={e => setSettings({...settings, engine_preference: e.target.value})}
                    >
                        <option value="auto">Auto (Best Available)</option>
                        <option value="faster-whisper">Faster Whisper (Local)</option>
                        <option value="openai">OpenAI Whisper (API)</option>
                        <option value="mock">Mock (Dev Only)</option>
                    </select>
                </div>

                <div style={styles.field}>
                    <label style={styles.label}>OpenAI API Key (for API mode)</label>
                    <input 
                        type="password"
                        style={styles.input}
                        id="openai-key-input"
                        name="openai_api_key"
                        placeholder="sk-..."
                        value={settings.openai_api_key}
                        onChange={e => setSettings({...settings, openai_api_key: e.target.value})}
                        autoComplete="new-password"
                    />
                </div>
            </div>

            {/* Audio Settings */}
            <div style={styles.section}>
                <div style={styles.sectionTitle}>🎤 Audio Settings</div>

                <div style={styles.field}>
                    <label style={styles.label}>Microphone Device</label>
                    <select 
                        style={styles.select}
                        value={settings.mic_device || ''}
                        onChange={e => setSettings({...settings, mic_device: e.target.value || null})}
                    >
                        <option value="">System Default</option>
                        {devices.map(dev => (
                            <option key={dev.id} value={dev.id}>
                                {dev.name} {dev.is_default ? '(Default)' : ''}
                            </option>
                        ))}
                    </select>
                </div>

                <div style={styles.field}>
                    <label style={styles.label}>
                        Recording Duration: {settings.record_seconds}s
                    </label>
                    <input 
                        type="range"
                        id="record-seconds-input"
                        name="record_seconds"
                        min="2"
                        max="15"
                        style={styles.slider}
                        value={settings.record_seconds}
                        onChange={e => setSettings({...settings, record_seconds: parseInt(e.target.value)})}
                    />
                </div>
            </div>

            {/* Actions */}
            <div style={{marginTop: '24px'}}>
                <button 
                    style={{...styles.button, ...styles.saveBtn}}
                    onClick={handleSave}
                    disabled={saving}
                >
                    {saving ? 'Saving...' : '💾 Save Settings'}
                </button>
                <button 
                    style={{...styles.button, ...styles.testBtn}}
                    onClick={handleTest}
                    disabled={testing}
                >
                    {testing ? '🎙️ Recording...' : '🧪 Test STT'}
                </button>
            </div>

            {/* Test Result */}
            {testResult && (
                <div style={{
                    ...styles.testResult,
                    background: testResult.success ? 'rgba(0,255,0,0.1)' : 'rgba(255,0,0,0.1)',
                    color: testResult.success ? '#00ff00' : '#ff4444'
                }}>
                    {testResult.success ? (
                        <div>
                            <strong>✓ Success</strong> — Engine: {testResult.engine}<br/>
                            <em>"{testResult.transcript || '(no speech detected)'}"</em>
                        </div>
                    ) : (
                        <div><strong>✗ Failed:</strong> {testResult.error}</div>
                    )}
                </div>
            )}
        </div>
    );
}

export default VoiceSettings;
