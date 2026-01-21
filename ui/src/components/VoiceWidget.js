import React, { useState, useRef, useEffect } from 'react';

const VoiceWidget = () => {
  const [isListening, setIsListening] = useState(false);
  const [error, setError] = useState(null);
  const audioContextRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const websocketRef = useRef(null);
  const API_URL = (window.BACKEND_URL || "http://localhost:8765").trim();
  const WS_URL = API_URL.startsWith('https') 
    ? API_URL.replace('https', 'wss') 
    : API_URL.replace('http', 'ws');

  // CRITICAL: Initialize on USER GESTURE ONLY
  const startVoiceSession = async () => {
    try {
      setError(null);
      
      // Step 1: Get permission from backend
      const permissionRes = await fetch(`${API_URL}/permission/grant`, {
        method: 'POST',
        credentials: 'include', // CRITICAL: Send cookies
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (!permissionRes.ok) {
        throw new Error(`Permission denied: ${permissionRes.status}`);
      }

      // Step 2: Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        }
      });
      mediaStreamRef.current = stream;

      // Step 3: Create Audio Context
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      audioContextRef.current = new AudioContext({ sampleRate: 16000 });
      
      if (audioContextRef.current.state === 'suspended') {
        await audioContextRef.current.resume();
      }

      // Step 4: Connect to WebSocket with session in URL
      const sessionId = document.cookie
        .split('; ')
        .find(row => row.startsWith('flash_session_js='))  // Use JS-accessible cookie
        ?.split('=')[1];

      if (!sessionId) {
        throw new Error("No session cookie found. Please grant permission first.");
      }

      const ws = new WebSocket(`${WS_URL}/voice/stream?session_id=${sessionId}`);
      websocketRef.current = ws;
      
      ws.onopen = () => {
        setIsListening(true);
        console.log('Voice pipeline connected');
      };
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'transcript') {
          // Send to your plan preview
          fetch(`${API_URL}/plan/preview`, {
            method: 'POST',
            credentials: 'include',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task: data.text }) // Adjusted prop name to 'task'
          });
        }
        if (data.type === 'error') {
          setError(data.message);
          stopVoiceSession();
        }
      };
      
      ws.onerror = () => {
        setError('Voice connection lost');
        stopVoiceSession();
      };

      // Step 5: Send audio chunks
      const source = audioContextRef.current.createMediaStreamSource(stream);
      const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1);
      
      processor.onaudioprocess = (e) => {
        if (ws.readyState === WebSocket.OPEN) {
          const float32Array = e.inputBuffer.getChannelData(0);
          const int16Array = new Int16Array(float32Array.length);
          for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
          }
          ws.send(int16Array.buffer);
        }
      };
      
      source.connect(processor);
      processor.connect(audioContextRef.current.destination);

    } catch (err) {
      console.error('Voice init failed:', err);
      setError(err.message);
      stopVoiceSession();
    }
  };

  const stopVoiceSession = () => {
    setIsListening(false);
    if (websocketRef.current) websocketRef.current.close();
    if (audioContextRef.current) audioContextRef.current.close();
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop());
    }
  };

  useEffect(() => {
    return () => stopVoiceSession(); // Cleanup
  }, []);

  return (
    <div className="voice-widget">
      <button 
        onClick={isListening ? stopVoiceSession : startVoiceSession}
        className={isListening ? 'active' : ''}
        disabled={!!error}
        style={{ padding: '10px 20px', borderRadius: '5px', background: isListening ? 'red' : 'green', color: 'white', border: 'none', cursor: 'pointer' }}
      >
        {isListening ? '🔴 Stop' : '🎤 Start Voice'}
      </button>
      {error && <div className="error" style={{ color: 'red', marginTop: '5px' }}>{error}</div>}
      {isListening && <div className="indicator" style={{ color: '#0f0', marginTop: '5px' }}>Listening...</div>}
    </div>
  );
};

export default VoiceWidget;
