import React from 'react';
import '../App.css';

export const CoreInterface = ({ status, transcript, onClick }) => {
  return (
    <div className="core-interface">
      <div
        className={`hex-frame ${status.toLowerCase().replace(/ /g, "-")}`}
        onClick={onClick}
      >
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
  );
};
