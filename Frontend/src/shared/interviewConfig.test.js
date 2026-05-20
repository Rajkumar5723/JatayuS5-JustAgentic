import { describe, expect, it } from "vitest";

import {
    AVAILABLE_ROUND_TYPES,
    flattenRoundLabels,
    parseInterviewConfig,
} from "./interviewConfig.js";

describe("interviewConfig", () => {
    it("includes Vibe Coding in the round picker", () => {
        expect(AVAILABLE_ROUND_TYPES).toContain("Vibe Coding");
    });

    it("includes Aptitude Test and Group Discussion in the round picker", () => {
        expect(AVAILABLE_ROUND_TYPES).toContain("Aptitude Test");
        expect(AVAILABLE_ROUND_TYPES).toContain("Group Discussion");
    });

    it("parses legacy vibe_coding configuration into the visible round label", () => {
        const config = parseInterviewConfig(JSON.stringify({
            coding_round: {
                enabled: true,
                types: ["vibe_coding"],
            },
            final_hr_round: {
                enabled: true,
                types: ["technical_hr"],
            },
        }));

        expect(flattenRoundLabels(config.stages)).toContain("Vibe Coding");
    });

    it("parses legacy aptitude configuration into the visible round label", () => {
        const config = parseInterviewConfig(JSON.stringify({
            shortlisting_test: {
                enabled: true,
                type: "aptitude",
            },
            final_hr_round: {
                enabled: true,
                types: ["technical_hr"],
            },
        }));

        expect(flattenRoundLabels(config.stages)).toContain("Aptitude Test");
    });
});
