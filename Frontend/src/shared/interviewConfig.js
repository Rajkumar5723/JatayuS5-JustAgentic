/** Interview pipeline: ordered stages with nested inner rounds (stored in jobs.rounds as JSON v2). */

export const FINAL_HR_STAGE_NAME = "Final HR Round";

export const AVAILABLE_ROUND_TYPES = [
    "MCQ Test",
    "Aptitude Test",
    "Coding",
    "Vibe Coding",
    "OOP Concepts",
    "Database Design",
    "API Design",
    "Group Discussion",
    "Technical HR",
    "HR Interview",
];

export const HR_ROUND_TYPES = new Set(["Technical HR", "HR Interview"]);

export function uid() {
    return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function createDefaultStages() {
    return [
        { id: uid(), name: "Stage 1", isFinalHr: false, rounds: [] },
        { id: uid(), name: FINAL_HR_STAGE_NAME, isFinalHr: true, locked: true, rounds: [] },
    ];
}

/** Parse jobs.rounds — v2 JSON, legacy v1 JSON, or comma-separated labels. */
export function parseInterviewConfig(raw) {
    if (!raw || !String(raw).trim()) {
        return { version: 2, stages: createDefaultStages() };
    }

    const text = String(raw).trim();
    if (text.startsWith("{")) {
        try {
            const config = JSON.parse(text);
            if (config?.version === 2 && Array.isArray(config.stages)) {
                const stages = config.stages.map((s) => ({
                    id: s.id || uid(),
                    name: s.name || "Stage",
                    isFinalHr: Boolean(s.is_final_hr || s.isFinalHr),
                    locked: Boolean(s.is_final_hr || s.isFinalHr || s.locked),
                    rounds: (s.rounds || []).map((r) => ({
                        id: r.id || uid(),
                        type: r.type || r.round_type || "",
                    })).filter((r) => r.type),
                }));
                if (!stages.some((s) => s.isFinalHr)) {
                    stages.push({
                        id: uid(),
                        name: FINAL_HR_STAGE_NAME,
                        isFinalHr: true,
                        locked: true,
                        rounds: [],
                    });
                }
                return { version: 2, stages: ensureFinalHrLast(stages) };
            }

            // Legacy v1 JSON → convert to stages
            const flat = [];
            if (config.shortlisting_test?.enabled) {
                flat.push(config.shortlisting_test.type === "aptitude" ? "Aptitude Test" : "MCQ Test");
            }
            if (config.coding_round?.enabled) {
                const map = {
                    coding: "Coding",
                    vibe_coding: "Vibe Coding",
                    oop_concepts: "OOP Concepts",
                    database_design: "Database Design",
                    api_design: "API Design",
                    group_discussion: "Group Discussion",
                };
                for (const t of config.coding_round.types || []) {
                    if (map[t]) flat.push(map[t]);
                }
            }
            if (config.final_hr_round?.enabled) {
                const map = { technical_hr: "Technical HR", hr_interview: "HR Interview" };
                for (const t of config.final_hr_round.types || []) {
                    if (map[t]) flat.push(map[t]);
                }
            }
            if (flat.length) return flatLabelsToStages(flat);
        } catch {
            /* fall through */
        }
    }

    // Comma-separated legacy
    const labels = text.split(",").map((s) => s.trim()).filter(Boolean);
    if (labels.length) return flatLabelsToStages(labels);
    return { version: 2, stages: createDefaultStages() };
}

function flatLabelsToStages(labels) {
    const hr = [];
    const other = [];
    for (const label of labels) {
        if (HR_ROUND_TYPES.has(label)) hr.push(label);
        else other.push(label);
    }
    const stages = [];
    if (other.length) {
        stages.push({
            id: uid(),
            name: "Stage 1",
            isFinalHr: false,
            rounds: other.map((type) => ({ id: uid(), type })),
        });
    } else {
        stages.push({ id: uid(), name: "Stage 1", isFinalHr: false, rounds: [] });
    }
    stages.push({
        id: uid(),
        name: FINAL_HR_STAGE_NAME,
        isFinalHr: true,
        locked: true,
        rounds: hr.map((type) => ({ id: uid(), type })),
    });
    return { version: 2, stages: ensureFinalHrLast(stages) };
}

export function ensureFinalHrLast(stages) {
    const regular = stages.filter((s) => !s.isFinalHr);
    const final = stages.filter((s) => s.isFinalHr);
    const finalStage = final[0] || {
        id: uid(),
        name: FINAL_HR_STAGE_NAME,
        isFinalHr: true,
        locked: true,
        rounds: [],
    };
    return [...regular, { ...finalStage, isFinalHr: true, locked: true }];
}

export function serializeInterviewConfig(stages) {
    const ordered = ensureFinalHrLast(stages);
    return JSON.stringify({
        version: 2,
        stages: ordered.map((s) => ({
            id: s.id,
            name: s.name,
            is_final_hr: Boolean(s.isFinalHr),
            rounds: (s.rounds || []).map((r) => ({ id: r.id, type: r.type })),
        })),
    });
}

export function flattenRoundLabels(stagesOrConfig) {
    const stages = Array.isArray(stagesOrConfig)
        ? stagesOrConfig
        : parseInterviewConfig(stagesOrConfig).stages;
    return stages.flatMap((s) => (s.rounds || []).map((r) => r.type).filter(Boolean));
}

export function getUsedRoundTypes(stages) {
    return new Set(flattenRoundLabels(stages));
}

export function validateInterviewStages(stages) {
    const errors = [];
    const ordered = ensureFinalHrLast(stages);
    const nonFinal = ordered.filter((s) => !s.isFinalHr);
    const finalStage = ordered.find((s) => s.isFinalHr);

    if (!finalStage) {
        errors.push("Final HR Round is required and must be the last stage.");
    }

    if (nonFinal.length === 0 && (!finalStage?.rounds?.length)) {
        errors.push("Add at least one interview stage with inner rounds.");
    }

    const seen = new Set();
    for (const stage of ordered) {
        if (!stage.rounds?.length) {
            errors.push(`"${stage.name}" has no inner rounds. Add at least one round or remove the stage.`);
        }
        for (const round of stage.rounds || []) {
            if (!round.type) {
                errors.push(`A round in "${stage.name}" is missing a type.`);
                continue;
            }
            if (seen.has(round.type)) {
                errors.push(`"${round.type}" is already used. Each test type can only appear once.`);
            }
            seen.add(round.type);
            if (stage.isFinalHr && !HR_ROUND_TYPES.has(round.type)) {
                errors.push(`"${round.type}" cannot be in Final HR Round. Use Technical HR or HR Interview.`);
            }
            if (!stage.isFinalHr && HR_ROUND_TYPES.has(round.type)) {
                errors.push(`"${round.type}" belongs in Final HR Round, not "${stage.name}".`);
            }
        }
    }

    if (finalStage && !finalStage.rounds?.length) {
        errors.push("Final HR Round must include at least one round (Technical HR or HR Interview).");
    }

    return { ok: errors.length === 0, errors };
}

export function moveItem(list, index, direction) {
    const next = index + direction;
    if (next < 0 || next >= list.length) return list;
    const copy = [...list];
    [copy[index], copy[next]] = [copy[next], copy[index]];
    return copy;
}
