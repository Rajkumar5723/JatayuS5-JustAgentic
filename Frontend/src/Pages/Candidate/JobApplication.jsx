import "./Candidate.css"
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { FiUser, FiMail, FiPhone, FiMapPin, FiGithub, FiGlobe, FiBook, FiBriefcase, FiCode, FiUpload, FiFileText, FiArrowLeft } from "react-icons/fi";
import {
    parseApplicationFieldTokens,
    orderDisplayFields,
    groupFieldsForDisplay,
    chunkFieldsIntoRows,
    UPLOAD_FIELD_LABELS,
} from "../../shared/applicationFields";
import { MAIN_API } from "../../shared/api.js";

const TYPE_MAP = { ft: "Full-Time", pt: "Part-Time", ct: "Contract" };
const DEPT_MAP = { dev: "Development", sal: "Sales", mkt: "Marketing" };

const LABEL_TO_FORM_KEY = {
    "Resume/CV": "__resume__",
    "Cover letter": "__cover_letter__",
    "Full Name": "full_name",
    "Email Id": "email",
    "Location / address": "location",
    "Phone Number": "phone",
    "Alternative Number": "alt_phone",
    "Degree type": "degree_type",
    "Field of study": "field_of_study",
    "Institution name": "institution",
    "Years of experience": "years_exp",
    "Current/past job titles": "current_title",
    "Company names": "company_name",
    "Current LPA": "current_lpa",
    "Notice Period": "notice_period",
    "Technical skills": "technical_skills",
    "Soft skills": "soft_skills",
    "Certifications / licenses": "certifications",
    "Portfolio link": "portfolio_url",
    "LinkedIn": "linkedin_url",
    "GitHub": "github_url",
    "LeetCode": "leetcode_url",
    "Codeforces": "codeforces_url",
    "HackerRank": "hackerrank_url",
    "Kaggle": "kaggle_url",
    "Stack Overflow": "stackoverflow_url",
    "Medium": "medium_url",
};

function isNonEmpty(v) {
    return v != null && String(v).trim().length > 0;
}

function isValidEmail(s) {
    if (!isNonEmpty(s)) return false;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(s).trim());
}

function getFieldRawValue(label, form, resumeFile, coverLetterFile) {
    const key = LABEL_TO_FORM_KEY[label] ?? label;
    if (key === "__resume__") {
        return resumeFile ? "1" : (form.resume_url || "").trim();
    }
    if (key === "__cover_letter__") {
        return coverLetterFile ? "1" : (form.cover_letter || "").trim();
    }
    return form[key];
}

function collectMissingMandatoryFields(mandatoryLabels, form, resumeFile, coverLetterFile) {
    const missing = [];
    for (const label of mandatoryLabels) {
        const raw = getFieldRawValue(label, form, resumeFile, coverLetterFile);
        if (!isNonEmpty(raw)) missing.push(label);
    }
    return missing;
}

function DocumentUploadZone({
    label,
    required,
    hasError,
    file,
    extracting,
    extractMsg,
    onFile,
    icon: Icon = FiFileText,
    emptyTitle,
    emptySub,
}) {
    const Req = required ? <span className="ja-req">*</span> : null;
    return (
        <div className={`ja-doc-upload${hasError ? " ja-doc-upload--error" : ""}`}>
            <label className="ja-resume-dropzone">
                <input type="file" accept=".pdf" style={{ display: "none" }} onChange={(e) => onFile(e.target.files[0])} />
                {extracting ? (
                    <div className="ja-resume-state">
                        <div className="ja-resume-spinner-ring" />
                        <div>
                            <p className="ja-resume-state-title">Analysing document...</p>
                            <p className="ja-resume-state-sub">Extracting text with AI</p>
                        </div>
                    </div>
                ) : file ? (
                    <div className="ja-resume-state">
                        <div className="ja-resume-file-icon"><Icon size={28} /></div>
                        <div>
                            <p className="ja-resume-state-title">{file.name}</p>
                            <p className="ja-resume-state-sub">Click to replace</p>
                        </div>
                        {extractMsg?.startsWith("✅") && <span className="ja-resume-badge">Parsed</span>}
                        {extractMsg?.startsWith("⚠️") && <span className="ja-resume-badge ja-resume-badge-warn">Manual</span>}
                    </div>
                ) : (
                    <div className="ja-resume-empty">
                        <div className="ja-resume-upload-icon"><FiUpload size={26} /></div>
                        <div>
                            <p className="ja-resume-empty-title">{emptyTitle} {Req}</p>
                            <p className="ja-resume-empty-sub">{emptySub}</p>
                        </div>
                    </div>
                )}
            </label>
        </div>
    );
}

