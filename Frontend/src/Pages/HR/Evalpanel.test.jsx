import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import EvalPanel from "./Evalpanel.jsx";

vi.mock("recharts", () => {
    const Box = ({ children }) => <div>{children}</div>;
    return {
        AreaChart: Box,
        Area: Box,
        BarChart: Box,
        Bar: Box,
        XAxis: Box,
        YAxis: Box,
        Tooltip: Box,
        ResponsiveContainer: Box,
        CartesianGrid: Box,
        PieChart: Box,
        Pie: Box,
        Cell: Box,
        RadarChart: Box,
        Radar: Box,
        PolarGrid: Box,
        PolarAngleAxis: Box,
        RadialBarChart: Box,
        RadialBar: Box,
    };
});

vi.mock("./AnalyticsComponents", () => ({
    GitHubAnalytics: ({ data }) => <div>GitHub analytics for {data.username}</div>,
    LeetCodeAnalytics: ({ data }) => <div>LeetCode analytics for {data.username}</div>,
    LinkedInAnalytics: () => <div>LinkedIn analytics</div>,
}));

describe("EvalPanel", () => {
    it("uses saved candidate profile URLs when evaluator raw data is missing", () => {
        render(
            <EvalPanel
                evalData={{
                    final_score: 48,
                    hiring_recommendation: "No Hire",
                    summary: "Evaluation complete.",
                    component_scores: {
                        resume: { score: 85 },
                        github: { score: 0 },
                        leetcode: { score: 0 },
                        linkedin: { score: 70 },
                    },
                    github_raw: {},
                    leetcode_raw: {},
                }}
                candidate={{
                    github_url: "https://github.com/rikin0102/",
                    leetcode_url: "https://leetcode.com/u/Rajkumar_57/",
                }}
            />
        );

        expect(screen.getByText("@rikin0102")).toBeInTheDocument();
        expect(screen.getByText("@Rajkumar_57")).toBeInTheDocument();
        expect(screen.queryByText(/No GitHub URL provided/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/No LeetCode URL provided/i)).not.toBeInTheDocument();
    });
});
