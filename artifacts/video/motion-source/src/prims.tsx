import React from "react";
import {
  AbsoluteFill,
  Easing,
  Img,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from "remotion";
import { evolvePath, getLength, getPointAtLength } from "@remotion/paths";

export const FPS = 30;

export const C = {
  ivory: "#f5f5f0",
  paper: "#fbfcf8",
  deep: "#142e27",
  deeper: "#0d211b",
  ink: "#233c34",
  muted: "#66766d",
  green: "#22705a",
  mint: "#d4e8d6",
  leaf: "#35866a",
  line: "#e2e7df",
  sage: "#a6bdb0",
  lime: "#b9e07f",
  amber: "#c79a2b",
  amberBg: "#f6efdc",
};

export const EASE = Easing.bezier(0.22, 1, 0.36, 1);
export const ip = (f: number, a: number, b: number, from = 0, to = 1, e = EASE) =>
  interpolate(f, [a, b], [from, to], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e });
export const sp = (f: number, delay = 0, damping = 18, mass = 0.9, stiffness = 120) =>
  spring({ frame: f - delay, fps: FPS, config: { damping, mass, stiffness } });
export const shot = (n: string) => staticFile(`shots/${n}.jpg`);

/* ---------- fonts (local woff2, loaded before the first frame) ---------- */
export const FONT = "InterV, Inter, 'Segoe UI', sans-serif";
export const MONO = "Consolas, 'Cascadia Mono', monospace";
let fontsRequested = false;
export const loadFonts = () => {
  if (fontsRequested || typeof document === "undefined") return;
  fontsRequested = true;
  const h = delayRender("fonts");
  Promise.all(
    [400, 500, 600, 700, 800].map((w) => {
      const ff = new FontFace("InterV", `url(${staticFile(`fonts/inter-latin-${w}-normal.woff2`)}) format('woff2')`, {
        weight: String(w),
      });
      return ff.load().then((x) => document.fonts.add(x));
    }),
  ).then(() => continueRender(h));
};

/* ---------- backgrounds ---------- */
export const Background: React.FC<{ dark?: boolean; glow?: [number, number] }> = ({ dark, glow = [70, 30] }) => {
  const f = useCurrentFrame();
  const drift = f * 0.18;
  return (
    <AbsoluteFill style={{ background: dark ? C.deeper : C.ivory, overflow: "hidden" }}>
      <AbsoluteFill
        style={{
          background: dark
            ? `radial-gradient(1100px 700px at ${glow[0]}% ${glow[1]}%, #22705a66, transparent 70%), radial-gradient(900px 700px at 8% 100%, #0a1914, transparent 70%)`
            : `radial-gradient(1000px 700px at ${glow[0]}% ${glow[1]}%, #d4e8d6bb, transparent 70%), radial-gradient(900px 600px at 0% 100%, #edf2e5, transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(${dark ? "#ffffff14" : "#14302714"} 1.3px, transparent 1.4px)`,
          backgroundSize: "34px 34px",
          backgroundPosition: `${drift}px ${drift * 0.6}px`,
          maskImage: "radial-gradient(1200px 800px at 50% 45%, black, transparent 85%)",
          WebkitMaskImage: "radial-gradient(1200px 800px at 50% 45%, black, transparent 85%)",
        }}
      />
      {dark && <AbsoluteFill style={{ background: "radial-gradient(1400px 900px at 50% 50%, transparent 60%, #00000055)" }} />}
    </AbsoluteFill>
  );
};

