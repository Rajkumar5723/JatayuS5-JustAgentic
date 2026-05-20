// import { useState, useEffect } from "react";
// import { useNavigate } from "react-router-dom";
// import { FiEdit2, FiCheck, FiLogOut, FiChevronLeft, FiChevronRight } from "react-icons/fi";

// export default function Profile() {
//     const email = localStorage.getItem("hr_email") || "";
//     const name = localStorage.getItem("hr_name") || "";

//     const [editing, setEditing] = useState(false);
//     const [saving, setSaving] = useState(false);
//     const [form, setForm] = useState({
//         name: name,
//         title: localStorage.getItem("hr_title") || "",
//         company: localStorage.getItem("hr_company") || "",
//     });

//     const [interviews, setInterviews] = useState([]);
//     const [eventPopup, setEventPopup] = useState(null);
//     const [calDate, setCalDate] = useState(new Date());
//     const [selectedDay, setSelectedDay] = useState(new Date().getDate());

//     const navigate = useNavigate();

//     const openMeetWithToken = (meetUrl, token) => {
//         const url = `${meetUrl}#hiersy=${token}`;
//         window.open(url, "_blank");
//     };

//     const startInterview = async (iv) => {
//         if (!iv.id) {
//             const demoToken =
//                 Math.random().toString(36).substring(2, 15) +
//                 Math.random().toString(36).substring(2, 15);
//             openMeetWithToken("https://meet.google.com/new", demoToken);
//             return;
//         }

//         const hr_email = localStorage.getItem("hr_email") || "";
//         const candidateName = iv.full_name;
//         const jobName = iv.job_name;

//         try {
//             let appData = {};
//             try {
//                 const appRes = await fetch(`http://127.0.0.1:8000/application/${iv.id}`);
//                 if (appRes.ok) appData = await appRes.json();
//             } catch { }

//             let github_data = {};
//             let eval_summary = "";
//             let github_url = appData.github_url || "";
//             try {
//                 const evalRes = await fetch(`http://127.0.0.1:8000/applications/${iv.id}/eval`);
//                 if (evalRes.ok) {
//                     const ev = await evalRes.json();
//                     github_data = ev.github_raw || {};
//                     eval_summary = ev.eval_summary || ev.summary || "";
//                 }
//             } catch { }

//             const now = new Date();
//             const scheduledStr = now.toLocaleString("en-IN", {
//                 weekday: "long", day: "numeric", month: "long",
//                 year: "numeric", hour: "2-digit", minute: "2-digit"
//             });

//             const res = await fetch("http://127.0.0.1:8004/livehr/session", {
//                 method: "POST",
//                 headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify({
//                     application_id: iv.id,
//                     candidate_name: candidateName,
//                     candidate_email: appData.email || "",
//                     job_title: jobName,
//                     job_skills: appData.technical_skills || "",
//                     github_url,
//                     github_data,
//                     eval_summary,
//                     scheduled_time: scheduledStr,
//                     hr_email,
//                 })
//             });

//             if (!res.ok) throw new Error(`HTTP ${res.status}`);
//             const data = await res.json();

//             openMeetWithToken(data.meet_url, data.token);

//         } catch (e) {
//             console.error("startInterview failed:", e);
//             alert(`Could not start interview: ${e.message}\n\nMake sure Backend/livehr is running on port 8004.`);
//         }
//     };

//     useEffect(() => {
//         fetch("http://127.0.0.1:8000/jobs")
//             .then(r => r.json())
//             .then(async jobs => {
//                 const all = [];
//                 await Promise.all(jobs.map(async job => {
//                     try {
//                         const res = await fetch(`http://127.0.0.1:8000/applications/${job.id}`);
//                         const apps = await res.json();
//                         apps.filter(a => a.status === "selected").forEach(a => {
//                             all.push({ ...a, job_name: job.job_name });
//                         });
//                     } catch { }
//                 }));
//                 setInterviews(all);
//             })
//             .catch(() => { });
//     }, []);

