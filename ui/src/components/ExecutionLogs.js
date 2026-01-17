import React, { useState, useEffect, useCallback } from 'react';

/**
 * ExecutionLogs Component - V23 Observability Dashboard
 * 
 * Timeline view showing:
 * - Transcript
 * - Plan ID
 * - Step ID  
 * - Strategy used
 * - Verification result
 * - Recovery attempts
 */
export function ExecutionLogs({ apiUrl }) {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all'); // all, success, failed, recovery

    const fetchLogs = useCallback(async () => {
        try {
            const res = await fetch(`${apiUrl}/logs/recent`);
            if (!res.ok) throw new Error('Failed to fetch logs');
            const data = await res.json();
            setLogs(data.logs || []);
            setError(null);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }, [apiUrl]);

    useEffect(() => {
        fetchLogs();
        // Auto-refresh every 10 seconds
        const interval = setInterval(fetchLogs, 10000);
        return () => clearInterval(interval);
    }, [fetchLogs]);

    const handleExport = () => {
        const dataStr = JSON.stringify(logs, null, 2);
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `flash-logs-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    };

    const filteredLogs = logs.filter(log => {
        if (filter === 'all') return true;
        if (filter === 'success') return log.success === true;
        if (filter === 'failed') return log.success === false;
        if (filter === 'recovery') return log.recovery_attempted;
        return true;
    });

    const styles = {
        container: {
            padding: '20px',
            color: '#fff'
        },
        header: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px'
        },
        title: {
            color: '#ffd700',
            fontSize: '1.2rem',
            margin: 0
        },
        controls: {
            display: 'flex',
            gap: '12px',
            alignItems: 'center'
        },
        select: {
            padding: '8px 12px',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '6px',
            color: '#fff',
            fontSize: '0.9rem'
        },
        button: {
            padding: '8px 16px',
            background: 'rgba(255,215,0,0.2)',
            border: '1px solid #ffd700',
            borderRadius: '6px',
            color: '#ffd700',
            cursor: 'pointer',
            fontSize: '0.9rem'
        },
        refreshBtn: {
            background: 'rgba(0,255,0,0.1)',
            borderColor: '#00ff00',
            color: '#00ff00'
        },
        timeline: {
            borderLeft: '2px solid rgba(255,215,0,0.3)',
            marginLeft: '10px',
            paddingLeft: '20px'
        },
        logEntry: {
            position: 'relative',
            marginBottom: '16px',
            padding: '14px',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.1)'
        },
        logDot: {
            position: 'absolute',
            left: '-26px',
            top: '18px',
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: '#ffd700'
        },
        logDotSuccess: { background: '#00ff00' },
        logDotFailed: { background: '#ff4444' },
        logDotRecovery: { background: '#ffaa00' },
        logHeader: {
            display: 'flex',
            justifyContent: 'space-between',
            marginBottom: '8px'
        },
        logTime: {
            color: '#888',
            fontSize: '0.8rem'
        },
        logTask: {
            color: '#fff',
            fontWeight: 'bold',
            marginBottom: '8px'
        },
        logMeta: {
            display: 'flex',
            gap: '16px',
            flexWrap: 'wrap',
            fontSize: '0.85rem',
            color: '#aaa'
        },
        metaItem: {
            display: 'flex',
            gap: '4px'
        },
        metaLabel: {
            color: '#666'
        },
        badge: {
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.75rem',
            fontWeight: 'bold'
        },
        badgeSuccess: {
            background: 'rgba(0,255,0,0.2)',
            color: '#00ff00'
        },
        badgeFailed: {
            background: 'rgba(255,0,0,0.2)',
            color: '#ff4444'
        },
        badgeRecovery: {
            background: 'rgba(255,170,0,0.2)',
            color: '#ffaa00'
        },
        emptyState: {
            textAlign: 'center',
            padding: '40px',
            color: '#666'
        },
        error: {
            color: '#ff4444',
            padding: '16px',
            background: 'rgba(255,0,0,0.1)',
            borderRadius: '8px'
        }
    };

    if (loading) {
        return <div style={styles.container}>Loading execution logs...</div>;
    }

    if (error) {
        return (
            <div style={styles.container}>
                <div style={styles.error}>⚠️ {error}</div>
                <button style={{...styles.button, marginTop: '12px'}} onClick={fetchLogs}>
                    Retry
                </button>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h3 style={styles.title}>📊 Execution Timeline</h3>
                <div style={styles.controls}>
                    <select 
                        style={styles.select} 
                        value={filter}
                        onChange={e => setFilter(e.target.value)}
                    >
                        <option value="all">All Events</option>
                        <option value="success">Successful</option>
                        <option value="failed">Failed</option>
                        <option value="recovery">Recovery Attempts</option>
                    </select>
                    <button style={{...styles.button, ...styles.refreshBtn}} onClick={fetchLogs}>
                        🔄 Refresh
                    </button>
                    <button style={styles.button} onClick={handleExport}>
                        📥 Export JSON
                    </button>
                </div>
            </div>

            {filteredLogs.length === 0 ? (
                <div style={styles.emptyState}>
                    <p>📭 No execution logs yet</p>
                    <p style={{fontSize: '0.9rem'}}>Execute some commands to see the timeline</p>
                </div>
            ) : (
                <div style={styles.timeline}>
                    {filteredLogs.map((log, i) => (
                        <div key={log.id || i} style={styles.logEntry}>
                            <div style={{
                                ...styles.logDot,
                                ...(log.success ? styles.logDotSuccess : styles.logDotFailed),
                                ...(log.recovery_attempted ? styles.logDotRecovery : {})
                            }} />
                            
                            <div style={styles.logHeader}>
                                <span style={styles.logTime}>
                                    {new Date(log.timestamp * 1000).toLocaleString()}
                                </span>
                                <span style={{
                                    ...styles.badge,
                                    ...(log.success ? styles.badgeSuccess : styles.badgeFailed)
                                }}>
                                    {log.success ? 'SUCCESS' : 'FAILED'}
                                </span>
                            </div>
                            
                            <div style={styles.logTask}>
                                {log.task || log.transcript || 'Unknown Task'}
                            </div>
                            
                            <div style={styles.logMeta}>
                                <div style={styles.metaItem}>
                                    <span style={styles.metaLabel}>Plan:</span>
                                    <span>{log.plan_id?.slice(0, 8) || 'N/A'}</span>
                                </div>
                                <div style={styles.metaItem}>
                                    <span style={styles.metaLabel}>Steps:</span>
                                    <span>{log.step_count || 0}</span>
                                </div>
                                <div style={styles.metaItem}>
                                    <span style={styles.metaLabel}>Strategy:</span>
                                    <span>{log.strategy || 'auto'}</span>
                                </div>
                                {log.error && (
                                    <div style={{...styles.metaItem, color: '#ff4444', flex: '1 0 100%'}}>
                                        <span style={styles.metaLabel}>Error:</span>
                                        <span>{log.error}</span>
                                    </div>
                                )}
                                {log.recovery_attempted && (
                                    <div style={{...styles.metaItem, flex: '1 0 100%'}}>
                                        <span style={{...styles.badge, ...styles.badgeRecovery}}>
                                            RECOVERY {log.recovery_success ? 'SUCCEEDED' : 'FAILED'}
                                        </span>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default ExecutionLogs;
