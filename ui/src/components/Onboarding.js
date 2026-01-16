import React, { useState } from 'react';
import '../App.css';

export function Onboarding({ onComplete }) {
  const [step, setStep] = useState(1);
  const [consent, setConsent] = useState(false);
  const [mode, setMode] = useState('voice'); // voice, chat

  const handleNext = () => {
      if (step === 1 && !consent) return alert("Please accept the terms.");
      setStep(step + 1);
  };

  const handleFinish = async () => {
      // Save preferences via API if needed
      // For now, just notify parent
      onComplete({ mode });
  };

  return (
    <div className="panel-overlay" style={{ background: 'rgba(0,0,0,0.95)', zIndex: 9999 }}>
      <div className="panel" style={{ width: '600px', height: '400px', display: 'flex', flexDirection: 'column' }}>
        <div className="panel-header">
          <h2>🚀 WELCOME TO FLASH AI</h2>
        </div>
        
        <div className="panel-content" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Step 1: Consent */}
            {step === 1 && (
                <>
                    <h3>⚠️ Beta Safety Warning</h3>
                    <p>Flash AI operates your computer with real mouse/keyboard actions.</p>
                    <ul style={{ paddingLeft: '20px', color: '#ccc' }}>
                        <li>We are NOT responsible for data loss.</li>
                        <li>Always supervise execution.</li>
                        <li>Check the "Kill Switch" (Revoke) button location.</li>
                    </ul>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '20px' }}>
                        <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />
                        I understand and accept the risks.
                    </label>
                </>
            )}

            {/* Step 2: Mode Selection */}
            {step === 2 && (
                <>
                    <h3>🎮 Select Control Mode</h3>
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <div 
                            className={`hex-frame ${mode === 'voice' ? 'listening' : ''}`} 
                            style={{ flex: 1, padding: '20px', cursor: 'pointer', border: mode === 'voice' ? '2px solid #0ff' : '1px solid #444' }}
                            onClick={() => setMode('voice')}
                        >
                            <div style={{ textAlign: 'center', fontWeight: 'bold' }}>🎤 Voice</div>
                            <p style={{ fontSize: '0.8em', color: '#888' }}>Hands-free. Push-to-talk available.</p>
                        </div>
                        <div 
                            className={`hex-frame ${mode === 'chat' ? 'listening' : ''}`} 
                            style={{ flex: 1, padding: '20px', cursor: 'pointer', border: mode === 'chat' ? '2px solid #0ff' : '1px solid #444' }}
                            onClick={() => setMode('chat')}
                        >
                            <div style={{ textAlign: 'center', fontWeight: 'bold' }}>💬 Chat</div>
                            <p style={{ fontSize: '0.8em', color: '#888' }}>Text-based. Safer for beginners.</p>
                        </div>
                    </div>
                </>
            )}

            {/* Step 3: Permissions & Kill Switch Demo */}
            {step === 3 && (
                <>
                    <h3>🛑 Safety Check</h3>
                    <p>The <strong>REVOKE SESSION</strong> button is your emergency stop.</p>
                    <button 
                        className="footer-btn" 
                        style={{ border: '1px solid red', color: 'red', margin: '20px auto', display: 'block' }}
                        onClick={() => alert("Good! This will instantly kill any running task.")}
                    >
                        TEST KILL SWITCH
                    </button>
                    <p>Permissions needed:</p>
                    <ul style={{ paddingLeft: '20px', color: '#ccc' }}>
                        <li>✅ Screen Recording (Vision)</li>
                        <li>✅ Microphone (Voice)</li>
                        <li>✅ File System (Work)</li>
                    </ul>
                </>
            )}

        </div>

        <div style={{ padding: '20px', borderTop: '1px solid #333', display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
            {step < 3 ? (
                <button className="footer-btn active" onClick={handleNext}>NEXT &gt;</button>
            ) : (
                <button className="footer-btn active" onClick={handleFinish}>FINISH SETUP ✨</button>
            )}
        </div>
      </div>
    </div>
  );
}
