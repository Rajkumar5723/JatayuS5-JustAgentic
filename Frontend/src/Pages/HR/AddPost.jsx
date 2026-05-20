
// import { useState, useRef } from "react";
// import { useNavigate } from "react-router-dom";
// import { MdOutlineArrowForwardIos, MdOutlineArrowBackIosNew } from "react-icons/md";

// const skillOptions = [
//     "Python", "C", "Java", "JavaScript", "TypeScript", "C++", "C#", "Ruby", "Go", "Rust",
//     "Kotlin", "Swift", "PHP", "R", "MATLAB", "Dart", "Scala", "Perl", "Haskell", "Lua",
//     "Julia", "Elixir", "OCaml", "Groovy", "Assembly", "COBOL", "Fortran",

//     "HTML", "CSS", "SASS", "LESS", "Tailwind", "Bootstrap", "Material UI", "Chakra UI", "Ant Design",
//     "React", "Angular", "Vue", "Next.js", "Nuxt.js", "Svelte", "SolidJS", "Alpine.js", "jQuery",

//     "Node.js", "Express.js", "Django", "Flask", "Spring Boot", "ASP.NET", "Laravel", "CodeIgniter",
//     "FastAPI", "NestJS", "AdonisJS", "Phoenix", "Ruby on Rails", "Micronaut", "Quarkus",

//     "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "Firebase", "Supabase", "Redis",
//     "Cassandra", "DynamoDB", "Neo4j", "MariaDB", "CockroachDB", "InfluxDB", "TimescaleDB",

//     "GraphQL", "REST API", "gRPC", "WebSockets", "SOAP", "tRPC",

//     "Docker", "Kubernetes", "OpenShift", "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI",
//     "Travis CI", "CircleCI", "ArgoCD",

//     "Git", "GitLab", "Bitbucket", "SVN", "Mercurial",

//     "Linux", "Ubuntu", "Debian", "CentOS", "Bash", "Shell Scripting", "PowerShell", "Zsh",

//     "Nginx", "Apache", "Caddy",

//     "AWS", "Azure", "Google Cloud", "Firebase Hosting", "Vercel", "Netlify", "Heroku",
//     "DigitalOcean", "Cloudflare", "Render", "Fly.io",

//     "Terraform", "Ansible", "Pulumi", "Chef", "Puppet",

//     "Serverless", "Lambda", "Cloud Functions", "API Gateway",

//     "Machine Learning", "Deep Learning", "Reinforcement Learning", "TensorFlow", "PyTorch",
//     "Keras", "Scikit-learn", "XGBoost", "LightGBM", "CatBoost",

//     "OpenCV", "NLP", "Computer Vision", "Speech Recognition", "Transformers", "LLMs",
//     "Hugging Face", "LangChain", "Prompt Engineering",

//     "Data Science", "Data Analysis", "Data Engineering", "Data Visualization",
//     "Pandas", "NumPy", "Seaborn", "Matplotlib", "Plotly", "D3.js",

//     "Excel", "Power BI", "Tableau", "Looker",

//     "Big Data", "Hadoop", "Spark", "Kafka", "Flink", "Beam",

//     "ETL", "Data Warehousing", "Snowflake", "Redshift", "BigQuery", "Airflow", "dbt",

//     "Cybersecurity", "Ethical Hacking", "Penetration Testing", "OWASP", "Cryptography",
//     "Network Security", "Application Security", "SIEM", "SOC", "IDS/IPS",

//     "OAuth", "JWT", "SSO", "SAML", "Authentication", "Authorization",

//     "Networking", "TCP/IP", "UDP", "DNS", "HTTP/HTTPS", "SSL/TLS",

//     "System Design", "Design Patterns", "OOP", "Functional Programming", "Reactive Programming",

//     "Algorithms", "Data Structures", "Problem Solving", "Competitive Programming",

//     "Debugging", "Profiling", "Performance Optimization",

//     "Testing", "Unit Testing", "Integration Testing", "E2E Testing", "Jest", "Mocha",
//     "Chai", "Cypress", "Selenium", "Playwright", "Vitest", "JUnit", "TestNG",

//     "TDD", "BDD",

//     "Agile", "Scrum", "Kanban", "Project Management", "JIRA", "Confluence", "Notion", "Trello",

//     "Figma", "Adobe XD", "Sketch", "InVision",

//     "UI Design", "UX Design", "Wireframing", "Prototyping", "Design Systems", "Accessibility",

//     "SEO", "Content Writing", "Technical Writing", "Copywriting", "Social Media", "Digital Marketing", "Google Analytics", "Meta Ads",

//     "API Integration", "Payment Gateway", "Stripe", "Razorpay", "PayPal",

//     "WebRTC", "Three.js", "Canvas API", "WebGL",

//     "Game Development", "Unity", "Unreal Engine", "Godot",

//     "AR/VR", "Mixed Reality",

//     "Blockchain", "Solidity", "Web3", "Smart Contracts", "Ethereum", "Polygon",

//     "Embedded Systems", "IoT", "Arduino", "Raspberry Pi", "ESP32", "Robotics",

//     "Mobile Development", "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic",

//     "Electron", "Tauri", "Progressive Web Apps",

//     "Multithreading", "Concurrency", "Parallel Computing",

//     "Compiler Design", "Operating Systems", "Distributed Systems",

//     "Logging", "Monitoring", "Prometheus", "Grafana", "ELK Stack",

//     "Search", "Elasticsearch", "Algolia", "Meilisearch",

//     "Message Queues", "RabbitMQ", "ActiveMQ", "SQS",

//     "Versioning", "Semantic Versioning", "Monorepo", "Nx", "Lerna"
// ];


// const STEPS = [
//     { id: 1, label: "Job Details" },
//     { id: 2, label: "Application Setup" },
//     { id: 3, label: "Interview Config" },
// ];

// export default function AddPost() {
//     const navigate = useNavigate();
//     const [step, setStep] = useState(1);

//     const [submitState, setSubmitState] = useState("idle");
//     const [submitMsg, setSubmitMsg] = useState("");
//     const [showLIPopup, setShowLIPopup] = useState(false);

//     // Step 1
//     const [jobName, setJobName] = useState("");
//     const [description, setDescription] = useState("");
//     const [salaryStart, setSalaryStart] = useState("");
//     const [salaryEnd, setSalaryEnd] = useState("");
//     const [showSalary, setShowSalary] = useState(false);
//     const [workStyle, setWorkStyle] = useState([]);
//     const [jobType, setJobType] = useState("ft");
//     const [skills, setSkills] = useState([]);
//     const [skillSearch, setSkillSearch] = useState("");
//     const [showDropdown, setShowDropdown] = useState(false);
//     const [expMin, setExpMin] = useState("");
//     const [expMax, setExpMax] = useState("");
//     const [department, setDepartment] = useState("dev");
//     const [openings, setOpenings] = useState("");
//     const [deadline, setDeadline] = useState("");

//     // Step 2
//     const [appFields, setAppFields] = useState(["Resume/CV", "Full Name", "Location / address", "Email Id", "LinkedIn", "GitHub", "LeetCode", "Years of experience", "Technical skills", "Degree type"]);
//     const [customFields, setCustomFields] = useState([]);
//     const [customInput, setCustomInput] = useState("");

//     // Step 3
//     const [difficulty, setDifficulty] = useState("Easy");
//     const [rounds, setRounds] = useState(["Shortlisting Test", "Final HR Round"]);
//     const [platforms, setPlatforms] = useState(["LinkedIn"]);
//     const [fileName, setFileName] = useState("No file chosen");

//     const filteredSkills = skillSearch.length >= 1
//         ? skillOptions.filter(s => s.toLowerCase().startsWith(skillSearch.toLowerCase()) && !skills.includes(s))
//         : [];

//     const toggle = (setter, list, val) =>
//         setter(list.includes(val) ? list.filter(v => v !== val) : [...list, val]);

//     const addCustomField = () => {
//         if (!customInput.trim()) return;
//         setCustomFields([...customFields, customInput.trim()]);
//         setCustomInput("");
//     };

//     const handleConnectLinkedIn = () => {
//         const email = localStorage.getItem("hr_email");
//         window.location.href = `http://127.0.0.1:8000/linkedin/connect?email=${encodeURIComponent(email)}`;
//     };

