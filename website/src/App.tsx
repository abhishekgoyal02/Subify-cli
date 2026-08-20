import { useEffect, useState } from "react";
import logoUrl from "../ChatGPT Image Aug 16, 2026, 10_57_58 PM.png";
import "./App.css";

type Command = {
  label: string;
  syntax: string;
  description: string;
};

type SocialLink = {
  label: string;
  href: string;
  icon: "linkedin" | "github" | "x" | "medium";
};

const coreCommands: Command[] = [
  {
    label: "SUBIFY",
    syntax: "subify",
    description: "Opens the main Subify shell, aka the chill command room where you run the whole subtitle workflow without menu hunting.",
  },
  {
    label: "DOCTOR",
    syntax: "subify doctor",
    description: "Runs a quick vibe check on Python, FFmpeg, folders, and setup stuff so you know the machine is not acting sus before processing.",
  },
];

const shellCommands: Command[] = [
  {
    label: "HELP",
    syntax: "/help",
    description: "Shows the command cheat sheet when your brain says wait, what was the move again?",
  },
  {
    label: "VERSION",
    syntax: "/version",
    description: "Prints the installed Subify version so you can confirm you are on the right build, not some ancient zip from the lore.",
  },
  {
    label: "PROCESS",
    syntax: '/process "video.mp4"',
    description: "The big one. Pulls audio, transcribes speech, generates an SRT, embeds subtitles, and packages the output like a whole cooked drop.",
  },
  {
    label: "GENERATE SRT",
    syntax: '/generate-srt "video.mp4"',
    description: "Creates only the subtitle file when you need captions ready for editing, uploading, or flexing somewhere else.",
  },
  {
    label: "EMBED",
    syntax: '/embed "video.mp4" "video.srt"',
    description: "Burns or attaches your ready-made SRT onto the video, so the final file actually carries the captions with it.",
  },
  {
    label: "UPDATE",
    syntax: "/update",
    description: "Checks for newer Subify sauce so you can grab fixes and features instead of living in yesterday's build.",
  },
  {
    label: "CONFIG",
    syntax: "/config",
    description: "Shows safe local settings like paths and defaults. Secrets stay hidden because leaking keys is not the aesthetic.",
  },
  {
    label: "CLEAR",
    syntax: "/clear",
    description: "Wipes the shell view clean when the terminal starts looking like a group chat at 3 AM.",
  },
  {
    label: "HISTORY",
    syntax: "/history",
    description: "Lists recent commands so you can rerun the good moves without scrolling through chaos.",
  },
  {
    label: "EXIT",
    syntax: "/exit",
    description: "Leaves the Subify shell cleanly when the job is done and you are officially out.",
  },
];

const watermarkTiles = [
  "00:00:01,420 --> 00:00:03,880",
  "speech detected / clean transcript",
  "whisper pass / confidence 98%",
  "subify process video.mp4",
  "caption sync / no drift",
  "srt export / ready",
  "ffmpeg embed / final render",
  "package output / zip",
];

const heroWords = ["VIDEO.", "CLIP.", "REEL.", "CUT."];
const subifyVersion = "Subify CLI v0.1.0";

const socialLinks: SocialLink[] = [
  {
    label: "LinkedIn",
    href: "https://www.linkedin.com/in/abhishek-goyals/",
    icon: "linkedin",
  },
  {
    label: "Github",
    href: "https://github.com/abhishekgoyal02",
    icon: "github",
  },
  {
    label: "X",
    href: "https://x.com/GoyalsAbhishek",
    icon: "x",
  },
  {
    label: "Medium",
    href: "https://medium.com/@abhishek-goyal",
    icon: "medium",
  },
];

const aboutPoints = [
  {
    label: "Offline-first",
    text: "Run the subtitle flow from your own terminal without needing the internet for the core CLI workflow.",
  },
  {
    label: "Local files stay local",
    text: "Videos, generated SRT files, and packaged outputs are handled on your machine instead of being pushed through a random web panel.",
  },
  {
    label: "One clean pipeline",
    text: "Transcribe, sync, embed, and package from one command path so subtitle work feels like a dev tool, not a drag-and-drop chore.",
  },
];

function LoadingScreen() {
  return (
    <main className="loading-page" aria-busy="true">
      <section className="loading-shell" aria-label="Subify website loading">
        <div className="loading-mark">
          <img className="loading-logo" src={logoUrl} alt="" aria-hidden="true" />
          <h1 className="loading-wordmark">Subify</h1>
        </div>
        <div className="subtitle-lab" aria-hidden="true">
          <div className="raw-speech">
            <span>RAW SPEECH</span>
            <p>this clip needs subtitles before it ships</p>
          </div>
          <div className="convert-lane">
            <span />
            <span />
            <span />
          </div>
          <div className="srt-preview">
            <span>SUBIFY.ZIP</span>
            <code>00:00:01,420 --&gt; 00:00:03,880</code>
            <p>This clip needs subtitles before it ships.</p>
          </div>
        </div>
        <div className="loading-status" role="status" aria-live="polite">
          <span>Building captions locally</span>
          <span>{subifyVersion}</span>
        </div>
        <div className="loading-pipeline" aria-hidden="true">
          <span>audio scan</span>
          <span>speech map</span>
          <span>srt sync</span>
          <span>embed queue</span>
        </div>
        <div className="loading-rail" aria-hidden="true">
          <span />
        </div>
      </section>
    </main>
  );
}

