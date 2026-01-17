import React from 'react';
import '../App.css';

export const MainLayout = ({ children, time, status, sessionActive, timeLeft }) => {
    
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  return (
    <div className="app">
      {/* Visual Effects */}
      <div className="scan-line"></div>
      <div className="corner corner-tl"></div>
      <div className="corner corner-tr"></div>
      <div className="corner corner-bl"></div>
      <div className="corner corner-br"></div>
      
      {/* Background */}
      <div className="hex-bg"></div>
      <div className="particles">
          {[...Array(12)].map((_, i) => <div key={i} className="particle"></div>)}
      </div>

      {/* Header */}
      <header className="header">
        <div className="logo">FLASH</div>
        <div className="header-info">
          <div>TIME: <span>{time}</span></div>
          <div>STATUS: <span>{status}</span></div>
          <div>
            SESSION:{" "}
            <span className={sessionActive ? "session-active" : "session-inactive"}>
              {sessionActive ? `ACTIVE (${formatTime(timeLeft)})` : "INACTIVE"}
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="main">
        {children}
      </main>
    </div>
  );
};
