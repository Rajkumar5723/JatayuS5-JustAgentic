import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { IoIosArrowBack } from "react-icons/io";
import {
    ResponsiveContainer,
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
} from "recharts";

import EvalPanel from "./Evalpanel.jsx";
import "./CandidateWorkflowView.css";
import { MAIN_API as API } from "../../shared/api.js";

const STATUS_TONES = {
    pending: { bg: "#f3f4f6", color: "#374151", border: "#d1d5db" },
    in_progress: { bg: "#fff7ed", color: "#c2410c", border: "#fdba74" },
    completed: { bg: "#ecfdf5", color: "#047857", border: "#6ee7b7" },
    rejected: { bg: "#fef2f2", color: "#b91c1c", border: "#fca5a5" },
    selected: { bg: "#eff6ff", color: "#1d4ed8", border: "#93c5fd" },
};

const EMPTY_EVIDENCE = {
    room_scans: [],
    webcam_snapshots: [],
    screen_snapshots: [],
    meet_snapshots: [],
    device_info: [],
    suspicious_events: [],
    ai_alerts: [],
    malpractice_incidents: [],
    agent_decisions: [],
    reconnect_logs: [],
    media_summary: {},
};

const OFFER_FIELDS = [
    "joining_date",
    "onboarding_instructions",
    "work_mode",
    "employment_type",
    "reporting_manager",
    "reporting_team",
    "compensation_text",
    "offered_compensation",
    "contract_duration_or_notes",
    "designation",
    "department",
    "company_details",
    "work_location",
    "hr_contact_details",
    "terms_and_conditions",
    "offer_valid_until",
];

function formatDateTime(value) {
    if (!value) return "Not captured";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return date.toLocaleString("en-US", {
        year: "numeric",
        month: "short",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
    });
}

function formatDuration(seconds) {
    if (seconds == null || Number.isNaN(Number(seconds))) return "Not captured";
    const total = Math.max(0, Math.round(Number(seconds)));
    const mins = Math.floor(total / 60);
    const secs = total % 60;
    if (mins === 0) return `${secs}s`;
    return `${mins}m ${secs}s`;
}

function withImageSource(value) {
    if (!value) return "";
    if (String(value).startsWith("data:") || String(value).startsWith("http")) return value;
    return `data:image/jpeg;base64,${value}`;
}

function evidenceImage(item) {
    return item?.image ||
        item?.image_b64 ||
        item?.url ||
        item?.storage_url ||
        item?.download_url ||
        item?.presigned_url ||
        "";
}

function toneFor(status) {
    return STATUS_TONES[status] || STATUS_TONES.pending;
}

function badge(label, status) {
    const tone = toneFor(status);
    return (
        <span
            className="wf-badge"
            style={{
                background: tone.bg,
                color: tone.color,
                border: `1px solid ${tone.border}`,
            }}
        >
            {label}
        </span>
    );
}

function flattenRoomFrames(roomScans) {
    return (roomScans || []).flatMap((scan) => {
        if ((scan.frames || []).length) {
            return (scan.frames || []).map((frame) => ({
                type: scan.scan_type || "room_scan",
                timestamp: frame.captured_at || scan.created_at,
                image: evidenceImage(frame),
                note: frame.has_violation
                    ? `Potential issue flagged${(scan.suspicious_items || []).length ? `: ${(scan.suspicious_items || []).join(", ")}` : ""}`
                    : `Clean frame${scan.verdict ? ` - ${scan.verdict}` : ""}`,
            }));
        }
        return [{
            type: scan.scan_type || "room_scan",
            timestamp: scan.completed_at || scan.created_at,
            image: "",
            note: scan.scan_status === "completed"
                ? "Scan completed for this attempt, but frame images were not persisted."
                : `Scan ${scan.scan_status || "pending"}`,
        }];
    });
}

function flattenIncidentEvidence(incidents) {
    return (incidents || []).flatMap((incident) =>
        (incident.evidence_files || []).map((file, index) => ({
            timestamp: incident.created_at,
            image: evidenceImage(file),
            note: `${incident.incident_type || "incident"} evidence ${index + 1}`,
        }))
    );
}

function stageRiskSummary(stage) {
    const evidence = { ...EMPTY_EVIDENCE, ...(stage?.evidence || {}) };
    const suspiciousCount = evidence.suspicious_events.length;
    const alertCount = evidence.ai_alerts.length;
    const incidentCount = evidence.malpractice_incidents.length;
    return {
        suspiciousCount,
        alertCount,
        incidentCount,
        totalRiskFlags: suspiciousCount + alertCount + incidentCount,
    };
}

function extractTimingRows(stage) {
    return (stage?.items || []).filter(
        (item) =>
            item.time_spent_seconds != null ||
            item.response_latency_seconds != null ||
            item.started_at ||
            item.ended_at
    );
}

function extractScoringRows(stage) {
    return (stage?.items || []).filter(
        (item) =>
            item.marks_awarded != null ||
            item.marks_reason ||
            (item.strengths || []).length ||
            (item.weaknesses || []).length ||
            item.confidence_analysis ||
            item.technical_analysis
    );
}

function toFieldValue(value) {
    return value == null ? "" : String(value);
}

function buildOfferForm(offer) {
    const next = {};
    OFFER_FIELDS.forEach((field) => {
        next[field] = toFieldValue(offer?.[field]);
    });
    return next;
}

function OverviewGrid({ children }) {
    return <div className="wf-overview-grid">{children}</div>;
}

function EmptyState({ title, detail }) {
    return (
        <div className="wf-empty">
            <p className="wf-empty-title">{title}</p>
            <p className="wf-empty-detail">{detail}</p>
        </div>
    );
}

function InfoRow({ label, value }) {
    return (
        <div className="wf-info-row">
            <span>{label}</span>
            <strong>{value || "Not captured"}</strong>
        </div>
    );
}

function groupVerificationDocuments(items) {
    const groups = { identity: [], education: [], travel: [], other: [] };
    (items || []).forEach((item) => {
        const category = item.category || "other";
        if (!groups[category]) groups[category] = [];
        groups[category].push(item);
    });
    return groups;
}

