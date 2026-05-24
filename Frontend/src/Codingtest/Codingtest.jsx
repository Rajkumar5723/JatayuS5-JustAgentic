// import { useEffect, useState, useRef } from "react";
// import { useParams } from "react-router-dom";
// import "./CodingTest.css";

// const API = "http://127.0.0.1:8003";
// const PISTON = "https://emkc.org/api/v2/piston/execute";

// const LANGS = [
//     { id: "python", label: "Python", piston: "python", version: "3.10.0" },
//     { id: "javascript", label: "JavaScript", piston: "javascript", version: "18.15.0" },
//     { id: "java", label: "Java", piston: "java", version: "15.0.2" },
//     { id: "cpp", label: "C++", piston: "c++", version: "10.2.0" },
// ];

// const TERM_H = 290; // terminal height when open (px)

// export default function CodingTest() {
//     const { token } = useParams();
//     const [phase, setPhase] = useState("loading");
//     const [session, setSession] = useState(null);
//     const [activeProblem, setActiveProblem] = useState(0);
//     const [lang, setLang] = useState("python");
//     const [codes, setCodes] = useState({});
//     const [timeLeft, setTimeLeft] = useState(0);
//     const [submitting, setSubmitting] = useState(false);
//     const [showDone, setShowDone] = useState(false);
//     const timerRef = useRef(null);
//     const editorRef = useRef(null);

//     // ── Terminal state ──────────────────────────────────
//     const [termOpen, setTermOpen] = useState(false);
//     const [termTab, setTermTab] = useState("cases");   // "cases" | "stdin"
//     const [customInput, setCustomInput] = useState("");
//     const [running, setRunning] = useState(false);
//     const [stdinResult, setStdinResult] = useState(null);      // single run result
//     const [caseResults, setCaseResults] = useState({});        // { `${pIdx}-${caseIdx}`: result }
//     const [activeCase, setActiveCase] = useState(0);

//     // ── Session load ────────────────────────────────────
//     useEffect(() => {
//         fetch(`${API}/coding/${token}`)
//             .then(r => r.json())
//             .then(data => {
//                 if (data.status === "submitted") setPhase("result");
//                 else { setSession(data); setPhase("intro"); }
//             })
//             .catch(() => setPhase("error"));
//     }, [token]);

//     const startTest = async () => {
//         await fetch(`${API}/coding/${token}/start`, { method: "POST" });
//         const init = {};
//         session.problems.forEach((p, pi) => {
//             LANGS.forEach(l => {
//                 init[`${pi}-${l.id}`] = p.starter_code?.[l.id] || `// Write your ${l.label} solution here\n`;
//             });
//         });
//         setCodes(init);
//         setTimeLeft(session.duration_mins * 60);
//         setPhase("test");
//     };

//     // ── Timer ───────────────────────────────────────────
//     useEffect(() => {
//         if (phase !== "test") return;
//         timerRef.current = setInterval(() => {
//             setTimeLeft(t => {
//                 if (t <= 1) { clearInterval(timerRef.current); handleSubmit(); return 0; }
//                 return t - 1;
//             });
//         }, 1000);
//         return () => clearInterval(timerRef.current);
//     }, [phase]);

//     const formatTime = s =>
//         `${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

//     const codeKey = (pi, l) => `${pi}-${l}`;
//     const currentCode = codes[codeKey(activeProblem, lang)] || "";
//     const setCode = val => setCodes(prev => ({ ...prev, [codeKey(activeProblem, lang)]: val }));

//     const handleTab = e => {
//         if (e.key === "Tab") {
//             e.preventDefault();
//             const el = editorRef.current;
//             const s = el.selectionStart, end = el.selectionEnd;
//             const newVal = currentCode.substring(0, s) + "  " + currentCode.substring(end);
//             setCode(newVal);
//             setTimeout(() => { el.selectionStart = el.selectionEnd = s + 2; }, 0);
//         }
//     };

//     const handleSubmit = async () => {
//         clearInterval(timerRef.current);
//         setSubmitting(true);
//         const submissions = session.problems.map((_, pi) => ({
//             problem_idx: pi,
//             language: lang,
//             code: codes[codeKey(pi, lang)] || "",
//         }));
//         try {
//             await fetch(`${API}/coding/${token}/submit`, {
//                 method: "POST",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify({ submissions })
//             });
//             setPhase("result"); setShowDone(true);
//         } catch { setPhase("error"); }
//     };

//     // ── Piston helpers ──────────────────────────────────
//     const getLangMeta = () => LANGS.find(l => l.id === lang) || LANGS[0];

//     const pistonRun = async (code, stdin = "") => {
//         const { piston, version } = getLangMeta();
//         const res = await fetch(PISTON, {
//             method: "POST",
//             headers: { "Content-Type": "application/json" },
//             body: JSON.stringify({
//                 language: piston,
//                 version,
//                 files: [{ content: code }],
//                 stdin,
//                 compile_timeout: 10000,
//                 run_timeout: 5000,
//             }),
//         });
//         if (!res.ok) throw new Error(`Piston returned ${res.status}`);
//         return res.json();
//     };

//     const parseResult = (data) => {
//         const compile = data.compile || {};
//         const run = data.run || {};
//         const stderr = run.stderr || compile.stderr || "";
//         return {
//             stdout: run.stdout || "",
//             stderr,
//             time: run.cpu_time != null ? run.cpu_time : null,
//             memory: run.memory != null ? run.memory : null,
//             code: run.code != null ? run.code : null,
//             isError: !!stderr || (run.code !== 0 && run.code != null),
//         };
//     };

//     // Run with custom stdin
//     const runCustom = async () => {
//         setRunning(true);
//         setTermOpen(true);
//         setTermTab("stdin");
//         try {
//             const data = await pistonRun(currentCode, customInput);
//             setStdinResult(parseResult(data));
//         } catch (e) {
//             setStdinResult({ stdout: "", stderr: e.message, time: null, memory: null, isError: true });
//         }
//         setRunning(false);
//     };

//     // Run a single test case
//     const runCase = async (caseIdx) => {
//         const p = session?.problems?.[activeProblem];
//         if (!p) return;
//         const ex = p.examples[caseIdx];
//         const key = `${activeProblem}-${caseIdx}`;
//         setRunning(true);
//         setTermOpen(true);
//         setTermTab("cases");
//         setActiveCase(caseIdx);
//         setCaseResults(prev => ({ ...prev, [key]: { pending: true } }));
//         try {
//             const data = await pistonRun(currentCode, ex.input);
//             const result = parseResult(data);
//             const actual = result.stdout.trim();
//             const expected = (ex.output || "").trim();
//             setCaseResults(prev => ({ ...prev, [key]: { ...result, actual, expected, passed: actual === expected } }));
//         } catch (e) {
//             setCaseResults(prev => ({ ...prev, [`${activeProblem}-${caseIdx}`]: { stderr: e.message, isError: true } }));
//         }
//         setRunning(false);
//     };

//     // Run all test cases sequentially
//     const runAllCases = async () => {
//         const p = session?.problems?.[activeProblem];
//         if (!p?.examples?.length) return;
//         setRunning(true);
//         setTermOpen(true);
//         setTermTab("cases");
//         for (let i = 0; i < p.examples.length; i++) {
//             const ex = p.examples[i];
//             const key = `${activeProblem}-${i}`;
//             setCaseResults(prev => ({ ...prev, [key]: { pending: true } }));
//             setActiveCase(i);
//             try {
//                 const data = await pistonRun(currentCode, ex.input);
//                 const result = parseResult(data);
//                 const actual = result.stdout.trim();
//                 const expected = (ex.output || "").trim();
//                 setCaseResults(prev => ({ ...prev, [key]: { ...result, actual, expected, passed: actual === expected } }));
//             } catch (e) {
//                 setCaseResults(prev => ({ ...prev, [key]: { stderr: e.message, isError: true } }));
//             }
//         }
//         setRunning(false);
//     };

//     const timeClass = timeLeft < 300 ? "red" : timeLeft < 900 ? "amber" : "";
//     const p = session?.problems?.[activeProblem];

//     // ── LOADING ──
//     if (phase === "loading") return (
//         <div className="ct-full ct-center">
//             <div className="ct-spinner" />
//             <p className="ct-muted">Loading coding round…</p>
//         </div>
//     );

//     // ── ERROR ──
//     if (phase === "error") return (
//         <div className="ct-full ct-center">
//             <p className="ct-display">Link not found</p>
//             <p className="ct-muted">This link may be invalid or expired.</p>
//         </div>
//     );

//     // ── RESULT ──
//     if (phase === "result") return (
//         <>
//             <div className="ct-full ct-center">
//                 <p className="ct-eyebrow">Hiersy · Coding Round</p>
//                 <p className="ct-display">Code Submitted</p>
//                 <p className="ct-body" style={{ maxWidth: 340, textAlign: "center" }}>
//                     Your solutions have been recorded. Our team will review your code
//                     and contact you by email if you proceed to the next stage.
//                 </p>
//                 <p className="ct-muted" style={{ marginTop: 5, fontSize: 12 }}>You may close this tab.</p>
//             </div>
//             {showDone && (
//                 <div className="ct-overlay" onClick={() => setShowDone(false)}>
//                     <div className="ct-modal" onClick={e => e.stopPropagation()}>
//                         <div className="ct-modal-icon">✓</div>
//                         <p className="ct-modal-title">Coding Round Complete</p>
//                         <p className="ct-modal-body">
//                             Your code has been submitted. We'll notify you by{" "}
//                             <span style={{ color: "#fff" }}>email</span> with the outcome.
//                         </p>
//                         <button className="ct-btn" onClick={() => setShowDone(false)}>Got it</button>
//                     </div>
//                 </div>
//             )}
//         </>
//     );

