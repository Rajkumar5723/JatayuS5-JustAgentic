import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import "./HRCopilot.css";
import { LIVEHR_API as API, LIVEHR_WS as WS_URL } from "../shared/api.js";

const SCORE_FIELDS = [
    { key: "technical_depth", label: "Technical Depth" },
    { key: "communication", label: "Communication" },
    { key: "problem_solving", label: "Problem Solving" },
    { key: "role_fit", label: "Role Fit" },
];

function defaultScores(source = {}) {
    return SCORE_FIELDS.reduce((acc, field) => {
        const value = Number(source[field.key]);
        acc[field.key] = Number.isFinite(value) ? value : 7;
        return acc;
    }, {});
}

function scoreTone(value) {
    if (value >= 8) return "#22c55e";
    if (value >= 6) return "#f59e0b";
    if (value >= 4) return "#ff6a00";
    return "#ef4444";
}

function typeColor(type) {
    return ({ technical: "#60a5fa", behavioral: "#a78bfa", project: "#22c55e", situational: "#2dd4bf" })[type] || "#555";
}

function priorityColor(priority) {
    return priority === "high" ? "#ef4444" : priority === "medium" ? "#f59e0b" : "#444";
}

function snapshotFromVideo(videoEl) {
    if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) return "";
    const canvas = document.createElement("canvas");
    canvas.width = Math.min(960, videoEl.videoWidth);
    canvas.height = Math.round((canvas.width / videoEl.videoWidth) * videoEl.videoHeight);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.82);
}

