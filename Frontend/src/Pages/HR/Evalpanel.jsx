// import "./EvalPanel.css";
// import { GitHubAnalytics, LeetCodeAnalytics, LinkedInAnalytics } from "./AnalyticsComponents";

// // ── Single colour system: #FF4400 ──
// const BASE = "#ff6b35b4";
// const LIGHT = "#ff663399";   // lighter tint
// const DIM = "rgba(255, 68, 0, 0.12)";
// const BORDER = "rgba(255, 68, 0, 0.30)";
// const DARK = "#b33000";   // darker shade
// const MUTED = "#3a1800";   // very dark tint for backgrounds

// function scoreColor(s) {
//     if (s >= 70) return LIGHT;
//     if (s >= 50) return BASE;
//     return DARK;
// }

// function Gauge({ value, size = 100 }) {
//     const r = size * 0.38, circ = 2 * Math.PI * r, arc = circ * 0.75;
//     const dash = (value / 100) * arc, sc = scoreColor(value);
//     return (
//         <svg width={size} height={size * 0.75} viewBox={`0 0 ${size} ${size * 0.75}`}>
//             <circle cx={size / 2} cy={size * 0.6} r={r} fill="none" stroke="#1c1c1c"
//                 strokeWidth={size * 0.08} strokeDasharray={`${arc} ${circ - arc}`}
//                 strokeDashoffset={circ * 0.125} strokeLinecap="round" />
//             <circle cx={size / 2} cy={size * 0.6} r={r} fill="none" stroke={sc}
//                 strokeWidth={size * 0.08} strokeDasharray={`${dash} ${circ - dash}`}
//                 strokeDashoffset={circ * 0.125} strokeLinecap="round" />
//             <text x={size / 2} y={size * 0.63} textAnchor="middle"
//                 fontSize={size * 0.22} fontWeight="800" fill={sc}>{value}</text>
//         </svg>
//     );
// }

// function SectionTitle({ children }) {
//     return (
//         <div className="ep-section-title-wrap">
//             <span className="ep-section-accent" />
//             <h3 className="ep-section-title">{children}</h3>
//         </div>
//     );
// }

// export default function EvalPanel({ evalData, evalSummary, candidate }) {
//     if (!evalData) return null;
//     let ev;
//     try { ev = typeof evalData === "string" ? JSON.parse(evalData) : evalData; } catch { return null; }

//     const cs = ev.component_scores || {}, gh = ev.github_raw || {}, lc = ev.leetcode_raw || {};
//     const overallScore = Math.round(ev.final_score || 0);

//     return (
//         <div className="ep-wrap">

//             {/* ══ VERDICT ══ */}
//             <div className="ep-verdict">
//                 <div className="ep-verdict-left">
//                     <span className="ep-rec-pill">{ev.hiring_recommendation}</span>
//                     <div className="ep-overall-score">{overallScore}<span className="ep-score-100">/100</span></div>
//                 </div>
//                 <p className="ep-verdict-text">{evalSummary}</p>
//             </div>

//             {/* ══ SCORES ══ */}
//             <div className="ep-scores-row">
//                 {[
//                     { label: "Resume", score: cs.resume?.score || 0 },
//                     { label: "GitHub", score: cs.github?.score || 0 },
//                     { label: "LeetCode", score: cs.leetcode?.score || 0 },
//                     { label: "LinkedIn", score: cs.linkedin?.score || 0 },
//                     { label: "Overall", score: overallScore, big: true },
//                 ].map((item, i) => (
//                     <div key={i} className={`ep-score-pill${item.big ? " ep-score-pill-big" : ""}`}>
//                         <Gauge value={item.score} size={item.big ? 80 : 64} />
//                         <span className="ep-score-pill-label">{item.label}</span>
//                     </div>
//                 ))}
//             </div>

//             {/* ══ GITHUB ══ */}
//             <div className="ep-section">
//                 <SectionTitle>GitHub Analytics{gh.username ? ` — @${gh.username}` : ""}</SectionTitle>
//                 {gh.username ? (
//                     <GitHubAnalytics data={gh} aiNote={cs.github?.reasoning} />
//                 ) : (
//                     <div className="ep-empty"><p>No GitHub profile provided</p></div>
//                 )}
//             </div>

//             {/* ══ LEETCODE ══ */}
//             <div className="ep-section">
//                 <SectionTitle>LeetCode Performance{lc.username ? ` — @${lc.username}` : ""}</SectionTitle>
//                 {lc.total ? (
//                     <LeetCodeAnalytics data={lc} aiNote={cs.leetcode?.reasoning} />
//                 ) : (
//                     <div className="ep-empty"><p>No LeetCode profile submitted</p></div>
//                 )}
//             </div>