/* ---------- type ---------- */
export const Words: React.FC<{
  text: string;
  start: number;
  size: number;
  color?: string;
  weight?: number;
  stagger?: number;
  exitAt?: number;
  tracking?: number;
  lineHeight?: number;
  style?: React.CSSProperties;
  highlight?: string[];
  hlColor?: string;
}> = ({ text, start, size, color = C.ink, weight = 800, stagger = 3, exitAt, tracking = -0.045, lineHeight = 1.06, style, highlight = [], hlColor = C.green }) => {
  const f = useCurrentFrame();
  const exit = exitAt !== undefined ? ip(f, exitAt, exitAt + 10) : 0;
  let idx = 0;
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: size,
        fontWeight: weight,
        color,
        letterSpacing: `${tracking}em`,
        lineHeight,
        opacity: 1 - exit,
        transform: `translateY(${-exit * 24}px)`,
        ...style,
      }}
    >
      {text.split("\n").map((line, li) => (
        <div key={li} style={{ whiteSpace: "nowrap" }}>
          {line.split(" ").map((w, wi) => {
            const i = idx++;
            const p = sp(f, start + i * stagger, 20, 0.8, 140);
            const clean = w.replace(/[.,?]/g, "");
            return (
              <span key={wi} style={{ display: "inline-block", overflow: "hidden", verticalAlign: "top", paddingBottom: "0.1em", marginRight: "0.24em" }}>
                <span style={{ display: "inline-block", transform: `translateY(${(1 - p) * 108}%)`, color: highlight.includes(clean) ? hlColor : undefined }}>{w}</span>
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export const Eyebrow: React.FC<{ text: string; start: number; dark?: boolean; style?: React.CSSProperties }> = ({ text, start, dark, style }) => {
  const f = useCurrentFrame();
  const p = ip(f, start, start + 18);
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: 19,
        fontWeight: 700,
        letterSpacing: "0.28em",
        color: dark ? C.lime : C.green,
        display: "flex",
        alignItems: "center",
        gap: 16,
        opacity: p,
        transform: `translateX(${(1 - p) * -20}px)`,
        ...style,
      }}
    >
      <span style={{ width: 38 * p, height: 2, background: dark ? C.lime : C.green, display: "inline-block" }} />
      {text}
    </div>
  );
};

export const Chip: React.FC<{ start: number; children: React.ReactNode; dot?: string; dark?: boolean; size?: number; style?: React.CSSProperties }> = ({
  start,
  children,
  dot = C.leaf,
  dark,
  size = 22,
  style,
}) => {
  const f = useCurrentFrame();
  const p = sp(f, start, 14, 0.7, 160);
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: size,
        fontWeight: 600,
        letterSpacing: "-0.01em",
        color: dark ? "#e8f0ea" : C.ink,
        background: dark ? "#ffffff10" : "#ffffffee",
        border: `1px solid ${dark ? "#ffffff24" : C.line}`,
        borderRadius: 999,
        padding: `${size * 0.55}px ${size * 0.95}px`,
        display: "inline-flex",
        alignItems: "center",
        gap: size * 0.5,
        boxShadow: dark ? "none" : "0 18px 50px #1c392418, 0 3px 10px #1c39240d",
        opacity: Math.min(1, p * 1.4),
        transform: `translateY(${(1 - p) * 26}px) scale(${0.92 + 0.08 * p})`,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      <span style={{ width: size * 0.42, height: size * 0.42, borderRadius: 99, background: dot, boxShadow: `0 0 0 ${size * 0.22}px ${dot}22` }} />
      {children}
    </div>
  );
};

/* ---------- browser window around a real 1600x900 (2x) capture ---------- */
export const Window: React.FC<{
  src: string;
  w: number;
  zoom?: number;
  focus?: [number, number];
  layers?: { src: string; opacity: number }[];
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ src, w, zoom = 1, focus = [800, 450], layers = [], style, children }) => {
  const h = (w * 9) / 16;
  const k = w / 1600;
  return (
    <div
      style={{
        width: w,
        height: h + 40,
        borderRadius: 20,
        overflow: "hidden",
        background: "#fff",
        boxShadow: "0 70px 150px #0f241e40, 0 18px 40px #1430271f, 0 0 0 1px #14302714",
        position: "relative",
        ...style,
      }}
    >
      <div style={{ height: 40, background: "#eef1ea", borderBottom: "1px solid #e2e7df", display: "flex", alignItems: "center", padding: "0 18px", gap: 8 }}>
        {["#e1675d", "#e9b74b", "#62b85a"].map((c) => (
          <span key={c} style={{ width: 12, height: 12, borderRadius: 9, background: c, opacity: 0.85 }} />
        ))}
        <div
          style={{
            margin: "0 auto",
            fontFamily: FONT,
            fontSize: 14,
            color: C.muted,
            background: "#fff",
            border: "1px solid #e2e7df",
            borderRadius: 8,
            padding: "5px 70px",
            display: "flex",
            alignItems: "center",
            gap: 8,
          }}
        >
          <svg width="11" height="13" viewBox="0 0 11 13">
            <rect x="1" y="5.5" width="9" height="7" rx="1.5" fill={C.muted} />
            <path d="M3 5.5V4a2.5 2.5 0 015 0v1.5" stroke={C.muted} strokeWidth="1.4" fill="none" />
          </svg>
          127.0.0.1:8501 · ComplaintIQ
        </div>
        <span style={{ width: 52 }} />
      </div>
      <div style={{ position: "relative", width: w, height: h, overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            width: w,
            height: h,
            transformOrigin: "0 0",
            transform: `translate(${w / 2}px, ${h / 2}px) scale(${zoom}) translate(${-focus[0] * k}px, ${-focus[1] * k}px)`,
          }}
        >
          <Img src={src} style={{ width: w, height: h, position: "absolute" }} />
          {layers.map((l, i) => (
            <Img key={i} src={l.src} style={{ width: w, height: h, position: "absolute", opacity: l.opacity }} />
          ))}
          {children}
        </div>
      </div>
    </div>
  );
};

export const Cursor: React.FC<{ x: number; y: number; press: number; opacity: number }> = ({ x, y, press, opacity }) => (
  <div style={{ position: "absolute", left: x, top: y, opacity, pointerEvents: "none" }}>
    <div
      style={{
        position: "absolute",
        left: -30,
        top: -30,
        width: 60,
        height: 60,
        borderRadius: 99,
        border: `3px solid ${C.green}`,
        opacity: press > 0 ? 1 - press : 0,
        transform: `scale(${0.4 + press * 1.4})`,
      }}
    />
    <svg width="30" height="36" viewBox="0 0 24 28" style={{ transform: `scale(${1 - 0.14 * Math.sin(Math.PI * press)})`, filter: "drop-shadow(0 6px 10px #0005)" }}>
      <path d="M2 2 L2 22 L7.5 17 L11 25.5 L14.5 24 L11 15.5 L18.5 15.5 Z" fill="#111" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  </div>
);

export const BrandMark: React.FC<{ size: number; glow?: boolean }> = ({ size, glow = true }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.28,
      background: C.mint,
      color: "#163b2c",
      fontFamily: FONT,
      fontWeight: 800,
      fontSize: size * 0.56,
      letterSpacing: -size * 0.07,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      paddingRight: size * 0.04,
      boxShadow: glow ? "0 30px 80px #0006" : "none",
      flexShrink: 0,
    }}
  >
    cq<span style={{ color: C.leaf, fontSize: size * 0.5, marginTop: size * 0.25, letterSpacing: 0 }}>•</span>
  </div>
);

