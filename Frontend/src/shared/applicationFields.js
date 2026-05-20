/** Shared Application Setup field order and parsing (HR AddPost ↔ candidate apply form). */

export const APP_FIELD_ORDER = [
    "Resume/CV", "Cover letter", "Portfolio link",
    "Full Name", "Location / address",
    "Email Id", "Phone Number", "Alternative Number",
    "Degree type", "Field of study", "Institution name",
    "Years of experience", "Current/past job titles", "Company names", "Current LPA", "Notice Period",
    "Technical skills", "Soft skills", "Certifications / licenses",
    "LinkedIn", "GitHub", "LeetCode", "Codeforces", "HackerRank", "Kaggle", "Stack Overflow", "Medium",
];

/** Shown as PDF upload zones on the apply form (not text inputs). */
export const UPLOAD_FIELD_LABELS = new Set(["Resume/CV", "Cover letter"]);

export const DEFAULT_APPLICATION_FIELDS = [
    "Resume/CV", "Full Name", "Email Id", "Phone Number", "Location / address",
    "LinkedIn", "GitHub", "Years of experience", "Technical skills", "Degree type",
];

/** Side-by-side pairs for a professional apply form layout. */
export const FIELD_ROW_PAIRS = [
    ["Full Name", "Email Id"],
    ["Phone Number", "Alternative Number"],
    ["Location / address", "Portfolio link"],
    ["Degree type", "Field of study"],
    ["Institution name", "Years of experience"],
    ["Current/past job titles", "Company names"],
    ["Current LPA", "Notice Period"],
    ["Technical skills", "Soft skills"],
    ["Certifications / licenses", null],
    ["LinkedIn", "GitHub"],
    ["LeetCode", "Codeforces"],
    ["HackerRank", "Kaggle"],
    ["Stack Overflow", "Medium"],
];

export const APPLICATION_SECTIONS = [
    { title: "Personal Info", fields: ["Full Name", "Email Id", "Phone Number", "Alternative Number", "Location / address"] },
    { title: "Education", fields: ["Degree type", "Field of study", "Institution name"] },
    { title: "Experience", fields: ["Years of experience", "Current/past job titles", "Company names", "Current LPA", "Notice Period"] },
    { title: "Skills", fields: ["Technical skills", "Soft skills", "Certifications / licenses"] },
    { title: "Links & Profiles", fields: ["LinkedIn", "GitHub", "LeetCode", "Codeforces", "HackerRank", "Kaggle", "Stack Overflow", "Medium", "Portfolio link"] },
];

/** Parse `application_fields`: legacy CSV (all required) vs `Name!` / `Name?` format. */
export function parseApplicationFieldTokens(raw) {
    const parts = String(raw ?? "")
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);

    if (parts.length === 0) {
        return {
            mandatory: [...DEFAULT_APPLICATION_FIELDS],
            optional: [],
            allFields: [...DEFAULT_APPLICATION_FIELDS],
        };
    }

    const newFormat = parts.some((p) => p.endsWith("!") || p.endsWith("?"));
    if (!newFormat) {
        return { mandatory: parts, optional: [], allFields: parts };
    }

    const mandatory = [];
    const optional = [];
    for (const p of parts) {
        if (p.endsWith("!")) mandatory.push(p.slice(0, -1).trim());
        else if (p.endsWith("?")) optional.push(p.slice(0, -1).trim());
        else optional.push(p.trim());
    }
    return { mandatory, optional, allFields: [...mandatory, ...optional] };
}

/** Fields in HR-configured order (matches Application Setup step). */
export function orderDisplayFields(allFields) {
    const set = new Set(allFields);
    const ordered = APP_FIELD_ORDER.filter((f) => set.has(f));
    for (const f of allFields) {
        if (!APP_FIELD_ORDER.includes(f)) ordered.push(f);
    }
    return ordered;
}

/** Group ordered fields into sections for the apply form UI. */
export function groupFieldsForDisplay(orderedFields) {
    const remaining = new Set(orderedFields.filter((f) => !UPLOAD_FIELD_LABELS.has(f)));
    const groups = [];

    for (const sec of APPLICATION_SECTIONS) {
        const fields = sec.fields.filter((f) => remaining.has(f));
        if (fields.length) {
            groups.push({ title: sec.title, fields });
            fields.forEach((f) => remaining.delete(f));
        }
    }

    if (remaining.size > 0) {
        groups.push({
            title: "Additional Info",
            fields: orderedFields.filter((f) => remaining.has(f)),
        });
    }

    return groups;
}

/** Split section fields into rows of 1–2 columns (e.g. name | email). */
export function chunkFieldsIntoRows(fields) {
    const remaining = new Set(fields);
    const rows = [];

    for (const [left, right] of FIELD_ROW_PAIRS) {
        const hasLeft = left && remaining.has(left);
        const hasRight = right && remaining.has(right);
        if (!hasLeft && !hasRight) continue;
        const row = [];
        if (hasLeft) {
            row.push(left);
            remaining.delete(left);
        }
        if (hasRight) {
            row.push(right);
            remaining.delete(right);
        }
        if (row.length) rows.push(row);
    }

    for (const f of fields) {
        if (remaining.has(f)) rows.push([f]);
    }
    return rows;
}