//     const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

//     const save = async () => {
//         setSaving(true);
//         localStorage.setItem("hr_name", form.name);
//         localStorage.setItem("hr_title", form.title);
//         localStorage.setItem("hr_company", form.company);
//         await new Promise(r => setTimeout(r, 500));
//         setSaving(false);
//         setEditing(false);
//     };

//     const logout = () => { localStorage.clear(); window.location.href = "/"; };

//     const initials = form.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase() || "HR";

//     const year = calDate.getFullYear();
//     const month = calDate.getMonth();
//     const monthName = calDate.toLocaleDateString("en-US", { month: "long", year: "numeric" });
//     const firstDay = new Date(year, month, 1).getDay();
//     const daysInMonth = new Date(year, month + 1, 0).getDate();
//     const today = new Date();
//     const isToday = (d) => d === today.getDate() && month === today.getMonth() && year === today.getFullYear();

//     const fakeSchedules = [
//         { full_name: "Rahul Sharma", job_name: "Senior Frontend Developer", time: "09:00", dur: "45m", meet: "" },
//         { full_name: "Priya Nair", job_name: "Data Analyst", time: "11:00", dur: "1h", meet: "" },
//         { full_name: "Arjun Mehta", job_name: "Backend Engineer", time: "14:00", dur: "1h", meet: "" },
//         { full_name: "Sneha Iyer", job_name: "Product Manager", time: "16:00", dur: "30m", meet: "" },
//         { full_name: "Vikram Reddy", job_name: "DevOps Engineer", time: "10:00", dur: "1h", meet: "" },
//         { full_name: "Ananya Krishnan", job_name: "UI/UX Designer", time: "13:00", dur: "45m", meet: "" },
//         { full_name: "Aadesh Siva", job_name: "Frontend Developer (Fresher)", time: "08:00", dur: "45m", meet: "https://meet.google.com/aad-esh-siva", day: 30 },
//     ];

//     const allSchedules = [
//         ...interviews.map((iv, i) => ({
//             ...iv,
//             time: `${String(10 + i).padStart(2, "0")}:00`,
//             dur: "1h",
//             meet: `https://meet.google.com/hier-sy${i + 1}0-abc`
//         })),
//         ...fakeSchedules,
//     ];

//     const scheduledDays = {};
//     allSchedules.forEach((s, i) => {
//         // Use explicit day if provided, otherwise derive from index
//         const day = s.day != null ? s.day : ((i * 4 + 3) % daysInMonth) + 1;
//         if (!scheduledDays[day]) scheduledDays[day] = [];
//         scheduledDays[day].push(s);
//     });
//     const interviewDays = new Set(Object.keys(scheduledDays).map(Number));

//     const prevMonth = () => setCalDate(new Date(year, month - 1, 1));
//     const nextMonth = () => setCalDate(new Date(year, month + 1, 1));
//     const dayInterviews = scheduledDays[selectedDay] || [];
//     const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

//     return (
//         <div className="pf-main">

//             {/* ── Top bar ── */}
//             <div className="pf-topbar">
//                 <p className="pf-topbar-title">Profile</p>
//                 <div className="pf-topbar-right">
//                     {!editing ? (
//                         <button className="pf-btn-ghost" onClick={() => setEditing(true)}>
//                             <FiEdit2 size={13} /> Edit
//                         </button>
//                     ) : (
//                         <>
//                             <button className="pf-btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
//                             <button className="pf-btn-orange" onClick={save} disabled={saving}>
//                                 {saving ? <span className="pf-spin" /> : <FiCheck size={13} />}
//                                 {saving ? "Saving" : "Save"}
//                             </button>
//                         </>
//                     )}
//                     <button className="pf-btn-logout" onClick={logout}>
//                         Logout <FiLogOut size={13} />
//                     </button>
//                 </div>
//             </div>

//             <div className="pf-body">

