import React, { useState } from 'react';

/**
 * TextCommandInput Component - Text input for commands (voice fallback).
 * 
 * Props:
 *   - onSubmit: Function called with the command text
 *   - disabled: Whether input is disabled
 *   - placeholder: Placeholder text
 */
export function TextCommandInput({ onSubmit, disabled = false, placeholder = "Type a command..." }) {
    const [input, setInput] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim() || disabled || isSubmitting) return;
        
        setIsSubmitting(true);
        try {
            await onSubmit(input.trim());
            setInput('');
        } finally {
            setIsSubmitting(false);
        }
    };

    const styles = {
        container: {
            display: 'flex',
            gap: '8px',
            padding: '12px',
            background: 'rgba(0, 0, 0, 0.3)',
            borderRadius: '12px',
            border: '1px solid rgba(255, 215, 0, 0.3)',
            marginTop: '20px'
        },
        input: {
            flex: 1,
            background: 'rgba(255, 255, 255, 0.1)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '8px',
            padding: '12px 16px',
            color: '#fff',
            fontSize: '1rem',
            outline: 'none',
            transition: 'border-color 0.3s ease'
        },
        inputFocus: {
            borderColor: '#ffd700'
        },
        button: {
            background: 'linear-gradient(135deg, #ffd700 0%, #ffaa00 100%)',
            color: '#000',
            border: 'none',
            borderRadius: '8px',
            padding: '12px 24px',
            fontSize: '1rem',
            fontWeight: 'bold',
            cursor: disabled || isSubmitting ? 'not-allowed' : 'pointer',
            opacity: disabled || isSubmitting ? 0.6 : 1,
            transition: 'all 0.3s ease'
        },
        label: {
            color: '#888',
            fontSize: '0.85rem',
            marginBottom: '8px',
            display: 'block'
        }
    };

    return (
        <form onSubmit={handleSubmit} style={styles.container}>
            <input
                type="text"
                id="cmd-input"
                name="command"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={placeholder}
                disabled={disabled || isSubmitting}
                style={styles.input}
                data-testid="command-input"
                autoComplete="off"
            />
            <button 
                type="submit" 
                disabled={disabled || isSubmitting || !input.trim()}
                style={styles.button}
            >
                {isSubmitting ? '...' : '⚡ EXECUTE'}
            </button>
        </form>
    );
}

export default TextCommandInput;