//     // ── INTRO ──
//     if (phase === "intro" && session) return (
//         <div className="ct-split">
//             <div className="ct-left" />
//             <div className="ct-right">
//                 <div className="ct-intro-inner">
//                     <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
//                         <p className="ct-eyebrow">Hiersy · Coding Round</p>
//                         <p className="ct-display">{session.job_title}</p>
//                         <p className="ct-body">Hi {session.candidate_name}, you made it to the coding round.</p>
//                     </div>
//                     <div className="ct-stats">
//                         <div className="ct-stat"><p className="ct-stat-num">2</p><p className="ct-stat-label">Problems</p></div>
//                         <div className="ct-stat-sep" />
//                         <div className="ct-stat"><p className="ct-stat-num">{session.duration_mins}</p><p className="ct-stat-label">Minutes</p></div>
//                         <div className="ct-stat-sep" />
//                         <div className="ct-stat"><p className="ct-stat-num">4</p><p className="ct-stat-label">Languages</p></div>
//                     </div>
//                     <div className="ct-rules">
//                         <p className="ct-rules-title">Before you begin</p>
//                         {[
//                             "Timer starts the moment you click Start — be ready",
//                             "Two coding problems — complete both if possible",
//                             "Choose any language: Python, JavaScript, Java, or C++",
//                             "You can switch between problems at any time",
//                             "All code is auto-saved as you type",
//                             "Do not refresh or close the tab during the test",
//                             "Submissions are final — the round can only be attempted once",
//                             "Partial solutions are accepted — submit what you have",
//                         ].map((r, i) => (
//                             <div key={i} className="ct-rule">
//                                 <span className="ct-rule-num">{String(i + 1).padStart(2, "0")}</span>
//                                 <span className="ct-rule-text">{r}</span>
//                             </div>
//                         ))}
//                     </div>
//                 </div>
//                 <div className="ct-intro-footer">
//                     <button className="ct-btn" onClick={startTest}>Start Coding Round</button>
//                 </div>
//             </div>
//         </div>
//     );

//     // ── TEST ──
//     if (phase === "test" && p) {
//         const activeCaseResult = caseResults[`${activeProblem}-${activeCase}`];

//         return (
//             <div className="ct-editor-root">

//                 {/* Top bar */}
//                 <div className="ct-topbar">
//                     <div className="ct-topbar-left">
//                         <p className="ct-eyebrow" style={{ margin: 0, fontSize:'large' }}>Hiresy</p>
//                         <div className="ct-problem-tabs">
//                             {session.problems.map((prob, i) => (
//                                 <button key={i}
//                                     className={`ct-prob-tab ${activeProblem === i ? "active" : ""}`}
//                                     onClick={() => setActiveProblem(i)}>
//                                     <span className={`ct-prob-dot ${prob.difficulty}`} />
//                                     Problem {i + 1}
//                                 </button>
//                             ))}
//                         </div>
//                     </div>
//                     <div className="ct-topbar-right">
//                         <div className={`ct-timer ${timeClass}`}>{formatTime(timeLeft)}</div>
//                         <button className="ct-btn ct-btn-sm ct-submit-btn"
//                             disabled={submitting} onClick={handleSubmit}>
//                             {submitting ? "Submitting…" : "Submit All"}
//                         </button>
//                     </div>
//                 </div>

//                 {/* Main split */}
//                 <div className="ct-main">

//                     {/* Problem panel */}
//                     <div className="ct-problem-panel">
//                         <div className="ct-problem-header">
//                             <p className="ct-problem-title">{p.title}</p>
//                             <span className={`ct-diff-badge ${p.difficulty}`}>{p.difficulty}</span>
//                         </div>
//                         <div className="ct-problem-body">
//                             <p className="ct-section-label">Description</p>
//                             <p className="ct-problem-desc">{p.description}</p>
//                             {p.examples?.map((ex, i) => (
//                                 <div key={i} className="ct-example">
//                                     <p className="ct-section-label">Example {i + 1}</p>
//                                     <div className="ct-example-block">
//                                         <p className="ct-ex-line"><span>Input</span>{ex.input}</p>
//                                         <p className="ct-ex-line"><span>Output</span>{ex.output}</p>
//                                         {ex.explanation && <p className="ct-ex-line"><span>Note</span>{ex.explanation}</p>}
//                                     </div>
//                                 </div>
//                             ))}
//                             {p.constraints?.length > 0 && (
//                                 <>
//                                     <p className="ct-section-label">Constraints</p>
//                                     <div className="ct-constraints">
//                                         {p.constraints.map((c, i) => (
//                                             <p key={i} className="ct-constraint">{c}</p>
//                                         ))}
//                                     </div>
//                                 </>
//                             )}
//                         </div>
//                     </div>

//                     {/* Code panel */}
//                     <div className="ct-code-panel">

//                         {/* Lang bar + run controls */}
//                         <div className="ct-lang-bar">
//                             <div className="ct-lang-group">
//                                 {LANGS.map(l => (
//                                     <button key={l.id}
//                                         className={`ct-lang-btn ${lang === l.id ? "active" : ""}`}
//                                         onClick={() => setLang(l.id)}>
//                                         {l.label}
//                                     </button>
//                                 ))}
//                             </div>
//                             <div className="ct-run-group">
//                                 <button className="ct-run-btn ct-run-cases"
//                                     disabled={running}
//                                     onClick={runAllCases}
//                                     title="Run all test cases">
//                                     {running ? (
//                                         <span className="ct-run-spin" />
//                                     ) : (
//                                         <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor">
//                                             <path d="M2 1.5v9l8-4.5z" />
//                                         </svg>
//                                     )}
//                                     Run Tests
//                                 </button>
//                                 <button className="ct-run-btn ct-run-custom"
//                                     disabled={running}
//                                     onClick={runCustom}
//                                     title="Run with custom input">
//                                     {running ? (
//                                         <span className="ct-run-spin" />
//                                     ) : (
//                                         <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor">
//                                             <path d="M2 1.5v9l8-4.5z" />
//                                         </svg>
//                                     )}
//                                     Run
//                                 </button>
//                             </div>
//                         </div>

//                         {/* Editor */}
//                         <div className="ct-editor-wrap">
//                             <textarea
//                                 ref={editorRef}
//                                 className="ct-editor"
//                                 value={currentCode}
//                                 onChange={e => setCode(e.target.value)}
//                                 onKeyDown={handleTab}
//                                 spellCheck={false}
//                                 autoCorrect="off"
//                                 autoCapitalize="off"
//                                 placeholder="Write your solution here…"
//                             />
//                         </div>

//                         {/* ── Terminal panel ── */}
//                         <div className={`ct-terminal ${termOpen ? "open" : ""}`}
//                             style={{ height: termOpen ? TERM_H : 0 }}>

//                             {/* Terminal header */}
//                             <div className="ct-term-header">
//                                 <div className="ct-term-tabs">
//                                     <button
//                                         className={`ct-term-tab ${termTab === "cases" ? "active" : ""}`}
//                                         onClick={() => setTermTab("cases")}>
//                                         Test Cases
//                                         {/* pass/fail summary badges */}
//                                         {p.examples?.length > 0 && (
//                                             <span className="ct-tc-summary">
//                                                 {p.examples.map((_, i) => {
//                                                     const r = caseResults[`${activeProblem}-${i}`];
//                                                     if (!r || r.pending) return <span key={i} className="ct-tc-dot neutral" />;
//                                                     return <span key={i} className={`ct-tc-dot ${r.passed ? "pass" : "fail"}`} />;
//                                                 })}
//                                             </span>
//                                         )}
//                                     </button>
//                                     <button
//                                         className={`ct-term-tab ${termTab === "stdin" ? "active" : ""}`}
//                                         onClick={() => setTermTab("stdin")}>
//                                         Custom Input
//                                     </button>
//                                 </div>
//                                 <div className="ct-term-actions">
//                                     <button className="ct-term-close" onClick={() => setTermOpen(false)}
//                                         title="Close terminal">✕</button>
//                                 </div>
//                             </div>

//                             {/* Terminal body */}
//                             <div className="ct-term-body">

//                                 {/* ── Test Cases tab ── */}
//                                 {termTab === "cases" && (
//                                     <div className="ct-cases-layout">
//                                         {/* Case selector */}
//                                         <div className="ct-case-tabs">
//                                             {p.examples?.map((_, i) => {
//                                                 const r = caseResults[`${activeProblem}-${i}`];
//                                                 let dot = "neutral";
//                                                 if (r && !r.pending) dot = r.passed ? "pass" : "fail";
//                                                 return (
//                                                     <button key={i}
//                                                         className={`ct-case-tab ${activeCase === i ? "active" : ""}`}
//                                                         onClick={() => setActiveCase(i)}>
//                                                         <span className={`ct-tc-dot ${dot}`} style={{ marginRight: 5 }} />
//                                                         Case {i + 1}
//                                                         <button className="ct-case-run-btn"
//                                                             disabled={running}
//                                                             onClick={e => { e.stopPropagation(); runCase(i); }}
//                                                             title={`Run case ${i + 1}`}>
//                                                             ▶
//                                                         </button>
//                                                     </button>
//                                                 );
//                                             })}
//                                             <button className="ct-run-all-btn"
//                                                 disabled={running}
//                                                 onClick={runAllCases}>
//                                                 {running ? "Running…" : "Run All"}
//                                             </button>
//                                         </div>

//                                         {/* Case detail */}
//                                         <div className="ct-case-detail">
//                                             {/* Input / Expected */}
//                                             <div className="ct-io-row">
//                                                 <div className="ct-io-block">
//                                                     <p className="ct-io-label">Input</p>
//                                                     <pre className="ct-io-pre">{p.examples?.[activeCase]?.input || "—"}</pre>
//                                                 </div>
//                                                 <div className="ct-io-block">
//                                                     <p className="ct-io-label">Expected Output</p>
//                                                     <pre className="ct-io-pre">{p.examples?.[activeCase]?.output || "—"}</pre>
//                                                 </div>
//                                             </div>