//             {/* ══ LINKEDIN ══ */}
//             <div className="ep-section">
//                 <SectionTitle>LinkedIn</SectionTitle>
//                 <LinkedInAnalytics
//                     score={cs.linkedin?.score || 0}
//                     reasoning={cs.linkedin?.reasoning}
//                     candidate={candidate || {}}
//                     linkedinUrl={candidate?.linkedin_url}
//                 />
//             </div>

//             {/* ══ RESUME ══ */}
//             <div className="ep-section">
//                 <SectionTitle>Resume Match</SectionTitle>
//                 <div className="ep-resume-bar-wrap">
//                     <div className="ep-resume-bar-labels">
//                         <span>Job Match Score</span>
//                         <span className="ep-resume-score">{cs.resume?.score || 0}%</span>
//                     </div>
//                     <div className="ep-resume-bar-track">
//                         <div className="ep-resume-bar-fill" style={{ width: `${cs.resume?.score || 0}%` }} />
//                     </div>
//                 </div>
//                 <div className="ep-ai-note">
//                     <span className="ep-ai-badge">AI</span>
//                     {cs.resume?.reasoning}
//                 </div>
//             </div>

//             {/* ══ FLAGS ══ */}
//             {ev.inconsistencies?.filter(Boolean).length > 0 && (
//                 <div className="ep-section">
//                     <SectionTitle>Flags</SectionTitle>
//                     {ev.inconsistencies.filter(Boolean).map((f, i) => (
//                         <div key={i} className="ep-flag">
//                             <span className="ep-flag-dot" />
//                             <span>{f}</span>
//                         </div>
//                     ))}
//                 </div>
//             )}
//         </div>
//     );
// }

























































import { useState } from "react";
import {
    FiGithub, FiCode, FiFileText, FiAlertTriangle,
    FiCheckCircle, FiXCircle, FiStar, FiGitBranch,
    FiUsers, FiActivity, FiExternalLink, FiAward,
    FiTrendingUp, FiZap, FiTarget, FiBarChart2
} from "react-icons/fi";
import {
    AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
    ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell,
    RadarChart, Radar, PolarGrid, PolarAngleAxis,
    RadialBarChart, RadialBar
} from "recharts";
import { GitHubAnalytics, LeetCodeAnalytics, LinkedInAnalytics } from "./AnalyticsComponents";
import "./Evalpanel.css";

const PALETTE = ["#6b8800", "#ff4400", "#0073ff", "#7445ff", "#00a892", "#f59e0b"];

function scoreColor(s) {
    if (s >= 75) return "#559600";
    if (s >= 50) return "#f59e0b";
    return "#ff4400";
}

/* ── Tooltip ── */
const Tip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    return (
        <div style={{ background: "rgba(170, 170, 170, 0.95)", border: "1px solid #d8d8d8", borderRadius: 10, padding: "10px 14px", fontSize: 13, color: "#ccc", backdropFilter: "blur(12px)" }}>
            {label && <p style={{ fontWeight: 700, color: "#fff", marginBottom: 4 }}>{label}</p>}
            {payload.map((p, i) => <p key={i} style={{ color: p.color || "#fff" }}>{p.name}: <b>{p.value}</b></p>)}
        </div>
    );
};

function cleanProfileUrl(value) {
    const cleaned = String(value || "").trim();
    return ["", "na", "n/a", "none", "null", "-", "--"].includes(cleaned.toLowerCase()) ? "" : cleaned;
}

function usernameFromUrl(pattern, value) {
    const match = cleanProfileUrl(value).match(pattern);
    return match?.[1]?.replace(/\/+$/, "") || "";
}

function withProtocol(value) {
    const cleaned = cleanProfileUrl(value);
    if (!cleaned) return "";
    return /^https?:\/\//i.test(cleaned) ? cleaned : `https://${cleaned}`;
}

