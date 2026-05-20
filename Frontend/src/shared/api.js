const MAIN_API_BASE = import.meta.env.VITE_MAIN_API_BASE || "/api";
const TEST_API_BASE = import.meta.env.VITE_TEST_API_BASE || "/test-api";
const CODING_API_BASE = import.meta.env.VITE_CODING_API_BASE || "/coding-api";
const LIVEHR_API_BASE = import.meta.env.VITE_LIVEHR_API_BASE || "/livehr-api";

function trimTrailingSlash(value) {
    return String(value || "").replace(/\/+$/, "");
}

function websocketBase() {
    if (typeof window === "undefined") {
        return "ws://127.0.0.1:8004/livehr/ws";
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/livehr-api/livehr/ws`;
}

export const MAIN_API = trimTrailingSlash(MAIN_API_BASE);
export const TEST_API = trimTrailingSlash(TEST_API_BASE);
export const CODING_API = trimTrailingSlash(CODING_API_BASE);
export const LIVEHR_API = trimTrailingSlash(LIVEHR_API_BASE);
export const LIVEHR_WS = import.meta.env.VITE_LIVEHR_WS_BASE || websocketBase();