//     const handleSubmit = async () => {
//         const hrEmail = localStorage.getItem("hr_email");
//         if (!hrEmail) { setSubmitMsg("Not logged in."); return; }
//         if (!jobName || !description || !openings) { setSubmitMsg("Fill all required fields."); return; }

//         try {
//             if (platforms.includes("LinkedIn")) {
//                 setSubmitState("checking");
//                 setSubmitMsg("Verifying LinkedIn connection…");
//                 const r = await fetch(`http://127.0.0.1:8000/linkedin/status/${hrEmail}`);
//                 const d = await r.json();
//                 if (!d.connected) {
//                     setSubmitState("idle");
//                     setSubmitMsg("");
//                     setShowLIPopup(true);
//                     return;
//                 }
//             }

//             setSubmitState("saving");
//             setSubmitMsg("Saving job listing…");
//             const payload = {
//                 posted_by: hrEmail, job_name: jobName, description,
//                 salary_start: salaryStart, salary_end: salaryEnd,
//                 show_salary: showSalary ? "true" : "false",
//                 work_style: workStyle.join(","),
//                 location: workStyle.includes("On-Site") ? location : "",
//                 job_type: jobType,
//                 skills: skills.join(","), exp_min: expMin, exp_max: expMax,
//                 department, openings: parseInt(openings), deadline,
//                 application_fields: [...appFields, ...customFields].join(","),
//                 difficulty, rounds: rounds.join(","), platforms: platforms.join(","),
//             };
//             const saveRes = await fetch("http://127.0.0.1:8000/jobs", {
//                 method: "POST", headers: { "Content-Type": "application/json" },
//                 body: JSON.stringify(payload),
//             });
//             const saveData = await saveRes.json();
//             if (!saveRes.ok) { setSubmitMsg(saveData.detail || "Failed to save."); setSubmitState("error"); return; }

//             if (platforms.includes("LinkedIn")) {
//                 setSubmitState("posting");
//                 setSubmitMsg("Publishing to LinkedIn…");
//                 const liRes = await fetch(`http://127.0.0.1:8000/jobs/${saveData.id}/post-linkedin`, { method: "POST" });
//                 const liData = await liRes.json();
//                 setSubmitMsg(liData.success ? "Job saved & posted to LinkedIn!" : `Job saved! LinkedIn: ${liData.error || "Post failed"}`);
//             } else {
//                 setSubmitMsg("Job posted successfully!");
//             }

//             setSubmitState("done");
//             setTimeout(() => navigate("/hrdashboard/all"), 2000);

//         } catch {
//             setSubmitMsg("Server error. Is the backend running?");
//             setSubmitState("error");
//         }
//     };

//     const btnLabel = { idle: "Publish Job", checking: "Checking…", saving: "Saving…", posting: "Publishing…", done: "Done ✓", error: "Retry" }[submitState];
//     const isBusy = ["checking", "saving", "posting", "done"].includes(submitState);

//     return (
//         <main className="ap-main">

//             {/* ── STEP TAB BAR ── */}
//             <div className="ap-tabbar">
//                 {STEPS.map((s) => (
//                     <div key={s.id}
//                         className={`ap-tab ${step === s.id ? "active" : ""} ${step > s.id ? "done" : ""}`}
//                         onClick={() => setStep(s.id)}>
//                         <span className="ap-tab-num">0{s.id}</span>
//                         <span className="ap-tab-label">{s.label}</span>
//                     </div>
//                 ))}
//             </div>

//             {/* ── STEP 1 ── */}
//             {step === 1 && (
//                 <section className="ap-section">
//                     <div className="ap-section-header">
//                         <h2 className="ap-section-title">Job Details</h2>
//                         <p className="ap-section-sub">Define the role, compensation, and requirements</p>
//                     </div>
//                     <div className="ap-grid">
//                         {/* Left column */}
//                         <div className="ap-col">
//                             <div className="ap-field">
//                                 <label className="ap-label">Job Title <span className="ap-required">*</span></label>
//                                 <input type="text" className="ap-input" placeholder="e.g. Senior Frontend Engineer" value={jobName} onChange={e => setJobName(e.target.value)} />
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Job Description <span className="ap-required">*</span></label>
//                                 <textarea className="ap-input ap-textarea" placeholder="Describe responsibilities, expectations, and team culture…" rows={5} value={description} onChange={e => setDescription(e.target.value)} />
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Annual Salary Range <span className="ap-hint">(optional)</span></label>
//                                 <div className="ap-row-gap">
//                                     <input type="text" className="ap-input" placeholder="Min (e.g. ₹8L)" value={salaryStart} onChange={e => setSalaryStart(e.target.value)} />
//                                     <input type="text" className="ap-input" placeholder="Max (e.g. ₹20L)" value={salaryEnd} onChange={e => setSalaryEnd(e.target.value)} />
//                                 </div>
//                                 <label className="ap-checkbox-small">
//                                     <input type="checkbox" checked={showSalary} onChange={e => setShowSalary(e.target.checked)} />
//                                     Display salary on job listing
//                                 </label>
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Work Style</label>
//                                 <div className="ap-chip-group">
//                                     {["On-Site", "Hybrid", "Remote"].map(ws => (
//                                         <button key={ws} type="button"
//                                             className={`ap-chip ${workStyle.includes(ws) ? "selected" : ""}`}
//                                             onClick={() => toggle(setWorkStyle, workStyle, ws)}>{ws}</button>
//                                     ))}
//                                 </div>
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Employment Type <span className="ap-required">*</span></label>
//                                 <select className="ap-input ap-select" value={jobType} onChange={e => setJobType(e.target.value)}>
//                                     <option value="ft">Full-Time</option>
//                                     <option value="pt">Part-Time</option>
//                                     <option value="ct">Contract</option>
//                                 </select>
//                             </div>
//                         </div>

//                         {/* Right column */}
//                         <div className="ap-col">
//                             <div className="ap-field">
//                                 <label className="ap-label">Required Skills</label>
//                                 <div className="ap-tags-wrapper">
//                                     {skills.length > 0 && (
//                                         <div className="ap-tags">
//                                             {skills.map(s => (
//                                                 <span key={s} className="ap-tag">{s}
//                                                     <button onClick={() => setSkills(skills.filter(x => x !== s))} className="ap-tag-remove">×</button>
//                                                 </span>
//                                             ))}
//                                         </div>
//                                     )}
//                                     <input type="text" className="ap-input" placeholder="Search and add skills…"
//                                         value={skillSearch}
//                                         onChange={e => { setSkillSearch(e.target.value); setShowDropdown(true); }}
//                                         onFocus={() => setShowDropdown(true)}
//                                         onBlur={() => setTimeout(() => setShowDropdown(false), 150)} />
//                                     {showDropdown && filteredSkills.length > 0 && (
//                                         <ul className="ap-dropdown">
//                                             {filteredSkills.map(s => (
//                                                 <li key={s} className="ap-dropdown-item"
//                                                     onMouseDown={() => { setSkills([...skills, s]); setSkillSearch(""); setShowDropdown(false); }}>{s}</li>
//                                             ))}
//                                         </ul>
//                                     )}
//                                 </div>
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Experience Range <span className="ap-hint">(years)</span></label>
//                                 <div className="ap-row-gap">
//                                     <input type="text" className="ap-input" placeholder="Min" value={expMin} onChange={e => setExpMin(e.target.value)} />
//                                     <input type="text" className="ap-input" placeholder="Max" value={expMax} onChange={e => setExpMax(e.target.value)} />
//                                 </div>
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Department <span className="ap-required">*</span></label>
//                                 <select className="ap-input ap-select" value={department} onChange={e => setDepartment(e.target.value)}>
//                                     <option value="dev">Development</option>
//                                     <option value="sal">Sales</option>
//                                     <option value="mkt">Marketing</option>
//                                 </select>
//                             </div>
//                             <div className="ap-row-gap">
//                                 <div className="ap-field" style={{ flex: 1 }}>
//                                     <label className="ap-label">Openings <span className="ap-required">*</span></label>
//                                     <input type="text" className="ap-input" placeholder="e.g. 3" value={openings} onChange={e => setOpenings(e.target.value)} />
//                                 </div>
//                                 <div className="ap-field" style={{ flex: 1 }}>
//                                     <label className="ap-label">Application Deadline</label>
//                                     <input type="date" className="ap-input" value={deadline} onChange={e => setDeadline(e.target.value)} />
//                                 </div>
//                             </div>
//                             <div className="ap-nav-row" style={{ marginTop: "auto" }}>
//                                 <button type="button" className="ap-btn-primary" onClick={() => setStep(2)}>
//                                     Application Setup <MdOutlineArrowForwardIos />
//                                 </button>
//                             </div>
//                         </div>
//                     </div>
//                 </section>
//             )}