//                 {/* ── Left ── */}
//                 <div className="pf-left">
//                     <div className="pf-avatar-block">
//                         <div className="pf-avatar">{initials}</div>
//                         <div>
//                             {editing ? (
//                                 <input className="pf-name-input" value={form.name}
//                                     placeholder="Full name"
//                                     onChange={e => set("name", e.target.value)} />
//                             ) : (
//                                 <p className="pf-name">{form.name || "Your Name"}</p>
//                             )}
//                             <p className="pf-email">{email}</p>
//                         </div>
//                     </div>

//                     <div className="pf-meta-rows">
//                         <div className="pf-meta-row">
//                             <span className="pf-meta-label">Role</span>
//                             {editing ? (
//                                 <input className="pf-meta-input" value={form.title} placeholder="e.g. HR Manager" onChange={e => set("title", e.target.value)} />
//                             ) : (
//                                 <span className="pf-meta-value">{form.title || "—"}</span>
//                             )}
//                         </div>
//                         <div className="pf-meta-row">
//                             <span className="pf-meta-label">Company</span>
//                             {editing ? (
//                                 <input className="pf-meta-input" value={form.company} placeholder="Company name" onChange={e => set("company", e.target.value)} />
//                             ) : (
//                                 <span className="pf-meta-value">{form.company || "—"}</span>
//                             )}
//                         </div>
//                     </div>

//                     <div className="pf-stats-row">
//                         <div className="pf-stat">
//                             <span className="pf-stat-num">{interviews.length}</span>
//                             <span className="pf-stat-label">Selected</span>
//                         </div>
//                         <div className="pf-stat">
//                             <span className="pf-stat-num">{allSchedules.length}</span>
//                             <span className="pf-stat-label">Scheduled</span>
//                         </div>
//                     </div>
//                 </div>

//                 {/* ── Right: Calendar ── */}
//                 <div className="pf-right">
//                     <div className="cal-header">
//                         <button className="cal-nav" onClick={prevMonth}><FiChevronLeft size={15} /></button>
//                         <p className="cal-month">{monthName}</p>
//                         <button className="cal-nav" onClick={nextMonth}><FiChevronRight size={15} /></button>
//                     </div>

//                     <div className="cal-days-row">
//                         {DAYS.map(d => <span key={d} className="cal-day-name">{d}</span>)}
//                     </div>

//                     <div className="cal-grid">
//                         {Array.from({ length: firstDay }).map((_, i) => (
//                             <div key={`e${i}`} className="cal-cell cal-cell-empty" />
//                         ))}
//                         {Array.from({ length: daysInMonth }, (_, i) => i + 1).map(d => (
//                             <div key={d}
//                                 className={[
//                                     "cal-cell",
//                                     isToday(d) ? "cal-today" : "",
//                                     selectedDay === d ? "cal-selected" : "",
//                                     interviewDays.has(d) ? "cal-has-event" : ""
//                                 ].join(" ")}
//                                 onClick={() => setSelectedDay(d)}>
//                                 <span>{d}</span>
//                                 {interviewDays.has(d) && (
//                                     <span className="cal-event-badge">{(scheduledDays[d] || []).length}</span>
//                                 )}
//                             </div>
//                         ))}
//                     </div>

//                     <div className="cal-events">
//                         <p className="cal-events-title">
//                             {new Date(year, month, selectedDay).toLocaleDateString("en-US", {
//                                 weekday: "long", month: "short", day: "numeric"
//                             })}
//                         </p>
//                         {dayInterviews.length === 0 ? (
//                             <p className="cal-events-empty">No interviews scheduled</p>
//                         ) : (
//                             dayInterviews.map((iv, i) => (
//                                 <div key={i} className="cal-event-item" onClick={() => setEventPopup(iv)}>
//                                     <div className="cal-event-time">
//                                         <span className="cal-event-clock">{iv.time || `${String(10 + i).padStart(2, "0")}:00`}</span>
//                                         <span className="cal-event-dur">{iv.dur || "1h"}</span>
//                                     </div>
//                                     <div className="cal-event-bar" />
//                                     <div className="cal-event-info">
//                                         <p className="cal-event-name">{iv.full_name}</p>
//                                         <p className="cal-event-role">{iv.job_name}</p>
//                                     </div>
//                                     <button
//                                         className="ep-popup-join-btn"
//                                         onClick={(e) => { e.stopPropagation(); startInterview(iv); }}>
//                                         Start Interview
//                                     </button>
//                                 </div>
//                             ))
//                         )}
//                     </div>
//                 </div>
//             </div>