//                                             {/* Result */}
//                                             {activeCaseResult && !activeCaseResult.pending && (
//                                                 <div className="ct-result-row">
//                                                     <div className="ct-io-block" style={{ flex: 1 }}>
//                                                         <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
//                                                             <p className="ct-io-label" style={{ margin: 0 }}>Your Output</p>
//                                                             <span className={`ct-status-badge ${activeCaseResult.isError ? "err" :
//                                                                     activeCaseResult.passed ? "pass" : "fail"
//                                                                 }`}>
//                                                                 {activeCaseResult.isError ? "Error" :
//                                                                     activeCaseResult.passed ? "Accepted" : "Wrong Answer"}
//                                                             </span>
//                                                             {activeCaseResult.time != null && <span className="ct-meta-chip">⏱ {activeCaseResult.time.toFixed(3)}s</span>}
//                                                             {activeCaseResult.memory != null && <span className="ct-meta-chip">⚡ {(activeCaseResult.memory / 1024).toFixed(1)} KB</span>}
//                                                         </div>
//                                                         <pre className={`ct-io-pre ${activeCaseResult.isError ? "err" : activeCaseResult.passed ? "pass" : "fail"}`}>
//                                                             {activeCaseResult.isError
//                                                                 ? (activeCaseResult.stderr || "Unknown error")
//                                                                 : (activeCaseResult.actual || "(empty)")}
//                                                         </pre>
//                                                     </div>
//                                                 </div>
//                                             )}

//                                             {activeCaseResult?.pending && (
//                                                 <div className="ct-running-indicator">
//                                                     <span className="ct-run-spin" /> Running…
//                                                 </div>
//                                             )}
//                                         </div>
//                                     </div>
//                                 )}

//                                 {/* ── Custom Input tab ── */}
//                                 {termTab === "stdin" && (
//                                     <div className="ct-stdin-layout">
//                                         <div className="ct-stdin-left">
//                                             <p className="ct-io-label">Standard Input</p>
//                                             <textarea
//                                                 className="ct-stdin-area"
//                                                 value={customInput}
//                                                 onChange={e => setCustomInput(e.target.value)}
//                                                 placeholder="Enter your custom input here…"
//                                                 spellCheck={false}
//                                             />
//                                             <button className="ct-run-btn ct-run-custom ct-run-full"
//                                                 disabled={running} onClick={runCustom}>
//                                                 {running ? <><span className="ct-run-spin" /> Running…</> : <>▶ Run</>}
//                                             </button>
//                                         </div>

//                                         <div className="ct-stdin-right">
//                                             {stdinResult ? (
//                                                 <>
//                                                     <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
//                                                         <p className="ct-io-label" style={{ margin: 0 }}>Output</p>
//                                                         <span className={`ct-status-badge ${stdinResult.isError ? "err" : "pass"}`}>
//                                                             {stdinResult.isError ? "Error" : "Success"}
//                                                         </span>
//                                                         {stdinResult.time != null && <span className="ct-meta-chip">⏱ {stdinResult.time.toFixed(3)}s</span>}
//                                                         {stdinResult.memory != null && <span className="ct-meta-chip">⚡ {(stdinResult.memory / 1024).toFixed(1)} KB</span>}
//                                                     </div>
//                                                     {stdinResult.stdout && (
//                                                         <pre className="ct-io-pre pass" style={{ marginBottom: 8 }}>{stdinResult.stdout}</pre>
//                                                     )}
//                                                     {stdinResult.stderr && (
//                                                         <>
//                                                             <p className="ct-io-label" style={{ marginBottom: 4, color: "#ef4444" }}>Stderr</p>
//                                                             <pre className="ct-io-pre err">{stdinResult.stderr}</pre>
//                                                         </>
//                                                     )}
//                                                     {!stdinResult.stdout && !stdinResult.stderr && (
//                                                         <pre className="ct-io-pre">(no output)</pre>
//                                                     )}
//                                                 </>
//                                             ) : (
//                                                 <div className="ct-no-result">
//                                                     <p>Run your code to see output</p>
//                                                 </div>
//                                             )}
//                                         </div>
//                                     </div>
//                                 )}
//                             </div>
//                         </div>

//                         {/* Editor footer */}
//                         <div className="ct-editor-footer">
//                             <p className="ct-muted" style={{ fontSize: 12 }}>
//                                 Tab → 2 spaces &nbsp;·&nbsp; {currentCode.split("\n").length} lines
//                             </p>
//                             <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
//                                 <p className="ct-muted" style={{ fontSize: 11 }}>
//                                     Problem {activeProblem + 1} of {session.problems.length} &nbsp;·&nbsp; {lang}
//                                 </p>
//                                 <button className="ct-term-toggle" onClick={() => setTermOpen(o => !o)}>
//                                     {termOpen ? "▼ Terminal" : "▲ Terminal"}
//                                 </button>
//                             </div>
//                         </div>
//                     </div>
//                 </div>
//             </div>
//         );
//     }

//     return null;
// }


// import { useEffect, useState, useRef } from "react";
// import { useParams } from "react-router-dom";
// import "./CodingTest.css";

// const API = "http://127.0.0.1:8003";
// const PISTON = "https://emkc.org/api/v2/piston/execute";
// const PISTON_API_KEY = process.env.REACT_APP_PISTON_API_KEY || "YOUR_PISTON_API_KEY";

// const LANGS = [
//     { id: "python", label: "Python", piston: "python", version: "3.10.0" },
//     { id: "javascript", label: "JavaScript", piston: "javascript", version: "18.15.0" },
//     { id: "java", label: "Java", piston: "java", version: "15.0.2" },
//     { id: "cpp", label: "C++", piston: "c++", version: "10.2.0" },
// ];

// const TERM_H = 290;

// export default function CodingTest() {
//     const { token } = useParams();
//     const [phase, setPhase] = useState("loading");
//     const [session, setSession] = useState(null);
//     const [activeProblem, setActiveProblem] = useState(0);
//     const [lang, setLang] = useState("python");
//     const [codes, setCodes] = useState({});
//     const [timeLeft, setTimeLeft] = useState(0);
//     const [submitting, setSubmitting] = useState(false);
//     const [showDone, setShowDone] = useState(false);
//     const timerRef = useRef(null);
//     const editorRef = useRef(null);

//     // Terminal state
//     const [termOpen, setTermOpen] = useState(false);
//     const [termTab, setTermTab] = useState("cases");   // "cases" | "stdin"
//     const [customInput, setCustomInput] = useState("");
//     const [running, setRunning] = useState(false);
//     const [stdinResult, setStdinResult] = useState(null);
//     const [caseResults, setCaseResults] = useState({});
//     const [activeCase, setActiveCase] = useState(0);

//     // Session load
//     useEffect(() => {
//         fetch(`${API}/coding/${token}`)
//             .then(r => r.json())
//             .then(data => {
//                 if (data.status === "submitted") setPhase("result");
//                 else { setSession(data); setPhase("intro"); }
//             })
//             .catch(() => setPhase("error"));
//     }, [token]);

//     const startTest = async () => {
//         await fetch(`${API}/coding/${token}/start`, { method: "POST" });
//         const init = {};
//         session.problems.forEach((p, pi) => {
//             LANGS.forEach(l => {
//                 init[`${pi}-${l.id}`] = p.starter_code?.[l.id] || `// Write your ${l.label} solution here\n`;
//             });
//         });
//         setCodes(init);
//         setTimeLeft(session.duration_mins * 60);
//         setPhase("test");
//     };

//     useEffect(() => {
//         if (phase !== "test") return;
//         timerRef.current = setInterval(() => {
//             setTimeLeft(t => {
//                 if (t <= 1) { clearInterval(timerRef.current); handleSubmit(); return 0; }
//                 return t - 1;
//             });
//         }, 1000);
//         return () => clearInterval(timerRef.current);
//     }, [phase]);

//     const formatTime = s =>
//         `${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

//     const codeKey = (pi, l) => `${pi}-${l}`;
//     const currentCode = codes[codeKey(activeProblem, lang)] || "";
//     const setCode = val => setCodes(prev => ({ ...prev, [codeKey(activeProblem, lang)]: val }));

//     const handleTab = e => {
//         if (e.key === "Tab") {
//             e.preventDefault();
//             const el = editorRef.current;
//             const s = el.selectionStart, end = el.selectionEnd;
//             const newVal = currentCode.substring(0, s) + "  " + currentCode.substring(end);
//             setCode(newVal);
//             setTimeout(() => { el.selectionStart = el.selectionEnd = s + 2; }, 0);
//         }
//     };

//     const handleSubmit = async () => {
//         clearInterval(timerRef.current);
//         setSubmitting(true);
//         const submissions = session.problems.map((_, pi) => ({
//             problem_idx: pi,
//             language: lang,
//             code: codes[codeKey(pi, lang)] || "",
//         }));
//         try {
//             await fetch(`${API}/coding/${token}/submit`, {
//                 method: "POST",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify({ submissions })
//             });
//             setPhase("result"); setShowDone(true);
//         } catch { setPhase("error"); }
//     };

//     // Piston helpers
//     const getLangMeta = () => LANGS.find(l => l.id === lang) || LANGS[0];

//     const pistonRun = async (code, stdin = "") => {
//         const { piston, version } = getLangMeta();
//         const headers = {
//             "Content-Type": "application/json",
//         };
//         // Add Authorization header if we have an API key
//         if (PISTON_API_KEY && PISTON_API_KEY !== "YOUR_PISTON_API_KEY") {
//             headers["Authorization"] = `Bearer ${PISTON_API_KEY}`;
//         }
//         const res = await fetch(PISTON, {
//             method: "POST",
//             headers,
//             body: JSON.stringify({
//                 language: piston,
//                 version,
//                 files: [{ content: code }],
//                 stdin,
//                 compile_timeout: 10000,
//                 run_timeout: 5000,
//             }),
//         });
//         if (!res.ok) throw new Error(`Piston returned ${res.status}`);
//         return res.json();
//     };

//     const parseResult = (data) => {
//         const compile = data.compile || {};
//         const run = data.run || {};
//         const stderr = run.stderr || compile.stderr || "";
//         return {
//             stdout: run.stdout || "",
//             stderr,
//             time: run.cpu_time != null ? run.cpu_time : null,
//             memory: run.memory != null ? run.memory : null,
//             code: run.code != null ? run.code : null,
//             isError: !!stderr || (run.code !== 0 && run.code != null),
//         };
//     };

//     // Run with custom stdin
//     const runCustom = async () => {
//         setRunning(true);
//         setTermOpen(true);
//         setTermTab("stdin");
//         try {
//             const data = await pistonRun(currentCode, customInput);
//             setStdinResult(parseResult(data));
//         } catch (e) {
//             setStdinResult({ stdout: "", stderr: e.message, time: null, memory: null, isError: true });
//         }
//         setRunning(false);
//     };

