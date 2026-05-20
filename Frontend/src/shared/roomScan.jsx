import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { MAIN_API } from "./api.js";

const PROCTORING_API = `${MAIN_API}/proctoring`;
const ACCEPTED_VERDICTS = new Set(["pass", "warning"]);
const CAPTURE_FRAME_COUNT = 6;
const CAPTURE_INTERVAL_MS = 800;

async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    const raw = await res.text();
    let data = {};
    if (raw) {
        try {
            data = JSON.parse(raw);
        } catch {
            data = { raw };
        }
    }
    if (!res.ok) {
        throw new Error(
            data.detail ||
                data.message ||
                data.raw ||
                `Request failed (${res.status}).`,
        );
    }
    return data;
}

function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function verdictTone(verdict) {
    if (verdict === "pass") return { color: "#1f8f4b", bg: "#1f8f4b14", label: "Ready" };
    if (verdict === "warning") return { color: "#9b6a00", bg: "#9b6a0014", label: "Ready With Warning" };
    if (verdict === "fail") return { color: "#c43333", bg: "#c4333314", label: "Scan Failed" };
    return { color: "#4f5d75", bg: "#4f5d7514", label: "Pending" };
}

function captureVideoFrame(videoEl, index) {
    return new Promise((resolve, reject) => {
        if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) {
            reject(new Error("Camera preview is not ready yet."));
            return;
        }

        const canvas = document.createElement("canvas");
        canvas.width = Math.min(960, videoEl.videoWidth);
        canvas.height = Math.round((canvas.width / videoEl.videoWidth) * videoEl.videoHeight);

        const ctx = canvas.getContext("2d");
        ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

        canvas.toBlob(
            (blob) => {
                if (!blob) {
                    reject(new Error("Could not capture a room scan frame."));
                    return;
                }
                resolve(new File([blob], `room-scan-${index + 1}.jpg`, { type: "image/jpeg" }));
            },
            "image/jpeg",
            0.86,
        );
    });
}

async function uploadRoomFrames(sessionToken, scanType, qrToken, files) {
    const formData = new FormData();
    files.forEach((file, index) => {
        formData.append("files", file, file.name || `room-scan-${index + 1}.jpg`);
    });

    return fetchJson(
        `${PROCTORING_API}/360/upload?session_token=${encodeURIComponent(sessionToken)}&scan_type=${encodeURIComponent(scanType)}&qr_token=${encodeURIComponent(qrToken)}`,
        {
            method: "POST",
            body: formData,
        },
    );
}

