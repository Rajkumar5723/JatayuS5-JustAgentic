import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { MAIN_API as API } from "../../shared/api.js";

const DOCUMENT_GROUPS = [
    {
        title: "Identity",
        items: [
            { key: "selfie", label: "Selfie", required: true, accept: "image/*", capture: "user" },
            { key: "aadhaar", label: "Aadhaar", required: true, accept: ".png,.jpg,.jpeg,.pdf" },
            { key: "pan", label: "PAN Card", required: false, accept: ".png,.jpg,.jpeg,.pdf" },
        ],
    },
    {
        title: "Education",
        items: [
            { key: "ug_marksheet", label: "UG Marksheet", required: true, accept: ".png,.jpg,.jpeg,.pdf" },
            { key: "pg_marksheet", label: "PG Marksheet", required: false, accept: ".png,.jpg,.jpeg,.pdf" },
            { key: "marksheet_10", label: "10th Marksheet", required: true, accept: ".png,.jpg,.jpeg,.pdf" },
            { key: "marksheet_12", label: "12th Marksheet", required: true, accept: ".png,.jpg,.jpeg,.pdf" },
        ],
    },
    {
        title: "Travel",
        items: [
            { key: "passport", label: "Passport", required: false, accept: ".png,.jpg,.jpeg,.pdf" },
        ],
    },
];

function statusTone(status) {
    return {
        pending_candidate: "#ff8b4a",
        submitted: "#ff8b4a",
        bgv_review: "#ff8b4a",
        accepted: "#1f8f4b",
        rejected: "#d10f35",
        hold: "#7a5c00",
    }[status] || "#555";
}

