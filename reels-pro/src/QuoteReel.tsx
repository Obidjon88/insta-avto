import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  random,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Audio } from "@remotion/media";
import { z } from "zod";

export const quoteSchema = z.object({
  lines: z.array(z.string()),
  topLabel: z.string(),
  theme: z.enum(["rain", "stars", "sunset", "road", "aurora", "ocean"]),
  handle: z.string(),
  cta: z.string(),
  music: z.string(),
  seed: z.number(),
});
export type QuoteProps = z.infer<typeof quoteSchema>;

// ---- vaqt ----
export const INTRO = 0.6; // s
export const PER_WORD = 0.16; // s
export const LINE_GAP = 0.35; // s
export const HOLD = 3.2; // s
export const OUTRO = 1.4; // s

export const wordTimings = (lines: string[]) => {
  let t = INTRO;
  return lines.map((line) => {
    const words = line.split(/\s+/).filter(Boolean);
    const starts = words.map((_, i) => t + i * PER_WORD);
    t += words.length * PER_WORD + LINE_GAP;
    return { words, starts };
  });
};

export const totalSeconds = (lines: string[]) => {
  const tm = wordTimings(lines);
  const last = tm[tm.length - 1];
  const end = last.starts[last.starts.length - 1] ?? INTRO;
  return Math.min(22, Math.max(9, end + HOLD + OUTRO));
};

const fontFace = `
@font-face { font-family: 'MontserratV'; src: url('${staticFile("fonts/Montserrat.ttf")}') format('truetype'); font-weight: 100 900; }
@font-face { font-family: 'MontserratV'; src: url('${staticFile("fonts/Montserrat-Italic.ttf")}') format('truetype'); font-weight: 100 900; font-style: italic; }
`;

// ---- ranglar ----
const PALETTES: Record<QuoteProps["theme"], { a: string; b: string; c: string; orbs: string[]; accent: [string, string] }> = {
  rain: { a: "#070914", b: "#16112a", c: "#2b1522", orbs: ["#ffb35c", "#ff7a59", "#7aa7ff", "#ffd88a"], accent: ["#ffe3a3", "#ffb547"] },
  stars: { a: "#02030b", b: "#0b1233", c: "#241a44", orbs: ["#8fb3ff", "#c6a6ff", "#ffffff"], accent: ["#fff1c1", "#ffcf6b"] },
  sunset: { a: "#2a1440", b: "#b8475a", c: "#f59f5b", orbs: ["#ffd9a0", "#ff9a76", "#ffe8c2"], accent: ["#fff6d8", "#ffd27a"] },
  road: { a: "#050508", b: "#0e0d17", c: "#1a1020", orbs: ["#ffcf7a", "#ff4d4d", "#ffe7b0"], accent: ["#ffe3a3", "#ffb547"] },
  aurora: { a: "#020711", b: "#06223a", c: "#0b3b3a", orbs: ["#4dffc3", "#5bb8ff", "#b28cff"], accent: ["#d9fff1", "#6cffc9"] },
  ocean: { a: "#020c18", b: "#06304f", c: "#0b5a73", orbs: ["#7fe3ff", "#c9f4ff", "#5aa0ff"], accent: ["#e8fbff", "#8fe6ff"] },
};

