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
 *   - rejected: Boolean - true if plan was rejected
 *   - violations: Array of violation strings
 *   - onEditSettings: Function called when user clicks edit settings
 */
export function PlanPreview({ plan, planId, estimatedTime, onApprove, onCancel, rejected = false, violations = [], onEditSettings }) {
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
            backdrop