export default function VerificationPage() {
    const { token } = useParams();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState("");
    const [caseData, setCaseData] = useState(null);
    const [files, setFiles] = useState({});
    const [form, setForm] = useState({
        full_name: "",
        address: "",
        city: "",
        state: "",
        pincode: "",
        pan_number: "",
        aadhaar_number: "",
    });

    useEffect(() => {
        fetch(`${API}/verification/${token}`)
            .then((r) => r.json())
            .then((data) => {
                setCaseData(data);
                setForm((prev) => ({
                    ...prev,
                    full_name: data.typed_full_name || data.candidate_name || "",
                    address: data.typed_address || "",
                    city: data.typed_city || "",
                    state: data.typed_state || "",
                    pincode: data.typed_pincode || "",
                    pan_number: data.typed_pan || "",
                    aadhaar_number: data.typed_aadhaar || "",
                }));
            })
            .catch(() => setMessage("Could not load verification request."))
            .finally(() => setLoading(false));
    }, [token]);

    const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));
    const setFile = (key, file) => setFiles((prev) => ({ ...prev, [key]: file }));

    const requiredMissing = useMemo(() => {
        const missing = [];
        if (!form.full_name.trim()) missing.push("Full Name");
        if (!form.address.trim()) missing.push("Address");
        if (!form.city.trim()) missing.push("City");
        if (!form.state.trim()) missing.push("State");
        if (!form.pincode.trim()) missing.push("Pincode");
        if (!form.aadhaar_number.trim()) missing.push("Aadhaar Number");
        DOCUMENT_GROUPS.flatMap((group) => group.items)
            .filter((item) => item.required)
            .forEach((item) => {
                if (!files[item.key] && !(caseData?.document_items || []).find((row) => row.document_type === item.key)) {
                    missing.push(item.label);
                }
            });
        return missing;
    }, [form, files, caseData]);

    const submit = async () => {
        if (requiredMissing.length) {
            setMessage(`Please complete the required fields: ${requiredMissing.join(", ")}`);
            return;
        }
        setSaving(true);
        setMessage("");
        try {
            const formData = new FormData();
            Object.entries(form).forEach(([key, value]) => formData.append(key, value));
            Object.entries(files).forEach(([key, file]) => {
                if (file) formData.append(`${key}_file`, file);
            });
            const res = await fetch(`${API}/verification/${token}/submit`, {
                method: "POST",
                body: formData,
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Submission failed");
            setCaseData(data);
            setMessage("Verification submitted. Our team will review it now.");
        } catch (err) {
            setMessage(err.message || "Submission failed.");
        } finally {
            setSaving(false);
        }
    };

    if (loading) {
        return <main style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>Loading verification...</main>;
    }

    if (!caseData) {
        return <main style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>{message || "Verification case not found."}</main>;
    }

    const tone = statusTone(caseData.status);
    const uploadedDocs = caseData.document_items || [];

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "linear-gradient(180deg, #faf7f3 0%, #f2ece6 100%)",
                padding: "32px 16px",
                fontFamily: "'Segoe UI', sans-serif",
            }}
        >
            <div style={{ maxWidth: 980, margin: "0 auto", display: "grid", gap: 20 }}>
                <section
                    style={{
                        background: "#101010",
                        color: "#fff",
                        borderRadius: 24,
                        padding: 28,
                        boxShadow: "0 18px 50px rgba(0,0,0,0.14)",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                        <div>
                            <p style={{ margin: 0, color: "#ff8b4a", letterSpacing: 1.5, textTransform: "uppercase", fontSize: 12 }}>Hiresy Verification</p>
                            <h1 style={{ margin: "10px 0 8px", fontSize: 34 }}>{caseData.job_title}</h1>
                            <p style={{ margin: 0, color: "#d3d3d3", maxWidth: 640 }}>
                                Complete the final background verification for {caseData.candidate_name}. Required:
                                selfie, Aadhaar, UG marksheet, 10th marksheet, and 12th marksheet. PAN, PG marksheet,
                                and passport are optional.
                            </p>
                        </div>
                        <span
                            style={{
                                alignSelf: "flex-start",
                                padding: "8px 14px",
                                borderRadius: 999,
                                background: `${tone}22`,
                                color: tone,
                                border: `1px solid ${tone}`,
                                fontSize: 12,
                                textTransform: "uppercase",
                                letterSpacing: 1.2,
                            }}
                        >
                            {caseData.status.replaceAll("_", " ")}
                        </span>
                    </div>
                </section>

                <section
                    style={{
                        background: "#fff",
                        borderRadius: 24,
                        padding: 28,
                        boxShadow: "0 18px 40px rgba(0,0,0,0.08)",
                        display: "grid",
                        gap: 18,
                    }}
                >
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
                        <label style={{ display: "grid", gap: 8 }}>
                            <span>Full Name *</span>
                            <input value={form.full_name} onChange={(e) => set("full_name", e.target.value)} style={{ padding: 12, borderRadius: 12, border: "1px solid #ddd" }} />
                        </label>
                        <label style={{ display: "grid", gap: 8 }}>
                            <span>Aadhaar Number *</span>
                            <input value={form.aadhaar_number} onChange={(e) => set("aadhaar_number", e.target.value)} style={{ padding: 12, borderRadius: 12, border: "1px solid #ddd" }} />
                        </label>
                        <label style={{ display: "grid", gap: 8 }}>
                            <span>PAN Number</span>
                            <input value={form.pan_number} onChange={(e) => set("pan_number", e.target.value.toUpperCase())} style={{ padding: 12, borderRadius: 12, border: "1px solid #ddd" }} />
                        </label>
                    </div>

                    <label style={{ display: "grid", gap: 8 }}>
                        <span>Current Address *</span>
                        <textarea value={form.address} onChange={(e) => set("address", e.target.value)} rows={4} style={{ padding: 12, borderRadius: 12, border: "1px solid #ddd", resize: "vertical" }} />
                    </label>

                    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(180px,1fr))", gap: 16 }}>
                        <label style={{ display: "grid", gap: 8 }}>
                            <span>City *</span>
                            <input value={form.city} onChange={(e) => set("city", e.target.value)} style={{ padding: 12, borderRadius: 12, border: "1px solid #ddd" }} />
                        </label>
                        <label style={{ display: "grid", gap: 8 }}>
                            <span>State *</span>
                            <input value={form.state} onChange={(e) => set("state", e.target.value)} style={{ padding: 12, borderRadius: 12, border: "1px solid #ddd" }} />
                        </label>
                        <label style={{ display: "grid", gap: 8 }}>
                            <span>Pincode *</span>
                            <input value={form.pincode} onChange={(e) => set("pincode", e.target.value)} style={{ padding: 12, borderRadius: 12, border: "1px solid #ddd" }} />
                        </label>
                    </div>

                    {DOCUMENT_GROUPS.map((group) => (
                        <div key={group.title} style={{ display: "grid", gap: 10 }}>
                            <strong style={{ color: "#222" }}>{group.title}</strong>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(220px,1fr))", gap: 16 }}>
                                {group.items.map((item) => {
                                    const uploaded = uploadedDocs.find((row) => row.document_type === item.key);
                                    return (
                                        <label key={item.key} style={{ display: "grid", gap: 8, padding: 14, borderRadius: 14, border: "1px solid #ececec" }}>
                                            <span>{item.label}{item.required ? " *" : " (Optional)"}</span>
                                            <input
                                                type="file"
                                                accept={item.accept}
                                                capture={item.capture}
                                                onChange={(e) => setFile(item.key, e.target.files?.[0] || null)}
                                            />
                                            <small style={{ color: "#777" }}>
                                                {files[item.key]?.name || uploaded?.filename || "No file selected"}
                                            </small>
                                            {uploaded ? (
                                                <small style={{ color: "#3b5bdb" }}>
                                                    OCR: {uploaded.ocr_status || "pending"} | Review: {uploaded.verification_status || "pending"}
                                                </small>
                                            ) : null}
                                        </label>
                                    );
                                })}
                            </div>
                        </div>
                    ))}

                    <button
                        onClick={submit}
                        disabled={saving || caseData.status === "accepted" || caseData.status === "rejected"}
                        style={{
                            width: "fit-content",
                            padding: "14px 24px",
                            borderRadius: 999,
                            border: "none",
                            background: "#111",
                            color: "#fff",
                            fontWeight: 700,
                            cursor: "pointer",
                        }}
                    >
                        {saving ? "Submitting..." : "Submit Verification"}
                    </button>

                    {message ? <p style={{ margin: 0, color: "#b34c00" }}>{message}</p> : null}

                    {uploadedDocs.length ? (
                        <div style={{ background: "#f7f7f7", borderRadius: 16, padding: 16, display: "grid", gap: 10 }}>
                            <strong>Uploaded Documents & OCR</strong>
                            {uploadedDocs.map((item) => (
                                <div key={item.id} style={{ display: "grid", gap: 4, padding: 12, borderRadius: 12, background: "#fff" }}>
                                    <span>{item.filename}</span>
                                    <small style={{ color: "#555" }}>{item.document_type.replaceAll("_", " ")} · OCR {item.ocr_status} · {item.verification_status}</small>
                                    {Object.keys(item.ocr_fields || {}).length ? (
                                        <small style={{ color: "#555" }}>
                                            {Object.entries(item.ocr_fields).map(([key, value]) => `${key}: ${value || "n/a"}`).join(" | ")}
                                        </small>
                                    ) : null}
                                </div>
                            ))}
                        </div>
                    ) : null}

                    {caseData.review_summary ? (
                        <div style={{ background: "#f7f7f7", borderRadius: 16, padding: 16 }}>
                            <strong>Latest Review Summary</strong>
                            <p style={{ margin: "8px 0 0", color: "#555" }}>{caseData.review_summary}</p>
                        </div>
                    ) : null}
                </section>
            </div>
        </main>
    );
}
