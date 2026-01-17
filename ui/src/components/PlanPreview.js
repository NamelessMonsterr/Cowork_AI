import React from 'react';

/**
 * PlanPreview Component - Shows pending plan steps with approve/cancel buttons.
 * 
 * Props:
 *   - plan: ExecutionPlan object with steps
 *   - planId: Plan ID for approval
 *   - estimatedTime: Estimated execution time in seconds
 *   - onApprove: Function called when user approves
 *   - onCancel: Function called when user cancels
 */
export function PlanPreview({ plan, planId, estimatedTime, onApprove, onCancel }) {
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
            border: '2px solid #ffd700',
            borderRadius: '16px',
            padding: '24px',
            maxWidth: '600px',
            width: '90%',
            maxHeight: '80vh',
            overflow: 'auto',
            boxShadow: '0 0 40px rgba(255, 215, 0, 0.3)'
        },
        header: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            borderBottom: '1px solid rgba(255, 215, 0, 0.3)',
            paddingBottom: '12px'
        },
        title: {
            color: '#ffd700',
            fontSize: '1.5rem',
            fontWeight: 'bold',
            margin: 0
        },
        meta: {
            color: '#888',
            fontSize: '0.9rem'
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
            gap: '12px'
        },
        stepNumber: {
            background: '#ffd700',
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
            color: '#ffd700',
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
            background: 'linear-gradient(135deg, #00ff00 0%, #00cc00 100%)',
            color: '#000'
        },
        cancelBtn: {
            background: 'rgba(255, 255, 255, 0.1)',
            color: '#fff',
            border: '1px solid rgba(255, 255, 255, 0.3)'
        }
    };

    return (
        <div style={styles.overlay} onClick={onCancel}>
            <div style={styles.panel} onClick={e => e.stopPropagation()}>
                <div style={styles.header}>
                    <h2 style={styles.title}>📋 PLAN PREVIEW</h2>
                    <span style={styles.meta}>
                        {plan.steps?.length || 0} steps • ~{estimatedTime}s
                    </span>
                </div>

                <p style={{ color: '#fff', marginBottom: '16px' }}>
                    <strong>Task:</strong> {plan.task}
                </p>

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
                        ❌ CANCEL
                    </button>
                    <button 
                        style={{...styles.btn, ...styles.approveBtn}}
                        onClick={() => onApprove(planId)}
                    >
                        ✅ APPROVE & EXECUTE
                    </button>
                </div>
            </div>
        </div>
    );
}

export default PlanPreview;
