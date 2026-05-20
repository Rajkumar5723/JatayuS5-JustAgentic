import { useState, useRef, useEffect } from "react";
import "./VibeCoding.css";

// ─── Language / icon maps ─────────────────────────────────────────────────────
const LANG_MAP = {
    js: "JavaScript", jsx: "React JSX", ts: "TypeScript", tsx: "TSX",
    html: "HTML", css: "CSS", scss: "SCSS",
    py: "Python", java: "Java", cpp: "C++", c: "C",
    go: "Go", rs: "Rust", rb: "Ruby", php: "PHP", sh: "Shell",
    json: "JSON", md: "Markdown", txt: "Text",
};
const FILE_ICONS = {
    js: "🟨", jsx: "⚛️", ts: "🔷", tsx: "⚛️", html: "🌐", css: "🎨",
    scss: "🎨", py: "🐍", java: "☕", cpp: "⚙️", c: "⚙️", go: "🐹",
    rs: "🦀", rb: "💎", php: "🐘", sh: "🖥️", json: "📋", md: "📝",
};

// Only CSS/HTML/SCSS are purely visual — JS/TS still need to run via backend
const PREVIEW_ONLY_EXTS = new Set(["html", "css", "scss"]);
const extOf = (n) => n.split(".").pop().toLowerCase();
const langOf = (n) => LANG_MAP[extOf(n)] || extOf(n).toUpperCase();
const iconOf = (n) => FILE_ICONS[extOf(n)] || "📄";

// ─── Build live preview srcdoc ────────────────────────────────────────────────
function buildPreview(files, activeFile) {
    // Prefer the active file if it's HTML, otherwise fall back to the first HTML file
    const htmlFile =
        (activeFile && extOf(activeFile.name) === "html" ? activeFile : null) ||
        files.find((f) => extOf(f.name) === "html");
    if (!htmlFile) return null;
    const css = files
        .filter((f) => ["css", "scss"].includes(extOf(f.name)))
        .map((f) => `<style>/* ${f.name} */\n${f.content}</style>`)
        .join("\n");
    const js = files
        .filter((f) => ["js", "jsx"].includes(extOf(f.name)))
        .map((f) => `<script>/* ${f.name} */\n${f.content}<\/script>`)
        .join("\n");
    let html = htmlFile.content;
    html = html.includes("</head>") ? html.replace("</head>", `${css}\n</head>`) : css + "\n" + html;
    html = html.includes("</body>") ? html.replace("</body>", `${js}\n</body>`) : html + "\n" + js;
    return html;
}

