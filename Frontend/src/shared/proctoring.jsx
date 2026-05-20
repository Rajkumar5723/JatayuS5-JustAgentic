/* eslint-disable react-refresh/only-export-components */
import { useCallback, useEffect, useRef, useState } from "react";

const SNAPSHOT_MS = 15000;
const DEVTOOLS_MS = 3000;

function snapshotFromVideo(videoEl) {
    if (!videoEl || !videoEl.videoWidth || !videoEl.videoHeight) return "";
    const canvas = document.createElement("canvas");
    canvas.width = Math.min(320, videoEl.videoWidth);
    canvas.height = Math.round((canvas.width / videoEl.videoWidth) * videoEl.videoHeight);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/jpeg", 0.8);
}

export function useProctoring({ enabled, endpoint, onSevere }) {
    const videoRef = useRef(null);
    const streamRef = useRef(null);
    const displayStreamRef = useRef(null);
    const screenVideoRef = useRef(null);
    const selfieCapturedRef = useRef(false);
    const snapshotTimerRef = useRef(null);
    const devtoolsTimerRef = useRef(null);
    const severeFiredRef = useRef(false);
    const onSevereRef = useRef(onSevere);

    const [risk, setRisk] = useState({ risk_level: "low", risk_score: 0, blocked: false, block_reason: "" });
    const [cameraReady, setCameraReady] = useState(false);
    const [warning, setWarning] = useState("");

    const postEvent = useCallback(async (eventType, payload = {}) => {
        if (!enabled || !endpoint) return null;
        try {
            const res = await fetch(endpoint, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    event_type: eventType,
                    payload: {
                        ...payload,
                        user_agent: navigator.userAgent,
                        url: window.location.href,
                    },
                }),
            });
            const data = await res.json();
            setRisk(data);
            if (data.blocked && !severeFiredRef.current) {
                severeFiredRef.current = true;
                setWarning(data.block_reason || "Severe proctoring risk detected. Submitting attempt.");
                onSevereRef.current?.();
            }
            return data;
        } catch (err) {
            console.error("Proctoring event failed", err);
            return null;
        }
    }, [enabled, endpoint]);

    const captureFaceWithRetry = useCallback(async function attemptFaceCapture(eventType, remainingAttempts = 4) {
        const face_b64 = snapshotFromVideo(videoRef.current);
        if (face_b64) {
            selfieCapturedRef.current = true;
            return postEvent(eventType, { face_b64 });
        }
        if (remainingAttempts <= 0) return null;
        return new Promise((resolve) => {
            setTimeout(() => {
                attemptFaceCapture(eventType, remainingAttempts - 1).then(resolve);
            }, 700);
        });
    }, [postEvent]);

    useEffect(() => {
        onSevereRef.current = onSevere;
    }, [onSevere]);

    const buildDeviceInfo = () => ({
        user_agent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        languages: navigator.languages,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        screen: `${window.screen.width}x${window.screen.height}`,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        hardware_concurrency: navigator.hardwareConcurrency || null,
        device_memory: navigator.deviceMemory || null,
    });

    useEffect(() => {
        if (!enabled) {
            severeFiredRef.current = false;
            return undefined;
        }

        let cancelled = false;

        const capture = async (eventType) => {
            const face_b64 = snapshotFromVideo(videoRef.current);
            if (!face_b64) return null;
            return postEvent(eventType, { face_b64 });
        };

        const captureScreen = async () => {
            const screen_b64 = snapshotFromVideo(screenVideoRef.current);
            if (!screen_b64) return null;
            return postEvent("screen_snapshot_captured", { screen_b64 });
        };

        const startCamera = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: "user", width: { ideal: 640 }, height: { ideal: 480 } },
                    audio: false,
                });
                if (cancelled) {
                    stream.getTracks().forEach((track) => track.stop());
                    return;
                }
                streamRef.current = stream;
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                    await videoRef.current.play().catch(() => {});
                }
                setCameraReady(true);
                setWarning("");
                await postEvent("device_info", { device: buildDeviceInfo() });
                setTimeout(async () => {
                    if (!selfieCapturedRef.current) {
                        await captureFaceWithRetry("selfie_captured");
                    }
                }, 900);

                snapshotTimerRef.current = setInterval(() => {
                    capture("snapshot_captured");
                    captureScreen();
                }, SNAPSHOT_MS);
            } catch (err) {
                setCameraReady(false);
                setWarning("Camera permission is required for this round.");
                await postEvent("permissions_denied", { reason: String(err) });
            }
        };

        const startScreenCapture = async () => {
            try {
                const stream = await navigator.mediaDevices.getDisplayMedia({
                    video: {
                        frameRate: { ideal: 1, max: 2 },
                    },
                    audio: false,
                });
                if (cancelled) {
                    stream.getTracks().forEach((track) => track.stop());
                    return;
                }
                displayStreamRef.current = stream;
                const [videoTrack] = stream.getVideoTracks();
                if (videoTrack) {
                    videoTrack.addEventListener("ended", () => {
                        postEvent("screen_share_stopped", { reason: "user_stopped_share" });
                    });
                }
                const hiddenVideo = document.createElement("video");
                hiddenVideo.muted = true;
                hiddenVideo.playsInline = true;
                hiddenVideo.srcObject = stream;
                await hiddenVideo.play().catch(() => {});
                screenVideoRef.current = hiddenVideo;
                await postEvent("screen_share_started", { device: buildDeviceInfo() });
            } catch (err) {
                await postEvent("screen_capture_unavailable", { reason: String(err) });
            }
        };

        const visibilityHandler = () => {
            if (document.hidden) postEvent("tab_hidden");
        };
        const blurHandler = () => postEvent("window_blur");
        const copyHandler = () => postEvent("copy");
        const pasteHandler = () => postEvent("paste");
        const fullscreenHandler = () => {
            if (!document.fullscreenElement) postEvent("fullscreen_exit");
        };

        document.addEventListener("visibilitychange", visibilityHandler);
        window.addEventListener("blur", blurHandler);
        document.addEventListener("copy", copyHandler);
        document.addEventListener("paste", pasteHandler);
        document.addEventListener("fullscreenchange", fullscreenHandler);

        document.documentElement.requestFullscreen?.().catch(() => {
            postEvent("fullscreen_exit", { reason: "request_rejected" });
        });

        devtoolsTimerRef.current = setInterval(() => {
            const widthDiff = window.outerWidth - window.innerWidth;
            const heightDiff = window.outerHeight - window.innerHeight;
            if (widthDiff > 180 || heightDiff > 180) {
                postEvent("devtools_suspected", { widthDiff, heightDiff });
            }
        }, DEVTOOLS_MS);

        startCamera();
        startScreenCapture();

        return () => {
            cancelled = true;
            document.removeEventListener("visibilitychange", visibilityHandler);
            window.removeEventListener("blur", blurHandler);
            document.removeEventListener("copy", copyHandler);
            document.removeEventListener("paste", pasteHandler);
            document.removeEventListener("fullscreenchange", fullscreenHandler);
            clearInterval(snapshotTimerRef.current);
            clearInterval(devtoolsTimerRef.current);
            if (streamRef.current) {
                streamRef.current.getTracks().forEach((track) => track.stop());
                streamRef.current = null;
            }
            if (displayStreamRef.current) {
                displayStreamRef.current.getTracks().forEach((track) => track.stop());
                displayStreamRef.current = null;
            }
            screenVideoRef.current = null;
            selfieCapturedRef.current = false;
        };
    }, [captureFaceWithRetry, enabled, endpoint, postEvent]);

    return { videoRef, risk, cameraReady, warning };
}