// ---- fon ----
const Backdrop: React.FC<{ theme: QuoteProps["theme"]; seed: number }> = ({ theme, seed }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const p = PALETTES[theme];
  const t = frame / fps;
  const zoom = interpolate(frame, [0, durationInFrames], [1.0, 1.12]);
  const orbs = new Array(16).fill(0).map((_, i) => {
    const r = (k: string) => random(`${seed}-${i}-${k}`);
    const size = 160 + r("s") * 380;
    const x = r("x") * width + Math.sin(t * (0.15 + r("vx") * 0.3) + i) * 60;
    const y = r("y") * height + Math.cos(t * (0.12 + r("vy") * 0.25) + i) * 80 - t * (theme === "stars" ? 0 : 8);
    const col = p.orbs[i % p.orbs.length];
    const op = 0.10 + r("o") * 0.22;
    return (
      <div
        key={i}
        style={{
          position: "absolute",
          left: x - size / 2,
          top: y - size / 2,
          width: size,
          height: size,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${col} 0%, ${col}00 70%)`,
          opacity: op * (0.75 + 0.25 * Math.sin(t * 1.3 + i)),
          filter: "blur(6px)",
        }}
      />
    );
  });

  return (
    <AbsoluteFill style={{ background: `linear-gradient(170deg, ${p.a} 0%, ${p.b} 55%, ${p.c} 100%)` }}>
      <AbsoluteFill style={{ scale: zoom }}>
        {theme === "aurora" || theme === "ocean" ? <Ribbons colors={p.orbs} /> : null}
        {theme === "sunset" ? <Sun /> : null}
        {theme === "stars" ? <Stars seed={seed} /> : null}
        {theme === "road" ? <RoadLights /> : null}
        {orbs}
        {theme === "rain" ? <Rain seed={seed} /> : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Ribbons: React.FC<{ colors: string[] }> = ({ colors }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const t = frame / fps;
  return (
    <svg width={width} height={1920} style={{ position: "absolute", inset: 0, filter: "blur(28px)" }}>
      {colors.map((c, i) => {
        const pts: string[] = [];
        for (let x = -100; x <= width + 100; x += 40) {
          const y = 520 + i * 170 + Math.sin(x * 0.004 + t * (0.5 + i * 0.15) + i) * 120 + Math.sin(x * 0.011 - t * 0.7) * 40;
          pts.push(`${x},${y}`);
        }
        return <polyline key={i} points={pts.join(" ")} fill="none" stroke={c} strokeOpacity={0.45} strokeWidth={90 - i * 15} />;
      })}
    </svg>
  );
};

const Sun: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const y = 1240 + Math.sin(frame / fps / 3) * 25;
  return (
    <div style={{ position: "absolute", left: 540 - 420, top: y - 420, width: 840, height: 840, borderRadius: "50%",
      background: "radial-gradient(circle, rgba(255,236,190,0.95) 0%, rgba(255,170,100,0.45) 30%, rgba(255,120,80,0) 70%)" }} />
  );
};

const Stars: React.FC<{ seed: number }> = ({ seed }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <>
      {new Array(180).fill(0).map((_, i) => {
        const r = (k: string) => random(`st-${seed}-${i}-${k}`);
        const s = 1 + r("s") * 3.2;
        return (
          <div key={i} style={{ position: "absolute", left: r("x") * 1080 + t * s * 2, top: r("y") * 1600, width: s, height: s,
            borderRadius: "50%", background: "#fff", opacity: 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * (1 + r("f") * 2) + r("p") * 6)) }} />
        );
      })}
      <svg width={1080} height={1920} style={{ position: "absolute", inset: 0 }}>
        <path d="M0 1920 L0 1560 Q 180 1430 330 1520 T 640 1450 T 900 1530 T 1080 1470 L1080 1920 Z" fill="#03030a" />
      </svg>
    </>
  );
};

const Rain: React.FC<{ seed: number }> = ({ seed }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  return (
    <>
      {new Array(110).fill(0).map((_, i) => {
        const r = (k: string) => random(`rn-${seed}-${i}-${k}`);
        const sp = 0.4 + r("v");
        const y = ((r("y") * 2100 + t * 1100 * sp) % 2100) - 100;
        return (
          <div key={i} style={{ position: "absolute", left: r("x") * 1080, top: y, width: 2 + sp, height: 30 + sp * 50,
            borderRadius: 2, background: "linear-gradient(rgba(220,230,255,0), rgba(220,230,255,0.45))", rotate: "8deg" }} />
        );
      })}
    </>
  );
};

const RoadLights: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const items = [];
  for (let i = 0; i < 36; i++) {
    const p = ((i / 36) + t * 0.32) % 1;
    const z = Math.pow(p, 2.2);
    for (const side of [-1, 1]) {
      const x = 540 + side * (30 + z * 950);
      const y = 860 + z * 1150;
      const s = 4 + z * 46;
      items.push(
        <div key={`${i}${side}`} style={{ position: "absolute", left: x - s / 2, top: y - s / 2, width: s, height: s, borderRadius: "50%",
          background: side < 0 ? "radial-gradient(circle,#fff3d0,#ffb34700 70%)" : "radial-gradient(circle,#ff8080,#ff2a2a00 70%)",
          opacity: 0.3 + 0.7 * z }} />,
      );
    }
  }
  for (let i = 0; i < 10; i++) {
    const p = ((i / 10) + t * 0.45) % 1;
    const z = Math.pow(p, 2.2);
    items.push(<div key={`l${i}`} style={{ position: "absolute", left: 540 - (2 + z * 10) / 2, top: 860 + z * 1150, width: 2 + z * 10,
      height: 10 + z * 140, background: "rgba(255,255,255,0.55)", borderRadius: 4 }} />);
  }
  return <>{items}</>;
};

// ---- kinematik qatlamlar ----
const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ opacity: 0.09, mixBlendMode: "overlay", pointerEvents: "none" }}>
      <svg width="100%" height="100%">
        <filter id="g">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={frame % 60} />
        </filter>
        <rect width="100%" height="100%" filter="url(#g)" />
      </svg>
    </AbsoluteFill>
  );
};

const LightLeak: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill
      style={{
        mixBlendMode: "screen",
        opacity: interpolate(frame, [0, 0.4 * fps, 1.6 * fps], [0.0, 0.55, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        background: "linear-gradient(115deg, rgba(255,170,90,0) 20%, rgba(255,170,90,0.9) 45%, rgba(255,90,120,0) 70%)",
        translate: interpolate(frame, [0, 1.6 * fps], ["-600px 0px", "600px 0px"], { extrapolateRight: "clamp" }),
      }}
    />
  );
};

const Vignette: React.FC = () => (
  <AbsoluteFill style={{ background: "radial-gradient(ellipse at 50% 45%, rgba(0,0,0,0) 35%, rgba(0,0,0,0.78) 100%)" }} />
);

// ---- matn ----
const Word: React.FC<{ text: string; start: number; accent: boolean; accentColors: [string, string] }> = ({ text, start, accent, accentColors }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f0 = start * fps;
  const shimmer = interpolate(frame, [f0 + 0.6 * fps, f0 + 2.2 * fps], [-120, 220], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <span
      style={{
        display: "inline-block",
        marginRight: "0.26em",
        opacity: interpolate(frame, [f0, f0 + 0.45 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        filter: `blur(${interpolate(frame, [f0, f0 + 0.5 * fps], [14, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}px)`,
        translate: interpolate(frame, [f0, f0 + 0.6 * fps], ["0px 38px", "0px 0px"], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) }),
        scale: interpolate(frame, [f0, f0 + 0.6 * fps], [accent ? 1.25 : 1.06, 1], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) }),
        ...(accent
          ? {
              backgroundImage: `linear-gradient(100deg, ${accentColors[1]} 0%, ${accentColors[0]} ${shimmer - 30}%, #ffffff ${shimmer}%, ${accentColors[0]} ${shimmer + 30}%, ${accentColors[1]} 100%)`,
              WebkitBackgroundClip: "text",
              backgroundClip: "text",
              color: "transparent",
              textShadow: "none",
            }
          : {}),
      }}
    >
      {text}
    </span>
  );
};

const Quote: React.FC<{ lines: string[]; theme: QuoteProps["theme"] }> = ({ lines, theme }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const tm = wordTimings(lines);
  const accentLine = lines.length >= 3 ? lines.length - 1 : -1;
  const normal = lines.filter((_, i) => i !== accentLine);
  const longest = Math.max(...normal.map((l) => l.length), 10);
  const base = Math.max(50, Math.min(80, Math.floor(1560 / longest)));
  const accentLen = accentLine >= 0 ? lines[accentLine].length : 10;
  const accentSize = Math.max(50, Math.min(base * 1.14, Math.floor(1480 / accentLen)));
  const accentStart = accentLine >= 0 ? tm[accentLine].starts[0] * fps : 0;
  return (
    <AbsoluteFill
      style={{
        justifyContent: "center",
        alignItems: "center",
        padding: "0 70px",
        paddingBottom: 220,
        opacity: interpolate(frame, [durationInFrames - OUTRO * fps, durationInFrames - 0.4 * fps], [1, 0], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
      }}
    >
      <div style={{ textAlign: "center", fontFamily: "MontserratV", color: "#fff",
        textShadow: "0 6px 30px rgba(0,0,0,0.55), 0 2px 6px rgba(0,0,0,0.5)" }}>
        {tm.map((ln, li) => {
          const accent = li === accentLine;
          return (
            <div key={li} style={{ fontSize: accent ? accentSize : base, fontWeight: accent ? 800 : 600, lineHeight: 1.28,
              letterSpacing: accent ? "-0.01em" : "0", marginTop: accent ? 26 : 0, whiteSpace: "nowrap" }}>
              {ln.words.map((w, wi) => (
                <Word key={wi} text={w} start={ln.starts[wi]} accent={accent} accentColors={PALETTES[theme].accent} />
              ))}
            </div>
          );
        })}
        {accentLine >= 0 ? (
          <div style={{ margin: "26px auto 0", height: 6, borderRadius: 3,
            background: `linear-gradient(90deg, ${PALETTES[theme].accent[1]}00, ${PALETTES[theme].accent[1]}, ${PALETTES[theme].accent[1]}00)`,
            width: interpolate(frame, [accentStart + 0.5 * fps, accentStart + 1.4 * fps], [0, 420], {
              extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.65, 0, 0.35, 1) }) }} />
        ) : null}
      </div>
    </AbsoluteFill>
  );
};

const TopLabel: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ alignItems: "center", top: 250 }}>
      <div style={{ fontFamily: "MontserratV", fontStyle: "italic", fontWeight: 500, fontSize: 40, color: "rgba(255,255,255,0.78)",
        letterSpacing: interpolate(frame, [0, 1.2 * fps], ["0.35em", "0.08em"], { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) }),
        opacity: interpolate(frame, [0.1 * fps, 0.9 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) }}>
        {text}
      </div>
    </AbsoluteFill>
  );
};

