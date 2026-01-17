import React, { useState, useEffect } from 'react';
import CloudSyncSettings from './CloudSyncSettings';
import LearningDashboard from './LearningDashboard';
import PermissionsPage from './PermissionsPage';
import VoiceSettings from './VoiceSettings';
import ExecutionLogs from '../components/ExecutionLogs';

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
  tabs: {
    display: 'flex',
    gap: '5px',
    marginBottom: '20px',
    borderBottom: '1px solid #333'
  },
  tab: {
    padding: '10px 20px',
    background: 'transparent',
    border: 'none',
    color: '#888',
    cursor: 'pointer',
    borderBottom: '2px solid transparent'
  },
  activeTab: {
    color: '#fff',
    borderBottom: '2px solid #4CAF50'
  },
  content: {
    padding: '20px',
    background: 'rgba(255,255,255,0.05)',
    borderRadius: '8px',
    minHeight: '300px'
  },
  setting: {
    marginBottom: '15px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  },
  input: {
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #555',
    background: '#333',
    color: '#fff',
    width: '100px'
  },
  select: {
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #555',
    background: '#333',
    color: '#fff'
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

/**
 * P3.1 Settings Page
 * Full configuration UI with tabs for all settings.
 */
export default function SettingsPage({ apiUrl }) {
  const [settings, setSettings] = useState(null);
  const [activeTab, setActiveTab] = useState('general');
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  async function fetchSettings() {
    try {
      const res = await fetch(`${apiUrl}/settings`);
      if (res.ok) {
        const data = await res.json();
        setSettings(data);
      } else {
        setSettings(getDefaultSettings());
      }
    } catch (e) {
      console.error('Failed to fetch settings:', e);
      setSettings(getDefaultSettings());
    }
  }

  function getDefaultSettings() {
    return {
      safety: {
        session_ttl_minutes: 30,
        require_confirmation_for_destructive: true,
        max_actions_per_session: 100,
        enable_kill_switch: true,
        kill_switch_hotkey: 'ctrl+shift+escape'
      },
      plugins: {
        dev_mode: false,
        allow_unsigned: false,
        sandbox_enabled: true
      },
      cloud: {
        enabled: false,
        sync_interval_minutes: 15
      },
      learning: {
        enabled: true,
        min_samples_for_ranking: 5,
        exclude_sensitive_windows: true
      },
      voice: {
        mode: 'push_to_talk',
        wake_word: 'flash',
        push_to_talk_key: 'ctrl+space'
      },
      theme: 'dark',
      show_step_details: true
    };
  }

  async function saveSettings() {
    setSaving(true);
    try {
      await fetch(`${apiUrl}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      console.error('Failed to save settings:', e);
    }
    setSaving(false);
  }

  function updateSetting(category, key, value) {
    setSettings(prev => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value
      }
    }));
  }

  function getSaveButtonText() {
    if (saving) return 'Saving...';
    if (saved) return 'Saved!';
    return 'Save Settings';
  }

  if (!settings) return <div style={styles.container}>Loading settings...</div>;

  const tabs = [
    { id: 'general', label: 'General' },
    { id: 'permissions', label: 'Permissions' },
    { id: 'safety', label: 'Safety' },
    { id: 'voice', label: 'Voice' },
    { id: 'plugins', label: 'Plugins' },
    { id: 'cloud', label: 'Cloud Sync' },
    { id: 'learning', label: 'Learning' },
    { id: 'logs', label: 'Logs' }
  ];

  return (
    <div style={styles.container}>
      <h2 style={styles.header}>Settings</h2>
      
      {/* Tab Navigation */}
      <div style={styles.tabs}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...styles.tab,
              ...(activeTab === tab.id ? styles.activeTab : {})
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>
      
      {/* Tab Content */}
      <div style={styles.content}>
        {activeTab === 'general' && (
          <div>
            <h3>General Settings</h3>
            <div style={styles.setting}>
              <label>Theme</label>
              <select
                value={settings.theme}
                onChange={(e) => setSettings({...settings, theme: e.target.value})}
                style={styles.select}
              >
                <option value="dark">Dark</option>
                <option value="light">Light</option>
              </select>
            </div>
            <div style={styles.setting}>
              <label>
                <input
                  type="checkbox"
                  checked={settings.show_step_details}
                  onChange={(e) => setSettings({...settings, show_step_details: e.target.checked})}
                />
                Show step details during execution
              </label>
            </div>
          </div>
        )}

        {activeTab === 'permissions' && <PermissionsPage apiUrl={apiUrl} />}
        
        {activeTab === 'safety' && (
          <div>
            <h3>Safety Settings</h3>
            <div style={styles.setting}>
              <label>Session Timeout (minutes)</label>
              <input
                type="number"
                value={settings.safety.session_ttl_minutes}
                onChange={(e) => updateSetting('safety', 'session_ttl_minutes', parseInt(e.target.value))}
                style={styles.input}
                min="1"
                max="120"
              />
            </div>
            <div style={styles.setting}>
              <label>
                <input
                  type="checkbox"
                  checked={settings.safety.require_confirmation_for_destructive}
                  onChange={(e) => updateSetting('safety', 'require_confirmation_for_destructive', e.target.checked)}
                />
                Require confirmation for destructive actions
              </label>
            </div>
            <div style={styles.setting}>
              <label>Max actions per session</label>
              <input
                type="number"
                value={settings.safety.max_actions_per_session}
                onChange={(e) => updateSetting('safety', 'max_actions_per_session', parseInt(e.target.value))}
                style={styles.input}
                min="10"
                max="1000"
              />
            </div>
            <div style={styles.setting}>
              <label>
                <input
                  type="checkbox"
                  checked={settings.safety.enable_kill_switch}
                  onChange={(e) => updateSetting('safety', 'enable_kill_switch', e.target.checked)}
                />
                Enable kill switch hotkey
              </label>
              <input
                type="text"
                value={settings.safety.kill_switch_hotkey}
                onChange={(e) => updateSetting('safety', 'kill_switch_hotkey', e.target.value)}
                style={{...styles.input, marginLeft: '10px', width: '150px'}}
                disabled={!settings.safety.enable_kill_switch}
              />
            </div>
          </div>
        )}
        
        {activeTab === 'voice' && <VoiceSettings apiUrl={apiUrl} />}
        
        {activeTab === 'plugins' && (
          <div>
            <h3>Plugin Settings</h3>
            <div style={styles.setting}>
              <label>
                <input
                  type="checkbox"
                  checked={settings.plugins.dev_mode}
                  onChange={(e) => updateSetting('plugins', 'dev_mode', e.target.checked)}
                />
                Developer Mode (enables extra logging)
              </label>
            </div>
            <div style={styles.setting}>
              <label>
                <input
                  type="checkbox"
                  checked={settings.plugins.allow_unsigned}
                  onChange={(e) => updateSetting('plugins', 'allow_unsigned', e.target.checked)}
                />
                Allow unsigned plugins (security risk)
              </label>
            </div>
            <div style={styles.setting}>
              <label>
                <input
                  type="checkbox"
                  checked={settings.plugins.sandbox_enabled}
                  onChange={(e) => updateSetting('plugins', 'sandbox_enabled', e.target.checked)}
                />
                Enable plugin sandbox
              </label>
            </div>
          </div>
        )}
        
        {activeTab === 'cloud' && <CloudSyncSettings apiUrl={apiUrl} />}
        
        {activeTab === 'learning' && <LearningDashboard apiUrl={apiUrl} />}
        
        {activeTab === 'logs' && <ExecutionLogs apiUrl={apiUrl} />}
      </div>
      
      {/* Save Button */}
      <div style={styles.footer}>
        <button onClick={saveSettings} style={styles.saveBtn} disabled={saving}>
          {getSaveButtonText()}
        </button>
      </div>
    </div>
  );
}
