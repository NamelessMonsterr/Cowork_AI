import React, { useState, useEffect } from 'react';
import './App.css';

const API_URL = 'http://127.0.0.1:8765';

function App() {
  const [status, setStatus] = useState("I AM VENGEANCE");
  const [transcript, setTranscript] = useState("Click the core to activate voice command");
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const [activePanel, setActivePanel] = useState(null); // 'settings', 'history', 'help', or null
  const [history, setHistory] = useState([]);
  const [sessionActive, setSessionActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [showSessionModal, setShowSessionModal] = useState(false);

  // Update time and format helper
  useEffect(() => {
    const interval = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Poll Session Status
  useEffect(() => {
    const checkSession = async () => {
      try {
        const res = await fetch(`${API_URL}/permission/status`);
        const data = await res.json();
        setSessionActive(data.allowed);
        setTimeLeft(data.time_remaining);
        
        // Auto-close modal if active
        if (data.allowed) setShowSessionModal(false);
      } catch (err) {
        console.warn("Session check failed", err);
      }
    };
    
    const interval = setInterval(checkSession, 5000); // Check every 5s
    checkSession(); // Initial check
    return () => clearInterval(interval);
  }, []);

  // Countdown Timer
  useEffect(() => {
    if (!sessionActive || timeLeft <= 0) return;
    const timer = setInterval(() => setTimeLeft(prev => Math.max(0, prev - 1)), 1000);
    return () => clearInterval(timer);
  }, [sessionActive, timeLeft]);

  // WebSocket with reconnection
  useEffect(() => {
    let socket = null;
    let reconnectTimeout = null;

    const connect = () => {
      socket = new WebSocket('ws://127.0.0.1:8765/ws');
      
      socket.onopen = () => {
        console.log('✅ WebSocket connected successfully');
      };

      socket.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.event === 'voice_listening') {
          setStatus("LISTENING");
          setTranscript("Listening for your command...");
        } else if (msg.event === 'voice_transcribed') {
          setStatus("PROCESSING");
          setTranscript(`"${msg.data.text}"`);
          // Add to history
          setHistory(prev => [...prev, { time: new Date().toLocaleTimeString(), text: msg.data.text }]);
        } else if (msg.event === 'plan_preview' || msg.event === 'action_executing') {
          setStatus("EXECUTING");
          setTranscript("Executing your command...");
        } else if (msg.event === 'voice_speak') {
          // Frontend TTS
          const utterance = new SpeechSynthesisUtterance(msg.data.text);
          // Optional: Select a specific voice if desired
          window.speechSynthesis.speak(utterance);
        } else if (msg.event === 'voice_error') {
          setStatus("I AM VENGEANCE");
          setTranscript("No command detected. Try again.");
        } else if (msg.type === 'PERMISSION_REQUIRED' || msg.event === 'permission_required') {
          console.warn('⚠️ Session permission required:', msg.data);
          setSessionActive(false);
          setStatus("I AM VENGEANCE");
          setTranscript(msg.data?.reason || "Session expired. Click core to restart.");
          // Show Modal
          setShowSessionModal(true);
        }
      };

      socket.onerror = (err) => {
        console.error('❌ WebSocket error:', err);
      };

      socket.onclose = (e) => {
        console.warn('⚠️ WebSocket disconnected. Reconnecting in 3s...', e.reason);
        reconnectTimeout = setTimeout(() => connect(), 3000);
      };
    };

    connect();

    return () => {
      if (socket) socket.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  const handleClick = async () => {
    if (status !== "I AM VENGEANCE") return;

    // Try to get browser mic access (for visual indicator only)
    // Backend records independently via sounddevice
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      // Auto-stop after 6 seconds
      setTimeout(() => stream.getTracks().forEach(track => track.stop()), 6000);
    } catch (err) {
      console.warn("Browser mic not available (OK, backend will record):", err.message);
    }

    // Start voice listening directly - session auto-starts on plan approval
    setStatus("LISTENING");
    setTranscript("Listening for your command...");
    setSessionActive(true);

    try {
      const response = await fetch(`${API_URL}/voice/listen`, { method: 'POST' });
      const data = await response.json();
      
      if (!data.success) {
        setStatus("I AM VENGEANCE");
        setTranscript(data.message || "No speech detected. Try again.");
        setSessionActive(false);
      }
      // Success cases are handled by WebSocket events
    } catch (err) {
      console.error("Backend error:", err);
      setStatus("I AM VENGEANCE");
      setTranscript("Backend not responding. Check connection.");
      setSessionActive(false);
    }
  };

  const togglePanel = (panel) => {
    setActivePanel(activePanel === panel ? null : panel);
  };

  const handleRevoke = async () => {
    try {
      await fetch(`${API_URL}/permission/revoke`, { method: 'POST' });
      setSessionActive(false);
      setTimeLeft(0);
      setStatus("I AM VENGEANCE");
      setTranscript("Session revoked.");
      setActivePanel(null); // Close settings
    } catch (err) {
      console.error("Revoke failed:", err);
    }
  };

  return (
    <div className="app">
      {/* Scan Line Effect */}
      <div className="scan-line"></div>

      {/* Corner Decorations */}
      <div className="corner corner-tl"></div>
      <div className="corner corner-tr"></div>
      <div className="corner corner-bl"></div>
      <div className="corner corner-br"></div>

      {/* Header */}
      <header className="header">
        <div className="logo">FLASH</div>
        <div className="header-info">
          <div>TIME: <span>{time}</span></div>
          <div>STATUS: <span>{status}</span></div>
          <div>
             SESSION: <span className={sessionActive ? 'session-active' : 'session-inactive'}>
               {sessionActive ? `ACTIVE (${formatTime(timeLeft)})` : 'INACTIVE'}
             </span>
          </div>
        </div>
      </header>

      {/* Main Interface */}
      <main className="main">
        {/* Background Elements */}
        <div className="hex-bg"></div>
        <div className="particles">
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
          <div className="particle"></div>
        </div>

        <div className="core-interface">
          <div className={`hex-frame ${status.toLowerCase().replace(/ /g, '-')}`} onClick={handleClick}>
            <div className="outer-ring"></div>
            <div className="inner-ring"></div>
            <div className="core">
              <div className="lightning-icon">⚡</div>
            </div>
          </div>

          <div className="status-display">
            <div className="status-main">{status}</div>
            <div className="status-sub">{transcript}</div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <button className={`footer-btn ${activePanel === 'settings' ? 'active' : ''}`} onClick={() => togglePanel('settings')}>SETTINGS</button>
        <button className={`footer-btn ${activePanel === 'history' ? 'active' : ''}`} onClick={() => togglePanel('history')}>HISTORY</button>
        <button className={`footer-btn ${activePanel === 'help' ? 'active' : ''}`} onClick={() => togglePanel('help')}>HELP</button>
      </footer>

      {/* Settings Panel */}
      {activePanel === 'settings' && (
        <div className="panel-overlay" onClick={() => setActivePanel(null)}>
          <div className="panel" onClick={(e) => e.stopPropagation()}>
            <div className="panel-header">
              <h2>⚙️ SETTINGS</h2>
              <button className="panel-close" onClick={() => setActivePanel(null)}>✕</button>
            </div>
            <div className="panel-content">
              <div className="setting-item">
                <label>Voice Activation</label>
                <span className="toggle on">ON</span>
              </div>
              <div className="setting-item">
                <label>Theme</label>
                <span className="setting-value">Justice League</span>
              </div>
              <div className="setting-item">
                <label>Language</label>
                <span className="setting-value">English</span>
              </div>
              <div className="setting-item">
                <label>AI Model</label>
                <span className="setting-value">Gemini Pro</span>
              </div>
              <div className="setting-item">
                <label>Backend URL</label>
                <span className="setting-value">localhost:8765</span>
              </div>
              <div className="setting-item" style={{ marginTop: '20px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '15px' }}>
                <label>Session Control</label>
                <button 
                  onClick={handleRevoke}
                  style={{ 
                    background: 'rgba(255, 50, 50, 0.2)', 
                    color: '#ff4444', 
                    border: '1px solid #ff4444',
                    padding: '5px 10px',
                    cursor: 'pointer',
                    fontSize: '0.8rem'
                  }}
                >
                  REVOKE SESSION
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* History Panel */}
      {activePanel === 'history' && (
        <div className="panel-overlay" onClick={() => setActivePanel(null)}>
          <div className="panel" onClick={(e) => e.stopPropagation()}>
            <div className="panel-header">
              <h2>📜 COMMAND HISTORY</h2>
              <button className="panel-close" onClick={() => setActivePanel(null)}>✕</button>
            </div>
            <div className="panel-content">
              {history.length === 0 ? (
                <div className="empty-state">No commands yet. Click the core to start!</div>
              ) : (
                <ul className="history-list">
                  {history.slice().reverse().map((item, i) => (
                    <li key={i} className="history-item">
                      <span className="history-time">{item.time}</span>
                      <span className="history-text">"{item.text}"</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Help Panel */}
      {activePanel === 'help' && (
        <div className="panel-overlay" onClick={() => setActivePanel(null)}>
          <div className="panel" onClick={(e) => e.stopPropagation()}>
            <div className="panel-header">
              <h2>❓ HELP</h2>
              <button className="panel-close" onClick={() => setActivePanel(null)}>✕</button>
            </div>
            <div className="panel-content">
              <div className="help-section">
                <h3>🎤 Voice Commands</h3>
                <p>Click the glowing core to activate voice recognition. Speak your command clearly.</p>
              </div>
              <div className="help-section">
                <h3>⚡ Available Actions</h3>
                <ul>
                  <li>"Open Chrome" - Launch browser</li>
                  <li>"Take a screenshot" - Capture screen</li>
                  <li>"Type [text]" - Type text</li>
                  <li>"Click [element]" - Click on screen</li>
                </ul>
              </div>
              <div className="help-section">
                <h3>🦸 About Flash</h3>
                <p>Flash is your AI-powered desktop assistant, ready to execute voice commands at superhuman speed.</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Session Expired Modal */}
      {showSessionModal && (
        <div className="panel-overlay">
          <div className="panel" style={{ maxWidth: '400px', textAlign: 'center' }}>
            <div className="panel-header" style={{ justifyContent: 'center' }}>
              <h2 style={{ color: '#ff4444' }}>⚠️ SESSION EXPIRED</h2>
            </div>
            <div className="panel-content">
              <p>Your secure session has timed out or was revoked.</p>
              <br/>
              <p>Click the <strong>Core</strong> to re-authenticate.</p>
              <br/>
              <button 
                className="footer-btn active" 
                style={{ width: '100%', marginTop: '10px' }}
                onClick={() => setShowSessionModal(false)}
              >
                CLOSE
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