/** A real UI element capture floating as a card, with optional highlight rings in image pixels. */
export const Card: React.FC<{
  src: string;
  iw: number;
  ih: number;
  scale: number;
  style?: React.CSSProperties;
  rings?: { x: number; y: number; w: number; h: number; p: number; color?: string; label?: string }[];
}> = ({ src, iw, ih, scale, style, rings = [] }) => (
  <div
    style={{
      position: "absolute",
      width: iw * scale,
      height: ih * scale,
      borderRadius: 18,
      background: "#fff",
      boxShadow: "0 60px 140px #1430273a, 0 0 0 1px #14302714",
      ...style,
    }}
  >
    <Img src={src} style={{ width: iw * scale, height: ih * scale, borderRadius: 18, display: "block" }} />
    {rings.map((r, i) => (
      <div
        key={i}
        style={{
          position: "absolute",
          left: r.x * scale - 8,
          top: r.y * scale - 8,
          width: r.w * scale + 16,
          height: r.h * scale + 16,
          borderRadius: 14,
          border: `3px solid ${r.color ?? C.green}`,
          background: `${r.color ?? C.green}0d`,
          opacity: r.p,
          transform: `scale(${1.05 - 0.05 * r.p})`,
        }}
      >
        {r.label && (
          <div
            style={{
              position: "absolute",
              right: -12,
              top: -22,
              background: r.color ?? C.green,
              color: "#fff",
              fontFamily: FONT,
              fontSize: 17,
              fontWeight: 700,
              padding: "7px 14px",
              borderRadius: 9,
              whiteSpace: "nowrap",
            }}
          >
            {r.label}
          </div>
        )}
      </div>
    ))}
  </div>
);