export default function LiveHR() {
    const { token } = useParams();
    const [session, setSession] = useState(null);
    const [transcript, setTranscript] = useState([]);
    const [suggestions, setSuggestions] = useState([]);
    const [insight, setInsight] = useState("");
    const [flag, setFlag] = useState("");
    const [connected, setConnected] = useState(false);
    const [tab, setTab] = useState("suggest");
    const [pinned, setPinned] = useState([]);
    const [question, setQuestion] = useState("");
    const [asking, setAsking] = useState(false);
    const [copiedIdx, setCopiedIdx] = useState(null);
    const [ending, setEnding] = useState(false);
    const [showOutcome, setShowOutcome] = useState(false);
    const [pipelineStatus, setPipelineStatus] = useState("");
    const [outcomeError, setOutcomeError] = useState("");
    const [isListening, setIsListening] = useState(false);
    const [audioMode, setAudioMode] = useState("");
    const [captureError, setCaptureError] = useState("");
    const [liveInterim, setLiveInterim] = useState("");
    const [outcomeForm, setOutcomeForm] = useState({
        manual_decision: "pass",
        hr_reason: "",
        hr_scores: defaultScores(),
    });

    const wsRef = useRef(null);
    const transcriptEl = useRef(null);
    const recognitionRef = useRef(null);
    const micStreamRef = useRef(null);
    const tabStreamRef = useRef(null);
    const displayVideoRef = useRef(null);
    const audioContextRef = useRef(null);
    const snapshotTimerRef = useRef(null);
    const speakingRef = useRef(false);

    const applySessionPayload = (data, syncReview = false) => {
        setSession(data);
        if (data.transcript) setTranscript(data.transcript.split("\n").filter(Boolean));
        if (Array.isArray(data.suggestions)) setSuggestions(data.suggestions);
        if (data.ai_reason) setInsight(data.ai_reason);
        if (Array.isArray(data.ai_flags) && data.ai_flags.length) {
            setFlag(data.ai_flags[data.ai_flags.length - 1]);
        }
        if (syncReview) {
            setOutcomeForm({
                manual_decision: data.outcome || "pass",
                hr_reason: data.manual_reason || "",
                hr_scores: defaultScores(data.manual_score && Object.keys(data.manual_score).length ? data.manual_score : data.ai_score),
            });
        }
    };

    const scrollTranscriptToEnd = useCallback(() => {
        window.setTimeout(() => {
            if (transcriptEl.current) {
                transcriptEl.current.scrollTop = transcriptEl.current.scrollHeight;
            }
        }, 50);
    }, []);

    const postLiveEvent = useCallback(async (eventType, payload = {}) => {
        if (!token) return null;
        try {
            const res = await fetch(`${API}/livehr/session/${token}/event`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ event_type: eventType, payload }),
            });
            return await res.json().catch(() => ({}));
        } catch {
            return null;
        }
    }, [token]);

    const sendCaption = useCallback(async (text, speaker = "conversation") => {
        const cleaned = String(text || "").trim();
        if (!cleaned || !token) return;
        const socket = wsRef.current;
        if (socket?.readyState === WebSocket.OPEN) {
            socket.send(JSON.stringify({ type: "caption", text: cleaned, speaker }));
            return;
        }
        try {
            await fetch(`${API}/livehr/caption`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token, text: cleaned, speaker }),
            });
        } catch {
            // best effort only
        }
    }, [token]);

    const stopListening = useCallback(() => {
        speakingRef.current = false;
        setIsListening(false);
        setAudioMode("");
        setLiveInterim("");
        window.clearInterval(snapshotTimerRef.current);
        snapshotTimerRef.current = null;
        try {
            recognitionRef.current?.stop();
        } catch {
            // no-op
        }
        recognitionRef.current = null;
        micStreamRef.current?.getTracks().forEach((track) => track.stop());
        micStreamRef.current = null;
        tabStreamRef.current?.getTracks().forEach((track) => track.stop());
        tabStreamRef.current = null;
        audioContextRef.current?.close?.().catch?.(() => {});
        audioContextRef.current = null;
        if (displayVideoRef.current) {
            displayVideoRef.current.srcObject = null;
        }
    }, []);

    const startSnapshotLoop = useCallback((stream) => {
        if (!displayVideoRef.current || !stream) return;
        displayVideoRef.current.srcObject = stream;
        displayVideoRef.current.muted = true;
        displayVideoRef.current.playsInline = true;
        displayVideoRef.current.play().catch(() => {});
        window.clearInterval(snapshotTimerRef.current);
        snapshotTimerRef.current = window.setInterval(() => {
            const snapshot_b64 = snapshotFromVideo(displayVideoRef.current);
            if (snapshot_b64) {
                void postLiveEvent("meet_snapshot_captured", {
                    snapshot_b64,
                    source: "live_room_capture",
                });
            }
        }, 15000);
    }, [postLiveEvent]);

    const startListening = useCallback(async () => {
        const SpeechApi = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechApi) {
            setCaptureError("Speech recognition requires Chrome or another Chromium browser.");
            return;
        }

        setCaptureError("");
        setLiveInterim("");

        try {
            micStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        } catch {
            setCaptureError("Microphone access is required to capture the interview transcript.");
            return;
        }

        try {
            const tabStream = await navigator.mediaDevices.getDisplayMedia({
                video: true,
                audio: true,
            });
            tabStreamRef.current = tabStream;
            startSnapshotLoop(tabStream);
            setAudioMode(tabStream.getAudioTracks().length ? "Room audio + snapshots" : "Snapshots only");
        } catch {
            setAudioMode("Microphone only");
            setCaptureError("Screen share was skipped. Transcript capture can continue, but live room snapshots will be limited.");
        }

        const recognition = new SpeechApi();
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";
        recognition.onresult = (event) => {
            let interim = "";
            let finalChunk = "";
            for (let index = event.resultIndex; index < event.results.length; index += 1) {
                const piece = event.results[index][0]?.transcript || "";
                if (event.results[index].isFinal) {
                    finalChunk += ` ${piece}`;
                } else {
                    interim += ` ${piece}`;
                }
            }
            setLiveInterim(interim.trim());
            if (finalChunk.trim()) {
                void sendCaption(finalChunk.trim(), "conversation");
            }
        };
        recognition.onerror = () => {};
        recognition.onend = () => {
            if (speakingRef.current) {
                try {
                    recognition.start();
                } catch {
                    // no-op
                }
            }
        };

        speakingRef.current = true;
        recognitionRef.current = recognition;
        recognition.start();
        setIsListening(true);
        void postLiveEvent("session_opened", {
            source: "live_room_app",
            user_agent: navigator.userAgent,
        });
    }, [postLiveEvent, sendCaption, startSnapshotLoop]);

    useEffect(() => {
        fetch(`${API}/livehr/session/${token}`)
            .then((r) => r.json())
            .then((data) => applySessionPayload(data, true));
    }, [token]);

    useEffect(() => {
        if (!token) return undefined;
        const connect = () => {
            const ws = new WebSocket(`${WS_URL}/${token}`);
            wsRef.current = ws;
            ws.onopen = () => setConnected(true);
            ws.onclose = () => {
                setConnected(false);
                setTimeout(connect, 3000);
            };
            ws.onerror = () => ws.close();
            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === "init") {
                    applySessionPayload(msg, false);
                }
                if (msg.type === "update") {
                    if (msg.transcript_line) {
                        setTranscript((prev) => [...prev, msg.transcript_line]);
                        scrollTranscriptToEnd();
                    }
                    if (msg.suggestions?.length) setSuggestions(msg.suggestions);
                    if (msg.candidate_score) {
                        setSession((prev) => prev ? { ...prev, ai_score: { ...(prev.ai_score || {}), ...msg.candidate_score } } : prev);
                    }
                    if (msg.insight) setInsight(msg.insight);
                    if (msg.flag) setFlag(msg.flag);
                }
            };
        };
        connect();
        return () => wsRef.current?.close();
    }, [scrollTranscriptToEnd, token]);

    useEffect(() => {
        return () => {
            void postLiveEvent("session_closed", { source: "live_room_app" });
            stopListening();
        };
    }, [postLiveEvent, stopListening]);

    const askManual = async () => {
        if (!question.trim()) return;
        setAsking(true);
        try {
            const res = await fetch(
                `${API}/hr/ask?token=${token}&question=${encodeURIComponent(question)}`,
                { method: "POST" }
            );
            const data = await res.json();
            if (data.questions?.length) setSuggestions(data.questions);
            if (data.insight) setInsight(data.insight);
            if (data.scores) {
                setSession((prev) => prev ? { ...prev, ai_score: { ...(prev.ai_score || {}), ...data.scores } } : prev);
            }
            setQuestion("");
        } catch {
            // best effort only
        } finally {
            setAsking(false);
        }
    };

    const setScore = (key, value) => {
        const numeric = Number(value);
        setOutcomeForm((prev) => ({
            ...prev,
            hr_scores: {
                ...prev.hr_scores,
                [key]: Number.isFinite(numeric) ? Math.max(0, Math.min(10, numeric)) : 0,
            },
        }));
    };

    const endInterview = async (decision) => {
        const reason = outcomeForm.hr_reason.trim();
        if (!reason) {
            setOutcomeError("Add the HR review reason before ending the interview.");
            return;
        }
        setOutcomeError("");
        setEnding(true);
        try {
            const res = await fetch(`${API}/livehr/session/${token}/outcome`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    outcome: decision,
                    manual_decision: decision,
                    hr_reason: reason,
                    hr_scores: outcomeForm.hr_scores,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Could not save the outcome");

            if (data.session) applySessionPayload(data.session, true);
            setPipelineStatus(data.application_status || "");
            setShowOutcome(false);
        } catch (err) {
            setOutcomeError(err.message || "Could not save the outcome");
        } finally {
            setEnding(false);
        }
    };

    const copy = (text, idx) => {
        navigator.clipboard.writeText(text);
        setCopiedIdx(idx);
        setTimeout(() => setCopiedIdx(null), 1500);
    };

    const pin = (item) => {
        if (!pinned.find((entry) => entry.text === item.text)) {
            setPinned((prev) => [...prev, item]);
        }
    };

    const aiScore = session?.ai_score || session?.candidate_score || {};
    const manualScore = session?.manual_score || {};
    const gh = session?.github_data || {};
    const topRepos = gh.top_repos || [];
    const langs = Object.entries(gh.languages || {}).slice(0, 6);
    const aiFlags = session?.ai_flags || [];
    const displayedOutcome = pipelineStatus || (session?.outcome === "pass" ? "bgv_pending" : session?.outcome === "fail" ? "rejected" : "");

    if (!session) {
        return (
            <div className="lhr-loading">
                <div className="lhr-spinner" />
                <p>Loading copilot...</p>
            </div>
        );
    }

    return (
        <div className="lhr-root">
            <div className="lhr-topbar">
                <div className="lhr-topbar-left">
                    <span className="lhr-eyebrow">Hiresy Live HR Copilot</span>
                    <div className="lhr-topbar-divider" />
                    <span className="lhr-candidate">{session.candidate_name}</span>
                    <span className="lhr-role">{session.job_title}</span>
                </div>
                <div className="lhr-topbar-right">
                    <div className={`lhr-dot ${connected ? "live" : "off"}`} />
                    <span className="lhr-dot-label">{connected ? "Live" : "Reconnecting"}</span>

                    {session.status === "ended" ? (
                        <span className="lhr-ended-badge">
                            Interview Ended {displayedOutcome === "bgv_pending" ? "- Sent to BGV" : displayedOutcome === "rejected" ? "- Rejected" : ""}
                        </span>
                    ) : (
                        <button className="lhr-meet-btn" onClick={() => window.open(session.meet_url, "_blank")}>
                            Open Live Room
                        </button>
                    )}

                    {session.status !== "ended" && (
                        <button className="lhr-end-btn" onClick={() => setShowOutcome(true)}>
                            End Interview
                        </button>
                    )}
                </div>
            </div>

            <div className="lhr-main">
                <div className="lhr-transcript-col">
                    <div className="lhr-room-panel">
                        <div className="lhr-room-head">
                            <div>
                                <p className="lhr-room-title">Embedded Live Room</p>
                                <p className="lhr-room-copy">This desk replaces the Google Meet extension flow with an in-app live room.</p>
                            </div>
                            <button className="lhr-room-link" onClick={() => window.open(session.meet_url, "_blank")}>
                                Open In New Tab
                            </button>
                        </div>
                        <div className="lhr-room-frame-shell">
                            {session.meet_url ? (
                                <iframe
                                    title="Live Interview Room"
                                    src={session.meet_url}
                                    allow="camera; microphone; fullscreen; display-capture; autoplay"
                                    className="lhr-room-frame"
                                />
                            ) : (
                                <div className="lhr-room-empty">Preparing live room...</div>
                            )}
                        </div>
                        <div className="lhr-capture-row">
                            <button className={`lhr-capture-btn ${isListening ? "active" : ""}`} onClick={isListening ? stopListening : startListening}>
                                {isListening ? "Stop Capture" : "Start Capture"}
                            </button>
                            <p className="lhr-capture-status">
                                {audioMode || "Start capture to feed transcript updates, AI guidance, and room snapshots into the workflow."}
                            </p>
                        </div>
                        {captureError ? <p className="lhr-capture-error">{captureError}</p> : null}
                        {liveInterim ? <p className="lhr-live-interim">Listening: {liveInterim}</p> : null}
                        <video ref={displayVideoRef} style={{ display: "none" }} muted playsInline autoPlay />
                    </div>
                    <p className="lhr-col-title">Live Transcript</p>
                    <div className="lhr-transcript" ref={transcriptEl}>
                        {transcript.length === 0 ? (
                            <div className="lhr-empty">
                                <p>Waiting for live transcript updates...</p>
                                <p style={{ marginTop: 8, fontSize: 12, opacity: 0.5 }}>
                                    Start capture after opening the live room so the copilot can follow the interview.
                                </p>
                            </div>
                        ) : transcript.map((line, i) => {
                            const isCandidate = line.includes("[candidate]");
                            const isHr = line.includes("[hr]");
                            return (
                                <div key={i} className={`lhr-line ${isCandidate ? "cand" : isHr ? "hr" : ""}`}>
                                    <p className="lhr-line-text">{line}</p>
                                </div>
                            );
                        })}
                    </div>

                    <div className="lhr-ask-row">
                        <input
                            className="lhr-ask-input"
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onKeyDown={(e) => e.key === "Enter" && askManual()}
                            placeholder="Type a topic to get question suggestions..."
                        />
                        <button className="lhr-ask-btn" onClick={askManual} disabled={asking}>
                            {asking ? "..." : "Ask AI"}
                        </button>
                    </div>
                </div>

                <div className="lhr-side">
                    <div className="lhr-tabs">
                        {[["suggest", "Suggestions"], ["review", "Review"], ["profile", "Profile"], ["pinned", "Pinned"]].map(([id, label]) => (
                            <button key={id} className={`lhr-tab ${tab === id ? "active" : ""}`} onClick={() => setTab(id)}>
                                {label}
                            </button>
                        ))}
                    </div>

                    <div className="lhr-tab-body">
                        {tab === "suggest" && (
                            <>
                                {flag && (
                                    <div className="lhr-flag">
                                        <span>!</span>
                                        <p>{flag}</p>
                                    </div>
                                )}
                                {insight && (
                                    <div className="lhr-insight">
                                        <span>i</span>
                                        <p>{insight}</p>
                                    </div>
                                )}

                                {aiFlags.length > 1 && (
                                    <div className="lhr-review-panel">
                                        <p className="lhr-section">AI Flags</p>
                                        <div className="lhr-flag-list">
                                            {aiFlags.map((item) => <span key={item} className="lhr-chip">{item}</span>)}
                                        </div>
                                    </div>
                                )}

                                <p className="lhr-section">Suggested Questions</p>
                                {suggestions.length === 0 ? (
                                    <p className="lhr-empty-small">Suggestions appear as the interview progresses...</p>
                                ) : suggestions.map((item, i) => (
                                    <div key={i} className="lhr-card">
                                        <div className="lhr-card-top">
                                            <span className="lhr-tag" style={{ color: typeColor(item.type), borderColor: `${typeColor(item.type)}30` }}>
                                                {item.type}
                                            </span>
                                            <span className="lhr-priority" style={{ color: priorityColor(item.priority) }}>
                                                {item.priority}
                                            </span>
                                        </div>
                                        <p className="lhr-card-text">{item.text}</p>
                                        <div className="lhr-card-actions">
                                            <button className="lhr-action" onClick={() => copy(item.text, i)}>
                                                {copiedIdx === i ? "Copied" : "Copy"}
                                            </button>
                                            <button className="lhr-action" onClick={() => pin(item)}>Pin</button>
                                        </div>
                                    </div>
                                ))}
                            </>
                        )}

                        {tab === "review" && (
                            <>
                                <div className="lhr-review-panel">
                                    <div className="lhr-review-header">
                                        <p className="lhr-section">Interview Decision</p>
                                        {session.status === "ended" ? (
                                            <span className={`lhr-review-status ${displayedOutcome === "bgv_pending" ? "pass" : displayedOutcome === "rejected" ? "fail" : ""}`}>
                                                {displayedOutcome === "bgv_pending" ? "BGV Pending" : displayedOutcome === "rejected" ? "Rejected" : session.outcome || "Ended"}
                                            </span>
                                        ) : null}
                                    </div>
                                    <p className="lhr-review-text">
                                        {session.final_summary || session.manual_reason || session.ai_reason || "No final summary saved yet."}
                                    </p>
                                    {session.status !== "ended" && (
                                        <div className="lhr-review-actions">
                                            <button className="lhr-review-cta" onClick={() => setShowOutcome(true)}>
                                                Capture HR Decision
                                            </button>
                                        </div>
                                    )}
                                </div>

                                <div className="lhr-review-grid">
                                    <div className="lhr-review-panel">
                                        <p className="lhr-section">AI Scorecard</p>
                                        <div className="lhr-score-grid">
                                            {SCORE_FIELDS.map((field) => {
                                                const value = Number(aiScore[field.key]);
                                                return (
                                                    <div key={field.key} className="lhr-score-card">
                                                        <span className="lhr-score-title">{field.label}</span>
                                                        <strong className="lhr-score-num" style={{ color: scoreTone(value || 0) }}>
                                                            {Number.isFinite(value) ? value.toFixed(1) : "--"}
                                                        </strong>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                        <div className="lhr-summary-box">
                                            <strong>AI Reason</strong>
                                            <p>{session.ai_reason || "AI reasoning has not been captured yet."}</p>
                                        </div>
                                    </div>

                                    <div className="lhr-review-panel">
                                        <p className="lhr-section">HR Scorecard</p>
                                        <div className="lhr-score-grid">
                                            {SCORE_FIELDS.map((field) => {
                                                const value = Number(manualScore[field.key]);
                                                return (
                                                    <div key={field.key} className="lhr-score-card">
                                                        <span className="lhr-score-title">{field.label}</span>
                                                        <strong className="lhr-score-num" style={{ color: scoreTone(value || 0) }}>
                                                            {Number.isFinite(value) ? value.toFixed(1) : "--"}
                                                        </strong>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                        <div className="lhr-summary-box">
                                            <strong>HR Reason</strong>
                                            <p>{session.manual_reason || "HR reasoning will appear here after the interview is ended."}</p>
                                        </div>
                                    </div>
                                </div>
                            </>
                        )}

                        {tab === "profile" && (
                            <>
                                {session.eval_summary && (
                                    <div className="lhr-eval-box">
                                        <p className="lhr-section">AI Evaluation Summary</p>
                                        <p className="lhr-eval-text">{session.eval_summary}</p>
                                    </div>
                                )}
                                <p className="lhr-section" style={{ marginTop: 16 }}>GitHub</p>
                                <div className="lhr-gh-row">
                                    {[["Repos", gh.total_repos || "--"], ["Stars", gh.total_stars || "--"], ["Followers", gh.followers || "--"]].map(([label, value]) => (
                                        <div key={label} className="lhr-gh-stat">
                                            <p className="lhr-gh-num">{value}</p>
                                            <p className="lhr-gh-label">{label}</p>
                                        </div>
                                    ))}
                                </div>
                                {langs.length > 0 && (
                                    <>
                                        <p className="lhr-section" style={{ marginTop: 16 }}>Languages</p>
                                        <div className="lhr-langs">
                                            {langs.map(([label]) => <span key={label} className="lhr-chip">{label}</span>)}
                                        </div>
                                    </>
                                )}
                                {topRepos.length > 0 && (
                                    <>
                                        <p className="lhr-section" style={{ marginTop: 16 }}>Projects</p>
                                        {topRepos.slice(0, 5).map((repo, i) => (
                                            <div key={i} className="lhr-repo">
                                                <div className="lhr-repo-top">
                                                    <p className="lhr-repo-name">{repo.name}</p>
                                                    <span className="lhr-repo-lang">{repo.language}</span>
                                                </div>
                                                {repo.description && <p className="lhr-repo-desc">{repo.description}</p>}
                                                <p className="lhr-repo-meta">Stars {repo.stars} · Forks {repo.forks}</p>
                                            </div>
                                        ))}
                                    </>
                                )}
                            </>
                        )}

                        {tab === "pinned" && (
                            <>
                                <p className="lhr-section">Pinned Questions</p>
                                {pinned.length === 0 ? (
                                    <p className="lhr-empty-small">Pin suggestions to save them here.</p>
                                ) : pinned.map((item, i) => (
                                    <div key={i} className="lhr-card">
                                        <span className="lhr-tag" style={{ color: typeColor(item.type), borderColor: `${typeColor(item.type)}30` }}>
                                            {item.type}
                                        </span>
                                        <p className="lhr-card-text" style={{ marginTop: 8 }}>{item.text}</p>
                                        <div className="lhr-card-actions">
                                            <button className="lhr-action" onClick={() => copy(item.text, `p${i}`)}>
                                                {copiedIdx === `p${i}` ? "Copied" : "Copy"}
                                            </button>
                                            <button className="lhr-action lhr-action-red" onClick={() => setPinned((prev) => prev.filter((_, idx) => idx !== i))}>
                                                Remove
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </>
                        )}
                    </div>
                </div>
            </div>

            {showOutcome && (
                <div className="lhr-overlay" onClick={() => setShowOutcome(false)}>
                    <div className="lhr-modal lhr-modal-wide" onClick={(e) => e.stopPropagation()}>
                        <p className="lhr-modal-title">Capture Final HR Review</p>
                        <p className="lhr-modal-body">
                            Save the HR scorecard and reasoning before moving this candidate to the next decision stage.
                        </p>

                        <div className="lhr-modal-form">
                            <div className="lhr-modal-section">
                                <p className="lhr-section">Rubric Scores (0-10)</p>
                                <div className="lhr-modal-grid">
                                    {SCORE_FIELDS.map((field) => (
                                        <label key={field.key} className="lhr-modal-field">
                                            <span className="lhr-modal-label">{field.label}</span>
                                            <input
                                                className="lhr-modal-input"
                                                type="number"
                                                min="0"
                                                max="10"
                                                step="0.5"
                                                value={outcomeForm.hr_scores[field.key]}
                                                onChange={(e) => setScore(field.key, e.target.value)}
                                            />
                                        </label>
                                    ))}
                                </div>
                            </div>

                            <div className="lhr-modal-section">
                                <p className="lhr-section">HR Reason</p>
                                <textarea
                                    className="lhr-modal-textarea"
                                    rows={5}
                                    value={outcomeForm.hr_reason}
                                    onChange={(e) => setOutcomeForm((prev) => ({ ...prev, hr_reason: e.target.value }))}
                                    placeholder="Summarize the interview outcome, strengths, risks, and why this candidate should move forward or stop here."
                                />
                            </div>
                        </div>

                        {outcomeError ? <p className="lhr-modal-error">{outcomeError}</p> : null}

                        <div className="lhr-modal-btns">
                            <button className="lhr-outcome-pass" disabled={ending} onClick={() => endInterview("pass")}>
                                {ending ? "Saving..." : "Pass - Send to Background Verification"}
                            </button>
                            <button className="lhr-outcome-fail" disabled={ending} onClick={() => endInterview("fail")}>
                                {ending ? "Saving..." : "Fail - Reject After HR Review"}
                            </button>
                        </div>
                        <button className="lhr-modal-cancel" onClick={() => setShowOutcome(false)}>
                            Cancel
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
