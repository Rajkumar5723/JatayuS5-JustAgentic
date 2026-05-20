import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import "./OfferPortal.css";
import { MAIN_API as API } from "../../shared/api.js";

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

function InfoRow({ label, value }) {
    return (
        <div className="offer-info-row">
            <span>{label}</span>
            <strong>{value || "Not captured"}</strong>
        </div>
    );
}

export default function OfferPortal() {
    const { token } = useParams();
    const canvasRef = useRef(null);
    const drawingRef = useRef(false);
    const lastPointRef = useRef({ x: 0, y: 0 });

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [offer, setOffer] = useState(null);
    const [decision, setDecision] = useState("accepted");
    const [remarks, setRemarks] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [signatureDataUrl, setSignatureDataUrl] = useState("");
    const [signatureFilename, setSignatureFilename] = useState("signature.png");

    const fetchOffer = async () => {
        setLoading(true);
        setError("");
        try {
            const res = await fetch(`${API}/offer-letter/${token}`);
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to load offer");
            setOffer(data);
            setDecision(data.candidate_response === "rejected" ? "rejected" : "accepted");
            setRemarks(data.candidate_remarks || "");
        } catch (err) {
            setError(err.message || "Failed to load offer");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOffer();
    }, [token]);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        ctx.strokeStyle = "#111111";
        ctx.lineWidth = 2.25;
        ctx.lineJoin = "round";
        ctx.lineCap = "round";
    }, [offer]);

    const toCanvasPoint = (event) => {
        const canvas = canvasRef.current;
        const rect = canvas.getBoundingClientRect();
        const source = event.touches?.[0] || event;
        return {
            x: ((source.clientX - rect.left) / rect.width) * canvas.width,
            y: ((source.clientY - rect.top) / rect.height) * canvas.height,
        };
    };

    const startDraw = (event) => {
        drawingRef.current = true;
        lastPointRef.current = toCanvasPoint(event);
    };

    const draw = (event) => {
        if (!drawingRef.current || !canvasRef.current) return;
        event.preventDefault?.();
        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        const point = toCanvasPoint(event);
        ctx.beginPath();
        ctx.moveTo(lastPointRef.current.x, lastPointRef.current.y);
        ctx.lineTo(point.x, point.y);
        ctx.stroke();
        lastPointRef.current = point;
        setSignatureDataUrl(canvas.toDataURL("image/png"));
        setSignatureFilename("signature-drawn.png");
    };

    const stopDraw = () => {
        drawingRef.current = false;
    };

    const clearSignature = () => {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = "#ffffff";
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        setSignatureDataUrl("");
        setSignatureFilename("signature.png");
    };

    const handleUpload = (event) => {
        const file = event.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = () => {
            setSignatureDataUrl(String(reader.result || ""));
            setSignatureFilename(file.name);
        };
        reader.readAsDataURL(file);
    };

    const submitResponse = async () => {
        if (decision === "accepted" && !signatureDataUrl) {
            setError("A signature is required to accept the offer.");
            return;
        }
        setSubmitting(true);
        setError("");
        try {
            const res = await fetch(`${API}/offer-letter/${token}/respond`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    decision,
                    remarks,
                    signature_data_url: decision === "accepted" ? signatureDataUrl : "",
                    signature_filename: signatureFilename,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to submit response");
            setOffer(data);
        } catch (err) {
            setError(err.message || "Failed to submit response");
        } finally {
            setSubmitting(false);
        }
    };

    if (loading) {
        return (
            <main className="offer-page">
                <div className="offer-state-card">Loading offer details...</div>
            </main>
        );
    }

    if (error && !offer) {
        return (
            <main className="offer-page">
                <div className="offer-state-card">
                    <h1>Offer Portal Unavailable</h1>
                    <p>{error}</p>
                </div>
            </main>
        );
    }

    if (!offer) return null;

    const expired = offer.expired;
    const completed = offer.candidate_response === "accepted" || offer.candidate_response === "rejected";
    const previewUrl = offer.signed_preview_url || offer.preview_url;

    return (
        <main className="offer-page">
            <section className="offer-hero">
                <p className="offer-kicker">Hiresy Offer Portal</p>
                <h1>{offer.job_title}</h1>
                <p>{offer.candidate_name}, review your offer details, confirm your decision, and submit your signature securely.</p>
                <div className="offer-chip-row">
                    <span className="offer-chip">{offer.status || "Pending"}</span>
                    <span className="offer-chip">Expires {formatDateTime(offer.candidate_portal_expires_at)}</span>
                </div>
            </section>

            {error ? <div className="offer-inline-error">{error}</div> : null}

            <section className="offer-grid">
                <div className="offer-card offer-card-large">
                    <div className="offer-card-head">
                        <div>
                            <p className="offer-section-label">Offer Preview</p>
                            <p className="offer-copy">Review the latest generated PDF before you respond.</p>
                        </div>
                        <a className="offer-btn offer-btn-light" href={offer.download_url} target="_blank" rel="noreferrer">
                            Download PDF
                        </a>
                    </div>
                    <div className="offer-preview-shell">
                        {previewUrl ? (
                            <iframe title="Offer preview" src={previewUrl} className="offer-preview-frame" />
                        ) : (
                            <div className="offer-empty">The PDF preview is not available yet.</div>
                        )}
                    </div>
                </div>

                <div className="offer-stack">
                    <div className="offer-card">
                        <p className="offer-section-label">Joining Details</p>
                        <InfoRow label="Candidate" value={offer.candidate_name} />
                        <InfoRow label="Email" value={offer.candidate_email} />
                        <InfoRow label="Role" value={offer.designation || offer.job_title} />
                        <InfoRow label="Department" value={offer.department} />
                        <InfoRow label="Employment Type" value={offer.employment_type} />
                        <InfoRow label="Joining Date" value={offer.joining_date} />
                        <InfoRow label="Offer Valid Until" value={offer.offer_valid_until} />
                        <InfoRow label="Work Mode" value={offer.work_mode} />
                        <InfoRow label="Work Location" value={offer.work_location || offer.job_location} />
                        <InfoRow label="Reporting Manager" value={offer.reporting_manager} />
                        <InfoRow label="Reporting Team" value={offer.reporting_team} />
                        <InfoRow label="Compensation" value={offer.offered_compensation || offer.compensation_text} />
                        <InfoRow label="Contract Notes" value={offer.contract_duration_or_notes} />
                    </div>

                    <div className="offer-card">
                        <p className="offer-section-label">Instructions & Terms</p>
                        <p className="offer-copy">{offer.onboarding_instructions || "No onboarding instructions provided."}</p>
                        <p className="offer-copy">{offer.hr_contact_details || "No HR contact details provided."}</p>
                        <p className="offer-copy">{offer.company_details || "No company details provided."}</p>
                        <p className="offer-copy">{offer.terms_and_conditions || "Terms will appear here once captured."}</p>
                    </div>
                </div>
            </section>

            <section className="offer-card">
                <div className="offer-card-head">
                    <div>
                        <p className="offer-section-label">Candidate Response</p>
                        <p className="offer-copy">Accept or reject the offer. A digital signature is required only if you accept.</p>
                    </div>
                </div>

                {expired && !completed ? (
                    <div className="offer-inline-error">This secure offer link has expired. Please contact HR for a refreshed link.</div>
                ) : null}

                <div className="offer-response-grid">
                    <label className={`offer-choice ${decision === "accepted" ? "active" : ""}`}>
                        <input type="radio" checked={decision === "accepted"} onChange={() => setDecision("accepted")} disabled={completed || expired} />
                        <div>
                            <strong>Accept Offer</strong>
                            <p>Proceed with the role and submit your signature.</p>
                        </div>
                    </label>
                    <label className={`offer-choice ${decision === "rejected" ? "active" : ""}`}>
                        <input type="radio" checked={decision === "rejected"} onChange={() => setDecision("rejected")} disabled={completed || expired} />
                        <div>
                            <strong>Reject Offer</strong>
                            <p>Decline the offer and optionally share your reason.</p>
                        </div>
                    </label>
                </div>

                <label className="offer-field">
                    Remarks
                    <textarea
                        value={remarks}
                        onChange={(e) => setRemarks(e.target.value)}
                        placeholder="Share any comments or clarifications for HR"
                        disabled={completed || expired}
                    />
                </label>

                {decision === "accepted" && !completed && !expired ? (
                    <div className="offer-sign-grid">
                        <div className="offer-sign-card">
                            <div className="offer-sign-head">
                                <strong>Draw Signature</strong>
                                <button type="button" className="offer-btn offer-btn-light" onClick={clearSignature}>
                                    Clear
                                </button>
                            </div>
                            <canvas
                                ref={canvasRef}
                                width={680}
                                height={220}
                                className="offer-sign-canvas"
                                onMouseDown={startDraw}
                                onMouseMove={draw}
                                onMouseUp={stopDraw}
                                onMouseLeave={stopDraw}
                                onTouchStart={startDraw}
                                onTouchMove={draw}
                                onTouchEnd={stopDraw}
                            />
                        </div>

                        <div className="offer-sign-card">
                            <div className="offer-sign-head">
                                <strong>Upload Signature</strong>
                            </div>
                            <label className="offer-upload">
                                <input type="file" accept="image/*" onChange={handleUpload} disabled={completed || expired} />
                                <span>Choose an image file</span>
                            </label>
                            <p className="offer-copy">You can either draw directly above or upload an existing signature image.</p>
                            {signatureDataUrl ? (
                                <div className="offer-sign-preview">
                                    <img src={signatureDataUrl} alt="Signature preview" />
                                </div>
                            ) : (
                                <div className="offer-empty">No signature captured yet.</div>
                            )}
                        </div>
                    </div>
                ) : null}

                <div className="offer-action-row">
                    <button
                        type="button"
                        className="offer-btn offer-btn-primary"
                        onClick={submitResponse}
                        disabled={completed || expired || submitting}
                    >
                        {submitting ? "Submitting..." : decision === "accepted" ? "Accept & Sign Offer" : "Reject Offer"}
                    </button>
                    {completed ? (
                        <a className="offer-btn offer-btn-light" href={offer.download_url} target="_blank" rel="noreferrer">
                            Download Latest PDF
                        </a>
                    ) : null}
                </div>

                {completed ? (
                    <div className="offer-confirmation">
                        <strong>{offer.candidate_response === "accepted" ? "Offer accepted" : "Offer rejected"}</strong>
                        <p>
                            Response recorded on {formatDateTime(offer.candidate_response_at)}.
                            {offer.candidate_remarks ? ` HR note: ${offer.candidate_remarks}` : ""}
                        </p>
                    </div>
                ) : null}
            </section>
        </main>
    );
}
