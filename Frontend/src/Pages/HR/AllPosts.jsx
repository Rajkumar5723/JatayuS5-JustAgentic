import { useCallback, useEffect, useState } from "react";
import { IoClose } from "react-icons/io5";
import { MdCalendarToday, MdPeople } from "react-icons/md";
import { FiUser } from "react-icons/fi";
import { IoIosArrowBack } from "react-icons/io";
import { useLocation, useOutletContext } from "react-router-dom";

import CandidateWorkflowView from "./CandidateWorkflowView.jsx";
import { flattenRoundLabels, parseInterviewConfig } from "../../shared/interviewConfig";
import { MAIN_API as API } from "../../shared/api.js";

const jobTypeLabel = { ft: "Full-Time", pt: "Part-Time", ct: "Contract" };
const deptLabel = { dev: "Development", sal: "Sales", mkt: "Marketing" };
const acceptedStatuses = new Set([
    "selected",
    "offer_pending",
    "offer_sent",
    "offer_signed",
    "approval_pending",
    "hired",
    "on_hold",
    "onboarding_in_progress",
    "onboarding_completed",
]);

function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "2-digit",
    });
}

function stageColor(status) {
    if (!status || status === "pending") return { bg: "#e0e0e0", color: "#000000", border: "#1e1e1e" };
    if (status === "bgv_pending") return { bg: "#fff3e6", color: "#b34c00", border: "#ff8b4a" };
    if (status === "bgv_review") return { bg: "#fff8dd", color: "#946300", border: "#e5b100" };
    if (status === "rejected") return { bg: "#ffdddd", color: "#cc0000", border: "#d20000" };
    if (["selected", "offer_pending", "offer_sent", "offer_signed", "approval_pending", "hired", "onboarding_in_progress", "onboarding_completed"].includes(status)) {
        return { bg: "#ddffec", color: "#00a854", border: "#00cc66" };
    }
    if (status === "on_hold") return { bg: "#f5f3ff", color: "#6d28d9", border: "#a78bfa" };
    return { bg: "#d4e8ff", color: "#0080ff", border: "#006dd9" };
}

function parseRoundLabels(raw) {
    if (!raw) return [];
    const text = String(raw).trim();
    if (text.startsWith("[")) {
        try {
            const parsed = JSON.parse(text);
            if (Array.isArray(parsed)) {
                const typeLabels = {
                    mcq: "MCQ Test",
                    aptitude: "Aptitude Test",
                    coding: "Coding",
                    vibe_coding: "Vibe Coding",
                    oop_concepts: "OOP Concepts",
                    database_design: "Database Design",
                    api_design: "API Design",
                    group_discussion: "Group Discussion",
                    technical_hr: "Technical HR",
                    hr_interview: "HR Interview",
                    live_hr: "Live Interview",
                };
                const labels = parsed
                    .map((item, index) => {
                        if (typeof item === "string") return item.trim();
                        if (!item || typeof item !== "object") return "";
                        return (
                            item.name ||
                            item.title ||
                            typeLabels[String(item.type || item.round_type || "").trim().toLowerCase()] ||
                            `Round ${index + 1}`
                        );
                    })
                    .filter(Boolean);
                if (labels.length) return labels;
            }
        } catch {
            /* fall through */
        }
    }
    if (text.startsWith("{")) {
        const flat = flattenRoundLabels(text);
        if (flat.length) return flat;
    }
    return text.split(",").map((part) => part.trim()).filter(Boolean);
}

function stageLabel(status, job) {
    if (!status || status === "pending") return "Applied";
    const labels = {
        bgv_pending: "BGV Pending",
        bgv_review: "BGV Review",
        joining_pending: "Joining Setup",
        offer_pending: "Offer Pending",
        offer_sent: "Offer Sent",
        offer_signed: "Offer Signed",
        approval_pending: "Approval Pending",
        hired: "Hired",
        on_hold: "On Hold",
        onboarding_in_progress: "Onboarding",
        onboarding_completed: "Onboarded",
        rejected: "Rejected",
        selected: "Selected",
    };
    if (labels[status]) return labels[status];
    const match = String(status).match(/^round_(\d+)$/);
    if (match) {
        const rounds = parseRoundLabels(job?.rounds);
        const idx = Number(match[1]) - 1;
        return rounds[idx] || `Round ${match[1]}`;
    }
    return String(status).replaceAll("_", " ");
}

