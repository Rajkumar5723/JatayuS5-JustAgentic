import "./Candidate.css"
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { MAIN_API } from "../../shared/api.js";

const TYPE_MAP = { ft: "Full-Time", pt: "Part-Time", ct: "Contract" };
const DEPT_MAP = { dev: "Development", sal: "Sales", mkt: "Marketing" };

export default function JobPost() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [job, setJob] = useState(null);
    const [err, setErr] = useState("");

    useEffect(() => {
        fetch(`${MAIN_API}/jobs/${id}`)
            .then(r => { if (!r.ok) throw new Error(); return r.json(); })
            .then(setJob)
            .catch(() => setErr("Job not found."));
    }, [id]);

    if (err) return <main className="jobpost-main"><p className="jobpost-err">{err}</p></main>;
    if (!job) return <main className="jobpost-main"><p className="jobpost-loading">Loading...</p></main>;

    const skills = job.skills ? job.skills.split(",").filter(Boolean) : [];
    const ws = job.work_style ? job.work_style.split(",").map(s => s.trim()).filter(Boolean) : [];
    const workStyles = ws.length ? ws : (job.work_style ? [String(job.work_style).trim()] : []);
    const onsiteOrHybrid = (s) => {
        const n = String(s).trim().toLowerCase().replace(/\s+/g, " ");
        return n === "on-site" || n === "onsite" || n === "hybrid";
    };
    const showWorkLocation =
        Boolean(job.location && String(job.location).trim()) &&
        workStyles.some(onsiteOrHybrid);
    const dept = DEPT_MAP[job.department] || job.department;
    const jobType = TYPE_MAP[job.job_type] || job.job_type;
    const deadline = job.deadline
        ? new Date(job.deadline).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })
        : null;

    return (
        <main className="jobpost-main">


            <div className="jobpost-side">
                <img src="/iconw.svg" alt="Hiresy" className="jobpost-side-logo" />
            </div>



            <div className="jobpost-content">
                <div className="jobpost-card">

                    <p className="jobpost-company">Hiresy</p>
                    <h1 className="jobpost-title">{job.job_name}</h1>

                    <div className="jobpost-tags">
                        {workStyles.map(w => <span key={w} className="jp-tag">{w}</span>)}
                        {jobType && <span className="jp-tag">{jobType}</span>}
                        {dept && <span className="jp-tag">{dept}</span>}
                        {job.openings && <span className="jp-tag jp-tag-green">{job.openings} Opening{job.openings > 1 ? "s" : ""}</span>}
                    </div>

                    <div className="jobpost-body">

                        <div className="jobpost-section">
                            <p className="jobpost-section-title">About the Role</p>
                            <p className="jobpost-desc">{job.description}</p>
                        </div>

                        <div className="jobpost-section">
                            <p className="jobpost-section-title">Job Details</p>
                            <div className="jobpost-detail-grid">
                                {job.exp_min && (
                                    <div className="jp-detail">
                                        <span className="jp-detail-label">Experience</span>
                                        <span>{job.exp_min} – {job.exp_max} years</span>
                                    </div>
                                )}
                                {job.show_salary === "true" && job.salary_start && (
                                    <div className="jp-detail">
                                        <span className="jp-detail-label">Salary</span>
                                        <span>₹{job.salary_start} – ₹{job.salary_end}</span>
                                    </div>
                                )}
                                {deadline && (
                                    <div className="jp-detail">
                                        <span className="jp-detail-label">Deadline</span>
                                        <span>{deadline}</span>
                                    </div>
                                )}
                                {showWorkLocation && (
                                    <div className="jp-detail">
                                        <span className="jp-detail-label">Location</span>
                                        <span>{job.location}</span>
                                    </div>
                                )}
                            </div>
                        </div>

                        {skills.length > 0 && (
                            <div className="jobpost-section">
                                <p className="jobpost-section-title">Skills Required</p>
                                <div className="jobpost-skills">
                                    {skills.map(s => <span key={s} className="jp-skill">{s}</span>)}
                                </div>
                            </div>
                        )}

                    </div>

                    <div className="jobpost-footer">
                        <p className="jobpost-footer-text">
                            Interested? Apply before {deadline || "the deadline"}.
                        </p>
                        <button className="jobpost-apply-btn" onClick={() => navigate(`/job/${id}/apply`)}>
                            Apply Now
                        </button>
                    </div>
                </div>
            </div>

          

        </main>
    );
}
