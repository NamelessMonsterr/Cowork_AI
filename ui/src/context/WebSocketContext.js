import React, { createContext, useContext, useEffect, useState, useRef, useCallback } from 'react';

const WebSocketContext = createContext(null);

export const useWebSocket = () => {
    return useContext(WebSocketContext);
};

export const WebSocketProvider = ({ url, children }) => {
    const [status, setStatus] = useState("DISCONNECTED");
    const [lastMessage, setLastMessage] = useState(null);
    const [connected, setConnected] = useState(false);
    const socketRef = useRef(null);
    const reconnectTimeoutRef = useRef(null);
    const mountedRef = useRef(true);

    const connect = useCallback(() => {
        // Don't connect if component is unmounted
        if (!mountedRef.current) return;
        
        const socket = new WebSocket(url);
        socketRef.current = socket;

        socket.onopen = () => {
            if (!mountedRef.current) return;
            console.log("Context: WebSocket Connected");
            setConnected(true);
            setStatus("CONNECTED");
        };

        socket.onclose = () => {
            if (!mountedRef.current) return;
            console.log("Context: WebSocket Disconnected");
            setConnected(false);
            setStatus("DISCONNECTED");
            // Reconnect only if still mounted
            if (mountedRef.current) {
                reconnectTimeoutRef.current = setTimeout(connect, 3000);
            }
        };

        socket.onmessage = (e) => {
            if (!mountedRef.current) return;
            try {
                const msg = JSON.parse(e.data);
                setLastMessage(msg);
            } catch (err) {
                console.error("Parse Error", err);
            }
        };
        
        socket.onerror = (e) => {
            // Suppress error logging during StrictMode cleanup
            if (!mountedRef.current) return;
            console.error("Context: WebSocket Error", e);
        };
    }, [url]);

    useEffect(() => {
        mountedRef.current = true;
        connect();
        
        return () => {
            mountedRef.current = false;
            if (reconnectTimeoutRef.current) {
                clearTimeout(reconnectTimeoutRef.current);
            }
            if (socketRef.current) {
                // Nullify callbacks to prevent any logging/state updates
                const sock = socketRef.current;
                sock.onopen = null;
                sock.onclose = null;
                sock.onerror = null;
                sock.onmessage = null;
                // Only close if actually OPEN (closing CONNECTING socket triggers browser warning)
                if (sock.readyState === WebSocket.OPEN) {
                    sock.close();
                }
                socketRef.current = null;
            }
        };
    }, [connect]);

    const value = {
        connected,
        status,
        lastMessage,
        socket: socketRef.current
    };

    return (
        <WebSocketContext.Provider value={value}>
            {children}
        </WebSocketContext.Provider>
    );
};
