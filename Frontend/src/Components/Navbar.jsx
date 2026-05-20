import './Components.css'

// Images
import logo from '/iconw.svg'


export default function Navbar() {
    return (
        <nav className='navbar-main'>
            <img src={logo} alt="" className="navbar-logo" />
            <menu className="nav-menu">
                <a href='/' className="menu-items">Home</a>
                <a href='/' className="menu-items">About</a>
                <a href='/' className="menu-items">Login</a>
            </menu>
            <a href='/' className="menu-items menu-getstared">Get Started</a>
        </nav>
    )
}