/* ── Score Ring (Recharts RadialBar) ── */
function ScoreArc({ value }) {
    const color = scoreColor(value);
    const data = [{ value: Math.max(value, 2), fill: color }];
    return (
        <div style={{ position: "relative", width: 220, height: 220, flexShrink: 0 }}>
            <RadialBarChart width={220} height={220} cx={110} cy={110}
                innerRadius={72} outerRadius={100} startAngle={220} endAngle={-40}
                data={data} barSize={20}>
                <RadialBar background={{ fill: "rgba(255,255,255,0.05)" }}
                    dataKey="value" cornerRadius={10} max={100} />
            </RadialBarChart>
            <div style={{
                position: "absolute", top: "50%", left: "50%",
                transform: "translate(-50%,-50%)", textAlign: "center", pointerEvents: "none"
            }}>
                <p style={{
                    fontSize: 52, fontWeight: 900, color, lineHeight: 1, margin: 0,
                    textShadow: `0 0 24px ${color}66`
                }}>{value}</p>
                <p style={{ fontSize: 13, color: "#555", margin: "4px 0 0", letterSpacing: 1 }}>/ 100</p>
            </div>
        </div>
    );
}

/* ── Glass Card ── */
function GlassCard({ children, className = "", style = {}, glow = "" }) {
    return (
        <div className={`gc ${className}`} >
            <div className="gc-inner">{children}</div>
        </div>
    );
}

