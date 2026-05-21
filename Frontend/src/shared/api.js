const MAIN_API_BASE = import.meta.env.VITE_MAIN_API_BASE || "/api";
const TEST_API_BASE = import.meta.env.VITE_TEST_API_BASE || defaultServiceBase("/test-api");
const CODING_API_BASE = import.meta.env.VITE_CODING_API_BASE || defaultServiceBase("/coding-api");
const LIVEHR_API_BASE = import.meta.env.VITE_LIVEHR_API_BASE || defaultServiceBase("/livehr-api");

function trimTrailingSlash(value) {
    return String(value || "").replace(/\/+$/, "");
}

function isAbsoluteHttp(value) {
    return /^https?:\/\//i.test(String(value || ""));
}

function defaultServiceBase(localProxyPath) {
    return isAbsoluteHttp(MAIN_API_BASE) ? MAIN_API_BASE : localProxyPath;
}

function websocketBase() {
    if (typeof window === "undefined") {
        return "ws://127.0.0.1:8004/livehr/ws";
    }
    if (isAbsoluteHttp(LIVEHR_API_BASE)) {
        const url = new URL(trimTrailingSlash(LIVEHR_API_BASE));
        url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
        url.pathname = "/livehr/ws";
        url.search = "";
        url.hash = "";
        return trimTrailingSlash(url.toString());
    }
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}/livehr-api/livehr/ws`;
}

export const MAIN_API = trimTrailingSlash(MAIN_API_BASE);
export const TEST_API = trimTrailingSlash(TEST_API_BASE);
export const CODING_API = trimTrailingSlash(CODING_API_BASE);
export const LIVEHR_API = trimTrailingSlash(LIVEHR_API_BASE);
export const LIVEHR_WS = import.meta.env.VITE_LIVEHR_WS_BASE || websocketBase();