function EvidenceGallery({ title, items, imageKey = "image", noteKey = "note", summary, summaryLabel }) {
    if (!items.length) {
        return <EmptyState title={title} detail="Not captured in this stage." />;
    }
    return (
        <div className="wf-evidence-block">
            <div className="wf-evidence-head">
                <p className="wf-section-label">{title}</p>
                {summary?.truncated ? (
                    <p className="wf-evidence-note">
                        Showing latest {summary.shown} of {summary.total} {summaryLabel || title.toLowerCase()} to keep this page fast.
                    </p>
                ) : null}
            </div>
            <div className="wf-image-grid">
                {items.map((item, index) => (
                    <div key={`${title}-${index}`} className="wf-image-card">
                        {item[imageKey] ? (
                            <img src={withImageSource(item[imageKey])} alt={title} />
                        ) : (
                            <div className="wf-image-placeholder">No image available</div>
                        )}
                        <p>{item[noteKey] || item.event_type || "Captured evidence"}</p>
                        <span>{formatDateTime(item.timestamp)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function EvidenceSection({ stage }) {
    const evidence = { ...EMPTY_EVIDENCE, ...(stage?.evidence || {}) };
    const mediaSummary = evidence.media_summary || {};
    const roomFrames = flattenRoomFrames(evidence.room_scans);
    const webcam = evidence.webcam_snapshots.map((item) => ({
        ...item,
        image: evidenceImage(item),
        note: item.event_type || "Candidate webcam capture",
    }));
    const screens = evidence.screen_snapshots.map((item) => ({
        ...item,
        image: evidenceImage(item),
        note: item.event_type || "Screen snapshot",
    }));
    const meet = evidence.meet_snapshots.map((item) => ({
        ...item,
        image: evidenceImage(item),
        note: item.event_type || "Meet snapshot",
    }));
    const incidentFiles = flattenIncidentEvidence(evidence.malpractice_incidents);

    return (
        <div className="wf-stage-pane">
            <EvidenceGallery title="Room 360 Monitoring" items={roomFrames} />
            <EvidenceGallery
                title="Candidate Webcam Photos"
                items={webcam}
                summary={mediaSummary.webcam_snapshots}
                summaryLabel="webcam captures"
            />
            <EvidenceGallery
                title="Screen Recording Snapshots"
                items={screens}
                summary={mediaSummary.screen_snapshots}
                summaryLabel="screen snapshots"
            />
            <EvidenceGallery
                title="Live Interview Room Snapshots"
                items={meet}
                summary={mediaSummary.meet_snapshots}
                summaryLabel="interview snapshots"
            />
            <EvidenceGallery title="Incident Evidence Files" items={incidentFiles} />

            <div className="wf-evidence-block">
                <p className="wf-section-label">Browser & Device Information</p>
                {evidence.device_info.length ? (
                    <div className="wf-stack">
                        {evidence.device_info.map((item, index) => (
                            <div key={`device-${index}`} className="wf-data-card">
                                <InfoRow label="Captured At" value={formatDateTime(item.timestamp)} />
                                <InfoRow label="Event" value={item.event_type} />
                                <InfoRow label="User Agent" value={item.payload?.device?.user_agent || item.payload?.user_agent} />
                                <InfoRow label="Platform" value={item.payload?.device?.platform} />
                                <InfoRow label="Viewport" value={item.payload?.device?.viewport} />
                                <InfoRow label="Timezone" value={item.payload?.device?.timezone} />
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="Device Information" detail="Not captured in this stage." />
                )}
            </div>

            <div className="wf-evidence-block">
                <p className="wf-section-label">Timestamped Monitoring Events</p>
                {evidence.suspicious_events.length ? (
                    <div className="wf-timeline-list">
                        {evidence.suspicious_events.map((event, index) => (
                            <div key={`event-${index}`} className="wf-timeline-row">
                                <strong>{event.event_type}</strong>
                                <span>{event.severity || "info"}</span>
                                <p>{formatDateTime(event.timestamp)}</p>
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="Monitoring Events" detail="No suspicious or monitoring events were captured." />
                )}
            </div>

            <div className="wf-evidence-block">
                <p className="wf-section-label">AI Proctoring Alerts</p>
                {evidence.ai_alerts.length ? (
                    <div className="wf-stack">
                        {evidence.ai_alerts.map((alert, index) => (
                            <div key={`alert-${index}`} className="wf-alert-card">
                                <strong>{alert.event_type}</strong>
                                <p>{alert.message || "AI-generated alert captured."}</p>
                                <span>{formatDateTime(alert.timestamp)}</span>
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="AI Proctoring Alerts" detail="No AI alerts were captured for this stage." />
                )}
            </div>

            <div className="wf-evidence-block">
                <p className="wf-section-label">Malpractice Incidents</p>
                {evidence.malpractice_incidents.length ? (
                    <div className="wf-stack">
                        {evidence.malpractice_incidents.map((incident, index) => (
                            <div key={`incident-${index}`} className="wf-data-card">
                                <InfoRow label="Type" value={incident.incident_type} />
                                <InfoRow label="Severity" value={incident.severity} />
                                <InfoRow label="Agent" value={incident.agent_name} />
                                <InfoRow label="Confidence" value={incident.confidence_score != null ? String(incident.confidence_score) : "Not captured"} />
                                <InfoRow label="Question" value={incident.question_id != null ? String(incident.question_id) : "Not linked"} />
                                <InfoRow label="Reason" value={incident.reason_text || "Not captured"} />
                                <InfoRow label="Captured At" value={formatDateTime(incident.created_at)} />
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="Malpractice Incidents" detail="No malpractice incidents were recorded for this stage." />
                )}
            </div>

            <div className="wf-evidence-block">
                <p className="wf-section-label">Agent Decisions</p>
                {evidence.agent_decisions.length ? (
                    <div className="wf-stack">
                        {evidence.agent_decisions.map((decision, index) => (
                            <div key={`decision-${index}`} className="wf-data-card">
                                <InfoRow label="Agent" value={decision.agent_name} />
                                <InfoRow label="Detection" value={decision.detection_type} />
                                <InfoRow label="Confidence" value={decision.confidence_score != null ? String(decision.confidence_score) : "Not captured"} />
                                <InfoRow label="Reasoning" value={decision.reasoning_text || "Not captured"} />
                                <InfoRow label="Processing Time" value={decision.processing_time_ms != null ? `${decision.processing_time_ms} ms` : "Not captured"} />
                                <InfoRow label="Captured At" value={formatDateTime(decision.created_at)} />
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="Agent Decisions" detail="No agent decision logs were captured for this stage." />
                )}
            </div>

            <div className="wf-evidence-block">
                <p className="wf-section-label">Reconnect / Gap Analysis</p>
                {evidence.reconnect_logs.length ? (
                    <div className="wf-stack">
                        {evidence.reconnect_logs.map((item, index) => (
                            <div key={`gap-${index}`} className="wf-data-card">
                                <InfoRow label="Captured At" value={formatDateTime(item.created_at)} />
                                <InfoRow label="Gap Duration" value={formatDuration(item.gap_duration_seconds)} />
                                <InfoRow label="Fingerprint Match" value={item.fingerprint_match ? "Matched" : "Mismatch"} />
                                <InfoRow label="Combined Verdict" value={item.combined_verdict} />
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="Reconnect Analysis" detail="Not captured in this stage." />
                )}
            </div>
        </div>
    );
}

function AssessmentOverview({ stage }) {
    const risk = stageRiskSummary(stage);
    return (
        <div className="wf-stage-pane">
            <OverviewGrid>
                <div className="wf-data-card">
                    <p className="wf-section-label">Stage Summary</p>
                    <p className="wf-copy">{stage.summary || "No summary available."}</p>
                    <InfoRow label="Status" value={stage.secondary_status} />
                    <InfoRow label="Average Score" value={stage.score != null ? `${stage.score}` : "Not captured"} />
                </div>
                <div className="wf-data-card">
                    <p className="wf-section-label">Risk Overview</p>
                    <InfoRow label="Suspicious Events" value={String(risk.suspiciousCount)} />
                    <InfoRow label="AI Alerts" value={String(risk.alertCount)} />
                    <InfoRow label="Malpractice Incidents" value={String(risk.incidentCount)} />
                    <InfoRow label="Total Flags" value={String(risk.totalRiskFlags)} />
                </div>
            </OverviewGrid>

            {(stage.rounds || []).length ? (
                <div className="wf-round-grid">
                    {stage.rounds.map((round, index) => (
                        <div key={`${stage.key}-round-${index}`} className="wf-round-card">
                            <div className="wf-round-head">
                                <strong>{round.label}</strong>
                                {badge(round.secondary_status || round.status_label || "Pending", round.primary_status || "pending")}
                            </div>
                            <p>{round.summary || "No round summary captured."}</p>
                            <div className="wf-inline-meta">
                                <span>Score: {round.score_pct != null ? `${round.score_pct}` : "Not captured"}</span>
                                <span>Pass Mark: {round.pass_score != null ? round.pass_score : "Not captured"}</span>
                                <span>Submitted: {formatDateTime(round.submitted_at)}</span>
                                <span>
                                    {round.display_only
                                        ? "Execution: UI only"
                                        : `Invite Email: ${round.email_sent ? "Sent" : "Manual / Not sent"}`}
                                </span>
                            </div>
                            {round.manual_round_url ? (
                                <div className="wf-link-row">
                                    <a
                                        className="wf-link-chip"
                                        href={round.manual_round_url}
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        Open Test Link
                                    </a>
                                </div>
                            ) : null}
                        </div>
                    ))}
                </div>
            ) : (
                <EmptyState title="Round Overview" detail="No attempts recorded for this stage yet." />
            )}
        </div>
    );
}

function QuestionsPane({ stage }) {
    if (!(stage.items || []).length) {
        return (
            <EmptyState
                title="Questions & Answers"
                detail="No detailed question or interview item data was captured for this stage."
            />
        );
    }
    return (
        <div className="wf-stage-pane">
            {(stage.items || []).map((item, index) => (
                <div key={`${stage.key}-item-${index}`} className="wf-question-card">
                    <p className="wf-question-title">{item.question_text || `Item ${index + 1}`}</p>
                    <InfoRow label="Candidate Answer" value={item.candidate_answer || "Not captured"} />
                    <InfoRow label="Correct Answer" value={item.correct_answer || "Not applicable"} />
                    <InfoRow label="AI Evaluation Summary" value={item.ai_summary || "Not captured"} />
                    <InfoRow label="Manual Comments" value={item.manual_comments || "Not captured"} />
                </div>
            ))}
        </div>
    );
}

function ScoringPane({ stage }) {
    const rows = extractScoringRows(stage);
    if (!rows.length) {
        return (
            <EmptyState
                title="Scoring Details"
                detail="No granular scoring details were recorded for this stage."
            />
        );
    }
    return (
        <div className="wf-stage-pane">
            {rows.map((item, index) => (
                <div key={`${stage.key}-score-${index}`} className="wf-score-card">
                    <div className="wf-score-head">
                        <strong>{item.question_text || `Item ${index + 1}`}</strong>
                        <span>{item.marks_awarded != null ? `${item.marks_awarded}` : "Manual review"}</span>
                    </div>
                    <p>{item.marks_reason || "No reason recorded."}</p>
                    <InfoRow label="Strengths" value={(item.strengths || []).join(", ") || "Not captured"} />
                    <InfoRow label="Weaknesses" value={(item.weaknesses || []).join(", ") || "Not captured"} />
                    <InfoRow label="Confidence / Communication" value={item.confidence_analysis || "Not captured"} />
                    <InfoRow label="Technical Accuracy" value={item.technical_analysis || "Not captured"} />
                </div>
            ))}
        </div>
    );
}

function TimingPane({ stage }) {
    const rows = extractTimingRows(stage);
    if (!rows.length) {
        return (
            <EmptyState
                title="Timing Analytics"
                detail="Timing analytics were not captured for this stage."
            />
        );
    }
    return (
        <div className="wf-stage-pane">
            <div className="wf-timing-table">
                <div className="wf-timing-head">
                    <span>Item</span>
                    <span>Time Spent</span>
                    <span>Latency</span>
                    <span>Started</span>
                    <span>Ended</span>
                </div>
                {rows.map((item, index) => (
                    <div key={`${stage.key}-time-${index}`} className="wf-timing-row">
                        <span>{item.question_text || `Item ${index + 1}`}</span>
                        <span>{formatDuration(item.time_spent_seconds || item.total_duration_seconds)}</span>
                        <span>{formatDuration(item.response_latency_seconds)}</span>
                        <span>{formatDateTime(item.started_at)}</span>
                        <span>{formatDateTime(item.ended_at)}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ApplicationReviewPane({ stage, workflow }) {
    const candidate = workflow?.candidate || {};
    const applicationDocuments = workflow?.application_documents || stage?.application_documents || candidate?.application_documents || [];
    const links = [
        { label: "LinkedIn", href: candidate.linkedin_url },
        { label: "GitHub", href: candidate.github_url },
        { label: "LeetCode", href: candidate.leetcode_url },
        { label: "Portfolio", href: candidate.portfolio_url },
    ].filter((item) => item.href);
    return (
        <div className="wf-stage-pane">
            <OverviewGrid>
                <div className="wf-data-card">
                    <p className="wf-section-label">Candidate Snapshot</p>
                    <InfoRow label="Name" value={candidate.full_name} />
                    <InfoRow label="Email" value={candidate.email} />
                    <InfoRow label="Phone" value={candidate.phone} />
                    <InfoRow label="Location" value={candidate.location} />
                    <InfoRow label="Current Role" value={candidate.current_title} />
                    <InfoRow label="Company" value={candidate.company_name} />
                    <InfoRow label="Experience" value={candidate.years_exp ? `${candidate.years_exp} years` : ""} />
                    <InfoRow label="Notice Period" value={candidate.notice_period} />
                    <InfoRow label="Current CTC" value={candidate.current_lpa ? `${candidate.current_lpa} LPA` : ""} />
                </div>
                <div className="wf-data-card">
                    <p className="wf-section-label">Application Review Summary</p>
                    <p className="wf-copy">{stage.summary || "No AI summary captured yet."}</p>
                    <InfoRow label="AI Recommendation" value={workflow?.application?.eval_recommendation || "Not captured"} />
                    <InfoRow label="AI Score" value={workflow?.application?.eval_score != null ? String(workflow.application.eval_score) : "Not captured"} />
                    <InfoRow label="Applied On" value={formatDateTime(candidate.submitted_at)} />
                </div>
            </OverviewGrid>

            {(candidate.technical_skills || candidate.soft_skills) && (
                <div className="wf-data-card">
                    <p className="wf-section-label">Skills</p>
                    <p className="wf-copy">{candidate.technical_skills || "Not captured"}</p>
                    <p className="wf-copy">{candidate.soft_skills || "Not captured"}</p>
                </div>
            )}

            {links.length > 0 && (
                <div className="wf-data-card">
                    <p className="wf-section-label">Links</p>
                    <div className="wf-link-row">
                        {links.map((item) => (
                            <a key={item.label} href={item.href} target="_blank" rel="noreferrer" className="wf-link-chip">
                                {item.label}
                            </a>
                        ))}
                    </div>
                </div>
            )}

            {candidate.cover_letter && (
                <div className="wf-data-card">
                    <p className="wf-section-label">Cover Letter</p>
                    <p className="wf-copy">{candidate.cover_letter}</p>
                </div>
            )}

            <div className="wf-data-card">
                <p className="wf-section-label">Uploaded Documents</p>
                {applicationDocuments.length ? (
                    <div className="wf-doc-grid">
                        {applicationDocuments.map((item) => (
                            <div key={item.id} className="wf-doc-card">
                                <strong>{item.document_type === "resume" ? "Resume" : "Cover Letter"}</strong>
                                <p>{item.filename}</p>
                                <span>{formatDateTime(item.uploaded_at)}</span>
                                <div className="wf-link-row">
                                    <a href={item.storage_url} target="_blank" rel="noreferrer" className="wf-link-chip">View</a>
                                    <a href={item.download_url} target="_blank" rel="noreferrer" className="wf-link-chip">Download</a>
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <EmptyState title="Application Documents" detail="Resume or cover-letter originals were not uploaded for this application." />
                )}
            </div>

            {stage.evaluation ? (
                <EvalPanel
                    evalData={stage.evaluation}
                    evalSummary={workflow?.application?.eval_summary}
                    candidate={candidate}
                />
            ) : (
                <EmptyState
                    title="AI Evaluation"
                    detail="The resume and profile evaluation payload has not been captured yet."
                />
            )}
        </div>
    );
}

function BgvPane({ stage, onReview, actionKey }) {
    const data = stage.data;
    const groupedDocs = groupVerificationDocuments(data?.document_items || []);
    return (
        <div className="wf-stage-pane">
            {!data ? (
                <EmptyState
                    title="Background Verification"
                    detail="The verification case has not been submitted yet."
                />
            ) : (
                <>
                    <OverviewGrid>
                        <div className="wf-data-card">
                            <p className="wf-section-label">Verification Status</p>
                            <InfoRow label="Status" value={data.status} />
                            <InfoRow label="Submitted At" value={formatDateTime(data.submitted_at)} />
                            <InfoRow label="Reviewed At" value={formatDateTime(data.reviewed_at)} />
                            <InfoRow label="Reviewer" value={data.reviewer_email} />
                        </div>
                        <div className="wf-data-card">
                            <p className="wf-section-label">Decision Reasoning</p>
                            <p className="wf-copy">{data.review_summary || "Awaiting HR review."}</p>
                            <p className="wf-copy">{data.review_reason || "No final review reason captured yet."}</p>
                        </div>
                    </OverviewGrid>

                    <OverviewGrid>
                        <div className="wf-data-card">
                            <p className="wf-section-label">Candidate Details</p>
                            <InfoRow label="Full Name" value={data.typed_full_name} />
                            <InfoRow label="Address" value={data.typed_address} />
                            <InfoRow label="City" value={data.typed_city} />
                            <InfoRow label="State" value={data.typed_state} />
                            <InfoRow label="Pincode" value={data.typed_pincode} />
                            <InfoRow label="PAN" value={data.typed_pan} />
                            <InfoRow label="Aadhaar" value={data.typed_aadhaar} />
                        </div>
                        <div className="wf-data-card">
                            <p className="wf-section-label">Risk Flags</p>
                            {(data.mismatches || []).length ? (
                                <div className="wf-chip-row">
                                    {(data.mismatches || []).map((item) => (
                                        <span key={item} className="wf-chip wf-chip-risk">{item}</span>
                                    ))}
                                </div>
                            ) : (
                                <p className="wf-copy">No mismatch flags recorded.</p>
                            )}
                        </div>
                    </OverviewGrid>

                    {["identity", "education", "travel"].map((groupKey) => (
                        <div key={groupKey} className="wf-data-card">
                            <p className="wf-section-label">{groupKey.replace(/^\w/, (c) => c.toUpperCase())} Documents</p>
                            {groupedDocs[groupKey]?.length ? (
                                <div className="wf-doc-grid">
                                    {groupedDocs[groupKey].map((item) => (
                                        <div key={item.id} className="wf-doc-card">
                                            <strong>{item.document_type.replaceAll("_", " ")}</strong>
                                            <p>{item.filename}</p>
                                            <span>OCR: {item.ocr_status} · Review: {item.verification_status}</span>
                                            {Object.keys(item.ocr_fields || {}).length ? (
                                                <small>{Object.entries(item.ocr_fields).map(([key, value]) => `${key}: ${value || "n/a"}`).join(" | ")}</small>
                                            ) : null}
                                            <div className="wf-link-row">
                                                <a href={item.storage_url} target="_blank" rel="noreferrer" className="wf-link-chip">View</a>
                                                <a href={item.download_url} target="_blank" rel="noreferrer" className="wf-link-chip">Download</a>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="wf-copy">No {groupKey} documents uploaded yet.</p>
                            )}
                        </div>
                    ))}

                    {stage.actions?.can_review && (
                        <div className="wf-action-row">
                            <button className="wf-btn wf-btn-primary" disabled={!!actionKey} onClick={() => onReview("accept")}>
                                {actionKey === "bgv-accept" ? "Saving..." : "Approve BGV"}
                            </button>
                            <button className="wf-btn wf-btn-secondary" disabled={!!actionKey} onClick={() => onReview("hold")}>
                                {actionKey === "bgv-hold" ? "Saving..." : "Put On Hold"}
                            </button>
                            <button className="wf-btn wf-btn-danger" disabled={!!actionKey} onClick={() => onReview("reject")}>
                                {actionKey === "bgv-reject" ? "Saving..." : "Reject BGV"}
                            </button>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function OfferFormPane({ title, subtitle, form, onChange, onSubmit, actionKey, stage, submitLabel, submitKey }) {
    return (
        <div className="wf-stage-pane">
            <div className="wf-data-card">
                <p className="wf-section-label">{title}</p>
                <p className="wf-copy">{subtitle}</p>
                <div className="wf-form-grid">
                    <label>
                        Joining Date
                        <input value={form.joining_date} onChange={(e) => onChange("joining_date", e.target.value)} />
                    </label>
                    <label>
                        Employment Type
                        <input value={form.employment_type} onChange={(e) => onChange("employment_type", e.target.value)} />
                    </label>
                    <label>
                        Designation
                        <input value={form.designation} onChange={(e) => onChange("designation", e.target.value)} />
                    </label>
                    <label>
                        Department
                        <input value={form.department} onChange={(e) => onChange("department", e.target.value)} />
                    </label>
                    <label>
                        Work Mode
                        <input value={form.work_mode} onChange={(e) => onChange("work_mode", e.target.value)} />
                    </label>
                    <label>
                        Work Location
                        <input value={form.work_location} onChange={(e) => onChange("work_location", e.target.value)} />
                    </label>
                    <label>
                        Reporting Manager
                        <input value={form.reporting_manager} onChange={(e) => onChange("reporting_manager", e.target.value)} />
                    </label>
                    <label>
                        Reporting Team
                        <input value={form.reporting_team} onChange={(e) => onChange("reporting_team", e.target.value)} />
                    </label>
                    <label>
                        Offered LPA / CTC
                        <input value={form.offered_compensation} onChange={(e) => onChange("offered_compensation", e.target.value)} />
                    </label>
                    <label>
                        Compensation / Package Notes
                        <textarea value={form.compensation_text} onChange={(e) => onChange("compensation_text", e.target.value)} />
                    </label>
                    <label>
                        Contract Duration / Notes
                        <textarea value={form.contract_duration_or_notes} onChange={(e) => onChange("contract_duration_or_notes", e.target.value)} />
                    </label>
                    <label>
                        Company Details
                        <textarea value={form.company_details} onChange={(e) => onChange("company_details", e.target.value)} />
                    </label>
                    <label>
                        HR Contact Details
                        <textarea value={form.hr_contact_details} onChange={(e) => onChange("hr_contact_details", e.target.value)} />
                    </label>
                    <label>
                        Onboarding Instructions
                        <textarea value={form.onboarding_instructions} onChange={(e) => onChange("onboarding_instructions", e.target.value)} />
                    </label>
                    <label>
                        Terms & Conditions
                        <textarea value={form.terms_and_conditions} onChange={(e) => onChange("terms_and_conditions", e.target.value)} />
                    </label>
                    <label>
                        Offer Valid Until
                        <input value={form.offer_valid_until} onChange={(e) => onChange("offer_valid_until", e.target.value)} />
                    </label>
                </div>
                <div className="wf-action-row">
                    <button className="wf-btn wf-btn-primary" disabled={!!actionKey} onClick={onSubmit}>
                        {actionKey === submitKey ? "Saving..." : submitLabel}
                    </button>
                    {stage?.data?.token ? (
                        <a
                            className="wf-btn wf-btn-link"
                            href={`${API}/offer-letter/${stage.data.token}/download?kind=unsigned`}
                            target="_blank"
                            rel="noreferrer"
                        >
                            Preview PDF
                        </a>
                    ) : null}
                </div>
            </div>
        </div>
    );
}

function CandidateAcceptancePane({ stage }) {
    const data = stage.data;
    const portalLink = data?.token ? `${window.location.origin}/offer/${data.token}` : "";
    return (
        <div className="wf-stage-pane">
            <OverviewGrid>
                <div className="wf-data-card">
                    <p className="wf-section-label">Candidate Response</p>
                    <InfoRow label="Decision" value={data?.candidate_response || "Pending"} />
                    <InfoRow label="Responded At" value={formatDateTime(data?.candidate_response_at)} />
                    <InfoRow label="Signed PDF" value={data?.signed_pdf_path ? "Available" : "Not captured"} />
                    <InfoRow label="Portal Expires" value={formatDateTime(data?.candidate_portal_expires_at)} />
                </div>
                <div className="wf-data-card">
                    <p className="wf-section-label">Remarks & Audit</p>
                    <p className="wf-copy">{data?.candidate_remarks || "No candidate remarks submitted yet."}</p>
                    <InfoRow label="IP Address" value={data?.candidate_ip || "Not captured"} />
                    <InfoRow label="User Agent" value={data?.candidate_user_agent || "Not captured"} />
                </div>
            </OverviewGrid>

            <div className="wf-action-row">
                {portalLink ? (
                    <a className="wf-btn wf-btn-link" href={portalLink} target="_blank" rel="noreferrer">
                        Open Candidate Portal
                    </a>
                ) : null}
                {data?.token ? (
                    <a className="wf-btn wf-btn-link" href={`${API}/offer-letter/${data.token}/download`} target="_blank" rel="noreferrer">
                        Download Latest PDF
                    </a>
                ) : null}
            </div>
        </div>
    );
}

function ApprovalPane({ stage, approvalForm, setApprovalForm, submitApproval, actionKey }) {
    return (
        <div className="wf-stage-pane">
            <div className="wf-data-card">
                <p className="wf-section-label">HR Final Approval</p>
                <div className="wf-form-grid wf-form-grid-compact">
                    <label>
                        Decision
                        <select
                            value={approvalForm.decision}
                            onChange={(e) => setApprovalForm((prev) => ({ ...prev, decision: e.target.value }))}
                        >
                            <option value="approved">Approve</option>
                            <option value="on_hold">On Hold</option>
                            <option value="rejected">Reject</option>
                        </select>
                    </label>
                    <label>
                        Recommendation Score
                        <input
                            type="number"
                            min="0"
                            max="10"
                            step="0.1"
                            value={approvalForm.recommendation_score}
                            onChange={(e) => setApprovalForm((prev) => ({ ...prev, recommendation_score: e.target.value }))}
                        />
                    </label>
                    <label>
                        Reason
                        <textarea
                            value={approvalForm.reason}
                            onChange={(e) => setApprovalForm((prev) => ({ ...prev, reason: e.target.value }))}
                        />
                    </label>
                </div>
                <div className="wf-action-row">
                    <button className="wf-btn wf-btn-primary" disabled={!!actionKey} onClick={submitApproval}>
                        {actionKey === "final-approval" ? "Saving..." : "Save Final Approval"}
                    </button>
                </div>
                <InfoRow label="Current Approval Status" value={stage.data?.hr_final_approval_status || "Pending"} />
                <InfoRow label="Reasoning" value={stage.data?.hr_final_approval_reason || "Not captured"} />
            </div>
        </div>
    );
}

function FinalOutcomePane({ form, setForm, saveOutcome, actionKey }) {
    return (
        <div className="wf-stage-pane">
            <div className="wf-data-card">
                <p className="wf-section-label">Final Hiring Outcome</p>
                <div className="wf-form-grid wf-form-grid-compact">
                    <label>
                        Outcome
                        <select value={form.outcome} onChange={(e) => setForm((prev) => ({ ...prev, outcome: e.target.value }))}>
                            <option value="hired">Hired</option>
                            <option value="on_hold">On Hold</option>
                            <option value="rejected">Rejected</option>
                        </select>
                    </label>
                    <label>
                        Recommendation Score
                        <input
                            type="number"
                            min="0"
                            max="100"
                            step="0.1"
                            value={form.recommendation_score}
                            onChange={(e) => setForm((prev) => ({ ...prev, recommendation_score: e.target.value }))}
                        />
                    </label>
                    <label>
                        Summary
                        <textarea value={form.summary} onChange={(e) => setForm((prev) => ({ ...prev, summary: e.target.value }))} />
                    </label>
                </div>
                <div className="wf-action-row">
                    <button className="wf-btn wf-btn-primary" disabled={!!actionKey} onClick={saveOutcome}>
                        {actionKey === "final-outcome" ? "Saving..." : "Update Final Outcome"}
                    </button>
                </div>
            </div>
        </div>
    );
}

function OnboardingPane({ stage, form, setForm, saveOnboarding, actionKey }) {
    return (
        <div className="wf-stage-pane">
            <div className="wf-data-card">
                <p className="wf-section-label">Employee Onboarding</p>
                <div className="wf-form-grid wf-form-grid-compact">
                    <label>
                        Onboarding Status
                        <select
                            value={form.onboarding_status}
                            onChange={(e) => setForm((prev) => ({ ...prev, onboarding_status: e.target.value }))}
                        >
                            <option value="pending">Pending</option>
                            <option value="in_progress">In Progress</option>
                            <option value="completed">Completed</option>
                        </select>
                    </label>
                    <label>
                        Notes
                        <textarea value={form.notes} onChange={(e) => setForm((prev) => ({ ...prev, notes: e.target.value }))} />
                    </label>
                </div>
                <div className="wf-action-row">
                    <button className="wf-btn wf-btn-primary" disabled={!!actionKey} onClick={saveOnboarding}>
                        {actionKey === "onboarding" ? "Saving..." : "Update Onboarding"}
                    </button>
                </div>
                <InfoRow label="Current Status" value={stage.secondary_status} />
                <InfoRow label="Notes" value={stage.data?.onboarding_notes || "Not captured"} />
            </div>
        </div>
    );
}

export default function CandidateWorkflowView({
    candidateId,
    initialCandidate,
    initialJob,
    onBack,
    onCandidateUpdate,
    showToast,
}) {
    const [workflow, setWorkflow] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [expanded, setExpanded] = useState({});
    const [activeTabs, setActiveTabs] = useState({});
    const [actionKey, setActionKey] = useState("");
    const [joiningForm, setJoiningForm] = useState(buildOfferForm(null));
    const [approvalForm, setApprovalForm] = useState({
        decision: "approved",
        reason: "",
        recommendation_score: "",
    });
    const [finalOutcomeForm, setFinalOutcomeForm] = useState({
        outcome: "hired",
        summary: "",
        recommendation_score: "",
    });
    const [onboardingForm, setOnboardingForm] = useState({
        onboarding_status: "pending",
        notes: "",
    });
    const onCandidateUpdateRef = useRef(onCandidateUpdate);
    const showToastRef = useRef(showToast);

    const actorEmail = localStorage.getItem("hr_email") || "";

    useEffect(() => {
        onCandidateUpdateRef.current = onCandidateUpdate;
    }, [onCandidateUpdate]);

    useEffect(() => {
        showToastRef.current = showToast;
    }, [showToast]);

    const stages = useMemo(
        () => [...(workflow?.stages || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0)),
        [workflow]
    );

    const fetchWorkflow = useCallback(async ({ silent = false } = {}) => {
        if (!silent) {
            setLoading(true);
            setError("");
        }
        let timeoutId;
        try {
            const controller = new AbortController();
            timeoutId = window.setTimeout(() => controller.abort(), 20000);
            const res = await fetch(`${API}/applications/${candidateId}/workflow`, {
                signal: controller.signal,
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to load workflow");
            setWorkflow(data);
            setExpanded((prev) => {
                if (Object.keys(prev).length) return prev;
                const orderedStages = [...(data.stages || [])].sort((a, b) => (a.order ?? 0) - (b.order ?? 0));
                return Object.fromEntries(orderedStages.map((stage, index) => [stage.key, index <= 1]));
            });
            const offerForm = buildOfferForm(data.offer_workflow);
            setJoiningForm(offerForm);
            setApprovalForm({
                decision: data.offer_workflow?.hr_final_approval_status || "approved",
                reason: data.offer_workflow?.hr_final_approval_reason || "",
                recommendation_score: toFieldValue(data.offer_workflow?.final_recommendation_score),
            });
            setFinalOutcomeForm({
                outcome: data.final_decision?.final_outcome || (data.application?.status === "rejected" ? "rejected" : "hired"),
                summary: data.final_decision?.summary || "",
                recommendation_score: toFieldValue(data.final_decision?.recommendation_score),
            });
            setOnboardingForm({
                onboarding_status: data.offer_workflow?.onboarding_status || "pending",
                notes: data.offer_workflow?.onboarding_notes || "",
            });
            onCandidateUpdateRef.current?.(candidateId, {
                status: data.application?.status,
            });
        } catch (err) {
            if (err?.name === "AbortError") {
                setError("Candidate workflow request timed out. Please retry.");
            } else {
                setError(err.message || "Failed to load workflow");
            }
        } finally {
            window.clearTimeout(timeoutId);
            if (!silent) setLoading(false);
        }
    }, [candidateId]);

    useEffect(() => {
        fetchWorkflow();
    }, [fetchWorkflow]);

    const runAction = async (key, task, successMessage) => {
        setActionKey(key);
        try {
            await task();
            await fetchWorkflow({ silent: true });
            if (successMessage) showToastRef.current?.(successMessage, "success");
        } catch (err) {
            showToastRef.current?.(err.message || "Action failed");
        } finally {
            setActionKey("");
        }
    };

    const updateJoiningField = (field, value) => {
        setJoiningForm((prev) => ({ ...prev, [field]: value }));
    };

    const saveJoining = () =>
        runAction("joining-save", async () => {
            const res = await fetch(`${API}/applications/${candidateId}/workflow/joining`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    ...joiningForm,
                    actor_email: actorEmail,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to save joining setup");
            setWorkflow(data);
        }, "Joining setup saved");

    const startBgv = () =>
        runAction("bgv-start", async () => {
            const res = await fetch(`${API}/applications/${candidateId}/workflow/bgv/start`, {
                method: "POST",
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to start background verification");
            setWorkflow(data);
        }, "Background verification started");

    const reviewBgv = (decision) =>
        runAction(`bgv-${decision}`, async () => {
            const caseId = workflow?.verification_case?.id;
            if (!caseId) throw new Error("Verification case not found");
            const res = await fetch(`${API}/verification/${caseId}/review`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    reviewer_email: actorEmail,
                    decision,
                    reason: `Decision recorded by ${actorEmail || "HR reviewer"}`,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to update verification case");
            return data;
        }, "Verification review updated");

    const generateOffer = () =>
        runAction("offer-generate", async () => {
            const res = await fetch(`${API}/offer-letter/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    application_id: candidateId,
                    ...joiningForm,
                    actor_email: actorEmail,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to generate offer letter");
            return data;
        }, "Offer letter generated");

    const submitApproval = () =>
        runAction("final-approval", async () => {
            const offerId = workflow?.offer_workflow?.id;
            if (!offerId) throw new Error("Offer workflow not found");
            const res = await fetch(`${API}/offer-letter/${offerId}/final-approval`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    decision: approvalForm.decision,
                    approver_email: actorEmail,
                    reason: approvalForm.reason,
                    recommendation_score: approvalForm.recommendation_score === "" ? null : Number(approvalForm.recommendation_score),
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to save final approval");
            return data;
        }, "Final approval saved");

    const saveFinalOutcome = () =>
        runAction("final-outcome", async () => {
            const res = await fetch(`${API}/applications/${candidateId}/workflow/final-outcome`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    outcome: finalOutcomeForm.outcome,
                    summary: finalOutcomeForm.summary,
                    recommendation_score: finalOutcomeForm.recommendation_score === "" ? null : Number(finalOutcomeForm.recommendation_score),
                    actor_email: actorEmail,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to update final outcome");
            setWorkflow(data);
        }, "Final outcome updated");

    const saveOnboarding = () =>
        runAction("onboarding", async () => {
            const res = await fetch(`${API}/applications/${candidateId}/workflow/onboarding`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    onboarding_status: onboardingForm.onboarding_status,
                    notes: onboardingForm.notes,
                    actor_email: actorEmail,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to update onboarding status");
            setWorkflow(data);
        }, "Onboarding status updated");

    const headerRisk = useMemo(() => {
        return stages.reduce(
            (acc, stage) => {
                const summary = stageRiskSummary(stage);
                acc.flags += summary.totalRiskFlags;
                acc.events += summary.suspiciousCount;
                return acc;
            },
            { flags: 0, events: 0 }
        );
    }, [stages]);

    if (loading) {
        return (
            <main className="wf-page">
                <div className="wf-loading">Loading candidate workflow...</div>
            </main>
        );
    }

    if (error || !workflow) {
        return (
            <main className="wf-page">
                <div className="wf-error-box">
                    <button className="wf-back" onClick={onBack}>
                        <IoIosArrowBack />
                    </button>
                    <div>
                        <p className="wf-error-title">Candidate workflow unavailable</p>
                        <p className="wf-error-copy">{error || "Failed to load workflow."}</p>
                    </div>
                </div>
            </main>
        );
    }

    const finalDecision = workflow.final_decision || {};
    const candidate = workflow.candidate || initialCandidate || {};
    const job = workflow.job || initialJob || {};

    return (
        <main className="wf-page">
            <div className="wf-header">
                <button className="wf-back" onClick={onBack}>
                    <IoIosArrowBack />
                </button>
                <div className="wf-header-copy">
                    <p className="wf-header-eyebrow">{job.job_name || "Candidate Workflow"}</p>
                    <h1>{candidate.full_name || "Candidate"}</h1>
                    <p>
                        {candidate.current_title || "Applicant"}
                        {candidate.company_name ? ` · ${candidate.company_name}` : ""}
                    </p>
                </div>
                <div className="wf-header-badges">
                    {badge(workflow.application?.status?.replaceAll("_", " ") || "Pending", stages.at(-2)?.primary_status || "pending")}
                    <span className="wf-metric-chip">{headerRisk.flags} risk flags</span>
                </div>
            </div>

            <div className="wf-banner-grid">
                <div className="wf-banner-card">
                    <span>Final Recommendation</span>
                    <strong>{finalDecision.recommendation_score != null ? finalDecision.recommendation_score : "Pending"}</strong>
                    <p>{finalDecision.summary || "No final recommendation summary recorded yet."}</p>
                </div>
                <div className="wf-banner-card">
                    <span>Decision Transparency</span>
                    <strong>{finalDecision.final_outcome || workflow.application?.status || "Pending"}</strong>
                    <p>{workflow.stages.find((stage) => stage.key === "final_hiring_outcome")?.summary || "Final decision will appear here."}</p>
                </div>
                <div className="wf-banner-card">
                    <span>Behavioral / Risk Signals</span>
                    <strong>{headerRisk.flags}</strong>
                    <p>{headerRisk.events} suspicious monitoring events and timeline alerts recorded across all stages.</p>
                </div>
            </div>

            <div className="wf-top-grid">
                <div className="wf-chart-card">
                    <div className="wf-card-head">
                        <div>
                            <p className="wf-section-label">Score Comparison</p>
                            <p className="wf-copy">Stage 0 AI evaluation, assessment outcomes, live interview scores, and final recommendation.</p>
                        </div>
                    </div>
                    {workflow.score_comparison?.length ? (
                        <div className="wf-chart-wrap">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={workflow.score_comparison}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ececec" />
                                    <XAxis dataKey="label" tick={{ fontSize: 11 }} interval={0} angle={-12} textAnchor="end" height={65} />
                                    <YAxis tick={{ fontSize: 11 }} />
                                    <Tooltip />
                                    <Bar dataKey="score" fill="#ff5e00" radius={[8, 8, 0, 0]} />
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                    ) : (
                        <EmptyState title="Score Comparison" detail="Scores will appear once the candidate completes evaluated stages." />
                    )}
                </div>

                <div className="wf-audit-card">
                    <p className="wf-section-label">Decision History</p>
                    <div className="wf-audit-list">
                        {(workflow.audit_log || []).slice(0, 8).map((item) => (
                            <div key={item.id} className="wf-audit-row">
                                <strong>{item.summary}</strong>
                                <span>{item.actor_email || item.actor_type}</span>
                                <p>{formatDateTime(item.created_at)}</p>
                            </div>
                        ))}
                        {(workflow.audit_log || []).length === 0 && (
                            <EmptyState title="Audit Log" detail="Workflow actions will appear here as HR and candidates interact with the process." />
                        )}
                    </div>
                </div>
            </div>

            <div className="wf-timeline">
                {stages.map((stage, index) => {
                    const isExpanded = expanded[stage.key] ?? index <= 1;
                    const currentTab = activeTabs[stage.key] || "overview";
                    const risk = stageRiskSummary(stage);
                    return (
                        <section key={stage.key} className="wf-stage-card">
                            <div className="wf-stage-rail">
                                <div className={`wf-stage-dot wf-stage-dot-${stage.primary_status}`} />
                                {index < stages.length - 1 && <div className="wf-stage-line" />}
                            </div>

                            <div className="wf-stage-shell">
                                <button
                                    className="wf-stage-head"
                                    onClick={() => setExpanded((prev) => ({ ...prev, [stage.key]: !isExpanded }))}
                                >
                                    <div>
                                        <p className="wf-stage-kicker">Stage {stage.order ?? index}</p>
                                        <h2>{stage.title}</h2>
                                        <p>{stage.summary || "No summary available."}</p>
                                    </div>
                                    <div className="wf-stage-meta">
                                        {badge(stage.primary_status.replaceAll("_", " "), stage.primary_status)}
                                        {badge(stage.secondary_status || "Pending", stage.primary_status)}
                                        {risk.totalRiskFlags > 0 ? <span className="wf-metric-chip">{risk.totalRiskFlags} flags</span> : null}
                                        {stage.score != null ? <span className="wf-score-chip">{stage.score}</span> : null}
                                    </div>
                                </button>

                                {isExpanded && (
                                    <div className="wf-stage-body">
                                        {stage.kind === "application_review" ? (
                                            <ApplicationReviewPane stage={stage} workflow={workflow} />
                                        ) : stage.kind === "assessment_stage" ? (
                                            <>
                                                <div className="wf-tab-row">
                                                    {["overview", "questions", "scoring", "timing", "evidence"].map((tab) => (
                                                        <button
                                                            key={tab}
                                                            className={`wf-tab ${currentTab === tab ? "active" : ""}`}
                                                            onClick={() => setActiveTabs((prev) => ({ ...prev, [stage.key]: tab }))}
                                                        >
                                                            {tab === "questions"
                                                                ? "Questions & Answers"
                                                                : tab === "scoring"
                                                                    ? "Scoring"
                                                                    : tab === "timing"
                                                                        ? "Timing Analytics"
                                                                        : tab === "evidence"
                                                                            ? "Evidence"
                                                                            : "Overview"}
                                                        </button>
                                                    ))}
                                                </div>
                                                {currentTab === "overview" && <AssessmentOverview stage={stage} />}
                                                {currentTab === "questions" && <QuestionsPane stage={stage} />}
                                                {currentTab === "scoring" && <ScoringPane stage={stage} />}
                                                {currentTab === "timing" && <TimingPane stage={stage} />}
                                                {currentTab === "evidence" && <EvidenceSection stage={stage} />}
                                            </>
                                        ) : stage.kind === "joining_setup" ? (
                                            <div className="wf-stage-pane">
                                                <OfferFormPane
                                                    title="Joining Setup"
                                                    subtitle="Capture joining date, manager, work mode, compensation, and all offer metadata before background verification."
                                                    form={joiningForm}
                                                    onChange={updateJoiningField}
                                                    onSubmit={saveJoining}
                                                    actionKey={actionKey}
                                                    stage={stage}
                                                    submitLabel="Save Joining Setup"
                                                    submitKey="joining-save"
                                                />
                                                {stage.actions?.can_start_bgv && (
                                                    <div className="wf-action-row">
                                                        <button className="wf-btn wf-btn-secondary" disabled={!!actionKey} onClick={startBgv}>
                                                            {actionKey === "bgv-start" ? "Starting..." : "Start Background Verification"}
                                                        </button>
                                                    </div>
                                                )}
                                            </div>
                                        ) : stage.kind === "background_verification" ? (
                                            <BgvPane stage={stage} onReview={reviewBgv} actionKey={actionKey} />
                                        ) : stage.kind === "offer_letter" ? (
                                            <OfferFormPane
                                                title="Offer Letter"
                                                subtitle="Generate the offer letter from the joining setup once verification is approved."
                                                form={joiningForm}
                                                onChange={updateJoiningField}
                                                onSubmit={generateOffer}
                                                actionKey={actionKey}
                                                stage={stage}
                                                submitLabel="Generate Offer Letter"
                                                submitKey="offer-generate"
                                            />
                                        ) : stage.kind === "candidate_acceptance" ? (
                                            <CandidateAcceptancePane stage={stage} />
                                        ) : stage.kind === "hr_final_approval" ? (
                                            <ApprovalPane
                                                stage={stage}
                                                approvalForm={approvalForm}
                                                setApprovalForm={setApprovalForm}
                                                submitApproval={submitApproval}
                                                actionKey={actionKey}
                                            />
                                        ) : stage.kind === "final_hiring_outcome" ? (
                                            <FinalOutcomePane
                                                form={finalOutcomeForm}
                                                setForm={setFinalOutcomeForm}
                                                saveOutcome={saveFinalOutcome}
                                                actionKey={actionKey}
                                            />
                                        ) : stage.kind === "employee_onboarding" ? (
                                            <OnboardingPane
                                                stage={stage}
                                                form={onboardingForm}
                                                setForm={setOnboardingForm}
                                                saveOnboarding={saveOnboarding}
                                                actionKey={actionKey}
                                            />
                                        ) : null}
                                    </div>
                                )}
                            </div>
                        </section>
                    );
                })}
            </div>
        </main>
    );
}