function Header() {
  const [menuOpen, setMenuOpen] = useState(false);
  const links = [
    { label: "Home", href: "#home" },
    { label: "About", href: "#about" },
    { label: "Commands", href: "#commands" },
  ];

  return (
    <header className="site-header">
      <a className="nav-logo" href="#home" aria-label="Subify home">
        <img src={logoUrl} alt="" aria-hidden="true" />
      </a>
      <nav className="desktop-nav" aria-label="Primary navigation">
        {links.map((link) => (
          <a key={link.href} href={link.href}>
            {link.label}
          </a>
        ))}
      </nav>
      <button
        className="menu-button"
        type="button"
        aria-label="Toggle navigation menu"
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((open) => !open)}
      >
        <span />
        <span />
        <span />
      </button>
      <nav className={`mobile-nav ${menuOpen ? "is-open" : ""}`} aria-label="Mobile navigation">
        {links.map((link) => (
          <a key={link.href} href={link.href} onClick={() => setMenuOpen(false)}>
            {link.label}
          </a>
        ))}
      </nav>
    </header>
  );
}

function CommandCard({ command }: { command: Command }) {
  const [copied, setCopied] = useState(false);

  const copyCommand = async () => {
    try {
      await navigator.clipboard.writeText(command.syntax);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };

  return (
    <article className="command-card">
      <div className="command-card-top">
        <span className="command-label">{command.label}</span>
        <button type="button" className="copy-button" onClick={copyCommand}>
          {copied ? "COPIED" : "COPY"}
        </button>
      </div>
      <code>{command.syntax}</code>
      <p>{command.description}</p>
    </article>
  );
}

function CommandGroup({ eyebrow, title, commands }: { eyebrow: string; title: string; commands: Command[] }) {
  return (
    <section className="command-group" aria-labelledby={`${eyebrow}-title`}>
      <div className="section-label">
        <span>{eyebrow}</span>
        <span>{String(commands.length).padStart(2, "0")}</span>
      </div>
      <h3 id={`${eyebrow}-title`}>{title}</h3>
      <div className="command-grid">
        {commands.map((command) => (
          <CommandCard key={command.syntax} command={command} />
        ))}
      </div>
    </section>
  );
}

function SocialIcon({ icon }: { icon: SocialLink["icon"] }) {
  if (icon === "linkedin") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5.2 8.7h3.4v10.6H5.2V8.7Zm1.7-5a2 2 0 1 1 0 4.1 2 2 0 0 1 0-4.1Zm4.1 5h3.2v1.4h.1c.4-.8 1.5-1.7 3.1-1.7 3.3 0 3.9 2.2 3.9 5v5.9h-3.4v-5.2c0-1.3 0-2.9-1.8-2.9s-2.1 1.4-2.1 2.8v5.3h-3.4V8.7Z" />
      </svg>
    );
  }

  if (icon === "github") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 2.8a9.4 9.4 0 0 0-3 18.3c.5.1.7-.2.7-.5v-1.8c-2.8.6-3.4-1.2-3.4-1.2-.5-1.1-1.1-1.4-1.1-1.4-.9-.6.1-.6.1-.6 1 0 1.6 1.1 1.6 1.1.9 1.5 2.4 1.1 3 .8.1-.7.4-1.1.7-1.3-2.3-.3-4.7-1.1-4.7-5a3.9 3.9 0 0 1 1-2.7c-.1-.3-.5-1.3.1-2.7 0 0 .9-.3 2.8 1a9.6 9.6 0 0 1 5.2 0c1.9-1.3 2.8-1 2.8-1 .6 1.4.2 2.4.1 2.7a3.9 3.9 0 0 1 1 2.7c0 3.9-2.4 4.7-4.7 5 .4.3.7.9.7 1.8v2.6c0 .3.2.6.7.5A9.4 9.4 0 0 0 12 2.8Z" />
      </svg>
    );
  }

  if (icon === "x") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4.4 4.6h4.2l4.1 5.4 4.8-5.4h2.2l-6 6.8 6.3 8h-4.2l-4.6-5.9-5.2 5.9H3.8l6.4-7.3-5.8-7.5Zm3.2 1.6 9 11.6h1.2L8.8 6.2H7.6Z" />
      </svg>
    );
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 6.3c0-.9.7-1.6 1.6-1.6h12.8c.9 0 1.6.7 1.6 1.6v11.4c0 .9-.7 1.6-1.6 1.6H5.6A1.6 1.6 0 0 1 4 17.7V6.3Zm3.2 10.1h2.1V9.8h.1l2.7 6.6h1.6l2.6-6.6h.1v6.6h2.1V7.6h-3l-2.5 6.2-2.6-6.2H7.2v8.8Z" />
    </svg>
  );
}