//             {/* ── STEP 2 ── */}
//             {step === 2 && (
//                 <section className="ap-section">
//                     <div className="ap-section-header">
//                         <h2 className="ap-section-title">Application Setup</h2>
//                         <p className="ap-section-sub">Choose what information applicants must provide</p>
//                     </div>
//                     <div className="ap-grid">
//                         <div className="ap-col">
//                             {[
//                                 { label: "Resume & Portfolio", fields: ["Resume/CV", "Cover letter", "Portfolio link"] },
//                                 { label: "Personal Information", fields: ["Full Name", "Location / address"] },
//                                 { label: "Contact Details", fields: ["Email Id", "Phone Number", "Alternative Number"] },
//                                 { label: "Education", fields: ["Degree type", "Field of study", "Institution name"] },
//                                 { label: "Work Experience", fields: ["Years of experience", "Current/past job titles", "Company names", "Current LPA", "Notice Period"] },
//                             ].map(({ label, fields }) => (
//                                 <div key={label} className="ap-field">
//                                     <label className="ap-label">{label}</label>
//                                     <div className="ap-check-group">
//                                         {fields.map(f => (
//                                             <label key={f} className="ap-check-item">
//                                                 <input type="checkbox" checked={appFields.includes(f)} onChange={() => toggle(setAppFields, appFields, f)} />
//                                                 <span>{f}</span>
//                                             </label>
//                                         ))}
//                                     </div>
//                                 </div>
//                             ))}
//                         </div>
//                         <div className="ap-col">
//                             {[
//                                 { label: "Skills & Qualifications", fields: ["Technical skills", "Soft skills", "Certifications / licenses"] },
//                                 { label: "Online Profiles", fields: ["LinkedIn", "GitHub", "LeetCode", "Codeforces", "HackerRank", "Kaggle", "Stack Overflow", "Medium"] },
//                             ].map(({ label, fields }) => (
//                                 <div key={label} className="ap-field">
//                                     <label className="ap-label">{label}</label>
//                                     <div className="ap-check-group">
//                                         {fields.map(f => (
//                                             <label key={f} className="ap-check-item">
//                                                 <input type="checkbox" checked={appFields.includes(f)} onChange={() => toggle(setAppFields, appFields, f)} />
//                                                 <span>{f}</span>
//                                             </label>
//                                         ))}
//                                     </div>
//                                 </div>
//                             ))}
//                             <div className="ap-field">
//                                 <label className="ap-label">Custom Fields</label>
//                                 <div className="ap-custom-row">
//                                     <input type="text" className="ap-input" placeholder="e.g. Portfolio URL, GitHub username…"
//                                         value={customInput} onChange={e => setCustomInput(e.target.value)}
//                                         onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addCustomField())} />
//                                     <button type="button" className="ap-btn-add" onClick={addCustomField}>+ Add</button>
//                                 </div>
//                                 <div className="ap-custom-list">
//                                     {customFields.map((f, i) => (
//                                         <div key={i} className="ap-custom-item">
//                                             <input type="text" className="ap-input" value={f}
//                                                 onChange={e => { const u = [...customFields]; u[i] = e.target.value; setCustomFields(u); }} />
//                                             <button type="button" className="ap-custom-remove" onClick={() => setCustomFields(customFields.filter((_, j) => j !== i))}>×</button>
//                                         </div>
//                                     ))}
//                                 </div>
//                             </div>
//                             <div className="ap-nav-row" style={{ marginTop: "auto" }}>
//                                 <button type="button" className="ap-btn-secondary" onClick={() => setStep(1)}>
//                                     <MdOutlineArrowBackIosNew /> Job Details
//                                 </button>
//                                 <button type="button" className="ap-btn-primary" onClick={() => setStep(3)}>
//                                     Interview Config <MdOutlineArrowForwardIos />
//                                 </button>
//                             </div>
//                         </div>
//                     </div>
//                 </section>
//             )}

//             {/* ── STEP 3 ── */}
//             {step === 3 && (
//                 <section className="ap-section">
//                     <div className="ap-section-header">
//                         <h2 className="ap-section-title">Interview Configuration</h2>
//                         <p className="ap-section-sub">Configure rounds, difficulty, and publishing platforms</p>
//                     </div>
//                     <div className="ap-grid">
//                         <div className="ap-col">
//                             <label className="ap-label" style={{ marginBottom: "0.5em" }}>Interview Rounds</label>
//                             {[
//                                 { title: "Shortlisting Test", sub: ["MCQ Test", "Chat Test", "Vibe Coding", "Aptitude / Logical"] },
//                                 { title: "Communication Round", sub: ["Group Discussion", "Verbal Ability Test", "Spoken English Test", "Situation Response", "Presentation Round", "Role Play Conversation"] },
//                                 { title: "System Design Round", sub: ["Basic Programming", "OOP Concepts", "Database Design", "API Design", "Scalability Discussion"] },
//                                 { title: "Final HR Round", sub: ["Technical HR", "Salary & Policy Discussion"] },
//                             ].map(({ title, sub }) => (
//                                 <div key={title} className="ap-round-block">
//                                     {/* Title is now a plain label — no checkbox */}
//                                     <span className="ap-label ap-check-parent">{title}</span>
//                                     <div className="ap-check-group ap-check-indent">
//                                         {sub.map(s => (
//                                             <label key={s} className="ap-check-item">
//                                                 <input type="checkbox" checked={rounds.includes(s)} onChange={() => toggle(setRounds, rounds, s)} />
//                                                 <span>{s}</span>
//                                             </label>
//                                         ))}
//                                     </div>
//                                 </div>
//                             ))}
//                         </div>
//                         <div className="ap-col">
//                             <div className="ap-field">
//                                 <label className="ap-label">Difficulty Level</label>
//                                 <div className="ap-chip-group">
//                                     {["Easy", "Medium", "Hard"].map(d => (
//                                         <button key={d} type="button"
//                                             className={`ap-chip ap-chip-difficulty ap-chip-${d.toLowerCase()} ${difficulty === d ? "selected" : ""}`}
//                                             onClick={() => setDifficulty(d)}>{d}</button>
//                                     ))}
//                                 </div>
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Questions Bank <span className="ap-hint">(CSV)</span></label>
//                                 <label className="ap-file-label">
//                                     <input type="file" accept=".csv" className="ap-file-input" onChange={e => setFileName(e.target.files[0]?.name || "No file chosen")} />
//                                     <span className="ap-file-btn">📎 Upload CSV</span>
//                                     <span className="ap-file-name">{fileName}</span>
//                                 </label>
//                             </div>
//                             <div className="ap-field">
//                                 <label className="ap-label">Publish To</label>
//                                 <div className="ap-chip-group ap-chip-wrap">
//                                     {["LinkedIn", "Naukri", "Indeed", "Glassdoor", "Internshala"].map(p => (
//                                         <button key={p} type="button"
//                                             className={`ap-chip ${platforms.includes(p) ? "selected" : ""}`}
//                                             onClick={() => toggle(setPlatforms, platforms, p)}>{p}</button>
//                                     ))}
//                                 </div>
//                             </div>

//                             {submitMsg && (
//                                 <div className={`ap-status ap-status-${submitState}`}>
//                                     {submitState === "checking" || submitState === "saving" || submitState === "posting"
//                                         ? <span className="ap-spinner" /> : null}
//                                     {submitMsg}
//                                 </div>
//                             )}

//                             <div className="ap-nav-row" style={{ marginTop: "auto" }}>
//                                 <button type="button" className="ap-btn-secondary" onClick={() => setStep(2)}>
//                                     <MdOutlineArrowBackIosNew /> Application Setup
//                                 </button>
//                                 <button type="button"
//                                     className={`ap-btn-primary ap-btn-publish ${isBusy ? "busy" : ""} ${submitState === "done" ? "done" : ""}`}
//                                     onClick={!isBusy ? handleSubmit : undefined}
//                                     disabled={isBusy}>
//                                     {btnLabel}
//                                 </button>
//                             </div>
//                         </div>
//                     </div>
//                 </section>
//             )}

