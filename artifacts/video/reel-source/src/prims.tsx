import React from "react";
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
} from "remotion";

export const FPS = 30;

export const C = {
  ivory: "#f5f5f0",
  paper: "#fbfcf8",
  deep: "#142e27",
  deeper: "#0f241e",
  ink: "#233c34",
  muted: "#66766d",
  green: "#22705a",
  mint: "#d4e8d6",
  leaf: "#35866a",
  line: "#e2e7df",
  sage: "#a6bdb0",
  lime: "#b9e07f",
  amber: "#f1e5cb",
};

export const EASE = Easing.bezier(0.22, 1, 0.36, 1);
export const ip = (f: number, a: number, b: number, from = 0, to = 1, e = EASE) =>
  interpolate(f, [a, b], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: e,
  });
export const sp = (f: number, delay = 0, damping = 18, mass = 0.9, stiffness = 120) =>
  spring({ frame: f - delay, fps: FPS, config: { damping, mass, stiffness } });
export const shot = (n: string) => staticFile(`shots/${n}.png`);

/* ---------- global type ---------- */
export const Fonts = () => (
  <style>{[400, 500, 600, 700, 800]
    .map(
      (w) =>
        `@font-face{font-family:'InterV';font-weight:${w};src:url(${staticFile(
          `fonts/inter-latin-${w}-normal.woff2`
        )}) format('woff2');}`
    )
    .join("\n")}</style>
);
export const FONT = "InterV, Inter, -apple-system, sans-serif";

/* ---------- primitives ---------- */
export const Background: React.FC<{ dark?: boolean; glow?: [number, number] }> = ({ dark, glow = [70, 30] }) => {
  const f = useCurrentFrame();
  const drift = f * 0.15;
  return (
    <AbsoluteFill
      style={{
        background: dark ? C.deep : C.ivory,
        overflow: "hidden",
      }}
    >
      <AbsoluteFill
        style={{
          background: dark
            ? `radial-gradient(1100px 700px at ${glow[0]}% ${glow[1]}%, #22705a55, transparent 70%), radial-gradient(900px 700px at 10% 100%, #0b1d18, transparent 70%)`
            : `radial-gradient(1000px 700px at ${glow[0]}% ${glow[1]}%, #d4e8d6aa, transparent 70%), radial-gradient(900px 600px at 0% 100%, #edf2e5, transparent 70%)`,
        }}
      />
      <AbsoluteFill
        style={{
          backgroundImage: `radial-gradient(${dark ? "#ffffff12" : "#14302712"} 1.3px, transparent 1.4px)`,
          backgroundSize: "34px 34px",
          backgroundPosition: `${drift}px ${drift * 0.6}px`,
          maskImage: "radial-gradient(1200px 800px at 50% 40%, black, transparent 85%)",
          WebkitMaskImage: "radial-gradient(1200px 800px at 50% 40%, black, transparent 85%)",
        }}
      />
    </AbsoluteFill>
  );
};

/** Word-by-word masked rise. */
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
}> = ({
  text,
  start,
  size,
  color = C.ink,
  weight = 800,
  stagger = 3,
  exitAt,
  tracking = -0.045,
  lineHeight = 1.04,
  style,
  highlight = [],
  hlColor = C.green,
}) => {
  const f = useCurrentFrame();
  const exit = exitAt !== undefined ? ip(f, exitAt, exitAt + 10) : 0;
  const lines = text.split("\n");
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
      {lines.map((line, li) => (
        <div key={li} style={{ display: "block", whiteSpace: "nowrap" }}>
          {line.split(" ").map((w, wi) => {
            const i = idx++;
            const p = sp(f, start + i * stagger, 20, 0.8, 140);
            const clean = w.replace(/[.,]/g, "");
            return (
              <span
                key={wi}
                style={{
                  display: "inline-block",
                  overflow: "hidden",
                  verticalAlign: "top",
                  paddingBottom: "0.08em",
                  marginRight: "0.24em",
                }}
              >
                <span
                  style={{
                    display: "inline-block",
                    transform: `translateY(${(1 - p) * 105}%)`,
                    color: highlight.includes(clean) ? hlColor : undefined,
                  }}
                >
                  {w}
                </span>
              </span>
            );
          })}
        </div>
      ))}
    </div>
  );
};

export const Eyebrow: React.FC<{ text: string; start: number; dark?: boolean; style?: React.CSSProperties }> = ({
  text,
  start,
  dark,
  style,
}) => {
  const f = useCurrentFrame();
  const p = ip(f, start, start + 18);
  return (
    <div
      style={{
        fontFamily: FONT,
        fontSize: 19,
        fontWeight: 600,
        letterSpacing: "0.28em",
        color: dark ? C.sage : C.green,
        display: "flex",
        alignItems: "center",
        gap: 16,
        opacity: p,
        transform: `translateX(${(1 - p) * -20}px)`,
        ...style,
      }}
    >
      <span style={{ width: 36 * p, height: 2, background: dark ? C.lime : C.green, display: "inline-block" }} />
      {text}
    </div>
  );
};

