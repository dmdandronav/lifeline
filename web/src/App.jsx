import { useEffect, useRef } from 'react';
import { useCall, TACTICS } from './lib/useCall.js';
import Gauge from './components/Gauge.jsx';

export default function App() {
  const { state, start, requestHandoff } = useCall();
  const transcriptRef = useRef(null);

  useEffect(() => {
    const el = transcriptRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [state.turns.length]);

  const idle = state.status === 'idle';

  return (
    <div className="console">
      <header className="topbar">
        <div className="brand">
          <span className="brand__dot" data-live={state.status === 'live' || state.status === 'handoff'} />
          <div>
            <h1>LIFELINE</h1>
            <p>a real-time firewall for phone scams</p>
          </div>
        </div>
        <div className="time-wasted">
          <span className="time-wasted__num">{state.timeWasted.toFixed(0)}s</span>
          <span className="time-wasted__label">scammer time wasted</span>
        </div>
      </header>

      <div className="grid">
        <section className="transcript-pane">
          <div className="transcript" ref={transcriptRef}>
            {idle && (
              <div className="placeholder">
                <p>A simulated “grandson in jail” scam call. Watch the tactics light up and the pressure climb — then hand the call to the AI when it’s armed.</p>
              </div>
            )}
            {state.turns.map((turn, i) => (
              <div key={i} className={`bubble bubble--${turn.speaker}`}>
                <span className="bubble__who">{whoLabel(turn.speaker)}</span>
                <p className="bubble__text">{turn.text}</p>
                {turn.tactics?.length > 0 && (
                  <div className="bubble__tactics">
                    {turn.tactics.map((t) => (
                      <span key={t.tactic} className="tactic-tag">{t.label}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
            {state.status === 'ended' && (
              <div className="ended">Call ended · {prettyReason(state.endReason)}</div>
            )}
          </div>
        </section>

        <aside className="rack">
          <Gauge pressure={state.pressure} threshold={state.threshold} />

          <div className="chips">
            {TACTICS.map((t) => (
              <div
                key={t.key}
                className={`chip ${state.activeTactics.includes(t.key) ? 'chip--on' : ''}`}
              >
                {t.label}
              </div>
            ))}
          </div>

          {idle || state.status === 'ended' ? (
            <button className="cta cta--start" onClick={start}>
              {state.status === 'ended' ? '↺ Replay the call' : '▶ Play the scam call'}
            </button>
          ) : (
            <button
              className={`cta cta--handoff ${state.handoffAvailable ? 'is-armed' : ''}`}
              onClick={requestHandoff}
              disabled={!state.handoffAvailable || state.status === 'handoff'}
            >
              {state.status === 'handoff' ? 'AI has the call…' : state.handoffAvailable ? '☎ Hand off to AI' : 'Gauge arming…'}
            </button>
          )}

          <p className="ethics">Defensive demo. Bundled scripted call — no real telephony, nothing dialed.</p>
        </aside>
      </div>
    </div>
  );
}

function whoLabel(speaker) {
  return speaker === 'scammer' ? 'Caller' : speaker === 'agent' ? 'LIFELINE AI' : 'You';
}

function prettyReason(reason) {
  if (reason === 'agent_exhausted_scammer') return 'the AI ran out the scammer';
  if (reason === 'script_complete') return 'scammer finished the script';
  return reason ?? '';
}
