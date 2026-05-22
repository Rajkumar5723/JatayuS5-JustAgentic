import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CandidateWorkflowView from "./CandidateWorkflowView.jsx";

vi.mock("./Evalpanel.jsx", () => ({
    default: function MockEvalPanel() {
        return <div data-testid="eval-panel">Eval panel</div>;
    },
}));

vi.mock("recharts", () => {
    const Box = ({ children }) => <div>{children}</div>;
    return {
        ResponsiveContainer: Box,
        BarChart: Box,
        Bar: () => <div />,
        XAxis: () => <div />,
        YAxis: () => <div />,
        CartesianGrid: () => <div />,
        Tooltip: () => <div />,
    };
});

const workflowPayload = {
    candidate: {
        id: 42,
        full_name: "Avery Chen",
        email: "avery@example.com",
        submitted_at: "2026-05-19T10:00:00Z",
    },
    application: {
        id: 42,
        status: "offer_pending",
        eval_score: 81,
        eval_recommendation: "Strong fit",
        eval_summary: "Solid resume and project depth.",
    },
    job: {
        id: 9,
        job_name: "Frontend Engineer",
        rounds: "",
        department: "dev",
        job_type: "ft",
    },
    stages: [
        {
            key: "offer_letter",
            title: "Offer Letter",
            kind: "offer_letter",
            order: 5,
            primary_status: "pending",
            secondary_status: "Pending",
            summary: "Offer not sent yet.",
            score: null,
            items: [],
            rounds: [],
            evidence: {},
            data: { token: "abc123" },
            actions: {},
        },
        {
            key: "application_review",
            title: "Stage 0 - Application Review",
            kind: "application_review",
            order: 0,
            primary_status: "completed",
            secondary_status: "Completed",
            summary: "Candidate application received and reviewed.",
            score: 81,
            items: [],
            rounds: [],
            evidence: {},
            evaluation: { summary: "Resume summary" },
            actions: {},
        },
        {
            key: "configured_stage_1",
            title: "Stage 1 - Shortlisting Test",
            kind: "assessment_stage",
            order: 1,
            primary_status: "completed",
            secondary_status: "Completed",
            summary: "Candidate completed the test.",
            score: 76,
            items: [
                {
                    question_text: "What is closure?",
                    candidate_answer: "A function with lexical scope.",
                    correct_answer: "A function with lexical scope.",
                    marks_awarded: 1,
                    marks_reason: "Correct.",
                    strengths: ["JavaScript"],
                    weaknesses: [],
                    time_spent_seconds: 42,
                    response_latency_seconds: 7,
                    started_at: "2026-05-19T10:05:00Z",
                    ended_at: "2026-05-19T10:05:42Z",
                },
            ],
            rounds: [
                {
                    label: "MCQ Test",
                    primary_status: "completed",
                    secondary_status: "Completed",
                    summary: "Passed",
                    score_pct: 76,
                    pass_score: 70,
                    submitted_at: "2026-05-19T10:25:00Z",
                    evidence: {},
                    items: [],
                },
            ],
            evidence: {
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
            },
            actions: {},
        },
        {
            key: "configured_stage_2",
            title: "Stage 2 - Coding Round",
            kind: "assessment_stage",
            order: 2,
            primary_status: "pending",
            secondary_status: "Pending",
            summary: "Waiting for this stage to begin.",
            score: null,
            items: [],
            rounds: [],
            evidence: {},
            actions: {},
        },
        {
            key: "configured_stage_3",
            title: "Stage 3 - Live Interview",
            kind: "assessment_stage",
            order: 3,
            primary_status: "pending",
            secondary_status: "Pending",
            summary: "Waiting for interview scheduling.",
            score: null,
            items: [],
            rounds: [],
            evidence: {},
            actions: {},
        },
    ],
    score_comparison: [
        { label: "Application Review", score: 81, stage_key: "application_review" },
        { label: "Stage 1 - Shortlisting Test", score: 76, stage_key: "configured_stage_1" },
    ],
    final_decision: {
        application_status: "offer_pending",
        final_outcome: "",
        summary: "",
        recommendation_score: null,
    },
    audit_log: [],
    offer_workflow: {
        id: 1,
        token: "abc123",
        status: "offer_pending",
        joining_date: "2026-06-15",
        onboarding_status: "pending",
        onboarding_notes: "",
    },
    verification_case: null,
};