export default function EvalPanel({ evalData, evalSummary, candidate }) {
    const [tab, setTab] = useState("github");
    const [showSummary, setShowSummary] = useState(false);

    if (!evalData) return (
        <div className="ep-empty"><FiActivity size={32} /><p>No evaluation data available</p></div>
    );
    let ev;
    try { ev = typeof evalData === "string" ? JSON.parse(evalData) : evalData; }
    catch { return null; }

    const cs = ev.component_scores || {};
    const candidateGithubUrl = withProtocol(candidate?.github_url || ev.github_url);
    const candidateLeetcodeUrl = withProtocol(candidate?.leetcode_url || ev.leetcode_url);
    const ghUsername = (ev.github_raw || {}).username || usernameFromUrl(/github\.com\/([a-zA-Z0-9-]+)/i, candidateGithubUrl);
    const lcUsername = (ev.leetcode_raw || {}).username || usernameFromUrl(/leetcode\.com\/(?:u\/)?([a-zA-Z0-9_-]+)/i, candidateLeetcodeUrl);
    const gh = { username: ghUsername, ...(ev.github_raw || {}) };
    const lc = { username: lcUsername, ...(ev.leetcode_raw || {}) };
    const hasGithubProfile = Boolean(gh.username || candidateGithubUrl);
    const hasLeetcodeProfile = Boolean(lc.username || candidateLeetcodeUrl);
    const githubHref = candidateGithubUrl || (gh.username ? `https://github.com/${gh.username}` : "");
    const leetcodeHref = candidateLeetcodeUrl || (lc.username ? `https://leetcode.com/u/${lc.username}` : "");
    const overall = Math.round(ev.final_score || 0);
    const rec = ev.hiring_recommendation || "—";
    const recColor = { "Strong Hire": "#92ba00", "Hire": "#006bef", "Borderline": "#cd8200", "No Hire": "#ff4400" }[rec] || "#888";

    const langEntries = Object.entries(gh.languages || {}).sort((a, b) => b[1] - a[1]).slice(0, 6);
    const totalLangs = langEntries.reduce((s, [, v]) => s + v, 0) || 1;
    const commitData = gh.commit_activity || Array.from({ length: 12 }, (_, i) => ({
        month: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][i], commits: 0
    }));

    const lcDiff = [
        { name: "Easy", value: lc.easy || 0, color: "#22c55e" },
        { name: "Medium", value: lc.medium || 0, color: "#f59e0b" },
        { name: "Hard", value: lc.hard || 0, color: "#ef4444" },
    ];

    const TABS = [
        { id: "github", label: "GitHub", icon: FiGithub },
        { id: "leetcode", label: "LeetCode", icon: FiCode },
        { id: "linkedin", label: "LinkedIn", icon: FiAward },
        { id: "resume", label: "Resume", icon: FiFileText },
        { id: "debate", label: "AI Debate", icon: FiZap },
    ];

    return (
        <div className="ep-root">

            {/* ── ROW 1: VERDICT — single wide horizontal bar ── */}
            <div className="ep-verdict-bar">

                {/* LEFT: Score + verdict */}
                <div className="evb-left">
                    <p className="evb-stage">Stage 0 · AI Evaluation</p>
                    <p className="evb-score" style={{ color: scoreColor(overall) }}>{overall}</p>
                    <p className="evb-score-label">/100</p>
                    <div className="evb-badge" style={{ background: recColor + "20", color: recColor, borderColor: recColor + "40" }}>
                        {/* {overall >= 65 ? <FiCheckCircle size={14} /> : <FiXCircle size={14} />} */}
                        {rec}
                    </div>
                </div>

                <div className="evb-divider" />

                {/* MIDDLE: 4 component scores in a row */}
                <div className="evb-scores">
                    {[
                        { label: "Resume", key: "resume", color: "#60a5fa", weight: "45%" },
                        { label: "GitHub", key: "github", color: "#ff4400", weight: "30%" },
                        { label: "LeetCode", key: "leetcode", color: "#a78bfa", weight: "25%" },
                        { label: "LinkedIn", key: "linkedin", color: "#2dd4bf", weight: "—" },
                    ].map(({ label, key, color, weight }) => {
                        const s = cs[key]?.score || 0;
                        const COLS = 30;
                        const filled = Math.round((s / 100) * COLS);
                        return (
                            <div key={key} className="evb-score-item">
                                <p className="evb-score-num" style={{ color }}>{s}</p>
                                <p className="evb-score-name">{label}</p>
                                <p className="evb-score-weight">{weight}</p>
                                <div className="evb-col-chart">
                                    {Array.from({ length: COLS }).map((_, i) => {
                                        const active = i < filled;
                                        const h = active
                                            ? 14 + Math.round(Math.sin((i / COLS) * Math.PI) * 28 + (i % 3 === 0 ? 4 : i % 2 === 0 ? 2 : 0))
                                            : 4 + (i % 3 === 0 ? 3 : i % 2 === 0 ? 2 : 1);
                                        return (
                                            <div key={i} className="evb-col-bar" style={{
                                                height: h,
                                                background: active ? color : "rgb(188, 188, 188)",
                                                borderRadius: 3,
                                            }} />
                                        );
                                    })}
                                </div>
                                <p className="evb-score-pct" style={{ color }}>{s}% match</p>
                            </div>
                        );
                    })}
                </div>

                <div className="evb-divider" />

                {/* RIGHT: Summary + flags */}
                <div className="evb-right">
                    <p className="evb-summary-title">AI Summary</p>
                    <p className="evb-summary">{evalSummary || ev.summary || "Evaluation complete."}</p>
                    <button className="evb-readmore" onClick={() => setShowSummary(true)}>Read more</button>
                    {ev.inconsistencies?.filter(Boolean).length > 0 && (
                        <div className="evb-flags">
                            <p className="evb-flags-title"><FiAlertTriangle size={11} /> Flags</p>
                            {ev.inconsistencies.filter(Boolean).slice(0, 2).map((f, i) => (
                                <p key={i} className="evb-flag">· {f}</p>
                            ))}
                        </div>
                    )}
                </div>

            </div>

            {/* ── Summary popup ── */}
            {showSummary && (
                <div className="evb-popup-overlay" onClick={() => setShowSummary(false)}>
                    <div className="evb-popup" onClick={e => e.stopPropagation()}>
                        <div className="evb-popup-header">
                            <p className="evb-popup-title">AI Summary</p>
                            <button className="evb-popup-close" onClick={() => setShowSummary(false)}>
                                <FiXCircle size={18} />
                            </button>
                        </div>
                        <p className="evb-popup-body">{evalSummary || ev.summary || "Evaluation complete."}</p>
                        {ev.inconsistencies?.filter(Boolean).length > 0 && (
                            <div className="evb-popup-flags">
                                <p className="evb-flags-title"><FiAlertTriangle size={13} /> Red Flags</p>
                                {ev.inconsistencies.filter(Boolean).map((f, i) => (
                                    <p key={i} className="evb-popup-flag">· {f}</p>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* ── ROW 2: GITHUB (3 cards) ── */}
            <div className="ep-section-label">
                <span className="ep-section-num">02</span>
                <span className="ep-section-title">GitHub Activity</span>
                {hasGithubProfile && githubHref && (
                    <a href={githubHref} target="_blank" rel="noreferrer" className="ep-ext">
                        @{gh.username || "GitHub"} <FiExternalLink size={11} />
                    </a>
                )}
            </div>

            {hasGithubProfile ? (
                <div className="ep-row ep-row-github">
                    {/* Stats card */}
                    <GlassCard className="gc-gh-stats" style={{ background: "linear-gradient(160deg, #0f0800 0%, #1a0a00 50%, #0d0d0d 100%)" }}>
                        
                        <p className="gc-eyebrow">Repository Overview</p>
                        <div className="gc-bignum" style={{ color: "#ff4400" }}>{gh.total_repos || 0}</div>
                        <p className="gc-bignum-sub">Total Repositories</p>
                        <div className="gc-stat-grid">
                            <div className="gc-stat"><span style={{ color: "#e89506", fontSize: 26, fontWeight: 900 }}>{gh.total_stars || 0}</span><span className="gc-stat-label"><br /> Stars</span></div>
                            <div className="gc-stat"><span style={{ color: "#2989ff", fontSize: 26, fontWeight: 900 }}>{gh.total_forks || 0}</span><span className="gc-stat-label">Forks</span></div>
                            <div className="gc-stat"><span style={{ color: "#7a4eff", fontSize: 26, fontWeight: 900 }}>{gh.followers || 0}</span><span className="gc-stat-label">Followers</span></div>
                            <div className="gc-stat"><span style={{ color: "#739301", fontSize: 26, fontWeight: 900 }}>{gh.repo_types?.original || 0}</span><span className="gc-stat-label">Original</span></div>
                        </div>
                    </GlassCard>

                    {/* Commit chart */}
                    <GlassCard className="gc-commit" style={{ background: "linear-gradient(135deg, #080808 0%, #0f0f0f 100%)" }}>
                        <p className="gc-eyebrow">Commit Activity</p>
                        <p className="gc-micro">Pushes per month · public events API</p>
                        <div className="ep-chart-frame ep-chart-frame-commit">
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={commitData} margin={{ top: 8, right: 4, left: -24, bottom: 0 }}>
                                    <defs>
                                        <linearGradient id="ca" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="5%" stopColor="#ff4400" stopOpacity={0.5} />
                                            <stop offset="95%" stopColor="#ff4400" stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <CartesianGrid strokeDasharray="3 8" stroke="#9e9e9e" />
                                    <XAxis dataKey="month" tick={{ fill: "#555", fontSize: 11 }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fill: "#555", fontSize: 11 }} axisLine={false} tickLine={false} />
                                    <Tooltip content={<Tip />} />
                                    <Area type="monotone" dataKey="commits" name="Commits"
                                        stroke="#ff4400" fill="url(#ca)" strokeWidth={3}
                                        dot={false} activeDot={{ r: 5, fill: "#ff4400", strokeWidth: 0 }} />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    </GlassCard>

                    {/* Languages */}
                    <GlassCard className="gc-langs" style={{ background: "linear-gradient(135deg, #080808 0%, #0f0f0f 100%)" }}>
                        <p className="gc-eyebrow">Languages Used</p>
                        <p className="gc-micro">By repository count</p>
                        {langEntries.length > 0 ? (
                            <>
                                <div className="gc-lang-bars">
                                    {langEntries.map(([name, count], i) => {
                                        const pct = (count / totalLangs * 100).toFixed(0);
                                        return (
                                            <div key={name} className="gc-lang-row">
                                                <span className="gc-lang-dot" style={{ background: PALETTE[i] }} />
                                                <span className="gc-lang-name">{name}</span>
                                                <div className="gc-lang-track">
                                                    <div className="gc-lang-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, ${PALETTE[i]}66, ${PALETTE[i]})` }} />
                                                </div>
                                                <span className="gc-lang-pct" style={{ color: PALETTE[i] }}>{pct}%</span>
                                            </div>
                                        );
                                    })}
                                </div>
                                <div className="ep-chart-frame ep-chart-frame-languages">
                                    <ResponsiveContainer width="100%" height="100%">
                                        <BarChart data={langEntries.map(([n, v], i) => ({ n, v, fill: PALETTE[i] }))} margin={{ top: 4, right: 4, left: -30, bottom: 0 }}>
                                            <Bar dataKey="v" name="Repos" radius={[4, 4, 0, 0]}>
                                                {langEntries.map((_, i) => <Cell key={i} fill={PALETTE[i]} />)}
                                            </Bar>
                                            <XAxis dataKey="n" tick={{ fill: "#555", fontSize: 10 }} axisLine={false} tickLine={false} />
                                            <Tooltip content={<Tip />} />
                                        </BarChart>
                                    </ResponsiveContainer>
                                </div>
                            </>
                        ) : <p style={{ color: "#333", fontSize: 13, padding: "20px 0" }}>No language data</p>}
                    </GlassCard>
                </div>
            ) : (
                <div className="ep-no-profile"><FiGithub size={24} /><p>No GitHub URL provided — scored 0</p></div>
            )}

            {/* Top repos */}
            {gh.top_repos?.length > 0 && (
                <div className="ep-row ep-row-repos">
                    <GlassCard className="gc-repos" style={{ background: "linear-gradient(135deg, #080808 0%, #0f0f0f 100%)" }}>
                        <p className="gc-eyebrow">Top Repositories</p>
                        <div className="gc-repo-table">
                            <div className="gc-repo-thead">
                                <span>Repository</span><span>Language</span><span>Stars</span><span>Forks</span><span>Description</span>
                            </div>
                            {gh.top_repos.map((r, i) => (
                                <div key={i} className="gc-repo-trow">
                                    <span className="gc-repo-name" style={{ color: PALETTE[i % PALETTE.length] }}>{r.name}</span>
                                    <span className="gc-repo-tag">{r.language || "—"}</span>
                                    <span style={{ color: "#f59e0b", fontWeight: 700, fontSize: 14 }}>{r.stars}</span>
                                    <span style={{ color: "#888", fontSize: 14 }}>{r.forks || 0}</span>
                                    <span className="gc-repo-desc">{r.description || "—"}</span>
                                </div>
                            ))}
                        </div>
                    </GlassCard>
                </div>
            )}

            {/* ── ROW 3: LEETCODE ── */}
            <div className="ep-section-label">
                <span className="ep-section-num">03</span>
                <span className="ep-section-title">LeetCode Performance</span>
                {hasLeetcodeProfile && leetcodeHref && (
                    <a href={leetcodeHref} target="_blank" rel="noreferrer" className="ep-ext">
                        @{lc.username || "LeetCode"} <FiExternalLink size={11} />
                    </a>
                )}
            </div>

            {hasLeetcodeProfile ? (
                <div className="ep-row ep-row-leetcode">
                    {/* Donut */}
                    <GlassCard className="gc-lc-donut" style={{ background: "linear-gradient(160deg, #050010 0%, #0a0020 50%, #0d0d0d 100%)" }}>
                        <div className="ep-bg-texture" style={{ backgroundImage: "url(/bgt.svg)" }} />
                        <p className="gc-eyebrow" style={{ color: "#a78bfa" }}>Problems Solved</p>
                        <div style={{ position: "relative", display: "flex", justifyContent: "center", margin: "8px 0" }}>
                            <PieChart width={260} height={260}>
                                <Pie data={lcDiff.filter(d => d.value > 0)} cx={128} cy={128}
                                    innerRadius={76} outerRadius={118}
                                    dataKey="value" strokeWidth={3} stroke="rgba(176, 176, 176, 0.8)">
                                    {lcDiff.map((d, i) => <Cell key={i} fill={d.color} style={{ filter: `drop-shadow(0 0 8px ${d.color}88)` }} />)}
                                </Pie>
                                <Tooltip content={<Tip />} />
                            </PieChart>
                            <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%,-50%)", textAlign: "center", pointerEvents: "none" }}>
                                <p style={{ fontSize: 46, fontWeight: 900, color: "#fff", lineHeight: 1 }}>{lc.total}</p>
                                <p style={{ fontSize: 12, color: "#666", textTransform: "uppercase", letterSpacing: "0.8px" }}>Total</p>
                            </div>
                        </div>
                        <div className="gc-lc-legend">
                            {lcDiff.map(d => (
                                <div key={d.name} className="gc-lc-legend-item">
                                    <span style={{ width: 10, height: 10, borderRadius: 3, background: d.color, display: "block", boxShadow: `0 0 6px ${d.color}` }} />
                                    <span style={{ color: "#aaa", fontSize: 13 }}>{d.name}</span>
                                    <span style={{ color: d.color, fontWeight: 900, fontSize: 20 }}>{d.value}</span>
                                </div>
                            ))}
                        </div>
                    </GlassCard>

                    {/* Bar chart */}
                    <GlassCard className="gc-lc-bar" style={{ background: "linear-gradient(135deg, #080808 0%, #0f0f0f 100%)" }}>
                        <p className="gc-eyebrow">Difficulty Comparison</p>
                        <p className="gc-micro">Easy · Medium · Hard solved count</p>
                        <div className="ep-chart-frame ep-chart-frame-leetcode">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={lcDiff} margin={{ top: 8, right: 4, left: -12, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 8" stroke="#aaaaaa" horizontal={true} vertical={false} />
                                    <XAxis dataKey="name" tick={{ fill: "#ccc", fontSize: 14, fontWeight: 700 }} axisLine={false} tickLine={false} />
                                    <YAxis tick={{ fill: "#555", fontSize: 12 }} axisLine={false} tickLine={false} />
                                    <Tooltip content={<Tip />} />
                                    <Bar dataKey="value" name="Solved" radius={[10, 10, 0, 0]} maxBarSize={64}>
                                        {lcDiff.map((d, i) => <Cell key={i} fill={d.color} style={{ filter: `drop-shadow(0 4px 12px ${d.color}66)` }} />)}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="gc-lc-stats">
                            <div className="gc-lc-stat" style={{ borderColor: "#a78bfa33" }}>
                                <p style={{ fontSize: 24, fontWeight: 900, color: "#a78bfa" }}>{lc.ranking ? `#${Number(lc.ranking).toLocaleString()}` : "N/A"}</p>
                                <p className="gc-lc-stat-label">Global Rank</p>
                            </div>
                            <div className="gc-lc-stat" style={{ borderColor: "#f59e0b33" }}>
                                <p style={{ fontSize: 24, fontWeight: 900, color: "#f59e0b" }}>{lc.contest_rating || "N/A"}</p>
                                <p className="gc-lc-stat-label">Contest Rating</p>
                            </div>
                            <div className="gc-lc-stat" style={{ borderColor: "#c8ff0033" }}>
                                <p style={{ fontSize: 24, fontWeight: 900, color: "#c8ff00" }}>{lc.active_days || 0}</p>
                                <p className="gc-lc-stat-label">Active Days</p>
                            </div>
                        </div>
                    </GlassCard>
                </div>
            ) : (
                <div className="ep-no-profile"><FiCode size={24} /><p>No LeetCode URL provided — scored 0</p></div>
            )}

            {/* ── ROW 4: DEEP ANALYSIS TABS ── */}
            <div className="ep-section-label">
                <span className="ep-section-num">04</span>
                <span className="ep-section-title">Deep Analysis</span>
            </div>

            <div className="ep-row ep-row-tabs">
                <GlassCard className="gc-tabs-card" style={{ background: "linear-gradient(135deg, #080808 0%, #0f0f0f 100%)" }}>
                    <div className="gc-tab-nav">
                        {TABS.map(({ id, label, icon: Icon }) => (
                            <button key={id} className={`gc-tab-btn ${tab === id ? "active" : ""}`}
                                onClick={() => setTab(id)}>
                                <Icon size={14} /> {label}
                            </button>
                        ))}
                    </div>
                    <div className="gc-tab-body">
                        {tab === "github" && (hasGithubProfile ? <GitHubAnalytics data={gh} aiNote={cs.github?.reasoning || "GitHub profile link was captured; detailed analysis may still be pending."} /> : <div className="ep-no-profile"><FiGithub size={24} /><p>No GitHub profile provided</p></div>)}
                        {tab === "leetcode" && (hasLeetcodeProfile ? <LeetCodeAnalytics data={lc} aiNote={cs.leetcode?.reasoning || "LeetCode profile link was captured; detailed analysis may still be pending."} /> : <div className="ep-no-profile"><FiCode size={24} /><p>No LeetCode profile submitted</p></div>)}
                        {tab === "linkedin" && <LinkedInAnalytics score={cs.linkedin?.score || 0} reasoning={cs.linkedin?.reasoning} candidate={candidate || {}} linkedinUrl={candidate?.linkedin_url} />}
                        {tab === "resume" && (
                            <div className="gc-resume">
                                <div className="gc-resume-top">
                                    <ScoreArc value={cs.resume?.score || 0} size={160} />
                                    <div className="gc-resume-info">
                                        <p className="gc-resume-title">Resume matches the Job Description</p>
                                        <div className="gc-bar-track" style={{ height: 10, marginBottom: 14 }}>
                                            <div className="gc-bar-fill" style={{ width: `${cs.resume?.score || 0}%`, height: 10, background: `linear-gradient(90deg, ${scoreColor(cs.resume?.score || 0)}66, ${scoreColor(cs.resume?.score || 0)})` }} />
                                        </div>
                                        <p className="gc-resume-note">{cs.resume?.reasoning || "No reasoning available."}</p>
                                    </div>
                                </div>
                                {ev.summary && (
                                    <div className="gc-resume-summary">
                                        <p className="gc-eyebrow">Full AI Summary</p>
                                        <p style={{ fontSize: 14, color: "#777", lineHeight: 1.8, marginTop: 8 }}>{ev.summary}</p>
                                    </div>
                                )}
                            </div>
                        )}
                        {tab === "debate" && (() => {
                            const dc = ev.debate_content || {};
                            const nameChecks = dc.name_consistency || [];
                            const namesFound = dc.names_found || {};
                            const wa = dc.weight_adjustments || {};
                            const flags = dc.inconsistencies_flagged || ev.inconsistencies || [];
                            const reasoning = dc.panel_reasoning || ev.summary || "";
                            return (
                                <div className="gc-debate">
                                    {/* Panel Reasoning */}
                                    <div className="gc-debate-section">
                                        <div className="gc-debate-section-head">
                                            <FiZap size={14} color="#f59e0b" />
                                            <span>AI Panel Reasoning</span>
                                        </div>
                                        {reasoning
                                            ? <p className="gc-debate-reasoning">{reasoning}</p>
                                            : <p className="gc-debate-empty">No panel reasoning available.</p>
                                        }
                                    </div>

                                    {/* Weight Adjustments */}
                                    {Object.keys(wa).length > 0 && (
                                        <div className="gc-debate-section">
                                            <div className="gc-debate-section-head">
                                                <FiBarChart2 size={14} color="#a78bfa" />
                                                <span>Weight Adjustments</span>
                                            </div>
                                            <div className="gc-debate-weights">
                                                {["resume", "github", "leetcode", "linkedin", "role_match"].map(k => {
                                                    const adj = wa[k] || 0;
                                                    const baseW = { resume: 45, github: 30, leetcode: 25, linkedin: 0, role_match: 0 }[k] || 0;
                                                    const adjColor = adj > 0 ? "#22c55e" : adj < 0 ? "#ef4444" : "#555";
                                                    const platformColor = { resume: "#60a5fa", github: "#ff4400", leetcode: "#a78bfa", linkedin: "#2dd4bf", role_match: "#f59e0b" }[k] || "#888";
                                                    return (
                                                        <div key={k} className="gc-debate-weight-row">
                                                            <span className="gc-debate-weight-label" style={{ color: platformColor }}>
                                                                {k.charAt(0).toUpperCase() + k.slice(1).replace("_", " ")}
                                                            </span>
                                                            <span className="gc-debate-weight-base">{baseW > 0 ? `Base: ${baseW}%` : "—"}</span>
                                                            <span className="gc-debate-weight-adj" style={{ color: adjColor }}>
                                                                {adj > 0 ? `+${adj.toFixed(2)}` : adj < 0 ? `${adj.toFixed(2)}` : "No change"}
                                                            </span>
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                    {/* Name Consistency */}
                                    <div className="gc-debate-section">
                                        <div className="gc-debate-section-head">
                                            <FiUsers size={14} color="#38bdf8" />
                                            <span>Identity Consistency Check</span>
                                        </div>
                                        {Object.keys(namesFound).length === 0
                                            ? <p className="gc-debate-empty">No cross-platform names to verify.</p>
                                            : (
                                                <>
                                                    <div className="gc-debate-names-found">
                                                        {Object.entries(namesFound).map(([plat, name]) => (
                                                            <div key={plat} className="gc-debate-name-chip">
                                                                <span className="gc-debate-name-plat">{plat}</span>
                                                                <span className="gc-debate-name-val">{name}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                    <div className="gc-debate-name-checks">
                                                        {nameChecks.map((nc, i) => (
                                                            <div key={i} className={`gc-debate-name-check ${nc.match ? "match" : "mismatch"}`}>
                                                                <span className="gc-debate-check-icon">{nc.match ? "✓" : "✗"}</span>
                                                                <span>
                                                                    <b>{nc.platforms[0]}</b>: {nc.names[0]}
                                                                    {" vs "}
                                                                    <b>{nc.platforms[1]}</b>: {nc.names[1]}
                                                                </span>
                                                                <span className="gc-debate-check-verdict">{nc.match ? "Match" : "Mismatch"}</span>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </>
                                            )
                                        }
                                    </div>

                                    {/* Inconsistencies */}
                                    <div className="gc-debate-section">
                                        <div className="gc-debate-section-head">
                                            <FiAlertTriangle size={14} color="#f87171" />
                                            <span>Red Flags &amp; Inconsistencies</span>
                                        </div>
                                        {flags.filter(Boolean).length === 0
                                            ? <p className="gc-debate-empty">✅ No inconsistencies detected.</p>
                                            : flags.filter(Boolean).map((f, i) => (
                                                <div key={i} className="gc-debate-flag">
                                                    <span className="gc-debate-flag-dot" />
                                                    <span>{f}</span>
                                                </div>
                                            ))
                                        }
                                    </div>
                                </div>
                            );
                        })()}

                    </div>
                </GlassCard>
            </div>

        </div>
    );
}
