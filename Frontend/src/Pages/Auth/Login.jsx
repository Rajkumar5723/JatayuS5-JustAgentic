import "./Auth.css"
import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { LiaStarOfLifeSolid } from "react-icons/lia"
import { MAIN_API } from "../../shared/api.js"

export default function Login() {

    const navigate = useNavigate()
    const [email, setEmail] = useState("")
    const [password, setPassword] = useState("")
    const [message, setMessage] = useState("")

    const handleLogin = async (e) => {
        e.preventDefault()
        try {
            const response = await fetch(`${MAIN_API}/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password })
            })
            const data = await response.json() 

            if (response.ok) {
                localStorage.setItem("hr_email", data.email)
                localStorage.setItem("hr_name", data.name)   // ← save name
                setMessage("Login successful")
                setTimeout(() => navigate("/hrdashboard/all"), 1000)
            } else {
                setMessage(data.detail || "Login failed!")
            }
        } catch (error) {
            setMessage("Server error. Is backend running?")
        }
    }

    return (
        <main className="login-main">
            <div className="login-side">
                <img src="/iconw.svg" alt="" className="login-logo" />
            </div>
            <div className="login-form-side">
                <LiaStarOfLifeSolid size={60} color="#ff5e00" />
                <form onSubmit={handleLogin} className="login-form">
                    <p className="login-login">Login</p>
                    <p className="login-sub">Welcome back to the powerful hiring engine.</p>

                    <label className="login-label">Email</label>
                    <input type="text" className="login-input" placeholder="example@company.com"
                        value={email} onChange={(e) => setEmail(e.target.value)} />

                    <label className="login-label">Password</label>
                    <input type="password" className="login-input" placeholder="••••••••••••••"
                        value={password} onChange={(e) => setPassword(e.target.value)} />

                    <input type="submit" value="Login" className="login-input login-submit" />
                    <p className={`login-info ${message === "Login successful" ? "login-info-success" : ""}`}>{message}</p>                </form>
            </div>
        </main>
    )
}
