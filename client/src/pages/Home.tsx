import { useEffect, useMemo, useState } from "react";

const avatarData = [
  ["https://polo-pecan-73837341.figma.site/_assets/v11/aa51718fb3af3637e6d666b6543fc27a175fada6.png", 1, 270, "square purple"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/ca755f7f93c1126fb8bdbf99ab364a33aa9ab272.png", 2, 60, "round yellow"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/dc01064c7093dcc32674876ee3cf5e41c4a485c6.png", 2, 180, "wide pink"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/d5470a58b02388336141575048720f19a50de832.png", 2, 300, "square blue"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/018736aa5d0275c4ce56cfebaf2ae3007d81ca1e.png", 3, 130, "wide pink"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/c76d8a0b99676de31c014344bfaf75bad090758d.png", 4, 30, "purple"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/7b1b5f039de7b54cc9913e96c1923c3b15a157fa.png", 4, 95, "wide orange"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/9ae171d8895199349755c43fbff00e122221a027.png", 4, 220, "wide pink"],
  ["https://polo-pecan-73837341.figma.site/_assets/v11/926c9eb7b4bc1df846fa0e39f0b0dc3fefd80671.png", 4, 320, "purple"],
] as const;

const logos = [
  "https://polo-pecan-73837341.figma.site/_assets/v11/1e7b0e6fcc016cd28aec5c68990118b8c54c35a5.svg",
  "https://polo-pecan-73837341.figma.site/_assets/v11/3eac03c183db2ae080d910159211c14843398b61.svg",
  "https://polo-pecan-73837341.figma.site/_assets/v11/17705a4c0023a0e5a99154dfb10582adbbf4260b.svg",
  "https://polo-pecan-73837341.figma.site/_assets/v11/0e5f442b09dc5c248e3e60d40a65505fb1887228.svg",
  "https://polo-pecan-73837341.figma.site/_assets/v11/63f99030ceb459e3c9ab9e429cfa2353491d3816.svg",
];

function useTypewriter(text: string, speed = 35) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    const start = window.setTimeout(() => {
      const timer = window.setInterval(() => setCount((value) => Math.min(value + 1, text.length)), speed);
      window.setTimeout(() => window.clearInterval(timer), text.length * speed + 100);
    }, 400);
    return () => window.clearTimeout(start);
  }, [text, speed]);
  return { value: text.slice(0, count), done: count === text.length };
}

function useCountUp() {
  const [number, setNumber] = useState(0);
  useEffect(() => {
    const start = window.setTimeout(() => {
      const began = performance.now();
      const tick = (now: number) => {
        const progress = Math.min((now - began) / 2000, 1);
        setNumber(Math.round(20 * (1 - Math.pow(1 - progress, 3))));
        if (progress < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, 1200);
    return () => window.clearTimeout(start);
  }, []);
  return number.toLocaleString("fa-IR");
}

function BorderButton({ children, className = "", primary = false }: { children: React.ReactNode; className?: string; primary?: boolean }) {
  return <div className={`btn-border-wrap ${className}`}><button className={`pill-button ${primary ? "primary" : ""}`}>{children}</button></div>;
}

export default function Home() {
  const headline = "استعدادهای برتر بازاریابی که فکر می‌کردید دور از دسترس‌اند — حالا فقط با یک کلیک!";
  const split = headline.indexOf("با یک کلیک!");
  const { value: typed, done } = useTypewriter(headline);
  const count = useCountUp();
  const ticker = useMemo(() => [...logos, ...logos, ...logos, ...logos], []);

  return (
    <main className="app" dir="rtl">
      <div className="app-glow" />
      <header className="site-header">
        <div className="brand-side">
          <img className="brand-logo" src="https://polo-pecan-73837341.figma.site/_assets/v11/17ae538989a509947a8de3892c644664895e69b1.png" alt="مارکتیم" />
          <nav className="nav-links" aria-label="منوی اصلی">
            {["تیم شما", "راهکارها", "وبلاگ", "تعرفه‌ها"].map((item) => <a href="#" key={item}>{item}</a>)}
          </nav>
        </div>
        <div className="account-side">
          <a className="login-link" href="#">ورود</a>
          <BorderButton>عضویت</BorderButton>
        </div>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-dot" /> شبکهٔ متخصصان رشد</div>
          <h1 aria-label={headline}>
            <span className="dark-text">{typed.slice(0, Math.min(typed.length, split))}</span><span className="light-text">{typed.slice(split)}</span><span className={`typing-cursor ${done ? "quiet" : ""}`} />
          </h1>
          <p className="subcopy">برای هر مرحله از رشد، آدم درست را کنار خودت داشته باش.</p>
          <div className={`project-cta ${done ? "show" : ""}`}>
            <BorderButton primary>شروع پروژه <span className="chevron">‹</span></BorderButton>
          </div>
          <div className={`profile-cursor ${done ? "show" : ""}`}><span className="pointer">➤</span><span className="name-badge">داوود</span></div>
        </div>

        <div className="orbit-stage" aria-label="شبکه متخصصان مارکتیم">
          <div className="orbit orbit-4"><div className="orbit orbit-3"><div className="orbit orbit-2"><div className="orbit orbit-1">
            <div className="orbit-center"><strong>{count}<small> هزار+</small></strong><span>متخصص</span></div>
          </div></div></div></div>
          {avatarData.map(([src, orbit, angle, variant], index) => <div key={src} className={`avatar avatar-${orbit} ${variant}`} style={{ "--angle": `${angle}deg`, "--delay": `${0.6 + index * 0.2}s` } as React.CSSProperties}><img src={src} alt="متخصص مارکتیم" /></div>)}
        </div>
      </section>

      <div className="ticker-wrap"><div className="ticker-track">{ticker.map((src, index) => <img src={src} alt="همکار مارکتیم" key={`${src}-${index}`} />)}</div></div>
    </main>
  );
}
