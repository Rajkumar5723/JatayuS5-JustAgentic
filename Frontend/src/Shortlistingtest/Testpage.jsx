import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import "./Testpage.css";
import { ProctoringMonitor, useProctoring } from "../shared/proctoring.jsx";
import { RoomScanGate } from "../shared/roomScan.jsx";
import { TEST_API as API } from "../shared/api.js";

export default function TestPage() {
    const { token } = useParams();
    const [phase, setPhase] = useState("loading");
    const [test, setTest] = useState(null);
    const [current, setCurrent] = useState(0);
    const [answers, setAnswers] = useState([]);
    const [selected, setSelected] = useState(null);
    const [timeLeft, setTimeLeft] = useState(0);
    const [submitting, setSubmitting] = useState(false);
    const [showDone, setShowDone] = useState(false);
    const [roomScanReady, setRoomScanReady] = useState(false);
    const timerRef = useRef(null);
    const submitAttemptRef = useRef(() => {});
    const testStartedAtRef = useRef(null);
    const questionStartedAtRef = useRef(null);
    const selectionTimesRef = useRef({});
    const questionMetricsRef = useRef([]);

    useEffect(() => {
        fetch(`${API}/test/${token}`)
            .then(r => r.json())
            .then(data => {
                setRoomScanReady(false);
                if (data.status === "submitted") { setPhase("result"); }
                else { setTest(data); setPhase("intro"); }
            })
            .catch(() => setPhase("error"));
    }, [token]);

    const startTest = async () => {
        if (!roomScanReady) return;
        const startRes = await fetch(`${API}/test/${token}/start`, { method: "POST" });
        const started = await startRes.json();
        const activeTest = started?.questions?.length
            ? started
            : await fetch(`${API}/test/${token}`).then((r) => r.json());
        setTest(activeTest);
        setTimeLeft(activeTest.duration_mins * 60);
        setAnswers(new Array((activeTest.questions || []).length).fill(null));
        testStartedAtRef.current = new Date();
        questionStartedAtRef.current = Date.now();
        selectionTimesRef.current = {};
        questionMetricsRef.current = [];
        setPhase("test");
    };

    useEffect(() => {
        if (phase !== "test") return;
        timerRef.current = setInterval(() => {
            setTimeLeft(t => {
                if (t <= 1) { clearInterval(timerRef.current); submitAttemptRef.current(); return 0; }
                return t - 1;
            });
        }, 1000);
        return () => clearInterval(timerRef.current);
    }, [phase]);

    const formatTime = s =>
        `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

    const recordCurrentMetric = (finalAnswer = selected) => {
        if (!test?.questions?.[current]) return;
        const startedAtMs = questionStartedAtRef.current || Date.now();
        const endedAtMs = Date.now();
        const answeredAtMs = selectionTimesRef.current[current] || endedAtMs;
        questionMetricsRef.current[current] = {
            question_index: current + 1,
            selected_answer: finalAnswer,
            started_at: new Date(startedAtMs).toISOString(),
            ended_at: new Date(endedAtMs).toISOString(),
            answered_at: new Date(answeredAtMs).toISOString(),
            time_spent_seconds: Number(((endedAtMs - startedAtMs) / 1000).toFixed(2)),
            response_latency_seconds: Number(((answeredAtMs - startedAtMs) / 1000).toFixed(2)),
        };
    };

    const nextQuestion = () => {
        recordCurrentMetric(selected);
        const updated = [...answers];
        updated[current] = selected;
        setAnswers(updated);
        setSelected(null);
        if (current < test.questions.length - 1) {
            setCurrent(c => c + 1);
            // eslint-disable-next-line react-hooks/purity
            questionStartedAtRef.current = Date.now();
        }
        else handleSubmit(updated);
    };

    const handleSubmit = async (finalAnswers) => {
        clearInterval(timerRef.current);
        setSubmitting(true);
        const resolvedAnswers = finalAnswers || answers;
        if (phase === "test" && !questionMetricsRef.current[current]) {
            recordCurrentMetric(resolvedAnswers[current] ?? selected ?? 0);
        }
        const ans = resolvedAnswers.map(a => a ?? 0);
        const totalDurationSeconds = testStartedAtRef.current
            ? Number(((Date.now() - testStartedAtRef.current.getTime()) / 1000).toFixed(2))
            : null;
        try {
            const res = await fetch(`${API}/test/${token}/submit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    answers: ans,
                    telemetry: {
                        started_at: testStartedAtRef.current?.toISOString() || null,
                        submitted_at: new Date().toISOString(),
                        total_duration_seconds: totalDurationSeconds,
                        answered_count: ans.filter((value) => value !== 0).length,
                        question_metrics: questionMetricsRef.current.filter(Boolean),
                    },
                })
            });
            const data = await res.json();
            void data;
            setPhase("result"); setShowDone(true);
        } catch { setPhase("error"); }
    };
    submitAttemptRef.current = handleSubmit;

    const proctoring = useProctoring({
        enabled: phase === "test",
        endpoint: `${API}/test/${token}/proctoring/event`,
        onSevere: () => submitAttemptRef.current(),
    });

    const q = test?.questions?.[current];
    const progress = test ? (current / test.questions.length) * 100 : 0;
    const isLast = test && current === test.questions.length - 1;
    const answeredCount = answers.filter(a => a !== null).length;

    // ── LOADING ──
    if (phase === "loading") return (
        <div className="tp-split">
            <div className="tp-left" />
            <div className="tp-right">
                <div className="tp-right-centered">
                    <div className="tp-spinner" />
                    <p className="tp-caption" >Loading your test…</p>
                </div>
            </div>
            <ProctoringMonitor
                videoRef={proctoring.videoRef}
                risk={proctoring.risk}
                warning={proctoring.warning}
                cameraReady={proctoring.cameraReady}
            />
        </div>
    );

    // ── ERROR ──
    if (phase === "error") return (
        <div className="tp-split">
            <div className="tp-left" />
            <div className="tp-right">
                <div className="tp-right-centered">
                    <p className="tp-display">Link not found</p>
                    <p className="tp-caption">This test link may be invalid or has already been used.</p>
                </div>
            </div>
        </div>
    );

    // ── RESULT ──
    if (phase === "result") return (
        <>
            <div className="tp-split">
                <div className="tp-left" />
                <div className="tp-right">
                    <div className="tp-right-centered">
                        <p className="tp-eyebrow">Hiresy · Shortlisting</p>
                        <p className="tp-display">Test Submitted</p>
                        <p className="tp-body" style={{ maxWidth: 320,fontSize:'medium'  }}>
                            Your responses have been recorded. Our team will review your performance
                            and reach out by email if you are selected for the next round.
                        </p>
                        <p className="tp-caption" style={{ marginTop: 8, color:'orangered' }}><i>You may close this tab.</i></p>
                    </div>
                </div>
            </div>

            {showDone && (
                <div className="tp-overlay" onClick={() => setShowDone(false)}>
                    <div className="tp-modal" onClick={e => e.stopPropagation()}>
                        <img className="tp-modal-icon" src="/testdone.svg" alt="" />
                        <p className="tp-modal-title">Test Completed</p>
                        <p className="tp-modal-body">
                            Thank you for completing the shortlisting test. We will review your answers
                            and notify you by <span style={{ color: "#fff", fontWeight:'500' }}>email</span> if you are
                            selected to proceed.
                        </p>
                        <button className="tp-modal-btn" onClick={() => setShowDone(false)}>
                            Got it
                        </button>
                    </div>
                </div>
            )}
        </>
    );

    // ── INTRO ──
    if (phase === "intro" && test) return (
        <div className="tp-split">
            <div className="tp-left" />
            <div className="tp-right">
                {/* Scrollable content */}
                <div className="tp-intro-inner">
                    <div className="tp-flex-col tp-gap-1">
                        <p className="tp-eyebrow">Hiresy · Shortlisting Test</p>
                        <p className="tp-display">{test.job_title}</p>
                        <p className="tp-body">Hi <span style={{ fontWeight:600}}>{test.candidate_name}</span>, you're one step away.</p>
                    </div>

                    <div className="tp-stats">
                        <div className="tp-stat">
                            <p className="tp-stat-num">{test.total_questions}</p>
                            <p className="tp-stat-label">Questions</p>
                        </div>
                        <div className="tp-stat-sep" />
                        <div className="tp-stat">
                            <p className="tp-stat-num">{test.duration_mins}</p>
                            <p className="tp-stat-label">Minutes</p>
                        </div>
                        <div className="tp-stat-sep" />
                        <div className="tp-stat">
                            <p className="tp-stat-num" style={{ color: "#ff4400" }}>{test.pass_score}%</p>
                            <p className="tp-stat-label">To Pass</p>
                        </div>
                    </div>

                    <div className="tp-rules">
                        <p className="tp-rules-title">Before you begin</p>
                        {[
                            "Timer starts immediately when you click Start — be ready",
                            "Each question has exactly one correct answer",
                            "You cannot return to a previous question",
                            "Test auto-submits when the timer reaches zero",
                            "Do not refresh or close the tab during the test",
                            "Ensure a stable internet connection throughout",
                            "Camera access is required for selfie and periodic verification snapshots",
                            "All questions are required — unanswered ones default to option A",
                            "This test can only be attempted once",
                        ].map((r, i) => (
                            <div key={i} className="tp-rule">
                                <span className="tp-rule-num">{String(i + 1).padStart(2, "0")}</span>
                                <span className="tp-rule-text">{r}</span>
                            </div>
                        ))}
                    </div>
                    <RoomScanGate sessionToken={token} onReadyChange={(ready) => setRoomScanReady(ready)} />
                </div>

                {/* Sticky Start Test button — fixed to bottom of right panel */}
                <div className="tp-intro-footer">
                    <button className="tp-btn" onClick={startTest} disabled={!roomScanReady}>
                        {roomScanReady ? "Start Test" : "Complete Room Scan to Start"}
                    </button>
                </div>
            </div>
        </div>
    );

    // ── TEST ──
    if (phase === "test" && q) return (
        <div className="tp-split">
            {/* Left — clean bg + floating timer */}
            <div className="tp-left">
                <div className="tp-timer-card">
                    <p className={`tp-timer-num ${timeLeft < 60 ? "red" : timeLeft < 180 ? "amber" : ""}`}>
                        {formatTime(timeLeft)}
                    </p>
                    <p className="tp-timer-label">remaining</p>
                </div>
            </div>

            {/* Right — question */}
            <div className="tp-right tp-question-right">
                <div className="tp-q-header">
                    <p className="tp-eyebrow">{test.job_title}</p>
                    <div className="tp-q-tags">
                        <span className="tp-tag-skill">{q.skill}</span>
                        <span className={`tp-tag-diff ${q.difficulty}`}>{q.difficulty}</span>
                    </div>
                </div>

                <div className="tp-q-progress">
                    <div className="tp-q-bar"><div className="tp-q-bar-fill" style={{ width: `${progress}%` }} /></div>
                    <p className="tp-caption">{current + 1} / {test.questions.length}</p>
                </div>

                <p className="tp-question">{q.question}</p>

                <div className="tp-options">
                    {q.options.map((opt, i) => (
                        <button key={i}
                            className={`tp-option ${selected === i ? "active" : ""}`}
                            onClick={() => {
                                if (!selectionTimesRef.current[current]) {
                                    selectionTimesRef.current[current] = Date.now();
                                }
                                setSelected(i);
                            }}>
                            <span className="tp-opt-letter">{["A", "B", "C", "D"][i]}</span>
                            <span className="tp-opt-text">{opt}</span>
                        </button>
                    ))}
                </div>

                <div className="tp-q-footer">
                    <p className="tp-caption">{answeredCount} of {test.questions.length} answered</p>
                    <button className="tp-btn tp-btn-sm"
                        disabled={selected === null || submitting}
                        onClick={nextQuestion}>
                        {submitting ? "Submitting…" : isLast ? "Submit" : "Next"}
                    </button>
                </div>
            </div>
        </div>
    );

    return null;
}
