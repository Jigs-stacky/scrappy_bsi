const projects = [
  {
    title: 'E-commerce Dashboard',
    description: 'A responsive analytics dashboard for online stores with charts and live sales tracking.',
    stack: 'React, Tailwind CSS, Chart.js'
  },
  {
    title: 'Travel Planner App',
    description: 'A collaborative trip planning tool with itinerary sharing and destination recommendations.',
    stack: 'React, Firebase, Google Maps API'
  },
  {
    title: 'Task Automation Tool',
    description: 'A productivity web app to automate recurring workflows and generate weekly reports.',
    stack: 'React, Node.js, PostgreSQL'
  }
];

const skills = ['React', 'JavaScript', 'TypeScript', 'HTML/CSS', 'Node.js', 'UI/UX'];

export default function App() {
  return (
    <>
      <header className="hero" id="home">
        <nav className="nav">
          <a href="#home" className="logo">YourName.dev</a>
          <div className="nav-links">
            <a href="#about">About</a>
            <a href="#projects">Projects</a>
            <a href="#contact">Contact</a>
          </div>
        </nav>

        <div className="hero-content">
          <p className="eyebrow">Frontend Developer</p>
          <h1>Hi, I build beautiful and fast web experiences.</h1>
          <p>
            I am a React developer focused on creating clean, user-friendly websites and web apps for modern businesses.
          </p>
          <div className="cta-group">
            <a className="btn primary" href="#projects">View Projects</a>
            <a className="btn secondary" href="#contact">Hire Me</a>
          </div>
        </div>
      </header>

      <main>
        <section id="about" className="section card">
          <h2>About Me</h2>
          <p>
            I am passionate about turning ideas into scalable digital products. With a strong foundation in React and UI design,
            I craft interfaces that are both elegant and easy to use.
          </p>
          <div className="skills">
            {skills.map((skill) => (
              <span key={skill} className="chip">{skill}</span>
            ))}
          </div>
        </section>

        <section id="projects" className="section">
          <h2>Featured Projects</h2>
          <div className="project-grid">
            {projects.map((project) => (
              <article key={project.title} className="project-card">
                <h3>{project.title}</h3>
                <p>{project.description}</p>
                <small>{project.stack}</small>
              </article>
            ))}
          </div>
        </section>

        <section id="contact" className="section card">
          <h2>Contact</h2>
          <p>Want to work together? Let us build something amazing.</p>
          <a className="btn primary" href="mailto:youremail@example.com">Send Email</a>
        </section>
      </main>

      <footer className="footer">
        <p>© {new Date().getFullYear()} Your Name. All rights reserved.</p>
      </footer>
    </>
  );
}