//             {/* ── LINKEDIN POPUP ── */}
//             {showLIPopup && (
//                 <div className="ap-overlay" onClick={() => setShowLIPopup(false)}>
//                     <div className="ap-popup" onClick={e => e.stopPropagation()}>
//                         <div className="ap-popup-icon">🔗</div>
//                         <h3 className="ap-popup-title">Connect LinkedIn Account</h3>
//                         <p className="ap-popup-body">
//                             You'll be redirected to LinkedIn to authorise access. Once approved, you'll be brought back automatically — no tokens or manual setup needed.
//                         </p>
//                         <div className="ap-popup-actions">
//                             <button className="ap-btn-secondary" onClick={() => setShowLIPopup(false)}>Cancel</button>
//                             <button className="ap-btn-primary" onClick={handleConnectLinkedIn}>Connect LinkedIn</button>
//                         </div>
//                     </div>
//                 </div>
//             )}
//         </main>
//     );
// }



import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { MdOutlineArrowForwardIos, MdOutlineArrowBackIosNew, MdArrowUpward, MdArrowDownward, MdAdd, MdDelete } from "react-icons/md";
import { MAIN_API } from "../../shared/api.js";
import {
    AVAILABLE_ROUND_TYPES,
    HR_ROUND_TYPES,
    FINAL_HR_STAGE_NAME,
    createDefaultStages,
    ensureFinalHrLast,
    serializeInterviewConfig,
    validateInterviewStages,
    getUsedRoundTypes,
    moveItem,
    uid,
} from "../../shared/interviewConfig";
import { APP_FIELD_ORDER } from "../../shared/applicationFields";

const skillOptions = [
    "Python", "C", "Java", "JavaScript", "TypeScript", "C++", "C#", "Ruby", "Go", "Rust",
    "Kotlin", "Swift", "PHP", "R", "MATLAB", "Dart", "Scala", "Perl", "Haskell", "Lua",
    "Julia", "Elixir", "OCaml", "Groovy", "Assembly", "COBOL", "Fortran",
    "HTML", "CSS", "SASS", "LESS", "Tailwind", "Bootstrap", "Material UI", "Chakra UI", "Ant Design",
    "React", "Angular", "Vue", "Next.js", "Nuxt.js", "Svelte", "SolidJS", "Alpine.js", "jQuery",
    "Node.js", "Express.js", "Django", "Flask", "Spring Boot", "ASP.NET", "Laravel", "CodeIgniter",
    "FastAPI", "NestJS", "AdonisJS", "Phoenix", "Ruby on Rails", "Micronaut", "Quarkus",
    "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Oracle", "Firebase", "Supabase", "Redis",
    "Cassandra", "DynamoDB", "Neo4j", "MariaDB", "CockroachDB", "InfluxDB", "TimescaleDB",
    "GraphQL", "REST API", "gRPC", "WebSockets", "SOAP", "tRPC",
    "Docker", "Kubernetes", "OpenShift", "CI/CD", "Jenkins", "GitHub Actions", "GitLab CI",
    "Travis CI", "CircleCI", "ArgoCD",
    "Git", "GitLab", "Bitbucket", "SVN", "Mercurial",
    "Linux", "Ubuntu", "Debian", "CentOS", "Bash", "Shell Scripting", "PowerShell", "Zsh",
    "Nginx", "Apache", "Caddy",
    "AWS", "Azure", "Google Cloud", "Firebase Hosting", "Vercel", "Netlify", "Heroku",
    "DigitalOcean", "Cloudflare", "Render", "Fly.io",
    "Terraform", "Ansible", "Pulumi", "Chef", "Puppet",
    "Serverless", "Lambda", "Cloud Functions", "API Gateway",
    "Machine Learning", "Deep Learning", "Reinforcement Learning", "TensorFlow", "PyTorch",
    "Keras", "Scikit-learn", "XGBoost", "LightGBM", "CatBoost",
    "OpenCV", "NLP", "Computer Vision", "Speech Recognition", "Transformers", "LLMs",
    "Hugging Face", "LangChain", "Prompt Engineering",
    "Data Science", "Data Analysis", "Data Engineering", "Data Visualization",
    "Pandas", "NumPy", "Seaborn", "Matplotlib", "Plotly", "D3.js",
    "Excel", "Power BI", "Tableau", "Looker",
    "Big Data", "Hadoop", "Spark", "Kafka", "Flink", "Beam",
    "ETL", "Data Warehousing", "Snowflake", "Redshift", "BigQuery", "Airflow", "dbt",
    "Cybersecurity", "Ethical Hacking", "Penetration Testing", "OWASP", "Cryptography",
    "Network Security", "Application Security", "SIEM", "SOC", "IDS/IPS",
    "OAuth", "JWT", "SSO", "SAML", "Authentication", "Authorization",
    "Networking", "TCP/IP", "UDP", "DNS", "HTTP/HTTPS", "SSL/TLS",
    "System Design", "Design Patterns", "OOP", "Functional Programming", "Reactive Programming",
    "Algorithms", "Data Structures", "Problem Solving", "Competitive Programming",
    "Debugging", "Profiling", "Performance Optimization",
    "Testing", "Unit Testing", "Integration Testing", "E2E Testing", "Jest", "Mocha",
    "Chai", "Cypress", "Selenium", "Playwright", "Vitest", "JUnit", "TestNG",
    "TDD", "BDD",
    "Agile", "Scrum", "Kanban", "Project Management", "JIRA", "Confluence", "Notion", "Trello",
    "Figma", "Adobe XD", "Sketch", "InVision",
    "UI Design", "UX Design", "Wireframing", "Prototyping", "Design Systems", "Accessibility",
    "SEO", "Content Writing", "Technical Writing", "Copywriting", "Social Media", "Digital Marketing", "Google Analytics", "Meta Ads",
    "API Integration", "Payment Gateway", "Stripe", "Razorpay", "PayPal",
    "WebRTC", "Three.js", "Canvas API", "WebGL",
    "Game Development", "Unity", "Unreal Engine", "Godot",
    "AR/VR", "Mixed Reality",
    "Blockchain", "Solidity", "Web3", "Smart Contracts", "Ethereum", "Polygon",
    "Embedded Systems", "IoT", "Arduino", "Raspberry Pi", "ESP32", "Robotics",
    "Mobile Development", "Android", "iOS", "React Native", "Flutter", "Xamarin", "Ionic",
    "Electron", "Tauri", "Progressive Web Apps",
    "Multithreading", "Concurrency", "Parallel Computing",
    "Compiler Design", "Operating Systems", "Distributed Systems",
    "Logging", "Monitoring", "Prometheus", "Grafana", "ELK Stack",
    "Search", "Elasticsearch", "Algolia", "Meilisearch",
    "Message Queues", "RabbitMQ", "ActiveMQ", "SQS",
    "Versioning", "Semantic Versioning", "Monorepo", "Nx", "Lerna"
];

const NON_HR_ROUND_TYPES = AVAILABLE_ROUND_TYPES.filter((t) => !HR_ROUND_TYPES.has(t));
const HR_ONLY_ROUND_TYPES = AVAILABLE_ROUND_TYPES.filter((t) => HR_ROUND_TYPES.has(t));

// Platforms: only LinkedIn is live
const PUBLISH_PLATFORMS = [
    { name: "LinkedIn", live: true },
    { name: "Naukri", live: false },
    { name: "Indeed", live: false },
    { name: "Glassdoor", live: false },
    { name: "Internshala", live: false },
];

const STEPS = [
    { id: 1, label: "Job Details" },
    { id: 2, label: "Application Setup" },
    { id: 3, label: "Interview Config" },
];

const DEFAULT_APP_FIELD_MODES = () => {
    const m = {};
    ["Resume/CV", "Full Name", "Location / address", "Email Id", "LinkedIn", "GitHub", "LeetCode", "Years of experience", "Technical skills", "Degree type"].forEach((k) => {
        m[k] = "mandatory";
    });
    return m;
};