export const Toast: React.FC<{ text: string; at: number; out?: number; style?: React.CSSProperties }> = ({ text, at, out, style }) => {
  const f = useCurrentFrame();
  if (f < at) return null;
  const p = sp(f, at, 15, 0.7, 150);
  const o = out !== undefined ? 1 - ip(f, out, out + 10) : 1;
  return (
    <div
      style={{
        position: "absolute",
        display: "flex",
        alignItems: "center",
        gap: 14,
        background: C.deep,
        color: "#eef4ee",
        fontFamily: FONT,
        fontSize: 22,
        fontWeight: 600,
        padding: "14px 24px 14px 14px",
        borderRadius: 14,
        boxShadow: "0 24px 60px #14302744",
        opacity: Math.min(1, p * 1.5) * o,
        transform: `translateY(${(1 - p) * 30 - (1 - o) * 14}px) scale(${0.95 + 0.05 * p})`,
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      <span style={{ width: 30, height: 30, borderRadius: 99, background: C.lime, color: C.deep, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 17, fontWeight: 800 }}>
        ✓
      </span>
      {text}
    </div>
  );
};

/* ---------- flow primitives ---------- */
/** Connector that draws itself, then lights up as a packet passes. */
export const Flow: React.FC<{
  d: string;
  draw: [number, number];
  run?: [number, number];
  color?: string;
  base?: string;
  width?: number;
  packet?: boolean;
  dashed?: boolean;
}> = ({ d, draw, run, color = C.green, base = "#14302724", width = 3, packet = true, dashed }) => {
  const f = useCurrentFrame();
  const len = getLength(d);
  const dp = ip(f, draw[0], draw[1], 0, 1, Easing.inOut(Easing.cubic));
  const ev = evolvePath(dp, d);
  const rp = run ? ip(f, run[0], run[1], 0, 1, Easing.inOut(Easing.sin)) : 0;
  const lit = evolvePath(rp, d);
  const pt = getPointAtLength(d, Math.max(0.01, Math.min(len - 0.01, rp * len)));
  const showPacket = packet && run && f >= run[0] && f <= run[1] + 4;
  return (
    <g>
      <path d={d} fill="none" stroke={base} strokeWidth={width} strokeLinecap="round" strokeDasharray={dashed ? "2 10" : ev.strokeDasharray} strokeDashoffset={dashed ? 0 : ev.strokeDashoffset} opacity={dashed ? dp : 1} />
      {run && rp > 0 && <path d={d} fill="none" stroke={color} strokeWidth={width + 0.5} strokeLinecap="round" strokeDasharray={lit.strokeDasharray} strokeDashoffset={lit.strokeDashoffset} />}
      {showPacket && (
        <g transform={`translate(${pt.x} ${pt.y})`}>
          <circle r={18} fill={color} opacity={0.16} />
          <circle r={9} fill={color} />
          <circle r={4} fill="#fff" />
        </g>
      )}
    </g>
  );
};

/** Packets looping along a path (continuous throughput). */
export const Stream: React.FC<{ d: string; from: number; every: number; travel: number; color?: string; until?: number; r?: number }> = ({
  d,
  from,
  every,
  travel,
  color = C.lime,
  until = 99999,
  r = 6,
}) => {
  const f = useCurrentFrame();
  const len = getLength(d);
  const dots: React.ReactNode[] = [];
  for (let s = from; s <= Math.min(f, until); s += every) {
    const p = (f - s) / travel;
    if (p < 0 || p > 1) continue;
    const pt = getPointAtLength(d, Math.max(0.01, Math.min(len - 0.01, Easing.inOut(Easing.sin)(p) * len)));
    const o = Math.min(1, p * 6, (1 - p) * 6);
    dots.push(
      <g key={s} transform={`translate(${pt.x} ${pt.y})`} opacity={o}>
        <circle r={r * 2.2} fill={color} opacity={0.18} />
        <circle r={r} fill={color} />
      </g>,
    );
  }
  return <g>{dots}</g>;
};

/* ---------- scene wrapper with varied entrances ---------- */
export type Enter = "fade" | "circle" | "up" | "left" | "zoom";
export const Scene: React.FC<{ from: number; dur: number; children: React.ReactNode; enter?: Enter; fadeOut?: number }> = ({ from, dur, children, enter = "fade", fadeOut = 14 }) => (
  <Sequence from={from} durationInFrames={dur}>
    <Fader dur={dur} enter={enter} fadeOut={fadeOut}>
      {children}
    </Fader>
  </Sequence>
);
const Fader: React.FC<{ dur: number; enter: Enter; fadeOut: number; children: React.ReactNode }> = ({ dur, enter, fadeOut, children }) => {
  const f = useCurrentFrame();
  const out = ip(f, dur - fadeOut, dur, 0, 1, Easing.in(Easing.quad));
  const e = ip(f, 0, enter === "circle" ? 26 : 20, 0, 1, Easing.bezier(0.65, 0, 0.35, 1));
  let style: React.CSSProperties = {};
  if (enter === "fade") style = { opacity: Math.min(1, f / 12) };
  if (enter === "circle") style = { clipPath: `circle(${e * 80}% at 50% 50%)` };
  if (enter === "up") style = { transform: `translateY(${(1 - e) * 1080}px)` };
  if (enter === "left") style = { transform: `translateX(${(1 - e) * 1920}px)` };
  if (enter === "zoom") style = { opacity: Math.min(1, f / 10), transform: `scale(${1.08 - 0.08 * e})` };
  return (
    <AbsoluteFill style={style}>
      <AbsoluteFill style={{ filter: `blur(${out * 8}px)`, transform: `scale(${1 - out * 0.04})` }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- icons (simple strokes) ---------- */
export const Icon: React.FC<{ name: string; size?: number; color?: string }> = ({ name, size = 34, color = C.green }) => {
  const s = { fill: "none", stroke: color, strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };
  const paths: Record<string, React.ReactNode> = {
    doc: (
      <>
        <path d="M6 3h8l4 4v14H6z" {...s} />
        <path d="M14 3v4h4M9 12h6M9 16h6" {...s} />
      </>
    ),
    shield: (
      <>
        <path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z" {...s} />
        <path d="M9 12l2 2 4-4" {...s} />
      </>
    ),
    chip: (
      <>
        <rect x="6" y="6" width="12" height="12" rx="2" {...s} />
        <rect x="9.5" y="9.5" width="5" height="5" rx="1" {...s} />
        <path d="M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3" {...s} />
      </>
    ),
    check: (
      <>
        <rect x="4" y="4" width="16" height="16" rx="3" {...s} />
        <path d="M8 12l3 3 5-6" {...s} />
      </>
    ),
    rules: (
      <>
        <path d="M5 6h14M5 12h14M5 18h9" {...s} />
        <circle cx="18" cy="18" r="2" {...s} />
      </>
    ),
    folder: (
      <>
        <path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" {...s} />
        <path d="M8 13h8" {...s} />
      </>
    ),
    person: (
      <>
        <circle cx="12" cy="8" r="4" {...s} />
        <path d="M4 21c1-4 4-6 8-6s7 2 8 6" {...s} />
      </>
    ),
    db: (
      <>
        <ellipse cx="12" cy="6" rx="7" ry="3" {...s} />
        <path d="M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3" {...s} />
      </>
    ),
    browser: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2.5" {...s} />
        <path d="M3 9h18M6.5 6.5h.01M9 6.5h.01" {...s} />
      </>
    ),
    server: (
      <>
        <rect x="4" y="4" width="16" height="7" rx="2" {...s} />
        <rect x="4" y="13" width="16" height="7" rx="2" {...s} />
        <path d="M8 7.5h.01M8 16.5h.01" {...s} />
      </>
    ),
    archive: (
      <>
        <rect x="3" y="4" width="18" height="5" rx="1.5" {...s} />
        <path d="M5 9v10a1 1 0 001 1h12a1 1 0 001-1V9M10 13h4" {...s} />
      </>
    ),
    bolt: <path d="M13 3L5 14h6l-1 7 8-11h-6z" {...s} />,
    package: (
      <>
        <path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z" {...s} />
        <path d="M4 7.5l8 4.5 8-4.5M12 12v9" {...s} />
      </>
    ),
    cloud: <path d="M7 18a4 4 0 01-.5-8 6 6 0 0111.5 1.5A3.5 3.5 0 0117.5 18z" {...s} />,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24">
      {paths[name]}
    </svg>
  );
};