function useTypedWord(words: string[]) {
  const [wordIndex, setWordIndex] = useState(0);
  const [letterCount, setLetterCount] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const currentWord = words[wordIndex];
    const isComplete = letterCount === currentWord.length;
    const isEmpty = letterCount === 0;
    const delay = isComplete && !isDeleting ? 1200 : isEmpty && isDeleting ? 260 : isDeleting ? 46 : 82;

    const timerId = window.setTimeout(() => {
      if (isComplete && !isDeleting) {
        setIsDeleting(true);
        return;
      }

      if (isEmpty && isDeleting) {
        setIsDeleting(false);
        setWordIndex((index) => (index + 1) % words.length);
        return;
      }

      setLetterCount((count) => count + (isDeleting ? -1 : 1));
    }, delay);

    return () => window.clearTimeout(timerId);
  }, [isDeleting, letterCount, wordIndex, words]);

  return words[wordIndex].slice(0, letterCount);
}

function HomePage() {
  const typedHeroWord = useTypedWord(heroWords);
  const visibleHeroWord = typedHeroWord || heroWords[0].slice(0, 1);

  return (
    <div className="site-page">
      <div className="watermark-field" aria-hidden="true">
        {watermarkTiles.map((tile) => (
          <span key={tile}>{tile}</span>
        ))}
      </div>
      <Header />
      <main id="home">
        <section className="hero-section" aria-labelledby="hero-title">
          <div className="hero-frame" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
          </div>
          <div className="hero-tiles" aria-hidden="true">
            <span>TRANSCRIBE</span>
            <span>SRT EXPORT</span>
            <span>EMBED</span>
            <span>PACKAGE</span>
            <span>LOCAL RUN</span>
            <span>CLI FLOW</span>
          </div>
          <p className="brand-eyebrow">SUBIFY</p>
          <div className="hero-layout">
            <div className="hero-copy">
              <p className="hero-index">01 / SPEECH TO SUBS</p>
              <h1 id="hero-title" aria-label={`The subtitle layer for every ${visibleHeroWord.toLowerCase()}`}>
                <span>THE SUBTITLE</span>
                <span>LAYER FOR</span>
                <span>EVERY</span>
                <span className="typed-line" aria-hidden="true">
                  <span className="typed-word">{visibleHeroWord}</span>
                </span>
              </h1>
              <p className="hero-subcopy">Lowkey the easiest way to turn speech into subtitles.</p>
              <p className="hero-meta">CLI / WHISPER / FFMPEG / ZIP</p>
              <div className="hero-actions" aria-label="Primary actions">
                <a className="button-primary" href="#commands">
                  EXPLORE COMMANDS
                </a>
              </div>
            </div>
          </div>
        </section>

        <section id="about" className="about-section" aria-labelledby="about-title">
          <div className="section-label">
            <span>ABOUT</span>
            <span>02</span>
          </div>
          <h2 id="about-title">Developer-first subtitle flow.</h2>
          <p>
            Subify turns spoken English into clean, embedded subtitles without turning the
            workflow into a whole production.
          </p>
          <div className="about-grid" aria-label="Subify workflow highlights">
            {aboutPoints.map((point) => (
              <article key={point.label} className="about-point">
                <span>{point.label}</span>
                <p>{point.text}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="commands" className="commands-section" aria-labelledby="commands-title">
          <div className="section-label">
            <span>COMMANDS</span>
            <span>03</span>
          </div>
          <h2 id="commands-title">Run it from the shell. Then move fast inside it.</h2>
          <CommandGroup eyebrow="core" title="Core commands" commands={coreCommands} />
          <CommandGroup eyebrow="shell" title="Shell commands" commands={shellCommands} />
        </section>
      </main>
      <section className="made-with" aria-label="Creator credit">
        <div className="made-with-line">
          <span>Made with</span>
          <span className="heart-logo" aria-label="love" role="img" />
          <span>by Abhishek Goyal.</span>
        </div>
        <nav className="social-links" aria-label="Abhishek Goyal social links">
          {socialLinks.map((link) => (
            <a key={link.href} href={link.href} target="_blank" rel="noreferrer">
              <SocialIcon icon={link.icon} />
              <span>{link.label}</span>
            </a>
          ))}
        </nav>
      </section>
      <footer className="site-footer">
        <span>SUBIFY</span>
        <span>CLI / LOCAL / OPEN SOURCE</span>
      </footer>
    </div>
  );
}

export function App() {
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const timerId = window.setTimeout(() => setLoaded(true), 4000);
    return () => window.clearTimeout(timerId);
  }, []);

  return (
    <>
      <div className={`loading-layer ${loaded ? "is-hidden" : ""}`} aria-hidden={loaded}>
        <LoadingScreen />
      </div>
      <div className={`home-layer ${loaded ? "is-visible" : ""}`} aria-hidden={!loaded}>
        <HomePage />
      </div>
    </>
  );
}