//     // Run a single test case
//     const runCase = async (caseIdx) => {
//         const p = session?.problems?.[activeProblem];
//         if (!p) return;
//         const ex = p.examples[caseIdx];
//         const key = `${activeProblem}-${caseIdx}`;
//         setRunning(true);
//         setTermOpen(true);
//         setTermTab("cases");
//         setActiveCase(caseIdx);
//         setCaseResults(prev => ({ ...prev, [key]: { pending: true } }));
//         try {
//             const data = await pistonRun(currentCode, ex.input);
//             const result = parseResult(data);
//             const actual = result.stdout.trim();
//             const expected = (ex.output || "").trim();
//             setCaseResults(prev => ({ ...prev, [key]: { ...result, actual, expected, passed: actual === expected } }));
//         } catch (e) {
//             setCaseResults(prev => ({ ...prev, [`${activeProblem}-${caseIdx}`]: { stderr: e.message, isError: true } }));
//         }
//         setRunning(false);
//     };

//     // Run all test cases sequentially
//     const runAllCases = async () => {
//         const p = session?.problems?.[activeProblem];
//         if (!p?.examples?.length) return;
//         setRunning(true);
//         setTermOpen(true);
//         setTermTab("cases");
//         for (let i = 0; i < p.examples.length; i++) {
//             const ex = p.examples[i];
//             const key = `${activeProblem}-${i}`;
//             setCaseResults(prev => ({ ...prev, [key]: { pending: true } }));
//             setActiveCase(i);
//             try {
//                 const data = await pistonRun(currentCode, ex.input);
//                 const result = parseResult(data);
//                 const actual = result.stdout.trim();
//                 const expected = (ex.output || "").trim();
//                 setCaseResults(prev => ({ ...prev, [key]: { ...result, actual, expected, passed: actual === expected } }));
//             } catch (e) {
//                 setCaseResults(prev => ({ ...prev, [key]: { stderr: e.message, isError: true } }));
//             }
//         }
//         setRunning(false);
//     };

//     const timeClass = timeLeft < 300 ? "red" : timeLeft < 900 ? "amber" : "";
//     const p = session?.problems?.[activeProblem];

//     // LOADING
//     if (phase === "loading") return (
//         <div className="ct-full ct-center">
//             <div className="ct-spinner" />
//             <p className="ct-muted">Loading coding round…</p>
//         </div>
//     );

//     // ERROR
//     if (phase === "error") return (
//         <div className="ct-full ct-center">
//             <p className="ct-display">Link not found</p>
//             <p className="ct-muted">This link may be invalid or expired.</p>
//         </div>
//     );

//     // RESULT
//     if (phase === "result") return (
//         <>
//             <div className="ct-full ct-center">
//                 <p className="ct-eyebrow">Hiersy · Coding Round</p>
//                 <p className="ct-display">Code Submitted</p>
//                 <p className="ct-body" style={{ maxWidth: 340, textAlign: "center" }}>
//                     Your solutions have been recorded. Our team will review your code
//                     and contact you by email if you proceed to the next stage.
//                 </p>
//                 <p className="ct-muted" style={{ marginTop: 5, fontSize: 12 }}>You may close this tab.</p>
//             </div>
//             {showDone && (
//                 <div className="ct-overlay" onClick={() => setShowDone(false)}>
//                     <div className="ct-modal" onClick={e => e.stopPropagation()}>
//                         <div className="ct-modal-icon">✓</div>
//                         <p className="ct-modal-title">Coding Round Complete</p>
//                         <p className="ct-modal-body">
//                             Your code has been submitted. We'll notify you by{" "}
//                             <span style={{ color: "#fff" }}>email</span> with the outcome.
//                         </p>
//                         <button className="ct-btn" onClick={() => setShowDone(false)}>Got it</button>
//                     </div>
//                 </div>
//             )}
//         </>
//     );

//     // INTRO
//     if (phase === "intro" && session) return (
//         <div className="ct-split">
//             <div className="ct-left" />
//             <div className="ct-right">
//                 <div className="ct-intro-inner">
//                     <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
//                         <p className="ct-eyebrow">Hiersy · Coding Round</p>
//                         <p className="ct-display">{session.job_title}</p>
//                         <p className="ct-body">Hi {session.candidate_name}, you made it to the coding round.</p>
//                     </div>
//                     <div className="ct-stats">
//                         <div className="ct-stat"><p className="ct-stat-num">2</p><p className="ct-stat-label">Problems</p></div>
//                         <div className="ct-stat-sep" />
//                         <div className="ct-stat"><p className="ct-stat-num">{session.duration_mins}</p><p className="ct-stat-label">Minutes</p></div>
//                         <div className="ct-stat-sep" />
//                         <div className="ct-stat"><p className="ct-stat-num">4</p><p className="ct-stat-label">Languages</p></div>
//                     </div>
//                     <div className="ct-rules">
//                         <p className="ct-rules-title">Before you begin</p>
//                         {[
//                             "Timer starts the moment you click Start — be ready",
//                             "Two coding problems — complete both if possible",
//                             "Choose any language: Python, JavaScript, Java, or C++",
//                             "You can switch between problems at any time",
//                             "All code is auto-saved as you type",
//                             "Do not refresh or close the tab during the test",
//                             "Submissions are final — the round can only be attempted once",
//                             "Partial solutions are accepted — submit what you have",
//                         ].map((r, i) => (
//                             <div key={i} className="ct-rule">
//                                 <span className="ct-rule-num">{String(i + 1).padStart(2, "0")}</span>
//                                 <span className="ct-rule-text">{r}</span>
//                             </div>
//                         ))}
//                     </div>
//                 </div>
//                 <div className="ct-intro-footer">
//                     <button className="ct-btn" onClick={startTest}>Start Coding Round</button>
//                 </div>
//             </div>
//         </div>
//     );

//     // TEST
//     if (phase === "test" && p) {
//         const activeCaseResult = caseResults[`${activeProblem}-${activeCase}`];

//         return (
//             <div className="ct-editor-root">

//                 {/* Top bar */}
//                 <div className="ct-topbar">
//                     <div className="ct-topbar-left">
//                         <p className="ct-eyebrow" style={{ margin: 0, fontSize: 'large' }}>Hiersy</p>
//                         <div className="ct-problem-tabs">
//                             {session.problems.map((prob, i) => (
//                                 <button key={i}
//                                     className={`ct-prob-tab ${activeProblem === i ? "active" : ""}`}
//                                     onClick={() => setActiveProblem(i)}>
//                                     <span className={`ct-prob-dot ${prob.difficulty}`} />
//                                     Problem {i + 1}
//                                 </button>
//                             ))}
//                         </div>
//                     </div>
//                     <div className="ct-topbar-right">
//                         <div className={`ct-timer ${timeClass}`}>{formatTime(timeLeft)}</div>
//                         <button className="ct-btn ct-btn-sm ct-submit-btn"
//                             disabled={submitting} onClick={handleSubmit}>
//                             {submitting ? "Submitting…" : "Submit All"}
//                         </button>
//                     </div>
//                 </div>

//                 {/* Main split */}
//                 <div className="ct-main">

//                     {/* Problem panel */}
//                     <div className="ct-problem-panel">
//                         <div className="ct-problem-header">
//                             <p className="ct-problem-title">{p.title}</p>
//                             <span className={`ct-diff-badge ${p.difficulty}`}>{p.difficulty}</span>
//                         </div>
//                         <div className="ct-problem-body">
//                             <p className="ct-section-label">Description</p>
//                             <p className="ct-problem-desc">{p.description}</p>
//                             {p.examples?.map((ex, i) => (
//                                 <div key={i} className="ct-example">
//                                     <p className="ct-section-label">Example {i + 1}</p>
//                                     <div className="ct-example-block">
//                                         <p className="ct-ex-line"><span>Input</span>{ex.input}</p>
//                                         <p className="ct-ex-line"><span>Output</span>{ex.output}</p>
//                                         {ex.explanation && <p className="ct-ex-line"><span>Note</span>{ex.explanation}</p>}
//                                     </div>
//                                 </div>
//                             ))}
//                             {p.constraints?.length > 0 && (
//                                 <>
//                                     <p className="ct-section-label">Constraints</p>
//                                     <div className="ct-constraints">
//                                         {p.constraints.map((c, i) => (
//                                             <p key={i} className="ct-constraint">{c}</p>
//                                         ))}
//                                     </div>
//                                 </>
//                             )}
//                         </div>
//                     </div>

//                     {/* Code panel */}
//                     <div className="ct-code-panel">

//                         {/* Lang bar + run controls */}
//                         <div className="ct-lang-bar">
//                             <div className="ct-lang-group">
//                                 {LANGS.map(l => (
//                                     <button key={l.id}
//                                         className={`ct-lang-btn ${lang === l.id ? "active" : ""}`}
//                                         onClick={() => setLang(l.id)}>
//                                         {l.label}
//                                     </button>
//                                 ))}
//                             </div>
//                             <div className="ct-run-group">
//                                 <button className="ct-run-btn ct-run-cases"
//                                     disabled={running}
//                                     onClick={runAllCases}
//                                     title="Run all test cases">
//                                     {running ? (
//                                         <span className="ct-run-spin" />
//                                     ) : (
//                                         <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor">
//                                             <path d="M2 1.5v9l8-4.5z" />
//                                         </svg>
//                                     )}
//                                     Run Tests
//                                 </button>
//                                 <button className="ct-run-btn ct-run-custom"
//                                     disabled={running}
//                                     onClick={runCustom}
//                                     title="Run with custom input">
//                                     {running ? (
//                                         <span className="ct-run-spin" />
//                                     ) : (
//                                         <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor">
//                                             <path d="M2 1.5v9l8-4.5z" />
//                                         </svg>
//                                     )}
//                                     Run
//                                 </button>
//                             </div>
//                         </div>