export const Chip: React.FC<{
  start: number;
  children: React.ReactNode;
  dot?: string;
  dark?: boolean;
  size?: number;
  style?: React.CSSProperties;
}> = ({ start, children, dot = C.leaf, dark, size = 24, style }) => {
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
        border: `1px solid ${dark ? "#ffffff22" : C.line}`,
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

/** UI window with camera control. Source captures are 1600x900 CSS px at 2x. */
export const Window: React.FC<{
  src: string;
  w: number;
  zoom?: number;
  focus?: [number, number];
  layers?: { src: string; opacity: number }[];
  radius?: number;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}> = ({ src, w, zoom = 1, focus = [800, 450], layers = [], radius = 22, style, children }) => {
  const h = (w * 9) / 16;
  const k = w / 1600;
  return (
    <div
      style={{
        width: w,
        height: h + 38,
        borderRadius: radius,
        overflow: "hidden",
        background: "#fff",
        boxShadow: "0 60px 140px #14302733, 0 18px 40px #1430271f, 0 0 0 1px #14302714",
        position: "relative",
        ...style,
      }}
    >
      <div
        style={{
          height: 38,
          background: "#f0f2ec",
          borderBottom: "1px solid #e2e7df",
          display: "flex",
          alignItems: "center",
          padding: "0 16px",
          gap: 8,
        }}
      >
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
            padding: "4px 60px",
            letterSpacing: "0.01em",
          }}
        >
          🔒 127.0.0.1 · ComplaintIQ — on this Mac
        </div>
        <span style={{ width: 52 }} />
      </div>
      <div style={{ position: "relative", width: w, height: h, overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
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
        left: -34,
        top: -34,
        width: 68,
        height: 68,
        borderRadius: 99,
        border: `3px solid ${C.green}`,
        opacity: press > 0 ? 1 - press : 0,
        transform: `scale(${0.4 + press * 1.4})`,
      }}
    />
    <svg width="34" height="40" viewBox="0 0 24 28" style={{ transform: `scale(${1 - 0.12 * Math.sin(Math.PI * press)})`, filter: "drop-shadow(0 6px 10px #0004)" }}>
      <path d="M2 2 L2 22 L7.5 17 L11 25.5 L14.5 24 L11 15.5 L18.5 15.5 Z" fill="#111" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  </div>
);

export const BrandMark: React.FC<{ size: number }> = ({ size }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.3,
      background: C.mint,
      color: "#163b2c",
      fontFamily: FONT,
      fontWeight: 800,
      fontSize: size * 0.58,
      letterSpacing: -size * 0.07,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      paddingRight: size * 0.04,
      boxShadow: "0 30px 80px #0006",
    }}
  >
    cq<span style={{ color: C.leaf, fontSize: size * 0.5, marginTop: size * 0.25, letterSpacing: 0 }}>•</span>
  </div>
);

/** Scene wrapper with varied entrances. */
export type Enter = "fade" | "circle" | "up" | "left";
export const Scene: React.FC<{ from: number; dur: number; children: React.ReactNode; enter?: Enter; fadeOut?: number }> = ({
  from,
  dur,
  children,
  enter = "fade",
  fadeOut = 10,
}) => (
  <Sequence from={from} durationInFrames={dur}>
    <Fader dur={dur} enter={enter} fadeOut={fadeOut}>
      {children}
    </Fader>
  </Sequence>
);
const Fader: React.FC<{ dur: number; enter: Enter; fadeOut: number; children: React.ReactNode }> = ({
  dur,
  enter,
  fadeOut,
  children,
}) => {
  const f = useCurrentFrame();
  const out = ip(f, dur - fadeOut, dur, 0, 1, Easing.in(Easing.quad));
  const e = ip(f, 0, enter === "circle" ? 24 : 18, 0, 1, Easing.bezier(0.65, 0, 0.35, 1));
  let style: React.CSSProperties = {};
  if (enter === "fade") style = { opacity: Math.min(1, f / 10) };
  if (enter === "circle") style = { clipPath: `circle(${e * 80}% at 50% 50%)` };
  if (enter === "up") style = { transform: `translateY(${(1 - e) * 1080}px)` };
  if (enter === "left") style = { transform: `translateX(${(1 - e) * 1920}px)` };
  return (
    <AbsoluteFill style={{ ...style }}>
      <AbsoluteFill style={{ opacity: 1 - out * 0.0, filter: `blur(${out * 6}px)`, transform: `scale(${1 - out * 0.04})` }}>
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
