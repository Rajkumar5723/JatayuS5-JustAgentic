import { useEffect, useRef, useState } from "react";

import VibeCoding from "./Vibecoding.jsx";
import { ProctoringMonitor, useProctoring } from "../shared/proctoring.jsx";
import { RoomScanGate } from "../shared/roomScan.jsx";
import { CODING_API as API } from "../shared/api.js";
import "./Codingtest.css";

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
        throw new Error(data.detail || "Request failed");
    }
    return data;
}

export default function VibeCodingRound({ token, initialSession = null }) {
    const [phase, setPhase] = useState(
        initialSession?.status === "submitted" ? "result" : initialSession?.status === "started" ? "test" : initialSession ? "intro" : "loading"
    );
    const [session, setSession] = useState(initialSession);
    const [roomScanReady, setRoomScanReady] = useState(false);
    const [result, setResult] = useState(initialSession?.status === "submitted" ? initialSession : null);
    const [showDone, setShowDone] = useState(false);
    const submitHandleRef = useRef(null);

    useEffect(() => {
        let cancelled = false;
        if (initialSession) return undefined;
        fetchJson(`${API}/coding/${token}`)
            .then((data) => {
                if (cancelled) return;
                setSession(data);
                setResult(data.status === "submitted" ? data : null);
                setPhase(data.status === "submitted" ? "result" : data.status === "started" ? "test" : "intro");
            })
            .catch(() => {
                if (!cancelled) setPhase("error");
            });
        return () => {
            cancelled = true;
        };
    }, [initialSession, token]);

    const startRound = async () => {
        if (!roomScanReady) return;
        try {
            const data = await fetchJson(`${API}/coding/${token}/start`, { method: "POST" });
            setSession(data);
            setPhase("test");
        } catch {
            setPhase("error");
        }
    };

    const handleComplete = (data) => {
        setResult(data);
        setPhase("result");
        setShowDone(true);
    };

    const proctoring = useProctoring({
        enabled: phase === "test",
        endpoint: `${API}/coding/${token}/proctoring/event`,
        onSevere: () => submitHandleRef.current?.(),
    });

    if (phase === "loading") {
        return (
            <div className="ct-full ct-center">
                <div className="ct-spinner" />
                <p className="ct-muted">Loading vibe coding round…</p>
            </div>
        );
    }

    if (phase === "error") {
        return (
            <div className="ct-full ct-center">
                <p className="ct-display">Link not found</p>
                <p className="ct-muted">This vibe coding link may be invalid or expired.</p>
            </div>
        );
    }

    if (phase === "result") {
        return (
            <>
                <div className="ct-full ct-center">
                    <p className="ct-eyebrow">Hiresy · Vibe Coding</p>
                    <p className="ct-display">Submission Received</p>
                    <p className="ct-body" style={{ maxWidth: 420, textAlign: "center" }}>
                        {result?.feedback || "Your vibe coding submission has been recorded and will be reviewed in the workflow."}
                    </p>
                    {result?.score_pct != null ? (
                        <p className="ct-muted" style={{ marginTop: 6 }}>
                            Score: {result.score_pct} {result?.passed ? "· Passed" : "· Not passed"}
                        </p>
                    ) : null}
                    <p className="ct-muted" style={{ marginTop: 5, fontSize: 12 }}>You may close this tab.</p>
                </div>
                {showDone && (
                    <div className="ct-overlay" onClick={() => setShowDone(false)}>
                        <div className="ct-modal" onClick={(e) => e.stopPropagation()}>
                            <div className="ct-modal-icon">✓</div>
                            <p className="ct-modal-title">Vibe Coding Complete</p>
                            <p className="ct-modal-body">
                                Your submission and proctoring evidence were saved successfully.
                            </p>
                            <button className="ct-btn" onClick={() => setShowDone(false)}>Got it</button>
                        </div>
                    </div>
                )}
            </>
        );
    }

    if (phase === "test" && session) {
        return (
            <>
                <VibeCoding
                    token={token}
                    test={session}
                    onComplete={handleComplete}
                    apiBase={API}
                    submitHandleRef={submitHandleRef}
                />
                <ProctoringMonitor
                    videoRef={proctoring.videoRef}
                    risk={proctoring.risk}
                    warning={proctoring.warning}
                    cameraReady={proctoring.cameraReady}
                />
            </>
        );
    }

    return (
        <div className="ct-split">
            <div className="ct-left" />
            <div className="ct-right">
                <div className="ct-intro-inner">
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                        <p className="ct-eyebrow">Hiresy · Vibe Coding</p>
                        <p className="ct-display">{session?.job_title}</p>
                        <p className="ct-body">Hi {session?.candidate_name}, your guided coding workspace is ready.</p>
                    </div>
                    <div className="ct-stats">
                        <div className="ct-stat"><p className="ct-stat-num">1</p><p className="ct-stat-label">Challenge</p></div>
                        <div className="ct-stat-sep" />
                        <div className="ct-stat"><p className="ct-stat-num">{session?.duration_mins}</p><p className="ct-stat-label">Minutes</p></div>
                        <div className="ct-stat-sep" />
                        <div className="ct-stat"><p className="ct-stat-num">{(session?.languages || []).length || 2}</p><p className="ct-stat-label">Languages</p></div>
                    </div>
                    <div className="ct-rules">
                        <p className="ct-rules-title">Before you begin</p>
                        {[
                            "The coding workspace unlocks only after QR verification and room scan approval",
                            "Camera and screen-share monitoring stay active during the round",
                            "AI assistant interactions are logged as part of the evidence trail",
                            "Use the workspace to structure, test, and submit your final solution",
                            "Do not refresh or close the tab during the round",
                        ].map((rule, index) => (
                            <div key={rule} className="ct-rule">
                                <span className="ct-rule-num">{String(index + 1).padStart(2, "0")}</span>
                                <span className="ct-rule-text">{rule}</span>
                            </div>
                        ))}
                    </div>
                    <RoomScanGate sessionToken={token} onReadyChange={(ready) => setRoomScanReady(ready)} />
                </div>
                <div className="ct-intro-footer">
                    <button className="ct-btn" onClick={startRound} disabled={!roomScanReady}>
                        {roomScanReady ? "Start Vibe Coding" : "Complete Room Scan to Start"}
                    </button>
                </div>
            </div>
        </div>
    );
}