const Footer: React.FC<{ handle: string; cta: string }> = ({ handle, cta }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const ctaIn = durationInFrames - (HOLD + OUTRO - 0.8) * fps;
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 330, fontFamily: "MontserratV" }}>
      <div style={{ padding: "18px 40px", borderRadius: 999, background: "rgba(255,255,255,0.12)", border: "1.5px solid rgba(255,255,255,0.35)",
        color: "#fff", fontWeight: 600, fontSize: 36, backdropFilter: "blur(8px)",
        opacity: interpolate(frame, [ctaIn, ctaIn + 0.5 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        translate: interpolate(frame, [ctaIn, ctaIn + 0.6 * fps], ["0px 30px", "0px 0px"], {
          extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) }) }}>
        {cta}
      </div>
      <div style={{ marginTop: 26, color: "rgba(255,255,255,0.55)", fontSize: 30, fontWeight: 500, letterSpacing: "0.05em" }}>{handle}</div>
    </AbsoluteFill>
  );
};

const Progress: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <div style={{ position: "absolute", top: 120, left: 90, right: 90, height: 4, borderRadius: 2, background: "rgba(255,255,255,0.18)" }}>
      <div style={{ height: "100%", borderRadius: 2, background: "rgba(255,255,255,0.85)",
        width: `${interpolate(frame, [0, durationInFrames], [0, 100])}%` }} />
    </div>
  );
};

export const QuoteReel: React.FC<QuoteProps> = ({ lines, topLabel, theme, handle, cta, music, seed }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  return (
    <AbsoluteFill style={{ backgroundColor: "#000" }}>
      <style>{fontFace}</style>
      <Backdrop theme={theme} seed={seed} />
      <Vignette />
      <LightLeak />
      {topLabel ? <TopLabel text={topLabel} /> : null}
      <Quote lines={lines} theme={theme} />
      <Footer handle={handle} cta={cta} />
      <Progress />
      <Grain />
      <AbsoluteFill style={{ backgroundColor: "#000", opacity: interpolate(frame, [0, 0.35 * fps], [1, 0], { extrapolateRight: "clamp" }) }} />
      {music ? (
        <Audio
          src={staticFile(music)}
          volume={(f) => interpolate(f, [0, fps, durationInFrames - 1.5 * fps, durationInFrames], [0, 0.9, 0.9, 0], {
            extrapolateLeft: "clamp", extrapolateRight: "clamp" })}
        />
      ) : null}
    </AbsoluteFill>
  );
};
