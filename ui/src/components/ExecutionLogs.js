import React, { useState, useEffect, useCallback, useMemo } from 'react';

/**
 * ExecutionLogs Component - V23 Observability Dashboard
 * 
 * Task Grouping View showing:
 * - Tasks grouped by task_id
 * - Plans nested under tasks by plan_id
 * - Steps nested under plans
 * - Expandable/collapsible hierarchy
 */
export function ExecutionLogs({ apiUrl }) {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all'); // all, success, failed, recovery
    const [expandedTasks, setExpandedTasks] = useState(new Set());
    const [expandedPlans, setExpandedPlans] = useState(new Set());
    const [viewMode, setViewMode] = useState('grouped'); // grouped, timeline

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

    // Group logs by task_id -> plan_id -> steps
    const groupedData = useMemo(() => {
        const taskMap = new Map();
        
        logs.forEach(log => {
            const taskId = log.task_id || log.plan_id || 'no-task';
            const planId = log.plan_id || 'no-plan';
            
            if (!taskMap.has(taskId)) {
                taskMap.set(taskId, {
                    id: taskId,
                    name: log.task || log.transcript || 'Unknown Task',
                    timestamp: log.timestamp,
                    plans: new Map(),
                    success: true,
                    totalSteps: 0
                });
            }
            
            const task = taskMap.get(taskId);
            
            if (!task.plans.has(planId)) {
                task.plans.set(planId, {
                    id: planId,
                    steps: [],
                    success: true,
                    strategy: log.strategy
                });
            }
            
            const plan = task.plans.get(planId);
            plan.steps.push(log);
            task.totalSteps++;
            
            if (!log.success) {
                plan.success = false;
                task.success = false;
            }
        });
        
        return Array.from(taskMap.values()).map(task => ({
            ...task,
            plans: Array.from(task.plans.values())
        })).sort((a, b) => b.timestamp - a.timestamp);
    }, [logs]);

    const filteredLogs = logs.filter(log => {
        if (filter === 'all') return true;
        if (filter === 'success') return log.success === true;
        if (filter === 'failed') return log.success === false;
        if (filter === 'recovery') return log.recovery_attempted;
        return true;
    });

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

    const toggleTask = (taskId) => {
        setExpandedTasks(prev => {
            const next = new Set(prev);
            if (next.has(taskId)) next.delete(taskId);
            else next.add(taskId);
            return next;
        });
    };

    const togglePlan = (planId) => {
        setExpandedPlans(prev => {
            const next = new Set(prev);
            if (next.has(planId)) next.delete(planId);
            else next.add(planId);
            return next;
        });
    };

    const expandAll = () => {
        setExpandedTasks(new Set(groupedData.map(t => t.id)));
        setExpandedPlans(new Set(groupedData.flatMap(t => t.plans.map(p => p.id))));
    };

    const collapseAll = () => {
        setExpandedTasks(new Set());
        setExpandedPlans(new Set());
    };

    const styles = {
        container: {
            padding: '20px',
            color: '#fff'
        },
        header: {
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '20px',
            flexWrap: 'wrap',
            gap: '12px'
        },
        title: {
            color: '#ffd700',
            fontSize: '1.2rem',
            margin: 0
        },
        controls: {
            display: 'flex',
            gap: '8px',
            alignItems: 'center',
            flexWrap: 'wrap'
        },
        select: {
            padding: '8px 12px',
            background: 'rgba(0,0,0,0.3)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: '6px',
            color: '#fff',
            fontSize: '0.85rem'
        },
        button: {
            padding: '6px 12px',
            background: 'rgba(255,215,0,0.2)',
            border: '1px solid #ffd700',
            borderRadius: '6px',
            color: '#ffd700',
            cursor: 'pointer',
            fontSize: '0.85rem'
        },
        refreshBtn: {
            background: 'rgba(0,255,0,0.1)',
            borderColor: '#00ff00',
            color: '#00ff00'
        },
        toggleBtn: {
            background: 'rgba(100,100,255,0.15)',
            borderColor: '#aaf',
            color: '#aaf'
        },
        // Grouped view styles
        taskGroup: {
            marginBottom: '12px',
            borderRadius: '10px',
            overflow: 'hidden',
            background: 'rgba(0,0,0,0.2)',
            border: '1px solid rgba(255,255,255,0.1)'
        },
        taskHeader: {
            display: 'flex',
            alignItems: 'center',
            padding: '12px 16px',
            cursor: 'pointer',
            background: 'rgba(255,215,0,0.08)',
            borderBottom: '1px solid rgba(255,255,255,0.05)',
            gap: '12px'
        },
        taskHeaderHover: {
            background: 'rgba(255,215,0,0.15)'
        },
        expandIcon: {
            fontSize: '0.8rem',
            color: '#888',
            transition: 'transform 0.2s'
        },
        expandIconOpen: {
            transform: 'rotate(90deg)'
        },
        taskName: {
            flex: 1,
            fontWeight: 'bold',
            color: '#fff'
        },
        taskMeta: {
            display: 'flex',
            gap: '12px',
            fontSize: '0.8rem',
            color: '#888'
        },
        planGroup: {
            marginLeft: '20px',
            borderLeft: '2px solid rgba(255,215,0,0.2)'
        },
        planHeader: {
            display: 'flex',
            alignItems: 'center',
            padding: '10px 14px',
            cursor: 'pointer',
            background: 'rgba(255,255,255,0.02)',
            gap: '10px'
        },
        planId: {
            fontFamily: 'monospace',
            fontSize: '0.85rem',
            color: '#aaa'
        },
        stepList: {
            marginLeft: '16px',
            borderLeft: '1px solid rgba(100,100,255,0.2)',
            paddingLeft: '12px'
        },
        stepItem: {
            padding: '8px 12px',
            margin: '4px 0',
            background: 'rgba(255,255,255,0.03)',
            borderRadius: '6px',
            fontSize: '0.85rem'
        },
        stepAction: {
            color: '#fff',
            marginBottom: '4px'
        },
        stepMeta: {
            display: 'flex',
            gap: '12px',
            fontSize: '0.75rem',
            color: '#777'
        },
        badge: {
            display: 'inline-block',
            padding: '2px 8px',
            borderRadius: '4px',
            fontSize: '0.7rem',
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
        // Timeline view styles (existing)
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
        },
        stats: {
            display: 'flex',
            gap: '20px',
            marginBottom: '16px',
            padding: '12px 16px',
            background: 'rgba(255,255,255,0.03)',
            borderRadius: '8px',
            fontSize: '0.85rem'
        },
        statItem: {
            display: 'flex',
            gap: '6px',
            alignItems: 'center'
        },
        statLabel: {
            color: '#888'
        },
        statValue: {
            fontWeight: 'bold',
            color: '#ffd700'
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

    const successCount = logs.filter(l => l.success).length;
    const failedCount = logs.filter(l => !l.success).length;
    const recoveryCount = logs.filter(l => l.recovery_attempted).length;

    const renderGroupedView = () => (
        <div>
            {groupedData.length === 0 ? (
                <div style={styles.emptyState}>
                    <p>📭 No execution logs yet</p>
                    <p style={{fontSize: '0.9rem'}}>Execute some commands to see the grouped view</p>
                </div>
            ) : (
                groupedData.map(task => (
                    <div key={task.id} style={styles.taskGroup}>
                        <div 
                            style={styles.taskHeader}
                            onClick={() => toggleTask(task.id)}
                        >
                            <span style={{
                                ...styles.expandIcon,
                                ...(expandedTasks.has(task.id) ? styles.expandIconOpen : {})
                            }}>▶</span>
                            <span style={styles.taskName}>{task.name}</span>
                            <div style={styles.taskMeta}>
                                <span>{task.plans.length} plan(s)</span>
                                <span>{task.totalSteps} step(s)</span>
                                <span style={{
                                    ...styles.badge,
                                    ...(task.success ? styles.badgeSuccess : styles.badgeFailed)
                                }}>
                                    {task.success ? '✓' : '✗'}
                                </span>
                            </div>
                        </div>
                        
                        {expandedTasks.has(task.id) && (
                            <div style={styles.planGroup}>
                                {task.plans.map(plan => (
                                    <div key={plan.id}>
                                        <div 
                                            style={styles.planHeader}
                                            onClick={() => togglePlan(plan.id)}
                                        >
                                            <span style={{
                                                ...styles.expandIcon,
                                                ...(expandedPlans.has(plan.id) ? styles.expandIconOpen : {})
                                            }}>▶</span>
                                            <span style={styles.planId}>📋 {plan.id.slice(0, 12)}...</span>
                                            <span style={{fontSize: '0.8rem', color: '#666'}}>
                                                {plan.strategy || 'auto'} • {plan.steps.length} steps
                                            </span>
                                            <span style={{
                                                ...styles.badge,
                                                ...(plan.success ? styles.badgeSuccess : styles.badgeFailed)
                                            }}>
                                                {plan.success ? '✓' : '✗'}
                                            </span>
                                        </div>
                                        
                                        {expandedPlans.has(plan.id) && (
                                            <div style={styles.stepList}>
                                                {plan.steps.map((step, i) => (
                                                    <div key={step.id || i} style={styles.stepItem}>
                                                        <div style={styles.stepAction}>
                                                            {step.step_id ? `Step ${step.step_id}: ` : ''}
                                                            {step.action || step.task || 'Action'}
                                                        </div>
                                                        <div style={styles.stepMeta}>
                                                            <span>
                                                                {new Date(step.timestamp * 1000).toLocaleTimeString()}
                                                            </span>
                                                            {step.duration_ms && (
                                                                <span>{step.duration_ms}ms</span>
                                                            )}
                                                            <span style={{
                                                                color: step.success ? '#0f0' : '#f44'
                                                            }}>
                                                                {step.success ? '✓ OK' : '✗ Failed'}
                                                            </span>
                                                            {step.recovery_attempted && (
                                                                <span style={styles.badgeRecovery}>
                                                                    RECOVERY
                                                                </span>
                                                            )}
                                                        </div>
                                                        {step.error && (
                                                            <div style={{color: '#f66', fontSize: '0.75rem', marginTop: '4px'}}>
                                                                ⚠️ {step.error}
                                                            </div>
                                                        )}
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))
            )}
        </div>
    );

    const renderTimelineView = () => (
        <>
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
        </>
    );

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h3 style={styles.title}>📊 Execution Dashboard</h3>
                <div style={styles.controls}>
                    <select 
                        style={styles.select}
                        value={viewMode}
                        onChange={e => setViewMode(e.target.value)}
                    >
                        <option value="grouped">📁 Grouped View</option>
                        <option value="timeline">📅 Timeline View</option>
                    </select>
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
                    {viewMode === 'grouped' && (
                        <>
                            <button style={{...styles.button, ...styles.toggleBtn}} onClick={expandAll}>
                                ⊞ Expand
                            </button>
                            <button style={{...styles.button, ...styles.toggleBtn}} onClick={collapseAll}>
                                ⊟ Collapse
                            </button>
                        </>
                    )}
                    <button style={{...styles.button, ...styles.refreshBtn}} onClick={fetchLogs}>
                        🔄
                    </button>
                    <button style={styles.button} onClick={handleExport}>
                        📥 Export
                    </button>
                </div>
            </div>

            {/* Stats Bar */}
            <div style={styles.stats}>
                <div style={styles.statItem}>
                    <span style={styles.statLabel}>Total:</span>
                    <span style={styles.statValue}>{logs.length}</span>
                </div>
                <div style={styles.statItem}>
                    <span style={styles.statLabel}>Tasks:</span>
                    <span style={styles.statValue}>{groupedData.length}</span>
                </div>
                <div style={styles.statItem}>
                    <span style={{...styles.statLabel, color: '#0f0'}}>✓ Success:</span>
                    <span style={{...styles.statValue, color: '#0f0'}}>{successCount}</span>
                </div>
                <div style={styles.statItem}>
                    <span style={{...styles.statLabel, color: '#f44'}}>✗ Failed:</span>
                    <span style={{...styles.statValue, color: '#f44'}}>{failedCount}</span>
                </div>
                {recoveryCount > 0 && (
                    <div style={styles.statItem}>
                        <span style={{...styles.statLabel, color: '#fa0'}}>↻ Recovery:</span>
                        <span style={{...styles.statValue, color: '#fa0'}}>{recoveryCount}</span>
                    </div>
                )}
            </div>

            {viewMode === 'grouped' ? renderGroupedView() : renderTimelineView()}
        </div>
    );
}

export default ExecutionLogs;
