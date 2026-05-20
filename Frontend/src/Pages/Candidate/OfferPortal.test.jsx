import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import OfferPortal from "./OfferPortal.jsx";

const initialOffer = {
    application_id: 42,
    candidate_name: "Avery Chen",
    candidate_email: "avery@example.com",
    job_title: "Frontend Engineer",
    job_location: "Remote",
    status: "offer_sent",
    candidate_response: "",
    candidate_remarks: "",
    joining_date: "2026-06-15",
    designation: "Frontend Engineer",
    department: "Development",
    compensation_text: "18 LPA fixed + bonus",
    work_location: "Remote",
    work_mode: "Remote",
    reporting_manager: "Jordan Lee",
    reporting_team: "Frontend Platform",
    company_details: "Hiresy Pvt Ltd",
    hr_contact_details: "hr@hiresy.ai",
    onboarding_instructions: "Keep your documents ready.",
    terms_and_conditions: "Standard offer terms apply.",
    candidate_portal_expires_at: "2026-06-01T10:00:00Z",
    expired: false,
    preview_url: "http://127.0.0.1:8000/offer-letter/token/download?kind=unsigned",
    signed_preview_url: null,
    download_url: "http://127.0.0.1:8000/offer-letter/token/download",
};

describe("OfferPortal", () => {
    beforeEach(() => {
        HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
            fillStyle: "",
            strokeStyle: "",
            lineWidth: 1,
            lineJoin: "round",
            lineCap: "round",
            fillRect: vi.fn(),
            beginPath: vi.fn(),
            moveTo: vi.fn(),
            lineTo: vi.fn(),
            stroke: vi.fn(),
        }));
        HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/png;base64,fakesignature");

        global.fetch = vi
            .fn()
            .mockResolvedValueOnce({
                ok: true,
                json: async () => initialOffer,
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({
                    ...initialOffer,
                    status: "rejected",
                    candidate_response: "rejected",
                    candidate_remarks: "I am pursuing another role.",
                    candidate_response_at: "2026-05-19T13:30:00Z",
                }),
            });
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    it("submits a rejection response without requiring a signature", async () => {
        render(
            <MemoryRouter initialEntries={["/offer/token123"]}>
                <Routes>
                    <Route path="/offer/:token" element={<OfferPortal />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByRole("heading", { name: "Frontend Engineer" })).toBeInTheDocument();
        });

        await userEvent.click(screen.getByRole("radio", { name: /Reject Offer/i }));
        await userEvent.clear(screen.getByRole("textbox", { name: /Remarks/i }));
        await userEvent.type(screen.getByRole("textbox", { name: /Remarks/i }), "I am pursuing another role.");
        await userEvent.click(screen.getByRole("button", { name: "Reject Offer" }));

        await waitFor(() => {
            expect(screen.getByText("Offer rejected")).toBeInTheDocument();
        });

        expect(global.fetch).toHaveBeenNthCalledWith(
            2,
            "/api/offer-letter/token123/respond",
            expect.objectContaining({
                method: "POST",
                body: expect.stringContaining('"decision":"rejected"'),
            })
        );
    });
});