// ─── Code formatter ───────────────────────────────────────────────────────────
function formatCode(code, ext) {
    const sp = "  ";
    const jsLike = ["js", "jsx", "ts", "tsx", "java", "c", "cpp", "go", "rs", "php", "css", "scss"].includes(ext);
    const pyLike = ext === "py";
    const lines = code.split("\n");
    let level = 0;
    const out = [];
    for (const raw of lines) {
        const line = raw.trim();
        if (!line) { out.push(""); continue; }
        if (jsLike && /^[}\])]/.test(line)) level = Math.max(0, level - 1);
        out.push(sp.repeat(level) + line);
        if (jsLike && /[{(\[]$/.test(line) && !/^\s*(\/\/|\/\*)/.test(line)) level++;
        if (pyLike && /:\s*$/.test(line) && !line.startsWith("#")) level++;
        if (pyLike && /^(return|pass|break|continue|raise)\b/.test(line)) level = Math.max(0, level - 1);
    }
    return out.join("\n");
}

// ─── ChatGPT-style message bubble ────────────────────────────────────────────
function MessageBubble({ msg, onUseCode }) {
    const parts = [];
    let last = 0;
    const re = /```(\w*)\n?([\s\S]*?)```/g;
    let m;
    while ((m = re.exec(msg.content)) !== null) {
        if (m.index > last) parts.push({ type: "text", value: msg.content.slice(last, m.index) });
        parts.push({ type: "code", lang: m[1] || "code", value: m[2].trim() });
        last = m.index + m[0].length;
    }
    if (last < msg.content.length) parts.push({ type: "text", value: msg.content.slice(last) });

    return (
        <div className={`vc-bubble vc-bubble-${msg.role}`}>
            {parts.map((p, i) =>
                p.type === "text" ? (
                    <p key={i} className="vc-bubble-text">{p.value}</p>
                ) : (
                    <div key={i} className="vc-code-block">
                        <div className="vc-code-block-bar">
                            <span className="vc-code-lang">{p.lang}</span>
                            <div className="vc-code-btns">
                                <button className="vc-cb-btn" onClick={() => navigator.clipboard?.writeText(p.value)}>
                                    Copy
                                </button>
                                <button className="vc-cb-btn vc-use-btn" onClick={() => onUseCode(p.value)}>
                                    Use Code
                                </button>
                            </div>
                        </div>
                        <pre className="vc-code-pre"><code>{p.value}</code></pre>
                    </div>
                )
            )}
        </div>
    );
}

// ─── Default files ────────────────────────────────────────────────────────────
function makeDefaultFiles(starterCode, languages) {
    if (starterCode) {
        const lang = (languages?.[0] || "py").toLowerCase();
        const extMap = { python: "py", javascript: "js", java: "java", go: "go", cpp: "cpp", typescript: "ts" };
        const ext = extMap[lang] || lang;
        return [{ id: 1, name: `main.${ext}`, content: starterCode }];
    }
    return [{ id: 1, name: "main.py", content: "" }];
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function VibeCoding({ token, test, onComplete, apiBase = "", submitHandleRef = null }) {
    const [files, setFiles] = useState(() => makeDefaultFiles(test.starter_code, test.languages));
    const [activeId, setActiveId] = useState(1);
    const [nextId, setNextId] = useState(2);
    const [output, setOutput] = useState("");
    const [running, setRunning] = useState(false);
    const [outputTab, setOutputTab] = useState("output");
    const [messages, setMessages] = useState([]);
    const [chatInput, setChatInput] = useState("");
    const [timeLeft, setTimeLeft] = useState(test.duration_mins * 60);
    const [showNewFile, setShowNewFile] = useState(false);
    const [newFileName, setNewFileName] = useState("");
    const [renaming, setRenaming] = useState(null);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [applying, setApplying] = useState(false);

    // Resize state
    const [explorerW, setExplorerW] = useState(11);
    const [chatW, setChatW] = useState(27);
    const [editorH, setEditorH] = useState(63);

    const timerRef = useRef(null);
    const chatEndRef = useRef(null);
    const newFileRef = useRef(null);
    const previewRef = useRef(null);
    const containerRef = useRef(null);
    const editorPanelRef = useRef(null);
    const dragging = useRef(null);
    const startedAtRef = useRef(Date.now());

    const activeFile = files.find((f) => f.id === activeId) || files[0];
    const previewSrc = buildPreview(files, activeFile);
    // A file has a live preview only if an HTML file exists in the project
    const hasPreview = !!previewSrc;

    // ── Global drag handlers ───────────────────────────────────────────────────
    useEffect(() => {
        const onMove = (e) => {
            if (!dragging.current) return;
            const x = e.touches ? e.touches[0].clientX : e.clientX;
            const y = e.touches ? e.touches[0].clientY : e.clientY;
            if (dragging.current === "explorer") {
                const r = containerRef.current?.getBoundingClientRect();
                if (r) setExplorerW(Math.max(7, Math.min(20, ((x - r.left) / r.width) * 100)));
            } else if (dragging.current === "chat") {
                const r = containerRef.current?.getBoundingClientRect();
                if (r) setChatW(Math.max(18, Math.min(42, ((r.right - x) / r.width) * 100)));
            } else if (dragging.current === "editorH") {
                const r = editorPanelRef.current?.getBoundingClientRect();
                if (r) setEditorH(Math.max(20, Math.min(85, ((y - r.top) / r.height) * 100)));
            }
        };
        const onUp = () => {
            dragging.current = null;
            document.body.style.cursor = "";
            document.body.style.userSelect = "";
        };
        window.addEventListener("mousemove", onMove);
        window.addEventListener("mouseup", onUp);
        return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
    }, []);

    const startDrag = (type, cursor) => {
        dragging.current = type;
        document.body.style.cursor = cursor;
        document.body.style.userSelect = "none";
    };

    // ── Timer ──────────────────────────────────────────────────────────────────
    useEffect(() => {
        timerRef.current = setInterval(() => {
            setTimeLeft((t) => {
                if (t <= 1) { clearInterval(timerRef.current); handleSubmit(); return 0; }
                return t - 1;
            });
        }, 1000);
        return () => clearInterval(timerRef.current);
    }, []);

    const formatTime = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;

    // ── FIX #3: Auto-scroll chat on every new message ─────────────────────────
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // ── FIX #4: Reset stale preview tab when no HTML exists ───────────────────
    useEffect(() => {
        if (outputTab === "preview" && !hasPreview) {
            setOutputTab("output");
        }
    }, [hasPreview, outputTab]);

    // ── File ops ───────────────────────────────────────────────────────────────
    const updateContent = (id, content) =>
        setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, content } : f)));

    const addFile = () => {
        const name = newFileName.trim() || `file${nextId}.py`;
        const id = nextId;
        setFiles((prev) => [...prev, { id, name, content: "" }]);
        setActiveId(id);
        setNextId(id + 1);
        setNewFileName("");
        setShowNewFile(false);
    };

    const deleteFile = (id) => {
        if (files.length === 1) return;
        const remaining = files.filter((f) => f.id !== id);
        setFiles(remaining);
        if (activeId === id) setActiveId(remaining[0]?.id);
    };

    const renameFile = (id, name) => {
        if (name.trim()) setFiles((prev) => prev.map((f) => (f.id === id ? { ...f, name: name.trim() } : f)));
        setRenaming(null);
    };

    const handleFormat = () => {
        const formatted = formatCode(activeFile.content, extOf(activeFile.name));
        updateContent(activeId, formatted);
    };

    // Tab key → spaces, Enter → auto-indent
    const handleEditorKey = (e) => {
        const ta = e.target;
        const { selectionStart: ss, selectionEnd: se, value } = ta;
        if (e.key === "Tab") {
            e.preventDefault();
            if (!e.shiftKey) {
                const nv = value.slice(0, ss) + "  " + value.slice(se);
                updateContent(activeId, nv);
                requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = ss + 2; });
            } else {
                const lineStart = value.lastIndexOf("\n", ss - 1) + 1;
                if (value.slice(lineStart, lineStart + 2) === "  ") {
                    const nv = value.slice(0, lineStart) + value.slice(lineStart + 2);
                    updateContent(activeId, nv);
                    requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = Math.max(lineStart, ss - 2); });
                }
            }
        }
        if (e.key === "Enter") {
            e.preventDefault();
            const lineStart = value.lastIndexOf("\n", ss - 1) + 1;
            const indent = value.slice(lineStart).match(/^(\s*)/)[1];
            const prevChar = value[ss - 1];
            const extra = ["{", ":", "(", "["].includes(prevChar) ? "  " : "";
            const ins = "\n" + indent + extra;
            const nv = value.slice(0, ss) + ins + value.slice(se);
            updateContent(activeId, nv);
            requestAnimationFrame(() => { ta.selectionStart = ta.selectionEnd = ss + ins.length; });
        }
    };

    // ── Run — correct preview vs backend-run logic ────────────────────────────
    const handleRun = async () => {
        const ext = extOf(activeFile.name);

        // Only show preview if the active file itself is HTML/CSS/SCSS
        if (PREVIEW_ONLY_EXTS.has(ext)) {
            if (hasPreview) {
                setOutputTab("preview");
            } else {
                setOutput("💡 Add an HTML file to see a live preview for CSS/HTML.");
                setOutputTab("output");
            }
            return;
        }

        // Everything else (py, js, ts, java, c, cpp, go, etc.) → run via backend
        setRunning(true);
        setOutput("Running…");
        setOutputTab("output");
        try {
            const res = await fetch(`${apiBase}/coding/${token}/run`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    code: activeFile.content,
                    language: langOf(activeFile.name),
                    filename: activeFile.name,
                    all_files: files.map((f) => ({ name: f.name, content: f.content })),
                }),
            });
            const data = await res.json();
            setOutput(
                data.passed
                    ? `✅ Passed\nActual:   ${data.actual_output}\nExpected: ${data.expected_output}`
                    : `❌ Failed\nActual:   ${data.actual_output}\nExpected: ${data.expected_output}\nError:    ${data.error || "None"}`
            );
        } catch (err) {
            setOutput(`Error: ${err.message}`);
        }
        setRunning(false);
    };

    // ── Submit ─────────────────────────────────────────────────────────────────
    const handleSubmit = async () => {
        clearInterval(timerRef.current);
        setOutput("⏳ Submitting your code… Please wait.");
        setOutputTab("output");
        try {
            const primaryLanguage = (activeFile?.name?.split(".").pop() || "py").toLowerCase();
            const durationSeconds = Math.max(0, Math.round((Date.now() - startedAtRef.current) / 1000));
            const res = await fetch(`${apiBase}/coding/${token}/submit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    submissions: [
                        {
                            problem_idx: 0,
                            problem_id: test.problem_id || 1,
                            language: primaryLanguage,
                            code: activeFile.content,
                            files: files.map((f) => ({ name: f.name, content: f.content })),
                        },
                    ],
                    telemetry: {
                        started_at: new Date(startedAtRef.current).toISOString(),
                        submitted_at: new Date().toISOString(),
                        total_duration_seconds: durationSeconds,
                        problem_metrics: [
                            {
                                problem_index: 1,
                                problem_id: test.problem_id || 1,
                                problem_title: test.problem_title || "Vibe Coding",
                                selected_language: primaryLanguage,
                                started_at: new Date(startedAtRef.current).toISOString(),
                                ended_at: new Date().toISOString(),
                                time_spent_seconds: durationSeconds,
                                response_latency_seconds: 0,
                                code_size: activeFile.content.length,
                            },
                        ],
                    },
                }),
            });
            onComplete?.(await res.json());
        } catch (err) {
            setOutput("❌ Submission failed. Please try again.");
        }
    };

    useEffect(() => {
        if (!submitHandleRef) return undefined;
        submitHandleRef.current = handleSubmit;
        return () => {
            submitHandleRef.current = null;
        };
    }, [submitHandleRef, handleSubmit]);

    // ── Chat ───────────────────────────────────────────────────────────────────
    const sendChat = async () => {
        if (!chatInput.trim()) return;
        const userMsg = { role: "user", content: chatInput };
        setMessages((prev) => [...prev, userMsg]);
        setChatInput("");
        try {
            const res = await fetch(`${apiBase}/coding/${token}/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: chatInput,
                    context: { code: activeFile.content, filename: activeFile.name, language: langOf(activeFile.name) },
                }),
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                const msg = res.status === 429
                    ? "⚠️ AI service is rate-limited. Wait a moment and try again."
                    : `⚠️ Server error ${res.status}: ${body.detail || "unknown error"}`;
                setMessages((prev) => [...prev, { role: "assistant", content: msg }]);
                return;
            }
            const data = await res.json();
            setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);
        } catch (err) {
            const is429 = err?.message?.includes("429") || (err instanceof Response && err.status === 429);
            setMessages((prev) => [...prev, {
                role: "assistant",
                content: is429
                    ? "⚠️ The AI service is rate-limited right now. Wait a few seconds and try again."
                    : "Sorry, I'm having trouble connecting to the AI service. Please retry.",
            }]);
        }
    };

    // ── FIX #2: Smart apply — merge small snippets via /edit, replace large ones ──
    const applyCode = async (snippet) => {
        const current = activeFile.content;
        const isEmpty = !current.trim();

        // Heuristic: if existing file is empty OR snippet is ≥ 60% the size of current
        // code, it's clearly a full rewrite — just replace directly.
        const snippetRatio = snippet.length / (current.length || 1);
        const isFullRewrite = isEmpty || snippetRatio >= 0.6;

        if (isFullRewrite) {
            updateContent(activeId, snippet);
            setMessages((prev) => [...prev, {
                role: "assistant",
                content: `Code applied to \`${activeFile.name}\`.`,
            }]);
            return;
        }

        // Small snippet → call /edit to intelligently integrate it into existing code
        setApplying(true);
        setMessages((prev) => [...prev, {
            role: "assistant",
            content: `⏳ Merging snippet into \`${activeFile.name}\`…`,
        }]);

        try {
            const res = await fetch(`${apiBase}/coding/${token}/edit`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    instruction: `Integrate this snippet into the existing code — do not discard anything that is not being replaced:\n\n${snippet}`,
                    code: current,
                }),
            });
            if (!res.ok) {
                const body = await res.json().catch(() => ({}));
                const msg = res.status === 429
                    ? "⚠️ AI service is rate-limited. Wait a moment and try again."
                    : `⚠️ Edit failed (${res.status}): ${body.detail || "unknown error"}`;
                setMessages((prev) => { const copy = [...prev]; copy[copy.length - 1] = { role: "assistant", content: msg }; return copy; });
                return;
            }
            const data = await res.json();
            updateContent(activeId, data.new_code);
            setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                    role: "assistant",
                    content: `Applied to \`${activeFile.name}\`: ${data.explanation}`,
                };
                return copy;
            });
        } catch {
            // Network or parse failure — fall back to direct insert
            updateContent(activeId, snippet);
            setMessages((prev) => {
                const copy = [...prev];
                copy[copy.length - 1] = {
                    role: "assistant",
                    content: `Code applied to \`${activeFile.name}\` (direct replace — edit endpoint unavailable).`,
                };
                return copy;
            });
        } finally {
            setApplying(false);
        }
    };

    // ── Fullscreen ─────────────────────────────────────────────────────────────
    const toggleFullscreen = () => {
        if (!document.fullscreenElement) {
            previewRef.current?.requestFullscreen?.().catch(() => { });
        } else {
            document.exitFullscreen?.();
        }
    };
    useEffect(() => {
        const cb = () => setIsFullscreen(!!document.fullscreenElement);
        document.addEventListener("fullscreenchange", cb);
        return () => document.removeEventListener("fullscreenchange", cb);
    }, []);

    useEffect(() => { if (showNewFile) newFileRef.current?.focus(); }, [showNewFile]);

    // ── Render ─────────────────────────────────────────────────────────────────
    return (
        <div className="vc-container">

            {/* Header */}
            <div className="vc-header">
                <div className="vc-timer">⏱ {formatTime(timeLeft)}</div>
                <div className="vc-header-mid">
                    <span className="vc-active-label">{iconOf(activeFile.name)} {activeFile.name}</span>
                    <span className="vc-lang-pill">{langOf(activeFile.name)}</span>
                </div>
                <button className="vc-submit-btn" onClick={handleSubmit}>Submit</button>
            </div>

            {/* Main split */}
            <div className="vc-split" ref={containerRef}>

                {/* ── File Explorer ── */}
                <div className="vc-explorer" style={{ width: `${explorerW}%` }}>
                    <div className="vc-panel-title">
                        <span>EXPLORER</span>
                        <button className="vc-icon-btn" onClick={() => setShowNewFile((v) => !v)} title="New file">＋</button>
                    </div>

                    {showNewFile && (
                        <div className="vc-new-file-row">
                            <input
                                ref={newFileRef}
                                value={newFileName}
                                onChange={(e) => setNewFileName(e.target.value)}
                                placeholder="file.py"
                                onKeyDown={(e) => { if (e.key === "Enter") addFile(); if (e.key === "Escape") setShowNewFile(false); }}
                            />
                            <button onClick={addFile}>✓</button>
                        </div>
                    )}

                    <div className="vc-file-list">
                        {files.map((f) => (
                            <div
                                key={f.id}
                                className={`vc-file-item${f.id === activeId ? " active" : ""}`}
                                onClick={() => setActiveId(f.id)}
                            >
                                <span className="vc-file-icon">{iconOf(f.name)}</span>
                                {renaming === f.id ? (
                                    <input
                                        className="vc-rename-input"
                                        defaultValue={f.name}
                                        autoFocus
                                        onBlur={(e) => renameFile(f.id, e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === "Enter") renameFile(f.id, e.target.value);
                                            if (e.key === "Escape") setRenaming(null);
                                        }}
                                        onClick={(e) => e.stopPropagation()}
                                    />
                                ) : (
                                    <span
                                        className="vc-file-name"
                                        onDoubleClick={(e) => { e.stopPropagation(); setRenaming(f.id); }}
                                    >{f.name}</span>
                                )}
                                {files.length > 1 && (
                                    <button className="vc-file-del" onClick={(e) => { e.stopPropagation(); deleteFile(f.id); }}>×</button>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Drag: explorer ↔ editor */}
                <div className="vc-drag-col" onMouseDown={() => startDrag("explorer", "col-resize")} />

                {/* ── Editor + Terminal ── */}
                <div className="vc-editor-panel" ref={editorPanelRef} style={{ flex: 1, minWidth: 0 }}>

                    {/* Toolbar */}
                    <div className="vc-editor-toolbar">
                        <span className="vc-toolbar-file">{iconOf(activeFile.name)} {activeFile.name}</span>
                        <button className="vc-format-btn" onClick={handleFormat} title="Auto-format">Format</button>
                    </div>

                    {/* Editor */}
                    <div className="vc-editor-wrap" style={{ height: `${editorH}%` }}>
                        <textarea
                            className="vc-code-editor"
                            value={activeFile.content}
                            onChange={(e) => updateContent(activeId, e.target.value)}
                            onKeyDown={handleEditorKey}
                            spellCheck={false}
                            placeholder={`// ${activeFile.name}`}
                        />
                    </div>

                    {/* Drag: editor ↔ terminal */}
                    <div className="vc-drag-row" onMouseDown={() => startDrag("editorH", "row-resize")} />

                    {/* Terminal */}
                    <div className="vc-terminal" style={{ height: `${100 - editorH - 2}%` }}>
                        <div className="vc-terminal-bar">
                            <div className="vc-term-tabs">
                                <button className={`vc-tab${outputTab === "output" ? " active" : ""}`} onClick={() => setOutputTab("output")}>
                                    ▶ Output
                                </button>
                                {/* Preview tab only shown when an HTML file actually exists */}
                                {hasPreview && (
                                    <button className={`vc-tab${outputTab === "preview" ? " active" : ""}`} onClick={() => setOutputTab("preview")}>
                                        🌐 Preview
                                    </button>
                                )}
                            </div>
                            <div className="vc-term-right">
                                {outputTab === "preview" && hasPreview && (
                                    <button className="vc-icon-btn" onClick={toggleFullscreen} title="Fullscreen">
                                        {isFullscreen ? "⊡" : "⛶"}
                                    </button>
                                )}
                                <button className="vc-run-btn" onClick={handleRun} disabled={running}>
                                    {running ? "Running…" : "▶ Run"}
                                </button>
                            </div>
                        </div>

                        {outputTab === "output" && (
                            <pre className="vc-output">{output || "Click ▶ Run to test your code."}</pre>
                        )}
                        {outputTab === "preview" && (
                            previewSrc
                                ? <iframe ref={previewRef} className="vc-preview-frame" srcDoc={previewSrc} sandbox="allow-scripts" title="Live Preview" />
                                : <div className="vc-preview-empty">Add an <strong>.html</strong> file to enable live preview.</div>
                        )}
                    </div>
                </div>

                {/* Drag: editor ↔ chat */}
                <div className="vc-drag-col" onMouseDown={() => startDrag("chat", "col-resize")} />

                {/* ── AI Chat (right) ── */}
                <div className="vc-chat" style={{ width: `${chatW}%` }}>
                    <div className="vc-panel-title">
                        <span>HYRA CODE</span>
                    </div>

                    <div className="vc-chat-messages">
                        {messages.length === 0 && (
                            <div className="vc-chat-empty">
                                Ask me to explain, debug, or write code.<br /><br />
                                Tap <i>Use Code</i> on any snippet — small changes are merged smartly into your file; full rewrites replace it.
                            </div>
                        )}
                        {messages.map((msg, i) => (
                            <MessageBubble key={i} msg={msg} onUseCode={applying ? () => { } : applyCode} />
                        ))}
                        <div ref={chatEndRef} />
                    </div>

                    <div className="vc-chat-input">
                        <textarea
                            value={chatInput}
                            onChange={(e) => setChatInput(e.target.value)}
                            placeholder="Ask a question or request a change…"
                            rows={2}
                            onKeyDown={(e) => {
                                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
                            }}
                        />
                        <button className="vc-send-btn" onClick={sendChat} title="Send">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round">
                                <line x1="12" y1="19" x2="12" y2="5" />
                                <polyline points="5 12 12 5 19 12" />
                            </svg>
                        </button>
                    </div>
                </div>

            </div>
        </div>
    );
}
