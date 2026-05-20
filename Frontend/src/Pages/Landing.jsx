import './Pages.css'
import Navbar from '../Components/Navbar'
import { Link } from 'react-router-dom'
export default function Landing() {
  return (
    <>
      <Navbar />
      <main className="landing-main">
        <p className="landing-sub"><img className='landing-multiagent-icon' src="/multiagent.svg" alt="" />Combination of 20+ Unified Agents</p>
        <p className="landing-head">Hire at the Speed of Intelligence.</p>
        <p className="landing-description">Enable <span className='landing-description-high'>Superhuman</span> HR performance with our Autonomous AI platform, strategically designed to transform modern recruitment processes and create <span className='landing-description-high'>lasting competitive advantage</span>.</p>
        <div className="landing-button">
          <p className="landing-access-button">
            Request a demo
          </p>
          <Link to={'/login'} className="landing-access-button">
            Login as HR
          </Link>



          
        </div>
        <div className="landing-info-container">

          <div className="landing-info-inner">
            <p className="info-percentage">18%</p>
            <div className="info-des">
              <p className="info-des-head">Cost Efficiency</p>
              <p className="info-des-sub">Reduce Recruiter time, Fewer Bad Hires, Tool Consolidation.</p>
            </div>
          </div>

          <div className="landing-info-inner landing-info-inner-two">
            <p className="info-percentage">35%</p>
            <div className="info-des">
              <p className="info-des-head">Accelerated Hiring</p>
              <p className="info-des-sub">Graphical Insights, Deep Profile
                Analysis, Auto Verification.</p>
            </div>
          </div>

          <div className="landing-info-inner">
            <p className="info-percentage">60%</p>
            <div className="info-des">
              <p className="info-des-head">Hiring Quality</p>
              <p className="info-des-sub">Reduce Recruiter time, Fewer Bad Hires, Tool Consolidation.</p>
            </div>
          </div>

        </div>
      </main>
      <section className="landing-one">

      </section>
    </>
  )
}