function serializeApplicationFields(fieldModes, customFields) {
    const out = [];
    for (const key of APP_FIELD_ORDER) {
        const mode = fieldModes[key];
        if (mode === "optional") out.push(`${key}?`);
        if (mode === "mandatory") out.push(`${key}!`);
    }
    for (const c of customFields) {
        const mode = fieldModes[c] || "optional";
        if (mode === "optional") out.push(`${c}?`);
        else if (mode === "mandatory") out.push(`${c}!`);
    }
    return out.join(",");
}

export default function AddPost() {
    const navigate = useNavigate();
    const [step, setStep] = useState(1);

    const [submitState, setSubmitState] = useState("idle");
    const [submitMsg, setSubmitMsg] = useState("");
    const [showLIPopup, setShowLIPopup] = useState(false);

    // Step 1
    const [jobName, setJobName] = useState("");
    const [description, setDescription] = useState("");
    const [salaryStart, setSalaryStart] = useState("");
    const [salaryEnd, setSalaryEnd] = useState("");
    const [showSalary, setShowSalary] = useState(false);
    const [workStyle, setWorkStyle] = useState("On-Site");
    const [jobType, setJobType] = useState("ft");
    const [skills, setSkills] = useState([]);
    const [skillSearch, setSkillSearch] = useState("");
    const [showDropdown, setShowDropdown] = useState(false);
    const [expMin, setExpMin] = useState("");
    const [expMax, setExpMax] = useState("");
    const [department, setDepartment] = useState("dev");
    const [openings, setOpenings] = useState("");
    const [deadline, setDeadline] = useState("");
    const [location, setLocation] = useState("");
    const [locationLoading, setLocationLoading] = useState(false);
    const [spellState, setSpellState] = useState("idle"); // idle | checking | done | error

    // Today in YYYY-MM-DD for deadline min
    const todayStr = new Date().toISOString().split("T")[0];

    // ── Spell-check / grammar-fix via Groq ──────────────────────
    const handleSpellCheck = async () => {
        if (!description.trim()) return;
        setSpellState("checking");
        try {
            const res = await fetch(`${MAIN_API}/ai/spellcheck`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: description }),
            });
            if (!res.ok) throw new Error("API error");
            const data = await res.json();
            setDescription(data.corrected || description);
            setSpellState("done");
            setTimeout(() => setSpellState("idle"), 2500);
        } catch {
            setSpellState("error");
            setTimeout(() => setSpellState("idle"), 2000);
        }
    };

    // ── Auto-location from browser GPS ──────────────────────────
    const handleOnSiteLocation = () => {
        if (!navigator.geolocation) return;
        setLocationLoading(true);
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                try {
                    const { latitude, longitude } = pos.coords;
                    const r = await fetch(
                        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${latitude}&lon=${longitude}`
                    );
                    const d = await r.json();
                    const addr = d.address || {};
                    const city  = addr.city || addr.town || addr.village || addr.county || "";
                    const state = addr.state || "";
                    const country = addr.country || "";
                    const loc = [city, state, country].filter(Boolean).join(", ");
                    setLocation(loc);
                } catch {
                    setLocation("");
                } finally {
                    setLocationLoading(false);
                }
            },
            () => setLocationLoading(false),
            { timeout: 8000 }
        );
    };

    // Step 2 — per field: off | optional (single click) | mandatory (double click)
    const [appFieldModes, setAppFieldModes] = useState(DEFAULT_APP_FIELD_MODES);
    const [customFields, setCustomFields] = useState([]);
    const [customInput, setCustomInput] = useState("");
    const apClickTimerRef = useRef(null);
    const apClickFieldRef = useRef(null);

    // Step 3 — ordered stages with nested inner rounds
    const [difficulty, setDifficulty] = useState("Easy");
    const [interviewStages, setInterviewStages] = useState(createDefaultStages);
    const [interviewConfigError, setInterviewConfigError] = useState("");
    const [platforms, setPlatforms] = useState(["LinkedIn"]);
    const [fileName, setFileName] = useState("No file chosen");
    const [pdfFile, setPdfFile] = useState(null);

    const filteredSkills = skillSearch.length >= 1
        ? skillOptions.filter(s => s.toLowerCase().startsWith(skillSearch.toLowerCase()) && !skills.includes(s))
        : [];

    const toggle = (setter, list, val) =>
        setter(list.includes(val) ? list.filter(v => v !== val) : [...list, val]);

    const applyApFieldSingle = (fieldName) => {
        setAppFieldModes((prev) => {
            const cur = prev[fieldName] || "off";
            if (cur === "off") return { ...prev, [fieldName]: "optional" };
            if (cur === "optional") return { ...prev, [fieldName]: "off" };
            if (cur === "mandatory") return { ...prev, [fieldName]: "optional" };
            return prev;
        });
    };

    const applyApFieldDouble = (fieldName) => {
        setAppFieldModes((prev) => ({ ...prev, [fieldName]: "mandatory" }));
    };

    const onApFieldClick = (fieldName) => {
        if (apClickTimerRef.current && apClickFieldRef.current === fieldName) {
            clearTimeout(apClickTimerRef.current);
            apClickTimerRef.current = null;
            apClickFieldRef.current = null;
            applyApFieldDouble(fieldName);
            return;
        }
        if (apClickTimerRef.current) {
            clearTimeout(apClickTimerRef.current);
            apClickTimerRef.current = null;
        }
        apClickFieldRef.current = fieldName;
        apClickTimerRef.current = setTimeout(() => {
            apClickTimerRef.current = null;
            apClickFieldRef.current = null;
            applyApFieldSingle(fieldName);
        }, 260);
    };

    const apFieldMode = (name) => appFieldModes[name] || "off";

    const orderedStages = ensureFinalHrLast(interviewStages);
    const usedRoundTypes = getUsedRoundTypes(orderedStages);

    const addStage = () => {
        setInterviewConfigError("");
        const regular = orderedStages.filter((s) => !s.isFinalHr);
        const nextNum = regular.length + 1;
        const newStage = { id: uid(), name: `Stage ${nextNum}`, isFinalHr: false, rounds: [] };
        const final = orderedStages.filter((s) => s.isFinalHr);
        setInterviewStages([...regular, newStage, ...final]);
    };

    const removeStage = (stageId) => {
        setInterviewConfigError("");
        setInterviewStages((prev) => prev.filter((s) => s.id !== stageId || s.isFinalHr));
    };

    const moveStage = (stageId, direction) => {
        setInterviewConfigError("");
        setInterviewStages((prev) => {
            const ordered = ensureFinalHrLast(prev);
            const idx = ordered.findIndex((s) => s.id === stageId);
            if (idx < 0 || ordered[idx].isFinalHr) return prev;
            const finalIdx = ordered.findIndex((s) => s.isFinalHr);
            if (direction > 0 && idx >= finalIdx - 1) return prev;
            const regular = ordered.filter((s) => !s.isFinalHr);
            const final = ordered.filter((s) => s.isFinalHr);
            const regIdx = regular.findIndex((s) => s.id === stageId);
            const moved = moveItem(regular, regIdx, direction);
            return [...moved, ...final];
        });
    };

    const renameStage = (stageId, name) => {
        setInterviewStages((prev) =>
            prev.map((s) => (s.id === stageId && !s.isFinalHr ? { ...s, name } : s))
        );
    };

    const addInnerRound = (stageId, type) => {
        if (!type || usedRoundTypes.has(type)) return;
        setInterviewConfigError("");
        setInterviewStages((prev) =>
            prev.map((s) =>
                s.id === stageId
                    ? { ...s, rounds: [...(s.rounds || []), { id: uid(), type }] }
                    : s
            )
        );
    };

    const removeInnerRound = (stageId, roundId) => {
        setInterviewConfigError("");
        setInterviewStages((prev) =>
            prev.map((s) =>
                s.id === stageId
                    ? { ...s, rounds: (s.rounds || []).filter((r) => r.id !== roundId) }
                    : s
            )
        );
    };

    const moveInnerRound = (stageId, roundId, direction) => {
        setInterviewStages((prev) =>
            prev.map((s) => {
                if (s.id !== stageId) return s;
                const idx = (s.rounds || []).findIndex((r) => r.id === roundId);
                if (idx < 0) return s;
                return { ...s, rounds: moveItem(s.rounds || [], idx, direction) };
            })
        );
    };

    const changeInnerRoundType = (stageId, roundId, type) => {
        if (!type) return;
        const current = orderedStages.find((s) => s.id === stageId)?.rounds?.find((r) => r.id === roundId)?.type;
        if (usedRoundTypes.has(type) && type !== current) {
            setInterviewConfigError(`"${type}" is already used. Each test type can only appear once.`);
            return;
        }
        setInterviewConfigError("");
        setInterviewStages((prev) =>
            prev.map((s) =>
                s.id === stageId
                    ? {
                          ...s,
                          rounds: (s.rounds || []).map((r) => (r.id === roundId ? { ...r, type } : r)),
                      }
                    : s
            )
        );
    };

    const addCustomField = () => {
        if (!customInput.trim()) return;
        const name = customInput.trim();
        if (customFields.includes(name) || APP_FIELD_ORDER.includes(name)) return;
        setCustomFields([...customFields, name]);
        setAppFieldModes((prev) => ({ ...prev, [name]: "optional" }));
        setCustomInput("");
    };

    const removeCustomField = (name) => {
        setCustomFields((prev) => prev.filter((x) => x !== name));
        setAppFieldModes((prev) => {
            const next = { ...prev };
            delete next[name];
            return next;
        });
    };

    const renderAppFieldCheckbox = (f) => {
        const mode = apFieldMode(f);
        return (
            <label
                key={f}
                className={`ap-check-item ap-app-cb ap-app-cb--${mode}`}
                onClick={(e) => {
                    e.preventDefault();
                    onApFieldClick(f);
                }}
                title="Single click: optional · Double click quickly: required"
            >
                <input
                    type="checkbox"
                    readOnly
                    checked={mode !== "off"}
                    className="ap-app-cb-input"
                    tabIndex={-1}
                />
                <span>{f}</span>
                {mode === "mandatory" && <span className="ap-app-cb-tag ap-app-cb-tag--req">Required</span>}
                {mode === "optional" && <span className="ap-app-cb-tag ap-app-cb-tag--opt">Optional</span>}
            </label>
        );
    };

    const handleConnectLinkedIn = () => {
        const email = localStorage.getItem("hr_email");
        window.location.href = `${MAIN_API}/linkedin/connect?email=${encodeURIComponent(email)}`;
    };

    const handleSubmit = async () => {
        const hrEmail = localStorage.getItem("hr_email");
        if (!hrEmail) { setSubmitMsg("Not logged in."); return; }
        if (!jobName || !description || !openings) { setSubmitMsg("Fill all required fields."); return; }

        const ivValidation = validateInterviewStages(interviewStages);
        if (!ivValidation.ok) {
            setInterviewConfigError(ivValidation.errors[0]);
            setStep(3);
            setSubmitMsg(ivValidation.errors.join(" "));
            setSubmitState("error");
            return;
        }
        setInterviewConfigError("");

        try {
            if (platforms.includes("LinkedIn")) {
                setSubmitState("checking");
                setSubmitMsg("Verifying LinkedIn connection…");
                const r = await fetch(`${MAIN_API}/linkedin/status/${hrEmail}`);
                const d = await r.json();
                if (!d.connected) {
                    setSubmitState("idle");
                    setSubmitMsg("");
                    setShowLIPopup(true);
                    return;
                }
            }

            setSubmitState("saving");
            setSubmitMsg("Saving job listing…");
            const payload = {
                posted_by: hrEmail, job_name: jobName, description,
                salary_start: salaryStart, salary_end: salaryEnd,
                show_salary: showSalary ? "true" : "false",
                work_style: workStyle,
                location: (workStyle === "On-Site" || workStyle === "Hybrid") ? location : "",
                job_type: jobType,
                skills: skills.join(","), exp_min: expMin, exp_max: expMax,
                department, openings: parseInt(openings), deadline,
                application_fields: serializeApplicationFields(appFieldModes, customFields),
                difficulty,
                rounds: serializeInterviewConfig(interviewStages),
                platforms: platforms.join(","),
            };
            const saveRes = await fetch(`${MAIN_API}/jobs`, {
                method: "POST", headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            const saveData = await saveRes.json();
            if (!saveRes.ok) { setSubmitMsg(saveData.detail || "Failed to save."); setSubmitState("error"); return; }

            if (platforms.includes("LinkedIn")) {
                setSubmitState("posting");
                setSubmitMsg("Publishing to LinkedIn…");
                const liRes = await fetch(`${MAIN_API}/jobs/${saveData.id}/post-linkedin`, { method: "POST" });
                const liData = await liRes.json();
                setSubmitMsg(liData.success ? "Job saved & posted to LinkedIn!" : `Job saved! LinkedIn: ${liData.error || "Post failed"}`);
            } else {
                setSubmitMsg("Job posted successfully!");
            }

            setSubmitState("done");
            setTimeout(() => navigate("/hrdashboard/all"), 2000);

        } catch {
            setSubmitMsg("Server error. Is the backend running?");
            setSubmitState("error");
        }
    };

    const btnLabel = { idle: "Publish Job", checking: "Checking…", saving: "Saving…", posting: "Publishing…", done: "Done ✓", error: "Retry" }[submitState];
    const isBusy = ["checking", "saving", "posting", "done"].includes(submitState);

    return (
        <main className="ap-main">

            {/* ── STEP TAB BAR ── */}
            <div className="ap-tabbar">
                {STEPS.map((s) => (
                    <div key={s.id}
                        className={`ap-tab ${step === s.id ? "active" : ""} ${step > s.id ? "done" : ""}`}
                        onClick={() => setStep(s.id)}>
                        <span className="ap-tab-num">0{s.id}</span>
                        <span className="ap-tab-label">{s.label}</span>
                    </div>
                ))}
            </div>

            {/* ── STEP 1 ── */}
            {step === 1 && (
                <section className="ap-section">
                    <div className="ap-section-header">
                        <h2 className="ap-section-title">Job Details</h2>
                        <p className="ap-section-sub">Define the role, compensation, and requirements</p>
                    </div>
                    <div className="ap-grid">
                        <div className="ap-col">
                            <div className="ap-field">
                                <label className="ap-label">Job Title <span className="ap-required">*</span></label>
                                <input type="text" className="ap-input" placeholder="e.g. Senior Frontend Engineer" value={jobName} onChange={e => setJobName(e.target.value)} />
                            </div>
                            <div className="ap-field">
                                <div className="ap-label-row">
                                    <label className="ap-label">Job Description <span className="ap-required">*</span></label>
                                    <button
                                        type="button"
                                        className={`ap-spell-btn ${spellState !== "idle" ? `ap-spell-${spellState}` : ""}`}
                                        onClick={handleSpellCheck}
                                        disabled={spellState === "checking" || !description.trim()}
                                        title="Fix spelling & grammar with AI"
                                    >
                                        {spellState === "checking" ? (
                                            <><span className="ap-spell-spinner" /> Fixing…</>
                                        ) : spellState === "done" ? (
                                            <>✓ Fixed!</>
                                        ) : spellState === "error" ? (
                                            <>✗ Failed</>
                                        ) : (
                                            <>✨ Fix Spelling</>
                                        )}
                                    </button>
                                </div>
                                <textarea
                                    className="ap-input ap-textarea"
                                    placeholder="Describe responsibilities, expectations, and team culture…"
                                    rows={5}
                                    value={description}
                                    onChange={e => setDescription(e.target.value)}
                                    spellCheck
                                />
                            </div>
                            <div className="ap-field">
                                <label className="ap-label">Annual Salary Range <span className="ap-hint">(optional)</span></label>
                                <div className="ap-row-gap">
                                    <input type="text" className="ap-input" placeholder="Min (e.g. ₹8L)" value={salaryStart} onChange={e => setSalaryStart(e.target.value)} />
                                    <input type="text" className="ap-input" placeholder="Max (e.g. ₹20L)" value={salaryEnd} onChange={e => setSalaryEnd(e.target.value)} />
                                </div>
                                <label className="ap-checkbox-small">
                                    <input type="checkbox" checked={showSalary} onChange={e => setShowSalary(e.target.checked)} />
                                    Display salary on job listing
                                </label>
                            </div>
                            <div className="ap-field">
                                <label className="ap-label">Work Style</label>
                                <div className="ap-chip-group">
                                    {["On-Site", "Hybrid", "Remote"].map(ws => (
                                        <button key={ws} type="button"
                                            className={`ap-chip ${workStyle === ws ? "selected" : ""}`}
                                            onClick={() => {
                                                setWorkStyle(ws);
                                                if ((ws === "On-Site" || ws === "Hybrid") && workStyle !== ws) {
                                                    handleOnSiteLocation();
                                                }
                                            }}>
                                            {ws}
                                            {(ws === "On-Site" || ws === "Hybrid") && locationLoading && workStyle === ws && <span className="ap-loc-spin" />}
                                        </button>
                                    ))}
                                </div>
                                {(workStyle === "On-Site" || workStyle === "Hybrid") && (
                                    <div className="ap-location-row">
                                        <span className="ap-loc-icon">📍</span>
                                        <input
                                            type="text"
                                            className="ap-input ap-loc-input"
                                            placeholder={`${workStyle} location (auto-detected or type manually)`}
                                            value={location}
                                            onChange={e => setLocation(e.target.value)}
                                        />
                                        {locationLoading ? (
                                            <span className="ap-loc-hint">Detecting…</span>
                                        ) : location ? (
                                            <span className="ap-loc-hint ap-loc-ok">✓ Located</span>
                                        ) : (
                                            <button type="button" className="ap-loc-retry" onClick={handleOnSiteLocation} title="Detect my location">
                                                🔄
                                            </button>
                                        )}
                                    </div>
                                )}
                            </div>
                            <div className="ap-field">
                                <label className="ap-label">Employment Type <span className="ap-required">*</span></label>
                                <select className="ap-input ap-select" value={jobType} onChange={e => setJobType(e.target.value)}>
                                    <option value="ft">Full-Time</option>
                                    <option value="pt">Part-Time</option>
                                    <option value="ct">Contract</option>
                                </select>
                            </div>
                        </div>

                        <div className="ap-col">
                            <div className="ap-field">
                                <label className="ap-label">Required Skills</label>
                                <div className="ap-tags-wrapper">
                                    {skills.length > 0 && (
                                        <div className="ap-tags">
                                            {skills.map(s => (
                                                <span key={s} className="ap-tag">{s}
                                                    <button onClick={() => setSkills(skills.filter(x => x !== s))} className="ap-tag-remove">×</button>
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                    <input type="text" className="ap-input" placeholder="Search and add skills…"
                                        value={skillSearch}
                                        onChange={e => { setSkillSearch(e.target.value); setShowDropdown(true); }}
                                        onFocus={() => setShowDropdown(true)}
                                        onBlur={() => setTimeout(() => setShowDropdown(false), 150)} />
                                    {showDropdown && filteredSkills.length > 0 && (
                                        <ul className="ap-dropdown">
                                            {filteredSkills.map(s => (
                                                <li key={s} className="ap-dropdown-item"
                                                    onMouseDown={() => { setSkills([...skills, s]); setSkillSearch(""); setShowDropdown(false); }}>{s}</li>
                                            ))}
                                        </ul>
                                    )}
                                </div>
                            </div>
                            <div className="ap-field">
                                <label className="ap-label">Experience Range <span className="ap-hint">(years)</span></label>
                                <div className="ap-row-gap">
                                    <input type="text" className="ap-input" placeholder="Min" value={expMin} onChange={e => setExpMin(e.target.value)} />
                                    <input type="text" className="ap-input" placeholder="Max" value={expMax} onChange={e => setExpMax(e.target.value)} />
                                </div>
                            </div>
                            <div className="ap-field">
                                <label className="ap-label">Department <span className="ap-required">*</span></label>
                                <select className="ap-input ap-select" value={department} onChange={e => setDepartment(e.target.value)}>
                                    <option value="dev">Development</option>
                                    <option value="sal">Sales</option>
                                    <option value="mkt">Marketing</option>
                                </select>
                            </div>
                            <div className="ap-row-gap">
                                <div className="ap-field" style={{ flex: 1 }}>
                                    <label className="ap-label">Openings <span className="ap-required">*</span></label>
                                    <input type="text" className="ap-input" placeholder="e.g. 3" value={openings} onChange={e => setOpenings(e.target.value)} />
                                </div>
                                <div className="ap-field" style={{ flex: 1 }}>
                                    <label className="ap-label">Application Deadline</label>
                                    <input
                                        type="date"
                                        className="ap-input"
                                        value={deadline}
                                        min={todayStr}
                                        onChange={e => {
                                            const v = e.target.value;
                                            if (v >= todayStr) setDeadline(v);
                                        }}
                                    />
                                    {deadline && deadline < todayStr && (
                                        <p className="ap-deadline-err">⚠ Deadline must be today or a future date</p>
                                    )}
                                </div>
                            </div>
                            <div className="ap-nav-row" style={{ marginTop: "auto" }}>
                                <button type="button" className="ap-btn-primary" onClick={() => setStep(2)}>
                                    Application Setup <MdOutlineArrowForwardIos />
                                </button>
                            </div>
                        </div>
                    </div>
                </section>
            )}

            {/* ── STEP 2 ── */}
            {step === 2 && (
                <section className="ap-section">
                    <div className="ap-section-header">
                        <h2 className="ap-section-title">Application Setup</h2>
                        <p className="ap-section-sub">Choose which fields appear on the application form</p>
                        <p className="ap-setup-hint">
                            <strong>Single click</strong> a field: include it as <em>optional</em> (candidates may leave it blank).
                            <strong> Double click</strong> (two clicks in quick succession): mark it <em>required</em> (candidates must fill it before submitting).
                            Single click again on an optional field removes it; on a required field, single click demotes it to optional.
                            <br />
                            <strong>Resume/CV</strong> and <strong>Cover letter</strong> appear as PDF upload zones on the apply page; text is extracted automatically (like resume parsing).
                        </p>
                    </div>
                    <div className="ap-grid">
                        <div className="ap-col">
                            {[
                                { label: "Resume & Portfolio", fields: ["Resume/CV", "Cover letter", "Portfolio link"] },
                                { label: "Personal Information", fields: ["Full Name", "Location / address"] },
                                { label: "Contact Details", fields: ["Email Id", "Phone Number", "Alternative Number"] },
                                { label: "Education", fields: ["Degree type", "Field of study", "Institution name"] },
                                { label: "Work Experience", fields: ["Years of experience", "Current/past job titles", "Company names", "Current LPA", "Notice Period"] },
                            ].map(({ label, fields }) => (
                                <div key={label} className="ap-field">
                                    <label className="ap-label">{label}</label>
                                    <div className="ap-check-group">
                                        {fields.map((f) => renderAppFieldCheckbox(f))}
                                    </div>
                                </div>
                            ))}
                        </div>
                        <div className="ap-col">
                            {[
                                { label: "Skills & Qualifications", fields: ["Technical skills", "Soft skills", "Certifications / licenses"] },
                                { label: "Online Profiles", fields: ["LinkedIn", "GitHub", "LeetCode", "Codeforces", "HackerRank", "Kaggle", "Stack Overflow", "Medium"] },
                            ].map(({ label, fields }) => (
                                <div key={label} className="ap-field">
                                    <label className="ap-label">{label}</label>
                                    <div className="ap-check-group">
                                        {fields.map((f) => renderAppFieldCheckbox(f))}
                                    </div>
                                </div>
                            ))}
                            <div className="ap-field">
                                <label className="ap-label">Custom Fields</label>
                                <div className="ap-custom-row">
                                    <input type="text" className="ap-input" placeholder="e.g. Portfolio URL, GitHub username…"
                                        value={customInput} onChange={e => setCustomInput(e.target.value)}
                                        onKeyDown={e => e.key === "Enter" && (e.preventDefault(), addCustomField())} />
                                    <button type="button" className="ap-btn-add" onClick={addCustomField}>+ Add</button>
                                </div>
                                <div className="ap-check-group ap-custom-app-list">
                                    {customFields.map((f) => (
                                        <div key={f} className="ap-custom-cb-row">
                                            {renderAppFieldCheckbox(f)}
                                            <button
                                                type="button"
                                                className="ap-custom-remove"
                                                onClick={(e) => {
                                                    e.preventDefault();
                                                    e.stopPropagation();
                                                    removeCustomField(f);
                                                }}
                                                title="Remove field"
                                            >
                                                ×
                                            </button>
                                        </div>
                                    ))}
                                </div>
                            </div>
                            <div className="ap-nav-row" style={{ marginTop: "auto" }}>
                                <button type="button" className="ap-btn-secondary" onClick={() => setStep(1)}>
                                    <MdOutlineArrowBackIosNew /> Job Details
                                </button>
                                <button type="button" className="ap-btn-primary" onClick={() => setStep(3)}>
                                    Interview Config <MdOutlineArrowForwardIos />
                                </button>
                            </div>
                        </div>
                    </div>
                </section>
            )}

            {/* ── STEP 3 ── */}
            {step === 3 && (
                <section className="ap-section">
                    <div className="ap-section-header">
                        <h2 className="ap-section-title">Interview Configuration</h2>
                        <p className="ap-section-sub">
                            Build ordered stages with inner rounds. Each test type can only be used once.
                            Final HR Round stays last and cannot be reordered.
                        </p>
                    </div>
                    <div className="ap-grid">

                        <div className="ap-col ap-col-stages">
                            <div className="ap-stages-toolbar">
                                <label className="ap-label">Interview Stages</label>
                                <button type="button" className="ap-btn-add" onClick={addStage}>
                                    <MdAdd size={16} /> Add Stage
                                </button>
                            </div>
                            {interviewConfigError && <p className="ap-interview-err">{interviewConfigError}</p>}
                            <div className="ap-stages-list">
                            {orderedStages.map((stage, stageIdx) => {
                                const roundOptions = stage.isFinalHr ? HR_ONLY_ROUND_TYPES : NON_HR_ROUND_TYPES;
                                const finalHrIdx = orderedStages.findIndex((s) => s.isFinalHr);
                                const canMoveStageUp = !stage.isFinalHr && stageIdx > 0;
                                const canMoveStageDown = !stage.isFinalHr && stageIdx < finalHrIdx - 1;
                                return (
                                <div key={stage.id} className={`ap-stage-card ${stage.isFinalHr ? "ap-stage-card--final" : ""}`}>
                                    <div className="ap-stage-header">
                                        {stage.isFinalHr ? (
                                            <span className="ap-stage-title">{FINAL_HR_STAGE_NAME}</span>
                                        ) : (
                                            <input type="text" className="ap-input ap-stage-name-input" value={stage.name} onChange={(e) => renameStage(stage.id, e.target.value)} />
                                        )}
                                        <div className="ap-stage-actions">
                                            {!stage.isFinalHr && (
                                                <>
                                                    <button type="button" className="ap-icon-btn" disabled={!canMoveStageUp} onClick={() => moveStage(stage.id, -1)}><MdArrowUpward size={16} /></button>
                                                    <button type="button" className="ap-icon-btn" disabled={!canMoveStageDown} onClick={() => moveStage(stage.id, 1)}><MdArrowDownward size={16} /></button>
                                                    <button type="button" className="ap-icon-btn ap-icon-btn-danger" onClick={() => removeStage(stage.id)}><MdDelete size={16} /></button>
                                                </>
                                            )}
                                            {stage.isFinalHr && <span className="ap-final-badge">Required · Last stage</span>}
                                        </div>
                                    </div>
                                    <div className="ap-inner-rounds">
                                        {(stage.rounds || []).map((round, roundIdx) => (
                                            <div key={round.id} className="ap-inner-round-row">
                                                <select className="ap-input ap-round-select" value={round.type} onChange={(e) => changeInnerRoundType(stage.id, round.id, e.target.value)}>
                                                    <option value="">Select round type…</option>
                                                    {roundOptions.map((t) => (
                                                        <option key={t} value={t} disabled={usedRoundTypes.has(t) && round.type !== t}>{t}</option>
                                                    ))}
                                                </select>
                                                <div className="ap-inner-round-actions">
                                                    <button type="button" className="ap-icon-btn" disabled={roundIdx === 0} onClick={() => moveInnerRound(stage.id, round.id, -1)}><MdArrowUpward size={14} /></button>
                                                    <button type="button" className="ap-icon-btn" disabled={roundIdx === (stage.rounds?.length || 0) - 1} onClick={() => moveInnerRound(stage.id, round.id, 1)}><MdArrowDownward size={14} /></button>
                                                    <button type="button" className="ap-icon-btn ap-icon-btn-danger" onClick={() => removeInnerRound(stage.id, round.id)}><MdDelete size={14} /></button>
                                                </div>
                                            </div>
                                        ))}
                                        <div className="ap-add-round-row">
                                            <select className="ap-input ap-round-select" defaultValue="" onChange={(e) => { const v = e.target.value; if (v) { addInnerRound(stage.id, v); e.target.value = ""; } }}>
                                                <option value="">+ Add inner round…</option>
                                                {roundOptions.filter((t) => !usedRoundTypes.has(t)).map((t) => (<option key={t} value={t}>{t}</option>))}
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                );
                            })}
                            </div>
                        </div>

                        {/* Right col */}
                        <div className="ap-col">
                            <div className="ap-field">
                                <label className="ap-label">Difficulty Level</label>
                                <div className="ap-chip-group">
                                    {["Easy", "Medium", "Hard"].map(d => (
                                        <button key={d} type="button"
                                            className={`ap-chip ap-chip-difficulty ap-chip-${d.toLowerCase()} ${difficulty === d ? "selected" : ""}`}
                                            onClick={() => setDifficulty(d)}>{d}</button>
                                    ))}
                                </div>
                            </div>

                            <div className="ap-field">
                                <label className="ap-label">Questions Bank <span className="ap-hint">(PDF — OCR supported)</span></label>
                                <label className="ap-file-label">
                                    <input
                                        type="file"
                                        accept=".pdf"
                                        className="ap-file-input"
                                        onChange={e => {
                                            const f = e.target.files[0];
                                            setPdfFile(f || null);
                                            setFileName(f?.name || "No file chosen");
                                        }}
                                    />
                                    <span className="ap-file-btn">📄 Upload PDF</span>
                                    <span className="ap-file-name">{fileName}</span>
                                </label>
                                {pdfFile && (
                                    <p className="ap-file-note">✓ PDF selected — questions will be extracted via OCR on publish</p>
                                )}
                            </div>

                            <div className="ap-field">
                                <label className="ap-label">Publish To</label>
                                <div className="ap-chip-group ap-chip-wrap">
                                    {PUBLISH_PLATFORMS.map(({ name, live }) => (
                                        <div key={name} className="ap-publish-wrap" title={!live ? "Coming Soon" : ""}>
                                            <button
                                                type="button"
                                                className={`ap-chip ${live && platforms.includes(name) ? "selected" : ""} ${!live ? "ap-chip-disabled" : ""}`}
                                                onClick={() => live && toggle(setPlatforms, platforms, name)}
                                                disabled={!live}
                                            >
                                                {name}
                                            </button>
                                            {!live && <span className="ap-soon-badge ap-soon-badge-pub">Soon</span>}
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {submitMsg && (
                                <div className={`ap-status ap-status-${submitState}`}>
                                    {submitState === "checking" || submitState === "saving" || submitState === "posting"
                                        ? <span className="ap-spinner" /> : null}
                                    {submitMsg}
                                </div>
                            )}

                            <div className="ap-nav-row" style={{ marginTop: "auto" }}>
                                <button type="button" className="ap-btn-secondary" onClick={() => setStep(2)}>
                                    <MdOutlineArrowBackIosNew /> Application Setup
                                </button>
                                <button type="button"
                                    className={`ap-btn-primary ap-btn-publish ${isBusy ? "busy" : ""} ${submitState === "done" ? "done" : ""}`}
                                    onClick={!isBusy ? handleSubmit : undefined}
                                    disabled={isBusy}>
                                    {btnLabel}
                                </button>
                            </div>
                        </div>
                    </div>
                </section>
            )}

            {/* ── LINKEDIN POPUP ── */}
            {showLIPopup && (
                <div className="ap-overlay" onClick={() => setShowLIPopup(false)}>
                    <div className="ap-popup" onClick={e => e.stopPropagation()}>
                        <div className="ap-popup-icon">🔗</div>
                        <h3 className="ap-popup-title">Connect LinkedIn Account</h3>
                        <p className="ap-popup-body">
                            You'll be redirected to LinkedIn to authorise access. Once approved, you'll be brought back automatically — no tokens or manual setup needed.
                        </p>
                        <div className="ap-popup-actions">
                            <button className="ap-btn-secondary" onClick={() => setShowLIPopup(false)}>Cancel</button>
                            <button className="ap-btn-primary" onClick={handleConnectLinkedIn}>Connect LinkedIn</button>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
}