//             {/* ── Event Popup ── */}
//             {eventPopup && (
//                 <div className="ep-overlay" onClick={() => setEventPopup(null)}>
//                     <div className="ep-popup" onClick={e => e.stopPropagation()}>

//                         <div className="ep-popup-header">
//                             <div>
//                                 <p className="ep-popup-time">{eventPopup.time} · {eventPopup.dur}</p>
//                                 <p className="ep-popup-title">{eventPopup.job_name}</p>
//                             </div>
//                             <button className="ep-popup-close" onClick={() => setEventPopup(null)}>✕</button>
//                         </div>

//                         <div className="ep-popup-candidate">
//                             <div className="ep-popup-avatar">{(eventPopup.full_name || "?")[0].toUpperCase()}</div>
//                             <div>
//                                 <p className="ep-popup-cname">{eventPopup.full_name}</p>
//                                 <p className="ep-popup-crole">{eventPopup.job_name}</p>
//                             </div>
//                         </div>

//                         <div className="ep-popup-meet-card">
//                             <div className="ep-popup-meet-icon">
//                                 <img src="/gmeet.svg" width="28" height="28" alt="Google Meet" />
//                             </div>
//                             <div className="ep-popup-meet-info">
//                                 <p className="ep-popup-meet-label">Google Meet</p>
//                                 <p className="ep-popup-meet-url">{eventPopup.meet || "Create a meeting to start"}</p>
//                             </div>
//                             <a
//                                 href={eventPopup.meet || "https://meet.google.com/"}
//                                 target="_blank"
//                                 rel="noreferrer"
//                                 className="ep-popup-join-btn">
//                                 Join Now
//                             </a>
//                         </div>

//                         <div className="ep-popup-actions">
//                             <button className="ep-popup-reschedule" onClick={() => setEventPopup(null)}>
//                                 ↻ Reschedule
//                             </button>
//                             <button className="ep-popup-view-btn" onClick={() => {
//                                 setEventPopup(null);
//                                 navigate("/hrdashboard/all", {
//                                     state: { candidateName: eventPopup.full_name, ts: Date.now() }
//                                 });
//                             }}>
//                                 View Profile
//                             </button>
//                         </div>

//                     </div>
//                 </div>
//             )}
//         </div>
//     );
// }










import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { FiEdit2, FiCheck, FiLogOut, FiChevronLeft, FiChevronRight } from "react-icons/fi";
import { LIVEHR_API, MAIN_API } from "../../shared/api.js";