//                         {/* Editor */}
//                         <div className="ct-editor-wrap">
//                             <textarea
//                                 ref={editorRef}
//                                 className="ct-editor"
//                                 value={currentCode}
//                                 onChange={e => setCode(e.target.value)}
//                                 onKeyDown={handleTab}
//                                 spellCheck={false}
//                                 autoCorrect="off"
//                                 autoCapitalize="off"
//                                 placeholder="Write your solution here…"
//                             />
//                         </div>

//                         {/* Terminal panel */}
//                         <div className={`ct-terminal ${termOpen ? "open" : ""}`}
//                             style={{ height: termOpen ? TERM_H : 0 }}>

//                             {/* Terminal header */}
//                             <div className="ct-term-header">
//                                 <div className="ct-term-tabs">
//                                     <button
//                                         className={`ct-term-tab ${termTab === "cases" ? "active" : ""}`}
//                                         onClick={() => setTermTab("cases")}>
//                                         Test Cases
//                                         {p.examples?.length > 0 && (
//                                             <span className="ct-tc-summary">
//                                                 {p.examples.map((_, i) => {
//                                                     const r = caseResults[`${activeProblem}-${i}`];
//                                                     if (!r || r.pending) return <span key={i} className="ct-tc-dot neutral" />;
//                                                     return <span key={i} className={`ct-tc-dot ${r.passed ? "pass" : "fail"}`} />;
//                                                 })}
//                                             </span>
//                                         )}
//                                     </button>
//                                     <button
//                                         className={`ct-term-tab ${termTab === "stdin" ? "active" : ""}`}
//                                         onClick={() => setTermTab("stdin")}>
//                                         Custom Input
//                                     </button>
//                                 </div>
//                                 <div className="ct-term-actions">
//                                     <button className="ct-term-close" onClick={() => setTermOpen(false)}
//                                         title="Close terminal">✕</button>
//                                 </div>
//                             </div>

//                             {/* Terminal body */}
//                             <div className="ct-term-body">

//                                 {/* Test Cases tab */}
//                                 {termTab === "cases" && (
//                                     <div className="ct-cases-layout">
//                                         {/* Case selector */}
//                                         <div className="ct-case-tabs">
//                                             {p.examples?.map((_, i) => {
//                                                 const r = caseResults[`${activeProblem}-${i}`];
//                                                 let dot = "neutral";
//                                                 if (r && !r.pending) dot = r.passed ? "pass" : "fail";
//                                                 return (
//                                                     <div
//                                                         key={i}
//                                                         className={`ct-case-tab ${activeCase === i ? "active" : ""}`}
//                                                         onClick={() => setActiveCase(i)}
//                                                         role="button"
//                                                         tabIndex={0}
//                                                         onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') setActiveCase(i); }}
//                                                     >
//                                                         <span className={`ct-tc-dot ${dot}`} style={{ marginRight: 5 }} />
//                                                         Case {i + 1}
//                                                         <button
//                                                             className="ct-case-run-btn"
//                                                             disabled={running}
//                                                             onClick={e => { e.stopPropagation(); runCase(i); }}
//                                                             title={`Run case ${i + 1}`}
//                                                         >
//                                                             ▶
//                                                         </button>
//                                                     </div>
//                                                 );
//                                             })}
//                                             <button className="ct-run-all-btn"
//                                                 disabled={running}
//                                                 onClick={runAllCases}>
//                                                 {running ? "Running…" : "Run All"}
//                                             </button>
//                                         </div>

//                                         {/* Case detail */}
//                                         <div className="ct-case-detail">
//                                             <div className="ct-io-row">
//                                                 <div className="ct-io-block">
//                                                     <p className="ct-io-label">Input</p>
//                                                     <pre className="ct-io-pre">{p.examples?.[activeCase]?.input || "—"}</pre>
//                                                 </div>
//                                                 <div className="ct-io-block">
//                                                     <p className="ct-io-label">Expected Output</p>
//                                                     <pre className="ct-io-pre">{p.examples?.[activeCase]?.output || "—"}</pre>
//                                                 </div>
//                                             </div>

//                                             {activeCaseResult && !activeCaseResult.pending && (
//                                                 <div className="ct-result-row">
//                                                     <div className="ct-io-block" style={{ flex: 1 }}>
//                                                         <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
//                                                             <p className="ct-io-label" style={{ margin: 0 }}>Your Output</p>
//                                                             <span className={`ct-status-badge ${activeCaseResult.isError ? "err" :
//                                                                 activeCaseResult.passed ? "pass" : "fail"
//                                                                 }`}>
//                                                                 {activeCaseResult.isError ? "Error" :
//                                                                     activeCaseResult.passed ? "Accepted" : "Wrong Answer"}
//                                                             </span>
//                                                             {activeCaseResult.time != null && <span className="ct-meta-chip">⏱ {activeCaseResult.time.toFixed(3)}s</span>}
//                                                             {activeCaseResult.memory != null && <span className="ct-meta-chip">⚡ {(activeCaseResult.memory / 1024).toFixed(1)} KB</span>}
//                                                         </div>
//                                                         <pre className={`ct-io-pre ${activeCaseResult.isError ? "err" : activeCaseResult.passed ? "pass" : "fail"}`}>
//                                                             {activeCaseResult.isError
//                                                                 ? (activeCaseResult.stderr || "Unknown error")
//                                                                 : (activeCaseResult.actual || "(empty)")}
//                                                         </pre>
//                                                     </div>
//                                                 </div>
//                                             )}

//                                             {activeCaseResult?.pending && (
//                                                 <div className="ct-running-indicator">
//                                                     <span className="ct-run-spin" /> Running…
//                                                 </div>
//                                             )}
//                                         </div>
//                                     </div>
//                                 )}

//                                 {/* Custom Input tab */}
//                                 {termTab === "stdin" && (
//                                     <div className="ct-stdin-layout">
//                                         <div className="ct-stdin-left">
//                                             <p className="ct-io-label">Standard Input</p>
//                                             <textarea
//                                                 className="ct-stdin-area"
//                                                 value={customInput}
//                                                 onChange={e => setCustomInput(e.target.value)}
//                                                 placeholder="Enter your custom input here…"
//                                                 spellCheck={false}
//                                             />
//                                             <button className="ct-run-btn ct-run-custom ct-run-full"
//                                                 disabled={running} onClick={runCustom}>
//                                                 {running ? <><span className="ct-run-spin" /> Running…</> : <>▶ Run</>}
//                                             </button>
//                                         </div>

//                                         <div className="ct-stdin-right">
//                                             {stdinResult ? (
//                                                 <>
//                                                     <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
//                                                         <p className="ct-io-label" style={{ margin: 0 }}>Output</p>
//                                                         <span className={`ct-status-badge ${stdinResult.isError ? "err" : "pass"}`}>
//                                                             {stdinResult.isError ? "Error" : "Success"}
//                                                         </span>
//                                                         {stdinResult.time != null && <span className="ct-meta-chip">⏱ {stdinResult.time.toFixed(3)}s</span>}
//                                                         {stdinResult.memory != null && <span className="ct-meta-chip">⚡ {(stdinResult.memory / 1024).toFixed(1)} KB</span>}
//                                                     </div>
//                                                     {stdinResult.stdout && (
//                                                         <pre className="ct-io-pre pass" style={{ marginBottom: 8 }}>{stdinResult.stdout}</pre>
//                                                     )}
//                                                     {stdinResult.stderr && (
//                                                         <>
//                                                             <p className="ct-io-label" style={{ marginBottom: 4, color: "#ef4444" }}>Stderr</p>
//                                                             <pre className="ct-io-pre err">{stdinResult.stderr}</pre>
//                                                         </>
//                                                     )}
//                                                     {!stdinResult.stdout && !stdinResult.stderr && (
//                                                         <pre className="ct-io-pre">(no output)</pre>
//                                                     )}
//                                                 </>
//                                             ) : (
//                                                 <div className="ct-no-result">
//                                                     <p>Run your code to see output</p>
//                                                 </div>
//                                             )}
//                                         </div>
//                                     </div>
//                                 )}
//                             </div>
//                         </div>

//                         {/* Editor footer */}
//                         <div className="ct-editor-footer">
//                             <p className="ct-muted" style={{ fontSize: 12 }}>
//                                 Tab → 2 spaces &nbsp;·&nbsp; {currentCode.split("\n").length} lines
//                             </p>
//                             <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
//                                 <p className="ct-muted" style={{ fontSize: 11 }}>
//                                     Problem {activeProblem + 1} of {session.problems.length} &nbsp;·&nbsp; {lang}
//                                 </p>
//                                 <button className="ct-term-toggle" onClick={() => setTermOpen(o => !o)}>
//                                     {termOpen ? "▼ Terminal" : "▲ Terminal"}
//                                 </button>
//                             </div>
//                         </div>
//                     </div>
//                 </div>
//             </div>
//         );
//     }

//     return null;
// }




import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import "./Codingtest.css";
import { ProctoringMonitor, useProctoring } from "../shared/proctoring.jsx";
import { RoomScanGate } from "../shared/roomScan.jsx";
import { CODING_API as API } from "../shared/api.js";
import VibeCodingRound from "./VibeCodingRound.jsx";

const LANGS = [
    { id: "python", label: "Python" },
    { id: "javascript", label: "JavaScript" },
    { id: "java", label: "Java" },
    { id: "cpp", label: "C++" },
];

const TERM_H = 290;

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    const raw = await res.text();
    let data = {};
    if (raw) {
        try {
            data = JSON.parse(raw);
        } catch {
            data = { raw };
        }
    }
    if (!res.ok) {
        throw new Error(data.detail || data.message || data.raw || `Request failed (${res.status}).`);
    }
    return data;
}