describe("CandidateWorkflowView", () => {
    beforeEach(() => {
        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => workflowPayload,
        });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("renders the workflow in stage order and shows empty evidence states", async () => {
        render(
            <CandidateWorkflowView
                candidateId={42}
                initialCandidate={{ id: 42, full_name: "Avery Chen" }}
                initialJob={{ id: 9, job_name: "Frontend Engineer" }}
                onBack={() => {}}
                onCandidateUpdate={() => {}}
                showToast={() => {}}
            />
        );

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Avery Chen" })).toBeInTheDocument();
        });

        const headings = screen.getAllByRole("heading", { level: 2 }).map((node) => node.textContent);
        expect(headings.slice(0, 4)).toEqual([
            "Stage 0 - Application Review",
            "Stage 1 - Shortlisting Test",
            "Stage 2 - Coding Round",
            "Stage 3 - Live Interview",
        ]);

        await userEvent.click(screen.getByRole("button", { name: "Evidence" }));
        expect(screen.getByText("Room 360 Monitoring")).toBeInTheDocument();
        expect(screen.getAllByText("Not captured in this stage.").length).toBeGreaterThan(0);
    });

    it("renders captured room scan, webcam, and incident evidence when available", async () => {
        const payload = JSON.parse(JSON.stringify(workflowPayload));
        payload.stages = payload.stages.map((stage) =>
            stage.key === "configured_stage_1"
                ? {
                    ...stage,
                    evidence: {
                        room_scans: [
                            {
                                scan_type: "initial",
                                verdict: "pass",
                                created_at: "2026-05-19T10:03:00Z",
                                completed_at: "2026-05-19T10:04:00Z",
                                frames: [
                                    {
                                        frame_index: 0,
                                        has_violation: false,
                                        storage_url: "https://example.com/room-frame.jpg",
                                    },
                                ],
                                suspicious_items: [],
                            },
                        ],
                        webcam_snapshots: [
                            {
                                download_url: "https://example.com/webcam.jpg",
                                event_type: "selfie_captured",
                                timestamp: "2026-05-19T10:05:00Z",
                            },
                        ],
                        screen_snapshots: [],
                        meet_snapshots: [
                            {
                                presigned_url: "https://example.com/live-room.jpg",
                                event_type: "meet_alert",
                                timestamp: "2026-05-19T10:05:30Z",
                            },
                        ],
                        device_info: [],
                        suspicious_events: [],
                        ai_alerts: [],
                        malpractice_incidents: [
                            {
                                incident_type: "tab_hidden",
                                created_at: "2026-05-19T10:06:00Z",
                                evidence_files: [
                                    {
                                        presigned_url: "https://example.com/incident.jpg",
                                    },
                                ],
                            },
                        ],
                        agent_decisions: [],
                        reconnect_logs: [],
                    },
                }
                : stage
        );

        global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => payload,
        });

        render(
            <CandidateWorkflowView
                candidateId={42}
                initialCandidate={{ id: 42, full_name: "Avery Chen" }}
                initialJob={{ id: 9, job_name: "Frontend Engineer" }}
                onBack={() => {}}
                onCandidateUpdate={() => {}}
                showToast={() => {}}
            />
        );

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Avery Chen" })).toBeInTheDocument();
        });

        await userEvent.click(screen.getByRole("button", { name: "Evidence" }));
        expect(screen.getByText("Clean frame - pass")).toBeInTheDocument();
        expect(screen.getByText("selfie_captured")).toBeInTheDocument();
        expect(screen.getByText("meet_alert")).toBeInTheDocument();
        expect(screen.getByText("tab_hidden evidence 1")).toBeInTheDocument();
    });

    it("does not refetch workflow in a loop when parent state updates from workflow data", async () => {
        function WorkflowHarness() {
            const [candidate, setCandidate] = useState({ id: 42, full_name: "Avery Chen", status: "pending" });

            return (
                <CandidateWorkflowView
                    candidateId={42}
                    initialCandidate={candidate}
                    initialJob={{ id: 9, job_name: "Frontend Engineer" }}
                    onBack={() => {}}
                    onCandidateUpdate={(appId, updated) => {
                        if (appId !== 42) return;
                        setCandidate((prev) => ({ ...prev, ...updated }));
                    }}
                    showToast={() => {}}
                />
            );
        }

        render(<WorkflowHarness />);

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Avery Chen" })).toBeInTheDocument();
        });

        await new Promise((resolve) => setTimeout(resolve, 80));
        expect(global.fetch).toHaveBeenCalledTimes(1);
    });
});