export default function Profile() {
    const email = localStorage.getItem("hr_email") || "";
    const name = localStorage.getItem("hr_name") || "";

    const [editing, setEditing] = useState(false);
    const [saving, setSaving] = useState(false);
    const [form, setForm] = useState({
        name: name,
        title: localStorage.getItem("hr_title") || "",
        company: localStorage.getItem("hr_company") || "",
    });

    const [interviews, setInterviews] = useState([]);
    const [eventPopup, setEventPopup] = useState(null);
    const [calDate, setCalDate] = useState(new Date());
    const [selectedDay, setSelectedDay] = useState(new Date().getDate());

    const navigate = useNavigate();

    useEffect(() => {
        if (!email) return;
        fetch(`${MAIN_API}/user-profile?email=${encodeURIComponent(email)}`)
            .then((r) => (r.ok ? r.json() : null))
            .then((data) => {
                if (data?.name) {
                    setForm((f) => ({ ...f, name: data.name }));
                    localStorage.setItem("hr_name", data.name);
                }
            })
            .catch(() => {});
    }, [email]);

    const openLiveDesk = (token, fallbackUrl = "") => {
        const controlUrl = token ? `${window.location.origin}/livehr/${token}` : fallbackUrl;
        window.open(controlUrl || fallbackUrl, "_blank");
    };

    const startInterview = async (iv) => {
        // ── If a meet link is already assigned, go there directly ──
        if (iv.meet) {
            window.open(iv.meet, "_blank");
            return;
        }

        if (!iv.id) {
            const demoToken =
                Math.random().toString(36).substring(2, 15) +
                Math.random().toString(36).substring(2, 15);
            openLiveDesk(demoToken, "https://meet.jit.si/");
            return;
        }

        const hr_email = localStorage.getItem("hr_email") || "";
        const candidateName = iv.full_name;
        const jobName = iv.job_name;

        try {
            let appData = {};
            try {
                const appRes = await fetch(`${MAIN_API}/application/${iv.id}`);
                if (appRes.ok) appData = await appRes.json();
            } catch {
                // optional prefetch
            }

            let github_data = {};
            let eval_summary = "";
            let github_url = appData.github_url || "";
            try {
                const evalRes = await fetch(`${MAIN_API}/applications/${iv.id}/eval`);
                if (evalRes.ok) {
                    const ev = await evalRes.json();
                    github_data = ev.github_raw || {};
                    eval_summary = ev.eval_summary || ev.summary || "";
                }
            } catch {
                // optional prefetch
            }

            const now = new Date();
            const scheduledStr = now.toLocaleString("en-IN", {
                weekday: "long", day: "numeric", month: "long",
                year: "numeric", hour: "2-digit", minute: "2-digit"
            });

            const res = await fetch(`${LIVEHR_API}/livehr/session`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    application_id: iv.id,
                    candidate_name: candidateName,
                    candidate_email: appData.email || "",
                    job_title: jobName,
                    job_skills: appData.technical_skills || "",
                    github_url,
                    github_data,
                    eval_summary,
                    scheduled_time: scheduledStr,
                    hr_email,
                })
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            openLiveDesk(data.token, data.control_url || data.meet_url);

        } catch (e) {
            console.error("startInterview failed:", e);
            alert(`Could not start interview: ${e.message}\n\nMake sure Backend/livehr is running on port 8004.`);
        }
    };

    useEffect(() => {
        const hrEmail = localStorage.getItem("hr_email");
        if (!hrEmail) {
            setInterviews([]);
            return;
        }
        fetch(`${MAIN_API}/jobs/my/${encodeURIComponent(hrEmail)}`)
            .then((r) => (r.ok ? r.json() : []))
            .then(async (jobs) => {
                const all = [];
                await Promise.all(
                    (jobs || []).map(async (job) => {
                        try {
                            const res = await fetch(`${MAIN_API}/applications/${job.id}`);
                            if (!res.ok) return;
                            const apps = await res.json();
                            apps
                                .filter((a) => a.status === "selected")
                                .forEach((a) => {
                                    all.push({ ...a, job_name: job.job_name });
                                });
                        } catch {
                            /* ignore */
                        }
                    })
                );
                setInterviews(all);
            })
            .catch(() => setInterviews([]));
    }, []);

    const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

    const save = async () => {
        setSaving(true);
        localStorage.setItem("hr_name", form.name);
        localStorage.setItem("hr_title", form.title);
        localStorage.setItem("hr_company", form.company);
        await new Promise(r => setTimeout(r, 500));
        setSaving(false);
        setEditing(false);
    };

    const logout = () => { localStorage.clear(); window.location.href = "/"; };

    const initials = form.name.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase() || "HR";

    const year = calDate.getFullYear();
    const month = calDate.getMonth();
    const monthName = calDate.toLocaleDateString("en-US", { month: "long", year: "numeric" });
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    const isToday = (d) => d === today.getDate() && month === today.getMonth() && year === today.getFullYear();

    const allSchedules = interviews.map((iv, i) => ({
        ...iv,
        time: `${String(10 + i).padStart(2, "0")}:00`,
        dur: "1h",
        meet: "",
    }));

    const scheduledDays = {};
    allSchedules.forEach((s, i) => {
        const day = s.day != null ? s.day : ((i * 4 + 3) % daysInMonth) + 1;
        if (!scheduledDays[day]) scheduledDays[day] = [];
        scheduledDays[day].push(s);
    });
    const interviewDays = new Set(Object.keys(scheduledDays).map(Number));

    const prevMonth = () => setCalDate(new Date(year, month - 1, 1));
    const nextMonth = () => setCalDate(new Date(year, month + 1, 1));
    const dayInterviews = scheduledDays[selectedDay] || [];
    const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

    return (
        <div className="pf-main">

            {/* ── Top bar ── */}
            <div className="pf-topbar">
                <p className="pf-topbar-title">Profile</p>
                <div className="pf-topbar-right">
                    {!editing ? (
                        <button className="pf-btn-ghost" onClick={() => setEditing(true)}>
                            <FiEdit2 size={13} /> Edit
                        </button>
                    ) : (
                        <>
                            <button className="pf-btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
                            <button className="pf-btn-orange" onClick={save} disabled={saving}>
                                {saving ? <span className="pf-spin" /> : <FiCheck size={13} />}
                                {saving ? "Saving" : "Save"}
                            </button>
                        </>
                    )}
                    <button className="pf-btn-logout" onClick={logout}>
                        Logout <FiLogOut size={13} />
                    </button>
                </div>
            </div>

            <div className="pf-body">

                {/* ── Left ── */}
                <div className="pf-left">
                    <div className="pf-avatar-block">
                        <div className="pf-avatar">{initials}</div>
                        <div>
                            {editing ? (
                                <input className="pf-name-input" value={form.name}
                                    placeholder="Full name"
                                    onChange={e => set("name", e.target.value)} />
                            ) : (
                                <p className="pf-name">{form.name || "Your Name"}</p>
                            )}
                            <p className="pf-email">{email}</p>
                        </div>
                    </div>

                    <div className="pf-meta-rows">
                        <div className="pf-meta-row">
                            <span className="pf-meta-label">Role</span>
                            {editing ? (
                                <input className="pf-meta-input" value={form.title} placeholder="e.g. HR Manager" onChange={e => set("title", e.target.value)} />
                            ) : (
                                <span className="pf-meta-value">{form.title || "—"}</span>
                            )}
                        </div>
                        <div className="pf-meta-row">
                            <span className="pf-meta-label">Company</span>
                            {editing ? (
                                <input className="pf-meta-input" value={form.company} placeholder="Company name" onChange={e => set("company", e.target.value)} />
                            ) : (
                                <span className="pf-meta-value">{form.company || "—"}</span>
                            )}
                        </div>
                    </div>

                    <div className="pf-stats-row">
                        <div className="pf-stat">
                            <span className="pf-stat-num">{interviews.length}</span>
                            <span className="pf-stat-label">Selected</span>
                        </div>
                        <div className="pf-stat">
                            <span className="pf-stat-num">{allSchedules.length}</span>
                            <span className="pf-stat-label">Scheduled</span>
                        </div>
                    </div>
                </div>

                {/* ── Right: Calendar ── */}
                <div className="pf-right">
                    <div className="cal-header">
                        <button className="cal-nav" onClick={prevMonth}><FiChevronLeft size={15} /></button>
                        <p className="cal-month">{monthName}</p>
                        <button className="cal-nav" onClick={nextMonth}><FiChevronRight size={15} /></button>
                    </div>

                    <div className="cal-days-row">
                        {DAYS.map(d => <span key={d} className="cal-day-name">{d}</span>)}
                    </div>

                    <div className="cal-grid">
                        {Array.from({ length: firstDay }).map((_, i) => (
                            <div key={`e${i}`} className="cal-cell cal-cell-empty" />
                        ))}
                        {Array.from({ length: daysInMonth }, (_, i) => i + 1).map(d => (
                            <div key={d}
                                className={[
                                    "cal-cell",
                                    isToday(d) ? "cal-today" : "",
                                    selectedDay === d ? "cal-selected" : "",
                                    interviewDays.has(d) ? "cal-has-event" : ""
                                ].join(" ")}
                                onClick={() => setSelectedDay(d)}>
                                <span>{d}</span>
                                {interviewDays.has(d) && (
                                    <span className="cal-event-badge">{(scheduledDays[d] || []).length}</span>
                                )}
                            </div>
                        ))}
                    </div>

                    <div className="cal-events">
                        <p className="cal-events-title">
                            {new Date(year, month, selectedDay).toLocaleDateString("en-US", {
                                weekday: "long", month: "short", day: "numeric"
                            })}
                        </p>
                        {dayInterviews.length === 0 ? (
                            <p className="cal-events-empty">No interviews scheduled</p>
                        ) : (
                            dayInterviews.map((iv, i) => (
                                <div key={i} className="cal-event-item" onClick={() => setEventPopup(iv)}>
                                    <div className="cal-event-time">
                                        <span className="cal-event-clock">{iv.time || `${String(10 + i).padStart(2, "0")}:00`}</span>
                                        <span className="cal-event-dur">{iv.dur || "1h"}</span>
                                    </div>
                                    <div className="cal-event-bar" />
                                    <div className="cal-event-info">
                                        <p className="cal-event-name">{iv.full_name}</p>
                                        <p className="cal-event-role">{iv.job_name}</p>
                                    </div>
                                    <button
                                        className="ep-popup-join-btn"
                                        onClick={(e) => { e.stopPropagation(); startInterview(iv); }}>
                                        Start Interview
                                    </button>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            </div>

            {/* ── Event Popup ── */}
            {eventPopup && (
                <div className="ep-overlay" onClick={() => setEventPopup(null)}>
                    <div className="ep-popup" onClick={e => e.stopPropagation()}>

                        <div className="ep-popup-header">
                            <div>
                                <p className="ep-popup-time">{eventPopup.time} · {eventPopup.dur}</p>
                                <p className="ep-popup-title">{eventPopup.job_name}</p>
                            </div>
                            <button className="ep-popup-close" onClick={() => setEventPopup(null)}>✕</button>
                        </div>

                        <div className="ep-popup-candidate">
                            <div className="ep-popup-avatar">{(eventPopup.full_name || "?")[0].toUpperCase()}</div>
                            <div>
                                <p className="ep-popup-cname">{eventPopup.full_name}</p>
                                <p className="ep-popup-crole">{eventPopup.job_name}</p>
                            </div>
                        </div>

                        <div className="ep-popup-meet-card">
                            <div className="ep-popup-meet-icon">
                                <img src="/gmeet.svg" width="28" height="28" alt="Live Interview Room" />
                            </div>
                            <div className="ep-popup-meet-info">
                                <p className="ep-popup-meet-label">Live Interview Room</p>
                                <p className="ep-popup-meet-url">{eventPopup.meet || "Create a live room to start"}</p>
                            </div>
<a

                                href={eventPopup.meet || "https://meet.jit.si/"}
                                target="_blank"
                                rel="noreferrer"
                                className="ep-popup-join-btn">
                                Join Now
                            </a>
                        </div>

                        <div className="ep-popup-actions">
                            <button className="ep-popup-reschedule" onClick={() => setEventPopup(null)}>
                                ↻ Reschedule
                            </button>
                            <button className="ep-popup-view-btn" onClick={() => {
                                setEventPopup(null);
                                navigate("/hrdashboard/all", {
                                    state: { candidateName: eventPopup.full_name, ts: Date.now() }
                                });
                            }}>
                                View Profile
                            </button>
                        </div>

                    </div>
                </div>
            )}
        </div>
    );
}