export default function JobApplication() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [job, setJob] = useState(null);
    const [submitState, setSubmitState] = useState("idle");
    const [msg, setMsg] = useState("");
    const [resumeFile, setResumeFile] = useState(null);
    const [resumeExtracting, setResumeExtracting] = useState(false);
    const [resumeExtractMsg, setResumeExtractMsg] = useState("");
    const [resumeText, setResumeText] = useState("");
    const [coverLetterFile, setCoverLetterFile] = useState(null);
    const [coverExtracting, setCoverExtracting] = useState(false);
    const [coverExtractMsg, setCoverExtractMsg] = useState("");

    const [form, setForm] = useState({
        full_name: "", email: "", phone: "", alt_phone: "", location: "",
        resume_url: "", linkedin_url: "", github_url: "", leetcode_url: "", portfolio_url: "",
        degree_type: "", field_of_study: "", institution: "",
        years_exp: "", current_title: "", company_name: "", current_lpa: "", notice_period: "",
        technical_skills: "", soft_skills: "", certifications: "", cover_letter: "",
        codeforces_url: "", hackerrank_url: "", kaggle_url: "", stackoverflow_url: "", medium_url: "",
    });
    const [confirmAccurate, setConfirmAccurate] = useState(false);
    const [missingFields, setMissingFields] = useState([]);
    const [confirmError, setConfirmError] = useState(false);

    useEffect(() => {
        fetch(`${MAIN_API}/jobs/${id}`)
            .then((r) => r.json()).then(setJob).catch(() => { });
    }, [id]);

    const set = (key, val) => setForm((f) => ({ ...f, [key]: val }));
    const { mandatory: mandatoryFields, allFields: displayFields } = parseApplicationFieldTokens(
        job?.application_fields ?? ""
    );
    const has = (label) => Boolean(job) && displayFields.includes(label);
    const isMandatory = (label) => mandatoryFields.includes(label);
    const fieldErr = (label) => missingFields.includes(label);

    const extractPdf = async (file, mode) => {
        const base64 = await new Promise((res, rej) => {
            const reader = new FileReader();
            reader.onload = () => res(reader.result.split(",")[1]);
            reader.onerror = rej;
            reader.readAsDataURL(file);
        });
        const res = await fetch(`${MAIN_API}/extract-resume`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ pdf_base64: base64, mode }),
        });
        if (!res.ok) {
            const e = await res.json();
            throw new Error(e.detail || "Could not parse PDF");
        }
        return res.json();
    };

    const handleResumeUpload = async (file) => {
        if (!file) return;
        setResumeFile(file);
        setResumeExtracting(true);
        setResumeExtractMsg("Reading your resume...");
        try {
            setResumeExtractMsg("Analysing with AI...");
            const extracted = await extractPdf(file, "resume");
            setResumeText(extracted.resume_text || "");
            setForm((f) => ({
                ...f,
                ...Object.fromEntries(
                    Object.entries(extracted).filter(([key, v]) => {
                        if (!v?.toString().trim()) return false;
                        return !f[key]?.toString().trim();
                    })
                ),
            }));
            setResumeExtractMsg("✅ Resume parsed! Review and fill any missing fields.");
        } catch (err) {
            setResumeExtractMsg("⚠️ " + (err.message || "Could not parse resume") + ". Fill manually.");
        } finally {
            setResumeExtracting(false);
        }
    };

    const handleCoverLetterUpload = async (file) => {
        if (!file) return;
        setCoverLetterFile(file);
        setCoverExtracting(true);
        setCoverExtractMsg("Reading your cover letter...");
        try {
            setCoverExtractMsg("Extracting text...");
            const extracted = await extractPdf(file, "cover_letter");
            if (extracted.cover_letter) {
                setForm((f) => ({ ...f, cover_letter: extracted.cover_letter }));
            }
            setCoverExtractMsg("✅ Cover letter parsed and saved.");
        } catch (err) {
            setCoverExtractMsg("⚠️ " + (err.message || "Could not parse PDF") + ". Try another file.");
        } finally {
            setCoverExtracting(false);
        }
    };

    const handleSubmit = async () => {
        setMsg("");
        setMissingFields([]);
        setConfirmError(false);

        const missing = collectMissingMandatoryFields(mandatoryFields, form, resumeFile, coverLetterFile);
        if (missing.length > 0) {
            setMissingFields(missing);
            setMsg(`Please complete all required fields (${missing.length} missing): ${missing.join(", ")}.`);
            return;
        }

        if (mandatoryFields.includes("Email Id") && !isValidEmail(form.email)) {
            setMissingFields(["Email Id"]);
            setMsg("Please enter a valid email address.");
            return;
        }

        if (!confirmAccurate) {
            setConfirmError(true);
            setMsg("Please confirm that your information is accurate and complete before submitting.");
            return;
        }

        setSubmitState("submitting");
        try {
            const payload = { job_id: parseInt(id, 10), ...form, resume_text: resumeText };
            const requestInit = { method: "POST" };
            if (resumeFile || coverLetterFile) {
                const formData = new FormData();
                formData.append("application_json", JSON.stringify(payload));
                if (resumeFile) formData.append("resume_file", resumeFile);
                if (coverLetterFile) formData.append("cover_letter_file", coverLetterFile);
                requestInit.body = formData;
            } else {
                requestInit.headers = { "Content-Type": "application/json" };
                requestInit.body = JSON.stringify(payload);
            }
            const res = await fetch(`${MAIN_API}/applications`, {
                ...requestInit,
            });
            if (res.ok) {
                setSubmitState("done");
                setMsg("✅ Application submitted successfully!");
                setMissingFields([]);
                setConfirmError(false);
            } else {
                const d = await res.json();
                setMsg(d.detail || "Submission failed.");
                setSubmitState("error");
            }
        } catch {
            setMsg("Server error.");
            setSubmitState("error");
        }
    };

    if (!job) return <main className="ja-main"><p className="ja-loading">Loading...</p></main>;

    const dept = DEPT_MAP[job.department] || job.department;
    const jobType = TYPE_MAP[job.job_type] || job.job_type;
    const fb = (label) =>
        fieldErr(label) && isMandatory(label) ? "ja-field-block ja-field-error" : "ja-field-block";
    const Req = ({ l }) => (isMandatory(l) ? <span className="ja-req">*</span> : null);

    const fieldIcon = (label) => {
        if (label === "LinkedIn") return <img src="/linkedin.svg" width={12} height={12} alt="LinkedIn" />;
        if (label === "LeetCode") return <img src="/leetcode.svg" width={12} height={12} alt="LeetCode" />;
        const icons = {
            "Full Name": FiUser, "Email Id": FiMail, "Phone Number": FiPhone, "Alternative Number": FiPhone,
            "Location / address": FiMapPin, "Degree type": FiBook, "Field of study": FiBook, "Institution name": FiBook,
            "Years of experience": FiBriefcase, "Current/past job titles": FiBriefcase, "Company names": FiBriefcase,
            "Current LPA": FiBriefcase, "Notice Period": FiBriefcase, "Technical skills": FiCode, "Soft skills": FiCode,
            "Certifications / licenses": FiBook, "GitHub": FiGithub, "Portfolio link": FiGlobe,
        };
        const Icon = icons[label] || FiCode;
        return <Icon size={12} />;
    };

    const renderFieldInput = (label) => {
        const ph = {
            "Full Name": "Your full name",
            "Email Id": "you@email.com",
            "Phone Number": "+91 98765 43210",
            "Alternative Number": "+91 91234 56789",
            "Location / address": "City, State",
            "Degree type": "B.Tech, MBA...",
            "Field of study": "Computer Science",
            "Institution name": "University / College",
            "Years of experience": "3",
            "Current/past job titles": "Software Engineer",
            "Company names": "Company name",
            "Current LPA": "12 LPA",
            "Notice Period": "30 days / Immediate",
            "Technical skills": "Python, React, SQL...",
            "Soft skills": "Leadership, Communication...",
            "Certifications / licenses": "AWS Certified, PMP...",
            "LinkedIn": "linkedin.com/in/username",
            "GitHub": "github.com/username",
            "LeetCode": "leetcode.com/username",
            "Codeforces": "codeforces.com/profile/username",
            "HackerRank": "hackerrank.com/username",
            "Kaggle": "kaggle.com/username",
            "Stack Overflow": "stackoverflow.com/users/...",
            "Medium": "medium.com/@username",
            "Portfolio link": "yourportfolio.com",
        };
        const key = LABEL_TO_FORM_KEY[label] ?? label;
        const type = label === "Email Id" ? "email" : "text";
        return (
            <input
                className="ja-input"
                type={type}
                placeholder={ph[label] || label}
                value={form[key] || ""}
                onChange={(e) => set(key, e.target.value)}
            />
        );
    };

    const orderedFields = orderDisplayFields(displayFields);
    const visibleSections = groupFieldsForDisplay(orderedFields);
    const uploadFields = orderedFields.filter((f) => UPLOAD_FIELD_LABELS.has(f));
    const hasUploads = uploadFields.length > 0;

    return (
        <main className="ja-main">
            <div className="ja-banner">
                <div className="ja-banner-inner">
                    <button type="button" className="ja-back" onClick={() => navigate(`/job/${id}`)}>
                        <FiArrowLeft size={14} /> Back to Job
                    </button>
                    <div className="ja-banner-info">
                        <p className="ja-banner-company">Hiresy</p>
                        <h1 className="ja-banner-title">{job.job_name}</h1>
                        <div className="ja-banner-tags">
                            {dept && <span className="ja-btag">{dept}</span>}
                            {jobType && <span className="ja-btag">{jobType}</span>}
                            {job.work_style?.split(",").filter(Boolean).map((w) => (
                                <span key={w} className="ja-btag">{w}</span>
                            ))}
                            {job.exp_min && (
                                <span className="ja-btag ja-btag-skill">{job.exp_min} – {job.exp_max} yrs exp</span>
                            )}
                            {job.show_salary === "true" && job.salary_start && (
                                <span className="ja-btag ja-btag-skill">₹{job.salary_start} – ₹{job.salary_end}</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            <div className="ja-wrap">
                {hasUploads && (
                    <div className="ja-uploads-block">
                        <p className="ja-col-label">Documents</p>
                        <div className={`ja-uploads-grid${uploadFields.length === 1 ? " ja-uploads-grid--one" : ""}`}>
                            {has("Resume/CV") && (
                                <DocumentUploadZone
                                    label="Resume/CV"
                                    required={isMandatory("Resume/CV")}
                                    hasError={fieldErr("Resume/CV")}
                                    file={resumeFile}
                                    extracting={resumeExtracting}
                                    extractMsg={resumeExtractMsg}
                                    onFile={handleResumeUpload}
                                    emptyTitle="Upload Resume"
                                    emptySub="PDF only · Auto-fills your application"
                                />
                            )}
                            {has("Cover letter") && (
                                <DocumentUploadZone
                                    label="Cover letter"
                                    required={isMandatory("Cover letter")}
                                    hasError={fieldErr("Cover letter")}
                                    file={coverLetterFile}
                                    extracting={coverExtracting}
                                    extractMsg={coverExtractMsg}
                                    onFile={handleCoverLetterUpload}
                                    emptyTitle="Upload Cover Letter"
                                    emptySub="PDF only · Text extracted internally"
                                />
                            )}
                        </div>
                    </div>
                )}

                <div className="ja-form-card">
                    <div className="ja-form-scroll">
                        <div className="ja-body ja-body--pro">
                            {visibleSections.length === 0 ? (
                                <p className="ja-empty-fields">No application fields configured for this job.</p>
                            ) : (
                                visibleSections.map((sec) => (
                                    <section key={sec.title} className="ja-section">
                                        <p className="ja-col-label">{sec.title}</p>
                                        {chunkFieldsIntoRows(sec.fields).map((row, ri) => (
                                            <div
                                                key={`${sec.title}-${ri}`}
                                                className={`ja-field-row${row.length === 1 ? " ja-field-row--single" : ""}`}
                                            >
                                                {row.map((label) => (
                                                    <div className={fb(label)} key={label}>
                                                        <label className="ja-label">
                                                            {fieldIcon(label)} {label} <Req l={label} />
                                                        </label>
                                                        {renderFieldInput(label)}
                                                    </div>
                                                ))}
                                            </div>
                                        ))}
                                    </section>
                                ))
                            )}
                        </div>

                        <div className="ja-form-footer">
                            {msg && (
                                <p className={`ja-msg ${submitState === "done" ? "ja-msg-success" : "ja-msg-error"}`}>{msg}</p>
                            )}
                            {submitState !== "done" && (
                                <>
                                    <label className={`ja-confirm-row${confirmError ? " ja-confirm-row-error" : ""}`}>
                                        <input
                                            type="checkbox"
                                            checked={confirmAccurate}
                                            onChange={(e) => {
                                                setConfirmAccurate(e.target.checked);
                                                if (e.target.checked) setConfirmError(false);
                                            }}
                                        />
                                        <span>
                                            I confirm that the information I have provided is accurate and complete, and I have reviewed all fields before submitting.
                                            <span className="ja-req"> *</span>
                                        </span>
                                    </label>
                                    <button type="button" className="ja-submit" onClick={handleSubmit} disabled={submitState === "submitting"}>
                                        {submitState === "submitting" ? "Submitting..." : "Submit Application"}
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </main>
    );
}