export function RoomScanGate({ sessionToken, scanType = "initial", onReadyChange }) {
    const [qrData, setQrData] = useState(null);
    const [status, setStatus] = useState({ scan_exists: false, scan_type: scanType });
    const [loadingQr, setLoadingQr] = useState(false);
    const [qrError, setQrError] = useState("");
    const [statusError, setStatusError] = useState("");

    const ready =
        status?.scan_exists &&
        status?.scan_status === "completed" &&
        ACCEPTED_VERDICTS.has((status?.verdict || "").toLowerCase());

    const tone = verdictTone(status?.verdict);
    useEffect(() => {
        onReadyChange?.(ready, status);
    }, [onReadyChange, ready, status]);

    const loadStatus = useCallback(async () => {
        if (!sessionToken) return;
        try {
            const data = await fetchJson(
                `${PROCTORING_API}/360/status/${encodeURIComponent(sessionToken)}?scan_type=${encodeURIComponent(scanType)}`,
            );
            setStatus(data);
            setStatusError("");
        } catch (err) {
            setStatusError(err.message || "Could not load room scan status.");
        }
    }, [scanType, sessionToken]);

    const loadQr = useCallback(async () => {
        if (!sessionToken) return;
        setLoadingQr(true);
        setQrError("");
        try {
            const data = await fetchJson(`${PROCTORING_API}/qr/generate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    session_token: sessionToken,
                    verification_type: scanType,
                }),
            });
            setQrData(data);
        } catch (err) {
            setQrError(err.message || "Could not generate QR code.");
        } finally {
            setLoadingQr(false);
        }
    }, [scanType, sessionToken]);

    useEffect(() => {
        setQrData(null);
        setStatus({ scan_exists: false, scan_type: scanType });
        setQrError("");
        setStatusError("");
        if (!sessionToken) return;
        loadStatus();
        loadQr();
    }, [loadQr, loadStatus, scanType, sessionToken]);

    useEffect(() => {
        if (!sessionToken || ready) return undefined;
        const timer = window.setInterval(() => {
            loadStatus();
        }, 3000);
        return () => window.clearInterval(timer);
    }, [loadStatus, ready, sessionToken]);

    return (
        <section
            style={{
                marginTop: 22,
                background: "#fff",
                border: "1px solid rgba(17,17,17,0.08)",
                borderRadius: 24,
                padding: 22,
                boxShadow: "0 16px 40px rgba(17,17,17,0.08)",
                display: "grid",
                gap: 18,
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                <div>
                    <p style={{ margin: 0, fontSize: 12, textTransform: "uppercase", letterSpacing: 1.4, color: "#ff6a1a" }}>
                        Room Scan Protection
                    </p>
                    <h3 style={{ margin: "8px 0 6px", fontSize: 24, color: "#111" }}>
                        Scan your room before the test starts
                    </h3>
                    <p style={{ margin: 0, color: "#5a5f66", lineHeight: 1.6, maxWidth: 620 }}>
                        Use the QR code to open the 360 room scan page on your phone. The test starts only after the mobile room
                        scan is completed and verified.
                    </p>
                </div>
                <span
                    style={{
                        alignSelf: "flex-start",
                        padding: "9px 14px",
                        borderRadius: 999,
                        background: tone.bg,
                        color: tone.color,
                        fontSize: 12,
                        fontWeight: 700,
                        letterSpacing: 0.6,
                        textTransform: "uppercase",
                    }}
                >
                    {ready ? tone.label : tone.label}
                </span>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
                    gap: 18,
                    alignItems: "start",
                }}
            >
                <div
                    style={{
                        minHeight: 264,
                        borderRadius: 20,
                        border: "1px dashed rgba(17,17,17,0.14)",
                        background: "#fbf8f5",
                        display: "grid",
                        placeItems: "center",
                        padding: 18,
                    }}
                >
                    {loadingQr ? (
                        <p style={{ margin: 0, color: "#5a5f66" }}>Generating QR code...</p>
                    ) : qrData?.qr_code ? (
                        <img
                            src={qrData.qr_code}
                            alt="Room scan QR code"
                            style={{ width: "100%", maxWidth: 220, borderRadius: 16, background: "#fff", padding: 12 }}
                        />
                    ) : (
                        <p style={{ margin: 0, color: "#5a5f66", textAlign: "center", lineHeight: 1.6 }}>
                            {qrError || "QR code will appear here."}
                        </p>
                    )}
                </div>

                <div style={{ display: "grid", gap: 12 }}>
                    <div style={{ display: "grid", gap: 8, color: "#23262b" }}>
                        <div>1. Scan the QR code with your phone camera.</div>
                        <div>2. Allow camera access and rotate slowly so all sides of the room are captured.</div>
                        <div>3. Return here after the scan finishes. This page checks the result automatically.</div>
                    </div>

                    <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                        <button
                            type="button"
                            onClick={loadQr}
                            style={{
                                border: "none",
                                borderRadius: 999,
                                padding: "12px 18px",
                                background: "#111",
                                color: "#fff",
                                fontWeight: 700,
                                cursor: "pointer",
                            }}
                        >
                            {loadingQr ? "Refreshing..." : "Refresh QR"}
                        </button>
                    </div>

                    {status?.scan_exists ? (
                        <div
                            style={{
                                borderRadius: 16,
                                padding: 14,
                                background: tone.bg,
                                color: tone.color,
                                lineHeight: 1.6,
                            }}
                        >
                            <strong style={{ display: "block", marginBottom: 4 }}>
                                Latest status: {(status.scan_status || "pending").replaceAll("_", " ")}
                            </strong>
                            <div>Verdict: {(status.verdict || "pending").replaceAll("_", " ")}</div>
                            {status.completed_at ? <div>Completed at: {new Date(status.completed_at).toLocaleString()}</div> : null}
                        </div>
                    ) : (
                        <div style={{ borderRadius: 16, padding: 14, background: "#f7f3ee", color: "#5a5f66", lineHeight: 1.6 }}>
                            No initial room scan has been submitted yet.
                        </div>
                    )}

                    {status?.verdict === "fail" ? (
                        <div style={{ color: "#b33a3a", lineHeight: 1.6 }}>
                            The last room scan was rejected. Remove extra devices or other suspicious items, then scan again.
                        </div>
                    ) : null}

                    {statusError ? <div style={{ color: "#b33a3a" }}>{statusError}</div> : null}
                    {qrError && !qrData?.qr_code ? <div style={{ color: "#b33a3a" }}>{qrError}</div> : null}
                </div>
            </div>
        </section>
    );
}

export function RoomScanMobilePage() {
    const [searchParams] = useSearchParams();
    const token = searchParams.get("token");
    const videoRef = useRef(null);
    const streamRef = useRef(null);

    const [sessionInfo, setSessionInfo] = useState(null);
    const [stage, setStage] = useState("validating");
    const [message, setMessage] = useState("Validating QR code...");
    const [cameraError, setCameraError] = useState("");
    const [captureStep, setCaptureStep] = useState(0);
    const [report, setReport] = useState(null);
    const cameraActive = Boolean(sessionInfo?.session_token) && (stage === "ready" || stage === "capturing");

    const stopCamera = () => {
        if (streamRef.current) {
            streamRef.current.getTracks().forEach((track) => track.stop());
            streamRef.current = null;
        }
    };

    const startCamera = useCallback(async () => {
        if (!navigator.mediaDevices?.getUserMedia) {
            setCameraError("Live mobile camera capture is not available in this browser. Open the scan link on a phone browser with camera access.");
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: { ideal: "environment" },
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                },
                audio: false,
            });
            streamRef.current = stream;
            if (videoRef.current) {
                videoRef.current.srcObject = stream;
                await videoRef.current.play().catch(() => {});
            }
            setCameraError("");
        } catch {
            setCameraError("Camera access was blocked on this device. Allow camera access on your phone browser, then refresh the QR and scan again.");
        }
    }, []);

    useEffect(() => {
        let cancelled = false;

        const validate = async () => {
            if (!token) {
                setStage("error");
                setMessage("Missing QR token. Open the page again from a fresh QR code.");
                return;
            }

            try {
                const data = await fetchJson(`${PROCTORING_API}/qr/validate`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ token }),
                });

                if (cancelled) return;

                if (!data.valid) {
                    setStage("error");
                    if (data.error === "JWT_EXPIRED") {
                        setMessage("This QR code expired. Go back to the test page and tap Refresh QR, then scan again.");
                    } else {
                        setMessage(data.message || "This QR code is no longer valid.");
                    }
                    return;
                }

                setSessionInfo({ ...data, qr_token: token });
                setStage("ready");
                setMessage("Stand in one place, rotate the phone slowly, and show all sides of the room before returning to the test tab.");
            } catch (err) {
                if (cancelled) return;
                setStage("error");
                setMessage(err.message || "Could not validate the QR code.");
            }
        };

        validate();

        return () => {
            cancelled = true;
        };
    }, [token]);

    useEffect(() => {
        if (!cameraActive) return undefined;
        const timer = window.setTimeout(() => {
            void startCamera();
        }, 0);
        return () => {
            window.clearTimeout(timer);
            stopCamera();
        };
    }, [cameraActive, startCamera]);

    const finalizeUpload = async (files) => {
        if (!sessionInfo?.session_token) return;
        setStage("uploading");
        setMessage("Uploading room scan for analysis...");
        try {
            const data = await uploadRoomFrames(
                sessionInfo.session_token,
                sessionInfo.verification_type || "initial",
                sessionInfo.qr_token,
                files,
            );
            stopCamera();
            setReport(data.report);
            setStage("done");
            if (data.report?.verdict === "fail") {
                setMessage("Room scan failed. Remove suspicious items and scan again.");
            } else if (data.report?.verdict === "warning") {
                setMessage("Room scan submitted with a warning. You can return to the test tab now.");
            } else {
                setMessage("Room scan completed successfully. Return to the test tab and start the test.");
            }
        } catch (err) {
            setStage("ready");
            setMessage(err.message || "Room scan upload failed.");
        }
    };

    const handleLiveCapture = async () => {
        if (!streamRef.current || !videoRef.current) {
            setMessage("Camera preview is not ready yet. Allow camera access and wait a moment, then try again.");
            return;
        }

        setStage("capturing");
        setMessage("Capturing the room. Keep the camera facing outward and rotate slowly across every side.");

        try {
            const frames = [];
            for (let index = 0; index < CAPTURE_FRAME_COUNT; index += 1) {
                setCaptureStep(index + 1);
                const frame = await captureVideoFrame(videoRef.current, index);
                frames.push(frame);
                await delay(CAPTURE_INTERVAL_MS);
            }
            await finalizeUpload(frames);
        } catch (err) {
            setStage("ready");
            setMessage(err.message || "Could not capture the room scan.");
        }
    };

    const resetForRetry = () => {
        setReport(null);
        setCaptureStep(0);
        setStage("ready");
        setMessage("Stand in one place, rotate the phone slowly, and show all sides of the room before returning to the test tab.");
    };

    const tone = verdictTone(report?.verdict);

    return (
        <main
            style={{
                minHeight: "100vh",
                background: "linear-gradient(180deg, #0f141a 0%, #17232d 100%)",
                color: "#fff",
                padding: "20px 14px 40px",
                fontFamily: "'Segoe UI', sans-serif",
            }}
        >
            <div style={{ maxWidth: 760, margin: "0 auto", display: "grid", gap: 18 }}>
                <section
                    style={{
                        background: "rgba(255,255,255,0.06)",
                        border: "1px solid rgba(255,255,255,0.08)",
                        borderRadius: 24,
                        padding: 22,
                        backdropFilter: "blur(12px)",
                    }}
                >
                    <p style={{ margin: 0, fontSize: 12, textTransform: "uppercase", letterSpacing: 1.4, color: "#ff8b4a" }}>
                        Hiresy Room Scan
                    </p>
                    <h1 style={{ margin: "10px 0 8px", fontSize: 30 }}>360 room scan before test</h1>
                    <p style={{ margin: 0, color: "#cfd7df", lineHeight: 1.6 }}>
                        Capture the room clearly so the test can begin. This page is only for the pre-test scan and does not apply
                        to HR interview rounds.
                    </p>
                </section>

                <section
                    style={{
                        background: "#fff",
                        color: "#111",
                        borderRadius: 24,
                        padding: 20,
                        display: "grid",
                        gap: 16,
                        boxShadow: "0 20px 60px rgba(0,0,0,0.18)",
                    }}
                >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
                        <div style={{ color: "#4b5563", lineHeight: 1.6 }}>
                            <div>Session: {sessionInfo?.session_token || "Waiting..."}</div>
                            <div>Scan type: {sessionInfo?.verification_type || "initial"}</div>
                        </div>
                        <span
                            style={{
                                alignSelf: "flex-start",
                                padding: "8px 14px",
                                borderRadius: 999,
                                background: stage === "done" ? tone.bg : "#eef2f7",
                                color: stage === "done" ? tone.color : "#4b5563",
                                fontWeight: 700,
                                textTransform: "uppercase",
                                fontSize: 12,
                            }}
                        >
                            {stage}
                        </span>
                    </div>

                    <div style={{ color: stage === "error" ? "#b33a3a" : "#374151", lineHeight: 1.6 }}>
                        {message}
                    </div>

                    {(stage === "ready" || stage === "capturing") && (
                        <>
                            <div
                                style={{
                                    borderRadius: 20,
                                    overflow: "hidden",
                                    background: "#111",
                                    minHeight: 280,
                                    display: "grid",
                                    placeItems: "center",
                                }}
                            >
                                {cameraError ? (
                                    <div style={{ padding: 20, color: "#fff", textAlign: "center", lineHeight: 1.6 }}>
                                        {cameraError}
                                    </div>
                                ) : (
                                    <video
                                        ref={videoRef}
                                        muted
                                        autoPlay
                                        playsInline
                                        style={{ width: "100%", minHeight: 280, objectFit: "cover" }}
                                    />
                                )}
                            </div>

                            {stage === "capturing" ? (
                                <div style={{ color: "#7a5c00", fontWeight: 700 }}>
                                    Capturing frame {captureStep} of {CAPTURE_FRAME_COUNT}...
                                </div>
                            ) : null}

                            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                                <button
                                    type="button"
                                    onClick={handleLiveCapture}
                                    disabled={stage !== "ready" || Boolean(cameraError)}
                                    style={{
                                        border: "none",
                                        borderRadius: 999,
                                        padding: "13px 18px",
                                        background: "#111",
                                        color: "#fff",
                                        fontWeight: 700,
                                        cursor: stage === "ready" && !cameraError ? "pointer" : "default",
                                    }}
                                >
                                    Start 360 Live Scan
                                </button>
                            </div>
                        </>
                    )}

                    {stage === "uploading" ? (
                        <div style={{ color: "#4b5563" }}>The room scan is being uploaded and analyzed...</div>
                    ) : null}

                    {stage === "done" && report ? (
                        <div
                            style={{
                                borderRadius: 18,
                                padding: 16,
                                background: tone.bg,
                                color: tone.color,
                                lineHeight: 1.7,
                                display: "grid",
                                gap: 6,
                            }}
                        >
                            <strong>Verdict: {report.verdict}</strong>
                            <div>Frames analyzed: {report.total_frames ?? 0}</div>
                            <div>Violations found: {report.total_violations ?? 0}</div>
                            {report.suspicious_items && Object.keys(report.suspicious_items).length > 0 ? (
                                <div>Flagged items: {Object.entries(report.suspicious_items).map(([item, count]) => `${item} (${count})`).join(", ")}</div>
                            ) : null}
                            {report.verdict === "fail" ? (
                                <button
                                    type="button"
                                    onClick={resetForRetry}
                                    style={{
                                        width: "fit-content",
                                        marginTop: 8,
                                        border: "none",
                                        borderRadius: 999,
                                        padding: "12px 18px",
                                        background: "#111",
                                        color: "#fff",
                                        fontWeight: 700,
                                        cursor: "pointer",
                                    }}
                                >
                                    Scan Again
                                </button>
                            ) : null}
                        </div>
                    ) : null}
                </section>
            </div>
        </main>
    );
}