const riskColor = (level) => ({
    low: "#1f8f4b",
    medium: "#c77b00",
    high: "#d95f02",
    critical: "#d10f35",
    severe: "#8c112d",
}[level] || "#5a5a5a");


export function ProctoringMonitor({ videoRef, risk, warning, cameraReady }) {
    return (
        <div
            style={{
                position: "fixed",
                right: 16,
                bottom: 16,
                width: 200,
                background: "rgba(8,8,8,0.92)",
                border: `1px solid ${riskColor(risk?.risk_level)}`,
                borderRadius: 16,
                padding: 12,
                color: "#fff",
                zIndex: 50,
                boxShadow: "0 16px 40px rgba(0,0,0,0.24)",
                backdropFilter: "blur(8px)",
            }}
        >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: 1.4, color: "#ff8b4a" }}>Proctoring</span>
                <span
                    style={{
                        fontSize: 11,
                        padding: "4px 8px",
                        borderRadius: 999,
                        background: `${riskColor(risk?.risk_level)}22`,
                        color: riskColor(risk?.risk_level),
                    }}
                >
                    {(risk?.risk_level || "low").toUpperCase()}
                </span>
            </div>
            <video
                ref={videoRef}
                muted
                playsInline
                autoPlay
                style={{
                    width: "100%",
                    height: 112,
                    objectFit: "cover",
                    borderRadius: 12,
                    background: "#111",
                    border: "1px solid rgba(255,255,255,0.08)",
                }}
            />
            <div style={{ marginTop: 8, fontSize: 12, color: "#d6d6d6", lineHeight: 1.5 }}>
                <div>Camera: {cameraReady ? "Active" : "Waiting"}</div>
                <div>Risk score: {risk?.risk_score ?? 0}</div>
                {risk?.block_reason ? <div>Reason: {risk.block_reason.replaceAll("_", " ")}</div> : null}
            </div>
            {warning ? (
                <p style={{ margin: "8px 0 0", fontSize: 12, color: "#ffb48c", lineHeight: 1.5 }}>{warning}</p>
            ) : null}
        </div>
    );
}
