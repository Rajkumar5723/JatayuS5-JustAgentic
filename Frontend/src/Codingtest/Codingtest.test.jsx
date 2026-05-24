import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import CodingTest from "./Codingtest.jsx";

vi.mock("../shared/proctoring.jsx", () => ({
    ProctoringMonitor: () => null,
    useProctoring: () => ({
        videoRef: { current: null },
        risk: null,
        warning: "",
        cameraReady: true,
    }),
}));

describe("CodingTest", () => {
    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("resumes a started coding round with object examples without crashing", async () => {
        vi.spyOn(globalThis, "fetch").mockResolvedValue({
            ok: true,
            text: async () =>
                JSON.stringify({
                    token: "coding-token",
                    candidate_name: "Rajkumar G",
                    job_title: "AI Developer",
                    duration_mins: 60,
                    status: "started",
                    started_at: new Date().toISOString(),
                    round_type: "coding",
                    content_locked: false,
                    room_scan_required: false,
                    problems: [
                        {
                            title: "Predicting Customer Churn",
                            difficulty: "Medium",
                            description: "Build a churn model.",
                            constraints: "Accuracy should be at least 80%.",
                            examples: [
                                {
                                    input: { customer_id: [1, 2], usage: [100, 200] },
                                    output: [0.2, 0.8],
                                },
                            ],
                            starter_code: "print('hello')",
                        },
                    ],
                }),
        });

        render(
            <MemoryRouter initialEntries={["/coding/coding-token"]}>
                <Routes>
                    <Route path="/coding/:token" element={<CodingTest />} />
                </Routes>
            </MemoryRouter>,
        );

        await waitFor(() => {
            expect(screen.getByText("Predicting Customer Churn")).toBeInTheDocument();
        });
        expect(screen.getAllByText(/customer_id/).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/0.2/).length).toBeGreaterThan(0);
        expect(screen.getByDisplayValue("print('hello')")).toBeInTheDocument();
    });
});
