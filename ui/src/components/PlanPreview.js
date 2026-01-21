import React from 'react';

/**
 * PlanPreview Component - Shows pending plan steps with approve/cancel buttons.
 * Now includes violation display for rejected plans.
 * 
 * Props:
 *   - plan: ExecutionPlan object with steps
 *   - planId: Plan ID for approval
 *   - estimatedTime: Estimated execution time in seconds
 *   - onApprove: Function called when user approves
 *   - onCancel: Function called when user cancels
 *   - rejected: Boolean - true if plan was rejected
 *   - violations: Array of violation strings
 *   - onEditSettings: Function to open safety settings
 */
export function PlanPreview({ 
    plan, 
    planId, 
    estimatedTime, 
    onApprove, 
    onCancel, 
    rejected = false, 
    violations = [], 
    onEditSettings 
}) {
    if (!plan) return null;

    const styles = {
        overlay: {
            position: 'fixed',
            top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0, 0, 0, 0.85)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            backdropFilter: 'blur(5px)'
        },
        panel: {
            background: 'linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)',
            border: rejected ? '2px solid #ff4444' : '2px solid #ffd700',
            borderRadius: '16px',
            padding: '24px',
            maxWidth: '600px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: rejected ? '0 0 40px rgba(255, 68, 68, 0.3)' : '0 0 40px rgba(255, 215, 0, 0.3)'
        },
        header: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            borderBottom: rejected ? '1px solid rgba(255, 68, 68, 0.3)' : '1px solid rgba(255, 215, 0, 0.3)',
            paddingBottom: '12px'
        },
        title: {
            color: rejected ? '#ff4444' : '#ffd700',
            fontSize: '1.5rem',
            fontWeight: 'bold',
            margin: 0
        },
        meta: {
            color: '#888',
            fontSize: '0.9rem'
        },
        violationBox: {
            background: 'rgba(255, 0, 0, 0.1)',
            border: '2px solid #ff4444',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '16px'
        },
        violationTitle: {
            color: '#ff4444',
            fontSize: '1.1rem',
            fontWeight: 'bold',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
        },
        violationList: {
            listStyle: 'none',
            padding: 0,
            margin: '8px 0'
        },
        violationItem: {
            color: '#ffaaaa',
            fontSize: '0.9rem',
            marginBottom: '8px',
            paddingLeft: '20px',
            position: 'relative',
            lineHeight: '1.4'
        },
        violationBullet: {
            position: 'absolute',
            left: 0,
            color: '#ff4444',
            fontWeight: 'bold'
        },
        settingsBtn: {
            background: 'rgba(255, 215, 0, 0.2)',
            color: '#ffd700',
            border: '1px solid #ffd700',
            padding: '10px 16px',
            borderRadius: '6px',
            fontSize: '0.9rem',
            cursor: 'pointer',
            marginTop: '12px',
            transition: 'all 0.3s ease',
            width: '100%'
        },
        stepList: {
            listStyle: 'none',
            padding: 0,
            margin: '16px 0'
        },
        step: {
            background: 'rgba(255, 255, 255, 0.05)',
            borderRadius: '8px',
            padding: '12px 16px',
            marginBottom: '8px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            opacity: rejected ? 0.5 : 1
        },
        stepNumber: {
            background: rejected ? '#666' : '#ffd700',
            color: '#1a1a2e',
            width: '28px',
            height: '28px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 'bold',
            flexShrink: 0
        },
        stepContent: {
            flex: 1
        },
        stepTool: {
            color: rejected ? '#888' : '#ffd700',
            fontWeight: 'bold',
            fontSize: '0.95rem'
        },
        stepDesc: {
            color: '#ccc',
            fontSize: '0.85rem',
            marginTop: '4px'
        },
        buttons: {
            display: 'flex',
            gap: '12px',
            marginTop: '20px'
        },
        btn: {
            flex: 1,
            padding: '14px 24px',
            border: 'none',
            borderRadius: '8px',
            fontSize: '1rem',
            fontWeight: 'bold',
            cursor: 'pointer',
            transition: 'all 0.3s ease'
        },
        approveBtn: {
            background: rejected ? '#444' : 'linear-gradient(135deg, #00ff00 0%, #00cc00 100%)',
            color: rejected ? '#888' : '#000',
            cursor: rejected ? 'not-allowed' : 'pointer',
            opacity: rejected ? 0.5 : 1
        },
        cancelBtn: {
            background: 'rgba(255, 255, 255, 0.1)',
            color: '#fff',
            border: '1px solid rgba(255, 255, 255, 0.3)'
        }
    };

    return (
        <div style={styles.overlay} onClick={onCancel}>
            <div style={styles.panel} onClick={e => e.stopPropagation()} data-testid="plan-preview">
                <div style={styles.header}>
                    <h2 style={styles.title}>
                        {rejected ? '🛡️ PLAN REJECTED' : '📋 PLAN PREVIEW'}
                    </h2>
                    <span style={styles.meta}>
                        {plan.steps?.length || 0} steps • ~{estimatedTime}s
                    </span>
                </div>

                <p style={{ color: '#fff', marginBottom: '16px' }}>
                    <strong>Task:</strong> {plan.task}
                </p>

                {/* Violations Display */}
                {rejected && violations.length > 0 && (
                    <div style={styles.violationBox}>
                        <div style={styles.violationTitle}>
                            🛡️ Blocked by Safety Policy
                        </div>
                        <ul style={styles.violationList}>
                            {violations.map((violation, index) => (
                                <li key={index} style={styles.violationItem} title={violation}>
                                    <span style={styles.violationBullet}>•</span>
                                    {violation}
                                </li>
                            ))}
                        </ul>
                        {onEditSettings && (
                            <button
                                style={styles.settingsBtn}
                                onClick={onEditSettings}
                                onMouseOver={e => e.target.style.background = 'rgba(255, 215, 0, 0.3)'}
                                onMouseOut={e => e.target.style.background = 'rgba(255, 215, 0, 0.2)'}
                            >
                                ⚙️ Edit Safety Settings
                            </button>
                        )}
                    </div>
                )}

                <ul style={styles.stepList}>
                    {plan.steps?.map((step, index) => (
                        <li key={step.id || index} style={styles.step}>
                            <span style={styles.stepNumber}>{index + 1}</span>
                            <div style={styles.stepContent}>
                                <div style={styles.stepTool}>{step.tool}</div>
                                <div style={styles.stepDesc}>{step.description}</div>
                            </div>
                        </li>
                    ))}
                </ul>

                <div style={styles.buttons}>
                    <button 
                        style={{...styles.btn, ...styles.cancelBtn}}
                        onClick={onCancel}
                    >
                        ❌ CLOSE
                    </button>
                    <button 
                        style={{...styles.btn, ...styles.approveBtn}}
                        onClick={() => !rejected && onApprove(planId)}
                        disabled={rejected}
                        data-testid="plan-approve-button"
                        title={rejected ? "Plan rejected by safety policy" : "Approve and execute plan"}
                    >
                        {rejected ? '🚫 BLOCKED' : '✅ APPROVE & EXECUTE'}
                    </button>
                </div>
            </div>
        </div>
    );
}

export default PlanPreview;
