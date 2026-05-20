import { useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import './HR.css'

import { RiApps2AiLine } from "react-icons/ri";
import { RiAddLargeLine } from "react-icons/ri";
import { LuCircleUserRound } from "react-icons/lu";
import { RiSettingsLine } from "react-icons/ri";
import { IoSearch } from "react-icons/io5";

export default function Dashboard() {


    const name = localStorage.getItem("hr_name")
    const [dashboardSearch, setDashboardSearch] = useState("")
    const [dashboardSearchPlaceholder, setDashboardSearchPlaceholder] = useState("Search Jobs")
    const menuClass = ({ isActive }) =>
        isActive
            ? "dashboard-menu-icon dashboard-menu-icon-selected"
            : "dashboard-menu-icon";

    const profileClass = ({ isActive }) =>
        isActive
            ? "dashboard-menu-icon dashboard-menu-icon-selected dashboard-menu-profile"
            : "dashboard-menu-icon dashboard-menu-profile";

    return (
        <main className="dashboard-main">

            <div className="dashbboard-navtop">
                <img src="/icon.svg" className="navtop-logo" alt="logo" />
                <p className="navtop-welcome">Welcome back, {name}</p>
                <div className="navtop-search">
                    <input
                        type="text"
                        className="navtop-search-input"
                        placeholder={dashboardSearchPlaceholder}
                        value={dashboardSearch}
                        onChange={(e) => setDashboardSearch(e.target.value)}
                    />
                    <span className="navtop-search-icon"><IoSearch size={17} /></span>
                </div>
            </div>

            <div className="dashboard-inner">
                <div className="dashboard-menuside">
                    <NavLink
                        to="all"
                        end
                        className={menuClass}
                    >
                        <RiApps2AiLine size={25} />
                    </NavLink>

                    <NavLink
                        to="add"
                        className={menuClass}
                    >
                        <RiAddLargeLine size={25} />
                    </NavLink>

                    <NavLink
                        to="settings"
                        className={menuClass}
                    >
                        <RiSettingsLine size={25} />
                    </NavLink>

                    <NavLink
                        to="profile"
                        className={profileClass}
                    >
                        <LuCircleUserRound size={25} />
                    </NavLink>

                </div>

                <div className="dashboard-post-container">
                    <Outlet
                        context={{
                            dashboardSearch,
                            setDashboardSearch,
                            dashboardSearchPlaceholder,
                            setDashboardSearchPlaceholder,
                        }}
                    />
                </div>

            </div>
        </main>
    )
}
