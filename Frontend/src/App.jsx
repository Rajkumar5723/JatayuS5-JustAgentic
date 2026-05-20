import './App.css'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

// Pages
import Landing from "./Pages/Landing"
import Login from "./Pages/Auth/Login"
import HRDashboard from './Pages/HR/Dashboard'

// Dashboard Sub Pages
import AllPosts from './Pages/HR/AllPosts.jsx'
import AddPost from './Pages/HR/AddPost.jsx'
import Settings from './Pages/HR/Settings.jsx'
import Profile from './Pages/HR/Profile.jsx'

import JobPost from './Pages/Candidate/JobPost.jsx'
import JobApplication from './Pages/Candidate/JobApplication.jsx'
import OfferPortal from './Pages/Candidate/OfferPortal.jsx'
import RoomScanPage from './Pages/Candidate/RoomScanPage.jsx'
import VerificationPage from './Pages/Candidate/VerificationPage.jsx'

import CodingTest from "./Codingtest/Codingtest.jsx";

import TestPage from "./Shortlistingtest/Testpage.jsx";

import LiveHR from './Livehr/HRCopilot.jsx'

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        
        <Route path="/job/:id" element={<JobPost />} />
        <Route path="/job/:id/apply" element={<JobApplication />} />
        <Route path="/offer/:token" element={<OfferPortal />} />
        <Route path="/verify/360" element={<RoomScanPage />} />
        <Route path="/verify/:token" element={<VerificationPage />} />

        <Route path="/test/:token" element={<TestPage />} />
        
        <Route path="/coding/:token" element={<CodingTest />} />

        <Route path="/livehr/:token" element={<LiveHR />} />

        <Route path="/hrdashboard" element={<HRDashboard />}>
          <Route index element={<AllPosts />} />
          <Route path="all" element={<AllPosts />} />
          <Route path="add" element={<AddPost />} />
          <Route path="settings" element={<Settings />} />
          <Route path="profile" element={<Profile />} />
        </Route>
      </Routes>
    </Router>
  )
}
