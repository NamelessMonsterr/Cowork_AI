import React, { useState, useEffect } from "react";
import "./App.css";
import { PluginsPanel } from "./components/PluginsPanel";
import { Onboarding } from "./components/Onboarding";
import SettingsPage from "./pages/SettingsPage";
import { WebSocketProvider, useWebSocket } from "./context/WebSocketContext";
import { MainLayout } from "./components/MainLayout";
import { CoreInterface } from "./components/CoreInterface";
import { PlanPreview } from "./components/PlanPreview";
import { TextCommandInput } from "./components/TextCommandInput";

// P2: Use dynamic port or default
const API_URL = window.BACKEND_URL || "http://127.0.0.1:8765";
const WS_URL = API_URL.replace("http", "ws") + "/ws";

function AppContent() {
  const { status: wsStatus, lastMessage } = useWebSocket();
  
  const [status, setStatus] = useState("I AM VENGEANCE");
  const [transcript, setTranscript] = useState("Click the core to activate voice command");
  const [time, setTime] = useState(new Date().toLocaleTimeString());
  const [activePanel, setActivePanel] = useState(null);
  const [history, setHistory] = useState([]);
  const [sessionActive, setSessionActive] = useState(false);
  const [timeLeft, setTimeLeft] = useState(0);
  const [showSessionModal, setShowSessionModal] = useState(false);
  const [showOnboarding, setShowOnboarding] = useState(false);
  
  // V2: Plan Preview State
  const [pendingPlan, setPendingPlan] = useState(null);
  const [pendingPlanId, setPendingPlanId] = useState(null);
  const [estimatedTime, setEstimatedTime] = useState(0);

  // --- Logic Hooks ---

  // 1. Time Update
  useEffect(() => {
    const interval = setInterval(() => setTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(interval);
  }, []);

  // 2. Onboarding Check
  useEffect(() => {
    if (!localStorage.getItem("flash_onboarding_complete")) setShowOnboarding(true);
  }, []);

  // 3. Poll Session Status
  useEffect(() => {
    const checkSession = async () => {
      try {
        const res = await fetch(`${API_URL}/permission/status`);
        const data = await res.json();
        setSessionActive(data.allowed);
        setTimeLeft(data.time_remaining);
        if (data.allowed) setShowSessionModal(false);
      } catch (err) { }
    };
    const interval = setInterval(checkSession, 5000);
    checkSession();
    return () => clearInterval(interval);
  }, []);

  // 4. Countdown
  useEffect(() => {
    if (!sessionActive || timeLeft <= 0) return;
    const timer = setInterval(() => setTimeLeft(prev => Math.max(0, prev - 1)), 1000);
    return () => clearInterval(timer);
  }, [sessionActive, timeLeft]);

  // 5. Handle WebSocket Messages (via Context)
  useEffect(() => {
    if (!lastMessage) return;
    const msg = lastMessage;
    
    // Match backend event names from main.py
    if (msg.event === "listening_started") {
      setStatus("LISTENING");
      setTranscript("Listening for your command...");
    } else if (msg.event === "speech_recognized") {
      setStatus("PROCESSING");
      setTranscript(`"${msg.data.text}"`);
      setHistory(prev => [...prev, { time: new Date().toLocaleTimeString(), text: msg.data.text }]);
    } else if (msg.event === "plan_started" || msg.event === "plan_generated") {
      setStatus("PLANNING");
      setTranscript("Creating execution plan...");
    } else if (msg.event === "step_started") {
      setStatus("EXECUTING");
      setTranscript(`Executing step ${msg.data.step_id}...`);
    } else if (msg.event === "step_completed") {
      // Update transcript with result
      if (msg.data.success) {
        setTranscript(`Step ${msg.data.step_id} completed.`);
      } else {
        setTranscript(`Step failed: ${msg.data.error}`);
      }
    } else if (msg.event === "execution_finished") {
      setStatus("I AM VENGEANCE");
      setTranscript("Task completed successfully!");
      setTimeout(() => setTranscript("Click the core to activate voice command"), 3000);
    } else if (msg.event === "execution_error") {
      setStatus("I AM VENGEANCE");
      setTranscript(`Error: ${msg.data.error}`);
    } else if (msg.event === "voice_speak") {
      const utterance = new SpeechSynthesisUtterance(msg.data.text);
      window.speechSynthesis.speak(utterance);
    } else if (msg.type === "PERMISSION_REQUIRED" || msg.event === "permission_required") {
      setSessionActive(false);
      setStatus("I AM VENGEANCE");
      setTranscript(msg.data?.reason || "Session expired.");
      setShowSessionModal(true);
    } else if (msg.event === "permission_granted") {
      setSessionActive(true);
    } else if (msg.event === "permission_revoked") {
      setSessionActive(false);
    }
  }, [lastMessage]);

  // --- Handlers ---

  const handleCoreClick = async () => {
    if (status !== "I AM VENGEANCE") return;

    // Visual mic check (optional)
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        setTimeout(() => stream.getTracks().forEach(t => t.stop()), 6000);
    } catch (e) { /* ignore */ }

    setStatus("LISTENING");
    setTranscript("Listening for your command...");

    try {
      // Grant session first
      await fetch(`${API_URL}/permission/grant`, { method: "POST" });
      setSessionActive(true);
      
      // Then call voice/listen
      const response = await fetch(`${API_URL}/voice/listen`, { method: "POST" });
      const data = await response.json();
      if (!data.success) {
        setStatus("I AM VENGEANCE");
        setTranscript(data.message || "No speech detected.");
        setSessionActive(false);
      }
    } catch (err) {
      setStatus("I AM VENGEANCE");
      setTranscript("Backend not responding.");
      setSessionActive(false);
    }
  };

  const handleOnboardingComplete = () => {
    localStorage.setItem("flash_onboarding_complete", "true");
    setShowOnboarding(false);
  };

  // V2: Text Command Handler - Gets plan preview first
  const handleTextCommand = async (commandText) => {
    setStatus("PLANNING");
    setTranscript("Generating plan preview...");
    
    try {
      // Grant session
      await fetch(`${API_URL}/permission/grant`, { method: "POST" });
      setSessionActive(true);
      
      // Get plan preview
      const response = await fetch(`${API_URL}/plan/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: commandText })
      });
      
      if (!response.ok) throw new Error("Plan generation failed");
      
      const data = await response.json();
      setPendingPlan(data.plan);
      setPendingPlanId(data.plan_id);
      setEstimatedTime(data.estimated_time_sec);
      setTranscript("Review plan and approve to execute");
    } catch (err) {
      setStatus("I AM VENGEANCE");
      setTranscript(`Error: ${err.message}`);
    }
  };

  // V2: Plan Approval Handler
  const handleApprovePlan = async (planId) => {
    setStatus("EXECUTING");
    setTranscript("Executing approved plan...");
    setPendingPlan(null);
    setPendingPlanId(null);
    
    try {
      const response = await fetch(`${API_URL}/plan/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ plan_id: planId })
      });
      
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || "Approval failed");
      }
      // Execution events will come via WebSocket
    } catch (err) {
      setStatus("I AM VENGEANCE");
      setTranscript(`Error: ${err.message}`);
    }
  };

  // V2: Plan Cancel Handler
  const handleCancelPlan = () => {
    setPendingPlan(null);
    setPendingPlanId(null);
    setStatus("I AM VENGEANCE");
    setTranscript("Plan cancelled. Click the core to try again.");
  };

  // --- Render ---

  return (
    <MainLayout 
        time={time} 
        status={status} 
        sessionActive={sessionActive} 
        timeLeft={timeLeft}
    >
        <CoreInterface 
            status={status} 
            transcript={transcript} 
            onClick={handleCoreClick} 
        />

        {/* V2: Text Command Input (Voice Fallback) */}
        <TextCommandInput 
            onSubmit={handleTextCommand}
            disabled={status !== "I AM VENGEANCE"}
            placeholder="Type a command (e.g., 'Open Notepad')..."
        />

        {/* V2: Plan Preview Modal */}
        {pendingPlan && (
            <PlanPreview 
                plan={pendingPlan}
                planId={pendingPlanId}
                estimatedTime={estimatedTime}
                onApprove={handleApprovePlan}
                onCancel={handleCancelPlan}
            />
        )}

        {/* Footer Navigation */}
        <footer className="footer">
            {['settings', 'history', 'plugins', 'help'].map(panel => (
                <button 
                    key={panel}
                    className={`footer-btn ${activePanel === panel ? "active" : ""}`}
                    onClick={() => setActivePanel(activePanel === panel ? null : panel)}
                >
                    {panel.toUpperCase()}
                </button>
            ))}
        </footer>

        {/* Panels */}
        {activePanel === "plugins" && <PluginsPanel onClose={() => setActivePanel(null)} />}
        
        {activePanel === "settings" && (
            <div className="panel-overlay" onClick={() => setActivePanel(null)}>
                <div className="panel" onClick={e => e.stopPropagation()}>
                    <div className="panel-header">
                        <h2>⚙️ SETTINGS</h2>
                        <button className="panel-close" onClick={() => setActivePanel(null)}>✕</button>
                    </div>
                    <div className="panel-content" style={{ padding: 0 }}>
                        <SettingsPage apiUrl={API_URL} />
                    </div>
                </div>
            </div>
        )}

        {/* ... Other panels (History/Help) simplified for brevity in this refactor step ... */}
        {activePanel === "history" && (
          <div className="panel-overlay" onClick={() => setActivePanel(null)}>
            <div className="panel" onClick={(e) => e.stopPropagation()}>
              <div className="panel-header"><h2>📜 HISTORY</h2></div>
              <div className="panel-content">
                 <ul className="history-list">
                    {history.slice().reverse().map((item, i) => (
                       <li key={i} className="history-item">
                           <span className="history-time">{item.time}</span>
                           <span className="history-text">"{item.text}"</span>
                       </li>
                    ))}
                 </ul>
              </div>
            </div>
          </div>
        )}
        
        {activePanel === "help" && (
           <div className="panel-overlay" onClick={() => setActivePanel(null)}>
             <div className="panel" onClick={(e) => e.stopPropagation()}>
               <div className="panel-header"><h2>❓ HELP</h2></div>
               <div className="panel-content">
                  <p>Voice Commands: Click core + Speak.</p>
                  <p>Try: "Open Notepad", "Type Hello".</p>
               </div>
             </div>
           </div>
        )}

        {/* Modals */}
        {showSessionModal && (
            <div className="panel-overlay">
                <div className="panel" style={{ maxWidth: "400px", textAlign: "center" }}>
                    <h2 style={{ color: "#ff4444" }}>⚠️ SESSION EXPIRED</h2>
                    <p>Click the Core to re-authenticate.</p>
                    <button className="footer-btn active" onClick={() => setShowSessionModal(false)}>CLOSE</button>
                </div>
            </div>
        )}

        {showOnboarding && <Onboarding onComplete={handleOnboardingComplete} />}
    </MainLayout>
  );
}

export default function App() {
    return (
        <WebSocketProvider url={WS_URL}>
            <AppContent />
        </WebSocketProvider>
    );
}
