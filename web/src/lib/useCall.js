import { useCallback, useEffect, useRef, useState } from 'react';

// The 5 tactics, in display order. Keys match the backend classifier.
export const TACTICS = [
  { key: 'urgency', label: 'Urgency' },
  { key: 'authority_impersonation', label: 'Authority' },
  { key: 'payment_redirection', label: 'Payment' },
  { key: 'secrecy_isolation', label: 'Secrecy' },
  { key: 'emotional_leverage', label: 'Emotional' },
];

const initialState = {
  status: 'idle', // idle | live | handoff | ended
  turns: [], // { speaker, text, tactics }
  pressure: 0,
  threshold: 1,
  handoffAvailable: false,
  activeTactics: [], // tactic keys lit by the latest scammer line
  timeWasted: 0,
  endReason: null,
};

// Drives one call over the WebSocket and exposes the reducer-like state plus a
// requestHandoff() action. Deterministic bundled scenario; no keys required.
export function useCall() {
  const [state, setState] = useState(initialState);
  const wsRef = useRef(null);

  const start = useCallback(() => {
    wsRef.current?.close();
    setState({ ...initialState, status: 'live' });

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/call?scenario=grandson_jail`);
    wsRef.current = ws;

    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      setState((s) => reduce(s, msg));
    };
    ws.onclose = () => setState((s) => (s.status === 'ended' ? s : { ...s, status: 'ended', endReason: s.endReason ?? 'disconnected' }));
  }, []);

  const requestHandoff = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ action: 'handoff' }));
  }, []);

  useEffect(() => () => wsRef.current?.close(), []);

  return { state, start, requestHandoff };
}

function reduce(s, msg) {
  switch (msg.type) {
    case 'call_started':
      return { ...s, status: 'live' };
    case 'utterance': {
      const activeTactics = msg.speaker === 'scammer' ? msg.tactics.map((t) => t.tactic) : s.activeTactics;
      return {
        ...s,
        turns: [...s.turns, { speaker: msg.speaker, text: msg.text, tactics: msg.tactics }],
        pressure: msg.pressure,
        threshold: msg.threshold,
        handoffAvailable: msg.handoff_available,
        activeTactics,
      };
    }
    case 'handoff_engaged':
      return { ...s, status: 'handoff' };
    case 'agent_reply':
      return {
        ...s,
        turns: [...s.turns, { speaker: 'agent', text: msg.text, tactics: [] }],
        timeWasted: msg.time_wasted_total ?? s.timeWasted,
      };
    case 'call_ended':
      return { ...s, status: 'ended', endReason: msg.reason };
    default:
      return s;
  }
}