function popupRounds(job) {
    const raw = String(job?.rounds || "").trim();
    if (!raw) return [];
    if (raw.startsWith("{")) {
        const config = parseInterviewConfig(raw);
        return (config?.stages || [])
            .map((stage) => {
                const roundNames = (stage.rounds || []).map((round) => round.type).filter(Boolean);
                if (!roundNames.length) return stage.name || "";
                return `${stage.name}: ${roundNames.join(", ")}`;
            })
            .filter(Boolean);
    }
    return parseRoundLabels(raw);
}

function searchableText(...values) {
    return values
        .flat()
        .filter(Boolean)
        .map((value) => String(value).toLowerCase())
        .join(" ");
}

function matchesJobSearch(job, query) {
    if (!query) return true;
    return searchableText(
        job.job_name,
        job.description,
        deptLabel[job.department] ?? job.department,
        jobTypeLabel[job.job_type] ?? job.job_type,
        job.skills,
        job.location,
        job.work_style,
        job.platforms,
        job.rounds,
    ).includes(query);
}

function matchesCandidateSearch(candidate, job, query) {
    if (!query) return true;
    return searchableText(
        candidate.full_name,
        candidate.email,
        candidate.phone,
        candidate.alt_phone,
        candidate.location,
        candidate.current_title,
        candidate.company_name,
        candidate.technical_skills,
        candidate.soft_skills,
        candidate.github_url,
        candidate.linkedin_url,
        candidate.leetcode_url,
        candidate.portfolio_url,
        candidate.cover_letter,
        candidate.recentTest?.title,
        candidate.recentTest?.score_pct,
        stageLabel(candidate.status, job),
    ).includes(query);
}

