import { useState, useEffect } from "react";
import { MAIN_API } from "../../shared/api.js";

export default function Settings() {
    const [liStatus, setLiStatus] = useState(null); // null | connected | disconnected
    const [loading, setLoading] = useState(true);
    const [actionMsg, setActionMsg] = useState("");

    const hrEmail = localStorage.getItem("hr_email");

    useEffect(() => {
        fetch(`${MAIN_API}/linkedin/status/${hrEmail}`)
            .then(r => r.json())
            .then(d => { setLiStatus(d.connected ? "connected" : "disconnected"); setLoading(false); })
            .catch(() => { setLiStatus("disconnected"); setLoading(false); });
    }, []);

    const handleConnect = () => {
        window.location.href = `${MAIN_API}/linkedin/connect?email=${encodeURIComponent(hrEmail)}`;
    };

    const handleDisconnect = async () => {
        setActionMsg("Disconnecting...");
        await fetch(`${MAIN_API}/linkedin/disconnect/${hrEmail}`, { method: "DELETE" });
        setLiStatus("disconnected");
        setActionMsg("Disconnected successfully.");
        setTimeout(() => setActionMsg(""), 2000);
    };

    return (
        <main className="setting-main">
            <div className="setting-container">
                <p className="setting-title">Settings</p>

                <div className="setting-section">
                    <p className="setting-section-label">Integrations</p>

                    <div className="setting-card">
                        <div className="setting-card-left">
                            {/* LinkedIn SVG Icon */}
                            <div className="setting-li-icon">
                                <svg viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                                    <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                                </svg>
                            </div>
                            <div className="setting-card-info">
                                <p className="setting-card-name">LinkedIn</p>
                                <p className="setting-card-desc">Auto-post jobs to your LinkedIn account when published</p>
                                {loading ? (
                                    <span className="setting-badge setting-badge-loading">Checking...</span>
                                ) : liStatus === "connected" ? (
                                    <span className="setting-badge setting-badge-connected">● Connected</span>
                                ) : (
                                    <span className="setting-badge setting-badge-disconnected">○ Not connected</span>
                                )}
                            </div>
                        </div>
                        <div className="setting-card-right">
                            {actionMsg && <p className="setting-action-msg">{actionMsg}</p>}
                            {!loading && (
                                liStatus === "connected" ? (
                                    <button className="setting-btn setting-btn-disconnect" onClick={handleDisconnect}>
                                        Disconnect
                                    </button>
                                ) : (
                                    <button className="setting-btn setting-btn-connect" onClick={handleConnect}>
                                        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                                            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                                        </svg>
                                        Connect LinkedIn
                                    </button>
                                )
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