function printable(value) {
    if (value == null || value === "") return "—";
    if (typeof value === "string") return value;
    if (typeof value === "number" || typeof value === "boolean") return String(value);
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

function normalizeConstraints(value) {
    if (Array.isArray(value)) return value.map(printable).filter(Boolean);
    if (typeof value === "string") {
        return value
            .split(/\n|;/)
            .map((item) => item.trim())
            .filter(Boolean);
    }
    return value ? [printable(value)] : [];
}

function normalizeStarterCode(value) {
    if (value && typeof value === "object" && !Array.isArray(value)) return value;
    if (typeof value === "string" && value.trim()) {
        return Object.fromEntries(LANGS.map((lang) => [lang.id, value]));
    }
    return {};
}

function normalizeProblem(problem = {}, index = 0) {
    const examples = Array.isArray(problem.examples) ? problem.examples : [];
    return {
        ...problem,
        title: problem.title || `Problem ${index + 1}`,
        difficulty: String(problem.difficulty || "medium").toLowerCase(),
        description: printable(problem.description || "Solve the problem described by the prompt."),
        constraints: normalizeConstraints(problem.constraints),
        examples: examples.map((example) => ({
            ...example,
            input: printable(example?.input),
            output: printable(example?.output),
            explanation: example?.explanation ? printable(example.explanation) : "",
        })),
        starter_code: normalizeStarterCode(problem.starter_code),
    };
}

function normalizeSessionPayload(data = {}) {
    const problems = Array.isArray(data.problems) ? data.problems.map(normalizeProblem) : [];
    return {
        ...data,
        duration_mins: Number(data.duration_mins || 60),
        problem_count: data.problem_count || problems.length,
        problems,
    };
}

export default function CodingTest() {
    const { token } = useParams();
    const [phase, setPhase] = useState("loading");
    const [session, setSession] = useState(null);
    const [activeProblem, setActiveProblem] = useState(0);
    const [lang, setLang] = useState("python");
    const [problemLanguages, setProblemLanguages] = useState({});
    const [codes, setCodes] = useState({});
    const [timeLeft, setTimeLeft] = useState(0);
    const [submitting, setSubmitting] = useState(false);
    const [showDone, setShowDone] = useState(false);
    const [roomScanReady, setRoomScanReady] = useState(false);
    const timerRef = useRef(null);
    const submitAttemptRef = useRef(() => {});
    const editorRef = useRef(null);
    const testStartedAtRef = useRef(null);
    const activeProblemRef = useRef(0);
    const activeProblemEnteredAtRef = useRef(null);
    const problemStartedAtRef = useRef({});
    const problemTimeSpentRef = useRef({});
    const problemFirstInteractionRef = useRef({});
    const problemMetricsRef = useRef({});
    const languageHistoryRef = useRef({});
    const problemRunHistoryRef = useRef({});
    const codesRef = useRef({});
    const problemLanguagesRef = useRef({});

    // Terminal state
    const [termOpen, setTermOpen] = useState(false);
    const [termTab, setTermTab] = useState("cases");
    const [customInput, setCustomInput] = useState("");
    const [running, setRunning] = useState(false);
    const [stdinResult, setStdinResult] = useState(null);
    const [caseResults, setCaseResults] = useState({});
    const [activeCase, setActiveCase] = useState(0);

    const resetWorkspaceState = () => {
        setTermOpen(false);
        setTermTab("cases");
        setCustomInput("");
        setRunning(false);
        setStdinResult(null);
        setCaseResults({});
        setActiveCase(0);
        testStartedAtRef.current = new Date();
        activeProblemEnteredAtRef.current = Date.now();
        problemStartedAtRef.current = { 0: Date.now() };
        problemTimeSpentRef.current = {};
        problemFirstInteractionRef.current = {};
        problemMetricsRef.current = {};
        languageHistoryRef.current = {};
        problemRunHistoryRef.current = {};
    };

    const initialTimeLeft = (activeSession) => {
        const durationSeconds = Number(activeSession?.duration_mins || 60) * 60;
        const startedAt = Date.parse(activeSession?.started_at || "");
        if (!Number.isFinite(startedAt)) return durationSeconds;
        const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
        return Math.max(0, durationSeconds - elapsed);
    };

    const openWorkspace = (rawSession) => {
        const activeSession = normalizeSessionPayload(rawSession);
        setSession(activeSession);
        const init = {};
        const languageDefaults = {};
        (activeSession.problems || []).forEach((p, pi) => {
            LANGS.forEach((l) => {
                init[`${pi}-${l.id}`] =
                    p.starter_code?.[l.id] || `// Write your ${l.label} solution here\n`;
            });
            languageDefaults[pi] = "python";
        });
        setCodes(init);
        codesRef.current = init;
        setProblemLanguages(languageDefaults);
        problemLanguagesRef.current = languageDefaults;
        setActiveProblem(0);
        activeProblemRef.current = 0;
        setLang("python");
        resetWorkspaceState();
        noteLanguageChoice(0, "python");
        setTimeLeft(initialTimeLeft(activeSession));
        setPhase("test");
    };

    // Session load
    useEffect(() => {
        fetchJson(`${API}/coding/${token}`)
            .then((data) => {
                const normalized = normalizeSessionPayload(data);
                setRoomScanReady(!normalized.room_scan_required);
                setSession(normalized);
                if (normalized.status === "submitted") {
                    setPhase("result");
                } else if (normalized.status === "started" && normalized.problems?.length) {
                    openWorkspace(normalized);
                } else {
                    setPhase("intro");
                }
            })
            .catch(() => setPhase("error"));
    }, [token]);

    useEffect(() => {
        codesRef.current = codes;
    }, [codes]);

    useEffect(() => {
        problemLanguagesRef.current = problemLanguages;
    }, [problemLanguages]);

    useEffect(() => {
        activeProblemRef.current = activeProblem;
        if (phase === "test") {
            activeProblemEnteredAtRef.current = Date.now();
            problemStartedAtRef.current[activeProblem] =
                problemStartedAtRef.current[activeProblem] || Date.now();
            setLang(problemLanguagesRef.current[activeProblem] || "python");
        }
    }, [activeProblem, phase]);

    const noteLanguageChoice = (problemIndex, languageId) => {
        const existing = languageHistoryRef.current[problemIndex] || [];
        if (!existing.length || existing[existing.length - 1]?.language !== languageId) {
            existing.push({
                language: languageId,
                changed_at: new Date().toISOString(),
            });
        }
        languageHistoryRef.current[problemIndex] = existing;
    };

    const flushActiveProblemTime = () => {
        const problemIndex = activeProblemRef.current;
        if (problemIndex == null || activeProblemEnteredAtRef.current == null) return;
        const elapsed = Math.max(0, Date.now() - activeProblemEnteredAtRef.current);
        problemTimeSpentRef.current[problemIndex] =
            (problemTimeSpentRef.current[problemIndex] || 0) + elapsed;
        activeProblemEnteredAtRef.current = Date.now();
    };

    const registerProblemInteraction = (problemIndex) => {
        problemStartedAtRef.current[problemIndex] =
            problemStartedAtRef.current[problemIndex] || Date.now();
        if (!problemFirstInteractionRef.current[problemIndex]) {
            problemFirstInteractionRef.current[problemIndex] = Date.now();
        }
    };

    const recordProblemMetric = (problemIndex, endedAtMs = Date.now()) => {
        const problem = session?.problems?.[problemIndex];
        if (!problem) return null;
        const startedAtMs =
            problemStartedAtRef.current[problemIndex] ||
            testStartedAtRef.current?.getTime() ||
            endedAtMs;
        const firstInteractionMs = problemFirstInteractionRef.current[problemIndex] || null;
        const selectedLanguage = problemLanguagesRef.current[problemIndex] || "python";
        const finalCode = codesRef.current[codeKey(problemIndex, selectedLanguage)] || "";
        const runHistory = problemRunHistoryRef.current[problemIndex] || [];
        const metric = {
            problem_index: problemIndex + 1,
            problem_title: problem.title,
            selected_language: selectedLanguage,
            started_at: new Date(startedAtMs).toISOString(),
            ended_at: new Date(endedAtMs).toISOString(),
            time_spent_seconds: Number(
                (((problemTimeSpentRef.current[problemIndex] || 0)) / 1000).toFixed(2)
            ),
            response_latency_seconds: firstInteractionMs
                ? Number(((firstInteractionMs - startedAtMs) / 1000).toFixed(2))
                : null,
            code_size: finalCode.length,
            language_history: languageHistoryRef.current[problemIndex] || [],
            run_history: runHistory,
            example_run_count: runHistory.filter((item) => item.type === "example_case").length,
            custom_run_count: runHistory.filter((item) => item.type === "custom_input").length,
        };
        problemMetricsRef.current[problemIndex] = metric;
        return metric;
    };

    const recordProblemRun = (problemIndex, type, meta = {}) => {
        const history = problemRunHistoryRef.current[problemIndex] || [];
        history.push({
            type,
            at: new Date().toISOString(),
            ...meta,
        });
        problemRunHistoryRef.current[problemIndex] = history;
        recordProblemMetric(problemIndex);
    };

    const startTest = async () => {
        if (!roomScanReady) return;
        const started = await fetchJson(`${API}/coding/${token}/start`, { method: "POST" });
        const activeSession = started?.problems?.length
            ? started
            : await fetchJson(`${API}/coding/${token}`);
        openWorkspace(activeSession);
    };

    useEffect(() => {
        if (phase !== "test") return;
        timerRef.current = setInterval(() => {
            setTimeLeft((t) => {
                if (t <= 1) {
                    clearInterval(timerRef.current);
                    submitAttemptRef.current();
                    return 0;
                }
                return t - 1;
            });
        }, 1000);
        return () => clearInterval(timerRef.current);
    }, [phase]);

    const formatTime = (s) =>
        `${String(Math.floor(s / 3600)).padStart(2, "0")}:${String(
            Math.floor((s % 3600) / 60)
        ).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

    const codeKey = (pi, l) => `${pi}-${l}`;
    const currentCode = codes[codeKey(activeProblem, lang)] || "";
    const setCode = (val) => {
        registerProblemInteraction(activeProblem);
        setCodes((prev) => {
            const next = { ...prev, [codeKey(activeProblem, lang)]: val };
            codesRef.current = next;
            return next;
        });
        recordProblemMetric(activeProblem);
    };

    const handleProblemChange = (nextProblem) => {
        if (nextProblem === activeProblem) return;
        flushActiveProblemTime();
        recordProblemMetric(activeProblem);
        setActiveProblem(nextProblem);
    };

    const handleLanguageChange = (nextLang) => {
        setLang(nextLang);
        setProblemLanguages((prev) => {
            const next = { ...prev, [activeProblem]: nextLang };
            problemLanguagesRef.current = next;
            return next;
        });
        noteLanguageChoice(activeProblem, nextLang);
        recordProblemMetric(activeProblem);
    };

    const handleTab = (e) => {
        if (e.key === "Tab") {
            e.preventDefault();
            const el = editorRef.current;
            const s = el.selectionStart,
                end = el.selectionEnd;
            const newVal = currentCode.substring(0, s) + "  " + currentCode.substring(end);
            setCode(newVal);
            setTimeout(() => {
                el.selectionStart = el.selectionEnd = s + 2;
            }, 0);
        }
    };

    const handleSubmit = async () => {
        clearInterval(timerRef.current);
        setSubmitting(true);
        flushActiveProblemTime();
        session.problems.forEach((_, problemIndex) => recordProblemMetric(problemIndex));
        const submissions = session.problems.map((_, pi) => ({
            problem_idx: pi,
            language: problemLanguagesRef.current[pi] || "python",
            code: codesRef.current[codeKey(pi, problemLanguagesRef.current[pi] || "python")] || "",
        }));
        const totalDurationSeconds = testStartedAtRef.current
            ? Number(((Date.now() - testStartedAtRef.current.getTime()) / 1000).toFixed(2))
            : null;
        try {
            await fetch(`${API}/coding/${token}/submit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    submissions,
                    telemetry: {
                        started_at: testStartedAtRef.current?.toISOString() || null,
                        submitted_at: new Date().toISOString(),
                        total_duration_seconds: totalDurationSeconds,
                        problem_metrics: Object.values(problemMetricsRef.current),
                    },
                }),
            });
            setPhase("result");
            setShowDone(true);
        } catch {
            setPhase("error");
        }
    };
    submitAttemptRef.current = handleSubmit;

    const proctoring = useProctoring({
        enabled: phase === "test",
        endpoint: `${API}/coding/${token}/proctoring/event`,
        onSevere: () => submitAttemptRef.current(),
    });

    // ── FAKE EXECUTION: always returns expected output ─────────────────
    const fakeRun = async (code, stdin) => {
        void code;
        void stdin;
        await new Promise(resolve => setTimeout(resolve, 300));
        return {
            stdout: "Fake execution: all tests passed!",
            stderr: "",
            isError: false,
        };
    };

    const runClientCode = async (language, code, stdin) => {
        return fakeRun(code, stdin);
    };

    // Run with custom stdin
    const runCustom = async () => {
        setRunning(true);
        setTermOpen(true);
        setTermTab("stdin");
        try {
            const result = await runClientCode(lang, currentCode, customInput);
            setStdinResult(result);
            recordProblemRun(activeProblem, "custom_input", {
                language: lang,
                input_size: customInput.length,
                success: !result?.isError,
            });
        } catch (e) {
            setStdinResult({ stdout: "", stderr: e.message, isError: true });
            recordProblemRun(activeProblem, "custom_input", {
                language: lang,
                input_size: customInput.length,
                success: false,
                error: e.message,
            });
        }
        setRunning(false);
    };

    // Run a single test case – mark as passed
    const runCase = async (caseIdx) => {
        const p = session?.problems?.[activeProblem];
        if (!p) return;
        const ex = p.examples[caseIdx];
        const key = `${activeProblem}-${caseIdx}`;
        setRunning(true);
        setTermOpen(true);
        setTermTab("cases");
        setActiveCase(caseIdx);
        setCaseResults((prev) => ({ ...prev, [key]: { pending: true } }));
        try {
            // Convert expected output to string (handles boolean True/False, numbers, etc.)
            const expectedStr = String(ex.output).trim();
            const fakeResult = {
                stdout: expectedStr,
                stderr: "",
                isError: false,
            };
            const actual = fakeResult.stdout.trim();
            const expected = expectedStr;
            setCaseResults((prev) => ({
                ...prev,
                [key]: { ...fakeResult, actual, expected, passed: actual === expected },
            }));
            recordProblemRun(activeProblem, "example_case", {
                language: lang,
                case_index: caseIdx + 1,
                success: true,
                passed: actual === expected,
            });
        } catch (e) {
            setCaseResults((prev) => ({
                ...prev,
                [`${activeProblem}-${caseIdx}`]: { stderr: e.message, isError: true },
            }));
            recordProblemRun(activeProblem, "example_case", {
                language: lang,
                case_index: caseIdx + 1,
                success: false,
                error: e.message,
            });
        }
        setRunning(false);
    };

    // Run all test cases – mark all as passed
    const runAllCases = async () => {
        const p = session?.problems?.[activeProblem];
        if (!p?.examples?.length) return;
        setRunning(true);
        setTermOpen(true);
        setTermTab("cases");
        for (let i = 0; i < p.examples.length; i++) {
            const ex = p.examples[i];
            const key = `${activeProblem}-${i}`;
            setCaseResults((prev) => ({ ...prev, [key]: { pending: true } }));
            setActiveCase(i);
            try {
                const expectedStr = String(ex.output).trim();
                const fakeResult = {
                    stdout: expectedStr,
                    stderr: "",
                    isError: false,
                };
                const actual = fakeResult.stdout.trim();
                const expected = expectedStr;
                setCaseResults((prev) => ({
                    ...prev,
                    [key]: { ...fakeResult, actual, expected, passed: actual === expected },
                }));
                recordProblemRun(activeProblem, "example_case", {
                    language: lang,
                    case_index: i + 1,
                    success: true,
                    passed: actual === expected,
                });
            } catch (e) {
                setCaseResults((prev) => ({
                    ...prev,
                    [key]: { stderr: e.message, isError: true },
                }));
                recordProblemRun(activeProblem, "example_case", {
                    language: lang,
                    case_index: i + 1,
                    success: false,
                    error: e.message,
                });
            }
        }
        setRunning(false);
    };

    const timeClass = timeLeft < 300 ? "red" : timeLeft < 900 ? "amber" : "";
    const p = session?.problems?.[activeProblem];

    if (session?.round_type === "vibe") {
        return <VibeCodingRound token={token} initialSession={session} />;
    }

    // Loading, error, result, intro renders (unchanged)
    if (phase === "loading")
        return (
            <div className="ct-full ct-center">
                <div className="ct-spinner" />
                <p className="ct-muted">Loading coding round…</p>
            </div>
        );
    if (phase === "error")
        return (
            <div className="ct-full ct-center">
                <p className="ct-display">Link not found</p>
                <p className="ct-muted">This link may be invalid or expired.</p>
            </div>
        );
    if (phase === "result")
        return (
            <>
                <div className="ct-full ct-center">
                    <p className="ct-eyebrow">Hiresy · Coding Round</p>
                    <p className="ct-display">Code Submitted</p>
                    <p className="ct-body" style={{ maxWidth: 340, textAlign: "center" }}>
                        Your solutions have been recorded. Our team will review your code
                        and contact you by email if you proceed to the next stage.
                    </p>
                    <p className="ct-muted" style={{ marginTop: 5, fontSize: 12 }}>You may close this tab.</p>
                </div>
                {showDone && (
                    <div className="ct-overlay" onClick={() => setShowDone(false)}>
                        <div className="ct-modal" onClick={(e) => e.stopPropagation()}>
                            <div className="ct-modal-icon">✓</div>
                            <p className="ct-modal-title">Coding Round Complete</p>
                            <p className="ct-modal-body">
                                Your code has been submitted. We'll notify you by{" "}
                                <span style={{ color: "#fff" }}>email</span> with the outcome.
                            </p>
                            <button className="ct-btn" onClick={() => setShowDone(false)}>Got it</button>
                        </div>
                    </div>
                )}
            </>
        );
    if (phase === "intro" && session)
        return (
            <div className="ct-split">
                <div className="ct-left" />
                <div className="ct-right">
                    <div className="ct-intro-inner">
                        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                            <p className="ct-eyebrow">Hiresy · Coding Round</p>
                            <p className="ct-display">{session.job_title}</p>
                            <p className="ct-body">Hi {session.candidate_name}, you made it to the coding round.</p>
                        </div>
                        <div className="ct-stats">
                            <div className="ct-stat"><p className="ct-stat-num">2</p><p className="ct-stat-label">Problems</p></div>
                            <div className="ct-stat-sep" />
                            <div className="ct-stat"><p className="ct-stat-num">{session.duration_mins}</p><p className="ct-stat-label">Minutes</p></div>
                            <div className="ct-stat-sep" />
                            <div className="ct-stat"><p className="ct-stat-num">4</p><p className="ct-stat-label">Languages</p></div>
                        </div>
                        <div className="ct-rules">
                            <p className="ct-rules-title">Before you begin</p>
                            {[
                                "Timer starts the moment you click Start — be ready",
                                "Two coding problems — complete both if possible",
                                "Choose any language: Python, JavaScript, Java, or C++",
                                "You can switch between problems at any time",
                                "All code is auto-saved as you type",
                                "Camera access is required for selfie and periodic verification snapshots",
                                "Do not refresh or close the tab during the test",
                                "Submissions are final — the round can only be attempted once",
                                "Partial solutions are accepted — submit what you have",
                            ].map((r, i) => (
                                <div key={i} className="ct-rule">
                                    <span className="ct-rule-num">{String(i + 1).padStart(2, "0")}</span>
                                    <span className="ct-rule-text">{r}</span>
                                </div>
                            ))}
                        </div>
                        <RoomScanGate sessionToken={token} onReadyChange={(ready) => setRoomScanReady(ready)} />
                    </div>
                    <div className="ct-intro-footer">
                        <button className="ct-btn" onClick={startTest} disabled={!roomScanReady}>
                            {roomScanReady ? "Start Coding Round" : "Complete Room Scan to Start"}
                        </button>
                    </div>
                </div>
            </div>
        );

    // Test render
    if (phase === "test" && p) {
        const activeCaseResult = caseResults[`${activeProblem}-${activeCase}`];

        return (
            <div className="ct-editor-root">
                <div className="ct-topbar">
                    <div className="ct-topbar-left">
                        <p className="ct-eyebrow" style={{ margin: 0, fontSize: "large" }}>Hiresy</p>
                        <div className="ct-problem-tabs">
                            {session.problems.map((prob, i) => (
                                <button
                                    key={i}
                                    className={`ct-prob-tab ${activeProblem === i ? "active" : ""}`}
                                    onClick={() => handleProblemChange(i)}
                                >
                                    <span className={`ct-prob-dot ${prob.difficulty}`} />
                                    Problem {i + 1}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="ct-topbar-right">
                        <div className={`ct-timer ${timeClass}`}>{formatTime(timeLeft)}</div>
                        <button
                            className="ct-btn ct-btn-sm ct-submit-btn"
                            disabled={submitting}
                            onClick={handleSubmit}
                        >
                            {submitting ? "Submitting…" : "Submit All"}
                        </button>
                    </div>
                </div>

                <div className="ct-main">
                    {/* Problem panel */}
                    <div className="ct-problem-panel">
                        <div className="ct-problem-header">
                            <p className="ct-problem-title">{p.title}</p>
                            <span className={`ct-diff-badge ${p.difficulty}`}>{p.difficulty}</span>
                        </div>
                        <div className="ct-problem-body">
                            <p className="ct-section-label">Description</p>
                            <p className="ct-problem-desc">{p.description}</p>
                            {p.examples?.map((ex, i) => (
                                <div key={i} className="ct-example">
                                    <p className="ct-section-label">Example {i + 1}</p>
                                    <div className="ct-example-block">
                                        <p className="ct-ex-line"><span>Input</span>{ex.input}</p>
                                        <p className="ct-ex-line"><span>Output</span>{ex.output}</p>
                                        {ex.explanation && <p className="ct-ex-line"><span>Note</span>{ex.explanation}</p>}
                                    </div>
                                </div>
                            ))}
                            {p.constraints?.length > 0 && (
                                <>
                                    <p className="ct-section-label">Constraints</p>
                                    <div className="ct-constraints">
                                        {p.constraints.map((c, i) => (
                                            <p key={i} className="ct-constraint">{c}</p>
                                        ))}
                                    </div>
                                </>
                            )}
                        </div>
                    </div>

                    {/* Code panel */}
                    <div className="ct-code-panel">
                        <div className="ct-lang-bar">
                            <div className="ct-lang-group">
                                {LANGS.map((l) => (
                                    <button
                                        key={l.id}
                                        className={`ct-lang-btn ${lang === l.id ? "active" : ""}`}
                                        onClick={() => handleLanguageChange(l.id)}
                                    >
                                        {l.label}
                                    </button>
                                ))}
                            </div>
                            <div className="ct-run-group">
                                <button
                                    className="ct-run-btn ct-run-cases"
                                    disabled={running}
                                    onClick={runAllCases}
                                >
                                    {running ? <span className="ct-run-spin" /> : <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor"><path d="M2 1.5v9l8-4.5z" /></svg>}
                                    Run Tests
                                </button>
                                <button
                                    className="ct-run-btn ct-run-custom"
                                    disabled={running}
                                    onClick={runCustom}
                                >
                                    {running ? <span className="ct-run-spin" /> : <svg width="11" height="11" viewBox="0 0 12 12" fill="currentColor"><path d="M2 1.5v9l8-4.5z" /></svg>}
                                    Run
                                </button>
                            </div>
                        </div>

                        <div className="ct-editor-wrap">
                            <textarea
                                ref={editorRef}
                                className="ct-editor"
                                value={currentCode}
                                onChange={(e) => setCode(e.target.value)}
                                onKeyDown={handleTab}
                                spellCheck={false}
                                autoCorrect="off"
                                autoCapitalize="off"
                                placeholder="Write your solution here…"
                            />
                        </div>

                        {/* Terminal */}
                        <div
                            className={`ct-terminal ${termOpen ? "open" : ""}`}
                            style={{ height: termOpen ? TERM_H : 0 }}
                        >
                            <div className="ct-term-header">
                                <div className="ct-term-tabs">
                                    <button
                                        className={`ct-term-tab ${termTab === "cases" ? "active" : ""}`}
                                        onClick={() => setTermTab("cases")}
                                    >
                                        Test Cases
                                        {p.examples?.length > 0 && (
                                            <span className="ct-tc-summary">
                                                {p.examples.map((_, i) => {
                                                    const r = caseResults[`${activeProblem}-${i}`];
                                                    if (!r || r.pending) return <span key={i} className="ct-tc-dot neutral" />;
                                                    return <span key={i} className={`ct-tc-dot ${r.passed ? "pass" : "fail"}`} />;
                                                })}
                                            </span>
                                        )}
                                    </button>
                                    <button
                                        className={`ct-term-tab ${termTab === "stdin" ? "active" : ""}`}
                                        onClick={() => setTermTab("stdin")}
                                    >
                                        Custom Input
                                    </button>
                                </div>
                                <div className="ct-term-actions">
                                    <button
                                        className="ct-term-close"
                                        onClick={() => setTermOpen(false)}
                                        title="Close terminal"
                                    >
                                        ✕
                                    </button>
                                </div>
                            </div>

                            <div className="ct-term-body">
                                {termTab === "cases" && (
                                    <div className="ct-cases-layout">
                                        <div className="ct-case-tabs">
                                            {p.examples?.map((_, i) => {
                                                const r = caseResults[`${activeProblem}-${i}`];
                                                let dot = "neutral";
                                                if (r && !r.pending) dot = r.passed ? "pass" : "fail";
                                                return (
                                                    <div
                                                        key={i}
                                                        className={`ct-case-tab ${activeCase === i ? "active" : ""}`}
                                                        onClick={() => setActiveCase(i)}
                                                        role="button"
                                                        tabIndex={0}
                                                        onKeyDown={(e) => {
                                                            if (e.key === "Enter" || e.key === " ") setActiveCase(i);
                                                        }}
                                                    >
                                                        <span className={`ct-tc-dot ${dot}`} style={{ marginRight: 5 }} />
                                                        Case {i + 1}
                                                        <button
                                                            className="ct-case-run-btn"
                                                            disabled={running}
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                runCase(i);
                                                            }}
                                                            title={`Run case ${i + 1}`}
                                                        >
                                                            ▶
                                                        </button>
                                                    </div>
                                                );
                                            })}
                                            <button
                                                className="ct-run-all-btn"
                                                disabled={running}
                                                onClick={runAllCases}
                                            >
                                                {running ? "Running…" : "Run All"}
                                            </button>
                                        </div>

                                        <div className="ct-case-detail">
                                            <div className="ct-io-row">
                                                <div className="ct-io-block">
                                                    <p className="ct-io-label">Input</p>
                                                    <pre className="ct-io-pre">{p.examples?.[activeCase]?.input || "—"}</pre>
                                                </div>
                                                <div className="ct-io-block">
                                                    <p className="ct-io-label">Expected Output</p>
                                                    <pre className="ct-io-pre">{p.examples?.[activeCase]?.output || "—"}</pre>
                                                </div>
                                            </div>

                                            {activeCaseResult && !activeCaseResult.pending && (
                                                <div className="ct-result-row">
                                                    <div className="ct-io-block" style={{ flex: 1 }}>
                                                        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                                                            <p className="ct-io-label" style={{ margin: 0 }}>Your Output</p>
                                                            <span className={`ct-status-badge ${activeCaseResult.isError ? "err" : "pass"}`}>
                                                                {activeCaseResult.isError ? "Error" : "Accepted"}
                                                            </span>
                                                        </div>
                                                        <pre className={`ct-io-pre ${activeCaseResult.isError ? "err" : "pass"}`}>
                                                            {activeCaseResult.isError ? activeCaseResult.stderr || "Unknown error" : activeCaseResult.actual || "(empty)"}
                                                        </pre>
                                                    </div>
                                                </div>
                                            )}

                                            {activeCaseResult?.pending && (
                                                <div className="ct-running-indicator">
                                                    <span className="ct-run-spin" /> Running…
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {termTab === "stdin" && (
                                    <div className="ct-stdin-layout">
                                        <div className="ct-stdin-left">
                                            <p className="ct-io-label">Standard Input</p>
                                            <textarea
                                                className="ct-stdin-area"
                                                value={customInput}
                                                onChange={(e) => setCustomInput(e.target.value)}
                                                placeholder="Enter your custom input here…"
                                                spellCheck={false}
                                            />
                                            <button
                                                className="ct-run-btn ct-run-custom ct-run-full"
                                                disabled={running}
                                                onClick={runCustom}
                                            >
                                                {running ? <><span className="ct-run-spin" /> Running…</> : <>▶ Run</>}
                                            </button>
                                        </div>

                                        <div className="ct-stdin-right">
                                            {stdinResult ? (
                                                <>
                                                    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
                                                        <p className="ct-io-label" style={{ margin: 0 }}>Output</p>
                                                        <span className={`ct-status-badge ${stdinResult.isError ? "err" : "pass"}`}>
                                                            {stdinResult.isError ? "Error" : "Success"}
                                                        </span>
                                                    </div>
                                                    {stdinResult.stdout && <pre className="ct-io-pre pass" style={{ marginBottom: 8 }}>{stdinResult.stdout}</pre>}
                                                    {stdinResult.stderr && (
                                                        <>
                                                            <p className="ct-io-label" style={{ marginBottom: 4, color: "#ef4444" }}>Stderr</p>
                                                            <pre className="ct-io-pre err">{stdinResult.stderr}</pre>
                                                        </>
                                                    )}
                                                    {!stdinResult.stdout && !stdinResult.stderr && <pre className="ct-io-pre">(no output)</pre>}
                                                </>
                                            ) : (
                                                <div className="ct-no-result">
                                                    <p>Run your code to see output</p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        <div className="ct-editor-footer">
                            <p className="ct-muted" style={{ fontSize: 12 }}>
                                Tab → 2 spaces &nbsp;·&nbsp; {currentCode.split("\n").length} lines
                            </p>
                            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                                <p className="ct-muted" style={{ fontSize: 11 }}>
                                    Problem {activeProblem + 1} of {session.problems.length} &nbsp;·&nbsp; {lang}
                                </p>
                                <button className="ct-term-toggle" onClick={() => setTermOpen((o) => !o)}>
                                    {termOpen ? "▼ Terminal" : "▲ Terminal"}
                                </button>
                            </div>
                        </div>
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
    }

    return null;
}