export default function AllPosts() {
    const location = useLocation();
    const {
        dashboardSearch = "",
        setDashboardSearch = () => {},
        setDashboardSearchPlaceholder = () => {},
    } = useOutletContext() || {};

    const [jobs, setJobs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [candCounts, setCandCounts] = useState({});

    const [selected, setSelected] = useState(null);
    const [deleting, setDeleting] = useState(false);
    const [confirmId, setConfirmId] = useState(null);

    const [candPage, setCandPage] = useState(null);
    const [candidates, setCandidates] = useState([]);
    const [candLoading, setCandLoading] = useState(false);
    const [statusUpdating, setStatusUpdating] = useState(null);

    const [candView, setCandView] = useState(null);
    const [toast, setToast] = useState(null);

    const showToast = useCallback((msg, type = "error") => {
        setToast({ msg, type });
        setTimeout(() => setToast(null), 3200);
    }, []);

    const handleWorkflowCandidateUpdate = useCallback((appId, updated) => {
        setCandView((prev) => (prev?.id === appId ? { ...prev, ...updated } : prev));
        setCandidates((prev) =>
            prev.map((candidate) =>
                candidate.id === appId ? { ...candidate, ...updated } : candidate
            )
        );
    }, []);

    const fetchJobs = async () => {
        try {
            const res = await fetch(`${API}/jobs`);
            if (!res.ok) throw new Error();
            const data = await res.json();
            setJobs(data);
            const counts = {};
            await Promise.all(
                data.map(async (job) => {
                    try {
                        const response = await fetch(`${API}/applications/job/${job.id}/count`);
                        const payload = await response.json();
                        counts[job.id] = payload.count;
                    } catch {
                        counts[job.id] = 0;
                    }
                })
            );
            setCandCounts(counts);
            return data;
        } catch {
            setError("Could not load jobs. Is the backend running?");
            return [];
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchJobs();
    }, []);

    useEffect(() => {
        const targetName = location.state?.candidateName;
        if (!targetName) return;
        const findAndOpen = async () => {
            try {
                const res = await fetch(`${API}/jobs`);
                const jobRows = await res.json();
                for (const job of jobRows) {
                    const response = await fetch(`${API}/applications/${job.id}`);
                    const applications = await response.json();
                    const found = applications.find((item) => item.full_name === targetName);
                    if (found) {
                        setCandPage(job);
                        setCandView(found);
                        window.history.replaceState({}, "");
                        return;
                    }
                }
                showToast(`Candidate "${targetName}" not found`);
            } catch {
                showToast("Failed to load candidate");
            }
        };
        findAndOpen();
    }, [location.key, location.state?.candidateName]);

    const openCandidates = async (job) => {
        setCandPage(job);
        setCandView(null);
        setCandidates([]);
        setDashboardSearch("");
        setCandLoading(true);
        try {
            const res = await fetch(`${API}/applications/${job.id}`);
            const data = await res.json();
            const withTestScores = await Promise.all(
                data.map(async (candidate) => {
                    try {
                        const testRes = await fetch(`${API}/applications/${candidate.id}/tests`);
                        if (testRes.ok) {
                            const tests = await testRes.json();
                            return { ...candidate, recentTest: tests.length ? tests[0] : null };
                        }
                    } catch {
                        return candidate;
                    }
                    return candidate;
                })
            );
            setCandidates(withTestScores);
        } catch {
            setCandidates([]);
        } finally {
            setCandLoading(false);
        }
    };

    const handleDelete = async (jobId) => {
        setDeleting(true);
        try {
            const res = await fetch(`${API}/jobs/${jobId}`, { method: "DELETE" });
            if (!res.ok) throw new Error();
            setJobs((prev) => prev.filter((job) => job.id !== jobId));
            setSelected(null);
            setConfirmId(null);
        } catch {
            showToast("Failed to delete job");
        } finally {
            setDeleting(false);
        }
    };

    const handleStatus = async (appId, status, options = {}) => {
        setStatusUpdating(appId);
        try {
            const res = await fetch(`${API}/applications/${appId}/status`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    status,
                    manual_override: Boolean(options.manualOverride),
                }),
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.detail || "Status update failed");
            const nextStatus = data.status || status;
            setCandidates((prev) => prev.map((candidate) => (candidate.id === appId ? { ...candidate, status: nextStatus } : candidate)));
            setCandView((prev) => (prev?.id === appId ? { ...prev, status: nextStatus } : prev));
            showToast(options.successMessage || "Candidate status updated", "success");
        } catch {
            showToast("Failed to update status");
        } finally {
            setStatusUpdating(null);
        }
    };

    const closePopup = () => {
        setSelected(null);
        setConfirmId(null);
    };

    const normalizedJobSearch = dashboardSearch.trim().toLowerCase();
    const visibleJobs = jobs.filter((job) => matchesJobSearch(job, normalizedJobSearch));

    const normalizedCandidateSearch = dashboardSearch.trim().toLowerCase();
    const visibleCandidates = candidates.filter((candidate) =>
        matchesCandidateSearch(candidate, candPage, normalizedCandidateSearch)
    );

    useEffect(() => {
        const placeholder = candPage && !candView ? "Search Candidates" : "Search Jobs";
        setDashboardSearchPlaceholder(placeholder);
        return () => {
            setDashboardSearchPlaceholder("Search Jobs");
        };
    }, [candPage, candView, setDashboardSearchPlaceholder]);

    if (candView) {
        return (
            <>
                {toast && <div className={`ap-toast ap-toast-${toast.type}`}>{toast.msg}</div>}
                <CandidateWorkflowView
                    candidateId={candView.id}
                    initialCandidate={candView}
                    initialJob={candPage}
                    onBack={() => setCandView(null)}
                    onCandidateUpdate={handleWorkflowCandidateUpdate}
                    showToast={showToast}
                />
            </>
        );
    }

    if (candPage) {
        const total = candidates.length;
        const rejected = candidates.filter((item) => item.status === "rejected").length;
        const hired = candidates.filter((item) => item.status === "hired").length;
        const bgv = candidates.filter((item) => ["bgv_pending", "bgv_review"].includes(item.status)).length;
        const onboarding = candidates.filter((item) => ["onboarding_in_progress", "onboarding_completed"].includes(item.status)).length;
        const applied = candidates.filter((item) => !item.status || item.status === "pending").length;

        return (
            <main className="cand-page">
                {toast && <div className={`ap-toast ap-toast-${toast.type}`}>{toast.msg}</div>}
                <div className="cand-page-header">
                    <button className="cand-page-back" onClick={() => { setCandPage(null); setDashboardSearch(""); fetchJobs(); }}>
                        <IoIosArrowBack />
                    </button>
                    <div>
                        <p className="cand-page-title">{candPage.job_name}</p>
                        <p className="cand-page-sub">
                            {deptLabel[candPage.department] ?? candPage.department} · {jobTypeLabel[candPage.job_type] ?? candPage.job_type}
                        </p>
                    </div>
                    {!candLoading && total > 0 && (
                        <div className="cand-summary">
                            <span className="cand-summary-item cand-summary-total">{total} Total</span>
                            {normalizedCandidateSearch && (
                                <span className="cand-summary-item cand-summary-round">{visibleCandidates.length} Showing</span>
                            )}
                            {applied > 0 && <span className="cand-summary-item cand-summary-new">{applied} Applied</span>}
                            {bgv > 0 && <span className="cand-summary-item cand-summary-round">{bgv} BGV</span>}
                            {hired > 0 && <span className="cand-summary-item cand-summary-selected">{hired} Hired</span>}
                            {onboarding > 0 && <span className="cand-summary-item cand-summary-round">{onboarding} Onboarding</span>}
                            {rejected > 0 && <span className="cand-summary-item cand-summary-rejected">{rejected} Rejected</span>}
                        </div>
                    )}
                </div>

                <div className="cand-page-body">
                    {candLoading && <p className="cand-empty">Loading candidates...</p>}
                    {!candLoading && candidates.length === 0 && <p className="cand-empty">No applications yet.</p>}
                    {!candLoading && candidates.length > 0 && visibleCandidates.length === 0 && (
                        <p className="cand-empty">No candidates matched your search.</p>
                    )}
                    {!candLoading && visibleCandidates.map((candidate) => {
                        const sc = stageColor(candidate.status);
                        const displayScore = candidate.recentTest?.score_pct ?? candidate.eval_score;
                        const isAccepted = acceptedStatuses.has(candidate.status);
                        return (
                            <div key={candidate.id} className="cand-card" onClick={() => setCandView(candidate)}>
                                <div className="cand-card-left">
                                    <div className="cand-avatar">{(candidate.full_name || "?")[0].toUpperCase()}</div>
                                    <div className="cand-info">
                                        <p className="cand-name">{candidate.full_name || "—"}</p>
                                        <p className="cand-email">{candidate.email || "—"}</p>
                                    </div>
                                </div>

                                <div className="cand-card-mid">
                                    {candidate.years_exp && <span className="cand-tag">{candidate.years_exp} yrs exp</span>}
                                    {candidate.current_title && <span className="cand-tag">{candidate.current_title}</span>}
                                    {candidate.location && <span className="cand-tag">{candidate.location}</span>}
                                </div>

                                {displayScore ? (
                                    <div className="cand-eval-score">
                                        <span className={`cand-score-num ${parseFloat(displayScore) >= 70 ? "score-good" : parseFloat(displayScore) >= 60 ? "score-mid" : "score-low"}`}>
                                            {displayScore}
                                        </span>
                                    </div>
                                ) : (
                                    <div className="cand-eval-pending">
                                        <div className="cand-eval-pending-bar"><div className="cand-eval-pending-fill" /></div>
                                        <span className="cand-score-pending">Evaluating</span>
                                    </div>
                                )}

                                <span
                                    className="cand-status-badge"
                                    style={{
                                        background: sc.bg,
                                        color: sc.color,
                                        border: `1px solid ${sc.border}`,
                                    }}
                                >
                                    {stageLabel(candidate.status, candPage)}
                                </span>

                                <div className="cand-card-actions">
                                    {!isAccepted && (
                                        <button
                                            className="cand-action-btn cand-select-btn"
                                            disabled={statusUpdating === candidate.id}
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                handleStatus(candidate.id, "selected", {
                                                    manualOverride: true,
                                                    successMessage: "Candidate manually accepted",
                                                });
                                            }}
                                        >
                                            Manual Accept
                                        </button>
                                    )}
                                    {candidate.status === "rejected" ? (
                                        <button
                                            className="cand-action-btn cand-neutral-btn"
                                            disabled={statusUpdating === candidate.id}
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                handleStatus(candidate.id, "pending", {
                                                    successMessage: "Candidate restored",
                                                });
                                            }}
                                        >
                                            Restore
                                        </button>
                                    ) : !isAccepted ? (
                                        <button
                                            className="cand-action-btn cand-reject-btn"
                                            disabled={statusUpdating === candidate.id}
                                            onClick={(event) => {
                                                event.stopPropagation();
                                                handleStatus(candidate.id, "rejected");
                                            }}
                                        >
                                            Reject
                                        </button>
                                    ) : (
                                        <span className="cand-accept-note">Accepted</span>
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            </main>
        );
    }

    return (
        <>
            {toast && <div className={`ap-toast ap-toast-${toast.type}`}>{toast.msg}</div>}
            <div className="allpost-title-bar">
                <p className="allpost-title">Active Job Openings</p>
            </div>
            <main className="allpost-main">
                {loading && <p className="allpost-status">Loading jobs...</p>}
                {error && <p className="allpost-status allpost-error">{error}</p>}
                {!loading && !error && jobs.length === 0 && <p className="allpost-status">No jobs posted yet.</p>}
                {!loading && !error && jobs.length > 0 && visibleJobs.length === 0 && (
                    <p className="allpost-status">No jobs matched your search.</p>
                )}

                {visibleJobs.map((job) => (
                    <div key={job.id} className="allpost-post-box">
                        {job.created_at && <p className="postbox-job-date">{formatDate(job.created_at)}</p>}
                        <p className="postbox-job-title">{job.job_name}</p>
                        <p className="postbox-job-team">{deptLabel[job.department] ?? job.department}</p>
                        <div className="postbox-job-des-wrap">
                            <p className="postbox-job-des">{job.description}</p>
                        </div>
                        <div className="postbox-tags">
                            {job.work_style && job.work_style.split(",").filter(Boolean).map((ws) => (
                                <span key={ws} className="postbox-tag postbox-tag-card">{ws}</span>
                            ))}
                            {job.job_type && <span className="postbox-tag postbox-tag-card">{jobTypeLabel[job.job_type] ?? job.job_type}</span>}
                        </div>
                        <div className="postbox-info">
                            <p className="postbox-info-application" style={{ cursor: "pointer" }} onClick={() => openCandidates(job)}>
                                <FiUser size={15} color="#ff4e0e" />
                                {candCounts[job.id] ?? 0} Candidate{(candCounts[job.id] ?? 0) !== 1 ? "s" : ""}
                            </p>
                            <p className="postbox-info-visit" onClick={() => { setSelected(job); setConfirmId(null); }}>View</p>
                        </div>
                    </div>
                ))}
            </main>

            {selected && (
                <div className="popup-overlay" onClick={closePopup}>
                    <div className="popup-box" onClick={(event) => event.stopPropagation()}>
                        <div className="popup-header">
                            <div>
                                <p className="popup-title">{selected.job_name}</p>
                                <p className="popup-sub">
                                    {deptLabel[selected.department] ?? selected.department}&nbsp;·&nbsp;
                                    {jobTypeLabel[selected.job_type] ?? selected.job_type}
                                </p>
                            </div>
                            <IoClose size={26} className="popup-close" onClick={closePopup} />
                        </div>

                        <div className="popup-body">
                            <div className="popup-meta-row">
                                {selected.created_at && (
                                    <span className="popup-meta-item"><MdCalendarToday size={14} /> Posted {formatDate(selected.created_at)}</span>
                                )}
                                <span className="popup-meta-item"><MdPeople size={14} /> {selected.openings} Opening{selected.openings !== 1 ? "s" : ""}</span>
                                {selected.deadline && <span className="popup-meta-item">Deadline: {selected.deadline}</span>}
                                <span className="popup-meta-item">{selected.posted_by}</span>
                            </div>

                            <div className="popup-section">
                                <p className="popup-section-title">Description</p>
                                <p className="popup-section-text">{selected.description}</p>
                            </div>

                            {selected.skills && (
                                <div className="popup-section">
                                    <p className="popup-section-title">Skills Required</p>
                                    <div className="popup-tags">
                                        {selected.skills.split(",").filter(Boolean).map((skill) => (
                                            <span key={skill} className="postbox-tag postbox-tag-round">{skill}</span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            <div className="popup-two-col">
                                {selected.salary_start && (
                                    <div className="popup-section">
                                        <p className="popup-section-title">Salary Range</p>
                                        <p className="popup-section-text">
                                            ₹{selected.salary_start} — ₹{selected.salary_end}
                                            {selected.show_salary === "false" && <span className="popup-hidden"> (hidden)</span>}
                                        </p>
                                    </div>
                                )}
                                {selected.exp_min && (
                                    <div className="popup-section">
                                        <p className="popup-section-title">Experience</p>
                                        <p className="popup-section-text">{selected.exp_min} — {selected.exp_max} yrs</p>
                                    </div>
                                )}
                            </div>

                            {selected.work_style && (
                                <div className="popup-section">
                                    <p className="popup-section-title">Work Style</p>
                                    <div className="popup-tags">
                                        {selected.work_style.split(",").filter(Boolean).map((item) => (
                                            <span key={item} className="postbox-tag postbox-tag-round">{item}</span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {selected.rounds && (
                                <div className="popup-section">
                                    <p className="popup-section-title">Interview Rounds</p>
                                    <div className="popup-tags">
                                        {popupRounds(selected).map((round) => (
                                            <span key={round} className="postbox-tag postbox-tag-round">{round}</span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {selected.platforms && (
                                <div className="popup-section">
                                    <p className="popup-section-title">Posted On</p>
                                    <div className="popup-tags">
                                        {selected.platforms.split(",").filter(Boolean).map((platform) => (
                                            <span key={platform} className="postbox-tag postbox-tag-platform">{platform}</span>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {selected.application_fields && (
                                <div className="popup-section">
                                    <p className="popup-section-title">Application Collects</p>
                                    <div className="popup-tags">
                                        {selected.application_fields.split(",").filter(Boolean).map((field) => {
                                            const trimmed = field.trim();
                                            const required = trimmed.endsWith("!");
                                            const optional = trimmed.endsWith("?");
                                            const label = trimmed.replace(/[!?]$/, "").trim();
                                            return (
                                                <span key={field} className="postbox-tag postbox-tag-appfield">
                                                    {label}
                                                    {required ? " · Req" : optional ? " · Opt" : ""}
                                                </span>
                                            );
                                        })}
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="popup-footer">
                            {confirmId === selected.id ? (
                                <div className="popup-confirm-row">
                                    <p className="popup-confirm-text">This will permanently delete the job post. Are you sure?</p>
                                    <div className="popup-confirm-btns">
                                        <button className="popup-cancel-btn" onClick={() => setConfirmId(null)}>Cancel</button>
                                        <button className="popup-delete-btn" disabled={deleting} onClick={() => handleDelete(selected.id)}>
                                            {deleting ? "Deleting..." : "Delete Job"}
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <>
                                    <button className="popup-close-btn" onClick={closePopup}>Close</button>
                                    <button className="popup-delete-open-btn" onClick={() => setConfirmId(selected.id)}>
                                        Delete Job
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
