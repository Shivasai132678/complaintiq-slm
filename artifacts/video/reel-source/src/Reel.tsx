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
export const TOTAL = 1710; // 57 s

const C = {
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

const EASE = Easing.bezier(0.22, 1, 0.36, 1);
const ip = (f: number, a: number, b: number, from = 0, to = 1, e = EASE) =>
  interpolate(f, [a, b], [from, to], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: e,
  });
const sp = (f: number, delay = 0, damping = 18, mass = 0.9, stiffness = 120) =>
  spring({ frame: f - delay, fps: FPS, config: { damping, mass, stiffness } });
const shot = (n: string) => staticFile(`shots/${n}.png`);

/* ---------- global type ---------- */
const Fonts = () => (
  <style>{[400, 500, 600, 700, 800]
    .map(
      (w) =>
        `@font-face{font-family:'InterV';font-weight:${w};src:url(${staticFile(
          `fonts/inter-latin-${w}-normal.woff2`
        )}) format('woff2');}`
    )
    .join("\n")}</style>
);
const FONT = "InterV, Inter, -apple-system, sans-serif";

/* ---------- primitives ---------- */
const Background: React.FC<{ dark?: boolean; glow?: [number, number] }> = ({ dark, glow = [70, 30] }) => {
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
const Words: React.FC<{
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

const Eyebrow: React.FC<{ text: string; start: number; dark?: boolean; style?: React.CSSProperties }> = ({
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

const Chip: React.FC<{
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
const Window: React.FC<{
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

const Cursor: React.FC<{ x: number; y: number; press: number; opacity: number }> = ({ x, y, press, opacity }) => (
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

const BrandMark: React.FC<{ size: number }> = ({ size }) => (
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

/** Scene wrapper with cross-fade + subtle push. */
const Scene: React.FC<{ from: number; dur: number; children: React.ReactNode; fadeIn?: number; fadeOut?: number }> = ({
  from,
  dur,
  children,
  fadeIn = 8,
  fadeOut = 8,
}) => (
  <Sequence from={from} durationInFrames={dur}>
    <Fader dur={dur} fadeIn={fadeIn} fadeOut={fadeOut}>
      {children}
    </Fader>
  </Sequence>
);
const Fader: React.FC<{ dur: number; fadeIn: number; fadeOut: number; children: React.ReactNode }> = ({
  dur,
  fadeIn,
  fadeOut,
  children,
}) => {
  const f = useCurrentFrame();
  const o = Math.min(ip(f, 0, fadeIn, 0, 1, Easing.linear), ip(f, dur - fadeOut, dur, 1, 0, Easing.linear));
  const s = 1 + ip(f, dur - fadeOut, dur, 0, 0.03, Easing.in(Easing.quad));
  return <AbsoluteFill style={{ opacity: o, transform: `scale(${s})` }}>{children}</AbsoluteFill>;
};

/* ---------- S1 · the challenge ---------- */
const SNIPPETS = [
  "I was charged a $39 late fee even though my payment posted before the due date.",
  "My credit report shows an account I never opened.",
  "This public record has been sitting on my report for years now.",
  "My checking account deposit has not arrived and the bank cannot locate the transfer.",
  "I have been charged interest on my 0 % APR card for the 3rd month in a row.",
  "My credit card statement includes a duplicate merchant charge.",
  "There is an unauthorized charge on my credit card statement.",
  "I disputed the transaction and the extra payment was never reversed.",
];
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const count = Math.round(ip(f, 95, 150, 0, 1031863, Easing.out(Easing.cubic)));
  return (
    <AbsoluteFill>
      <Background glow={[78, 40]} />
      {/* stream of unsorted complaints */}
      <AbsoluteFill style={{ left: 1010, width: 820, perspective: 1600 }}>
        <div style={{ transform: "rotateY(-16deg) rotateX(6deg)", transformOrigin: "left center" }}>
          {Array.from({ length: 14 }).map((_, i) => {
            const y = 1180 - ((f * 3.2 + i * 150) % (14 * 150));
            const appear = ip(f, 4 + i * 4, 22 + i * 4);
            const col = i % 2;
            return (
              <div
                key={i}
                style={{
                  position: "absolute",
                  left: col ? 140 : 0,
                  top: y - 200,
                  width: 620,
                  background: "#fff",
                  borderRadius: 18,
                  padding: "22px 26px",
                  border: `1px solid ${C.line}`,
                  boxShadow: "0 22px 50px #1c39241a",
                  fontFamily: FONT,
                  opacity: appear * (0.55 + 0.45 * Math.sin((i + 1) * 1.7) ** 2),
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 14, letterSpacing: "0.2em", color: C.muted, fontWeight: 600 }}>COMPLAINT</span>
                  <span
                    style={{
                      fontSize: 14,
                      color: "#8a6a2a",
                      background: "#f6efdc",
                      borderRadius: 7,
                      padding: "3px 10px",
                      fontWeight: 600,
                    }}
                  >
                    Unsorted
                  </span>
                </div>
                <div style={{ fontSize: 22, color: C.ink, lineHeight: 1.4 }}>{SNIPPETS[i % SNIPPETS.length]}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          background: `linear-gradient(90deg, ${C.ivory} 0%, ${C.ivory} 46%, ${C.ivory}00 62%)`,
        }}
      />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${C.ivory} 0%, transparent 14%, transparent 86%, ${C.ivory} 100%)` }} />
      <div style={{ position: "absolute", left: 140, top: 250 }}>
        <Eyebrow text="THE CHALLENGE" start={4} />
        <Words
          text={"Every complaint is\na customer's story."}
          start={10}
          size={92}
          style={{ marginTop: 30 }}
          highlight={["story"]}
        />
        <Words
          text={"Most are still sorted by hand."}
          start={62}
          size={44}
          weight={600}
          color={C.muted}
          tracking={-0.025}
          style={{ marginTop: 34 }}
        />
        <div
          style={{
            marginTop: 70,
            fontFamily: FONT,
            opacity: ip(f, 92, 108),
            transform: `translateY(${ip(f, 92, 110, 20, 0)}px)`,
            display: "flex",
            alignItems: "baseline",
            gap: 22,
          }}
        >
          <span style={{ fontSize: 76, fontWeight: 800, color: C.deep, letterSpacing: "-0.04em", fontVariantNumeric: "tabular-nums" }}>
            {count.toLocaleString("en-US")}
          </span>
          <span style={{ fontSize: 24, color: C.muted, lineHeight: 1.35, fontWeight: 500 }}>
            complaint records in the
            <br />
            public CFPB archive we learned from
          </span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S2 · brand ---------- */
const S2: React.FC = () => {
  const f = useCurrentFrame();
  const m = sp(f, 4, 13, 1, 110);
  const wipe = ip(f, 16, 44);
  return (
    <AbsoluteFill>
      <Background dark glow={[50, 45]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div
          style={{
            position: "absolute",
            width: 900,
            height: 900,
            borderRadius: 999,
            background: "radial-gradient(circle, #35866a44, transparent 60%)",
            transform: `scale(${0.6 + m * 0.6})`,
            opacity: m,
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 46, transform: `translateY(${ip(f, 60, 90, 0, -50)}px)` }}>
          <div style={{ transform: `scale(${0.5 + 0.5 * m}) rotate(${(1 - m) * -14}deg)`, opacity: Math.min(1, m * 2) }}>
            <BrandMark size={190} />
          </div>
          <div style={{ clipPath: `inset(0 ${(1 - wipe) * 100}% 0 0)` }}>
            <div style={{ fontFamily: FONT, fontSize: 150, fontWeight: 800, color: "#fff", letterSpacing: "-0.05em", lineHeight: 1 }}>
              ComplaintIQ
            </div>
            <div
              style={{
                fontFamily: FONT,
                fontSize: 24,
                letterSpacing: "0.42em",
                color: C.sage,
                fontWeight: 600,
                marginTop: 18,
                opacity: ip(f, 30, 50),
              }}
            >
              LOCAL COMPLAINT INTELLIGENCE
            </div>
          </div>
        </div>
        <div style={{ position: "absolute", top: 720, display: "flex", gap: 22 }}>
          <Chip start={70} dark dot={C.lime}>Fine-tuned Qwen2.5 · 1.5B</Chip>
          <Chip start={80} dark dot={C.lime}>Runs on Apple Silicon</Chip>
          <Chip start={90} dark dot={C.lime}>No cloud. No API.</Chip>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- S3 · analyze ---------- */
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const W = 1360;
  const k = W / 1600;
  const enter = sp(f, 0, 20, 1, 90);
  // frames
  const typing = Math.floor(ip(f, 26, 112, 0, 10, Easing.linear));
  const pressAt = 140;
  const busy = f >= pressAt + 3 && f < 168;
  const caseO = ip(f, 166, 178, 0, 1, Easing.linear);
  let src = shot(`analyze_${String(typing).padStart(2, "0")}`);
  if (busy || f >= 166) src = shot("analyze_busy");
  // camera
  let zoom = 1;
  let focus: [number, number] = [800, 450];
  const zIn = ip(f, 14, 44);
  const zOut = ip(f, 108, 132);
  zoom = 1 + 0.42 * zIn - 0.32 * zOut;
  focus = [interpolate(zIn - zOut * 0.6, [0, 1], [800, 650]), interpolate(zIn, [0, 1], [450, 520]) + zOut * 120];
  // case page camera
  const cz = ip(f, 186, 236);
  if (f >= 170) {
    zoom = interpolate(cz, [0, 1], [1.1, 1.5]);
    focus = [interpolate(cz, [0, 1], [760, 560]), interpolate(cz, [0, 1], [470, 360])];
  }
  // cursor (in window-local display px, before zoom we map through camera)
  const cp = ip(f, 112, 138);
  const cx = interpolate(cp, [0, 1], [1120, 391]);
  const cy = interpolate(cp, [0, 1], [880, 761]);
  const press = f >= pressAt ? ip(f, pressAt, pressAt + 14, 0, 1, Easing.out(Easing.quad)) : 0;
  const curO = ip(f, 108, 116) * (1 - ip(f, 160, 168));
  return (
    <AbsoluteFill>
      <Background glow={[60, 25]} />
      <div style={{ position: "absolute", left: 120, top: 70, width: 1700, height: 120 }}>
        <Eyebrow text="01 — ANALYZE" start={0} />
        <Words text="Paste the customer's story." start={4} size={58} exitAt={160} style={{ position: "absolute", top: 44 }} />
        <Words
          text="Classified in about a second."
          start={172}
          size={58}
          highlight={["second"]}
          style={{ position: "absolute", top: 44 }}
        />
      </div>
      <div
        style={{
          position: "absolute",
          left: (1920 - W) / 2 + 120,
          top: 230,
          perspective: 2200,
        }}
      >
        <div
          style={{
            transform: `translateY(${(1 - enter) * 160}px) rotateX(${(1 - enter) * 14}deg)`,
            opacity: Math.min(1, enter * 1.6),
            transformOrigin: "50% 100%",
          }}
        >
          <Window
            src={src}
            w={W}
            zoom={zoom}
            focus={focus}
            layers={[{ src: shot("case_new"), opacity: caseO }]}
          >
            <div style={{ position: "absolute", left: cx * k, top: cy * k }}>
              <Cursor x={0} y={0} press={press} opacity={curO} />
            </div>
          </Window>
        </div>
      </div>
      {/* result chips */}
      <div style={{ position: "absolute", left: 930, top: 118, display: "flex", gap: 16 }}>
        <Chip start={204} size={22}>
          <span>
            Credit card <span style={{ color: C.muted, fontWeight: 500 }}>·</span> Fees or interest
          </span>
        </Chip>
        <Chip start={212} size={22} dot={C.lime}>
          0.79 s · on this Mac
        </Chip>
        <Chip start={220} size={22} dot="#7aa58c">
          Fine-tuned Qwen2.5
        </Chip>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S4 · policy ---------- */
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const e = sp(f, 4, 18, 1, 80);
  const hl1 = ip(f, 40, 58);
  const hl2 = ip(f, 78, 96);
  const S = 0.7;
  const rows: [string, string, number][] = [
    ["Priority", "Medium", 60],
    ["Route to", "Card Services Team", 74],
    ["Reason", "Rule matched “refund”", 88],
  ];
  return (
    <AbsoluteFill>
      <Background glow={[75, 50]} />
      <div style={{ position: "absolute", left: 130, top: 220, width: 760 }}>
        <Eyebrow text="02 — TRANSPARENT POLICY" start={2} />
        <Words text={"Rules you can read.\nReasons you can see."} start={6} size={74} style={{ marginTop: 28 }} highlight={["see"]} />
        <div style={{ marginTop: 60, display: "flex", flexDirection: "column", gap: 18 }}>
          {rows.map(([k, v, s]) => {
            const p = sp(f, s, 16, 0.8, 140);
            return (
              <div
                key={k}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 26,
                  fontFamily: FONT,
                  opacity: p,
                  transform: `translateX(${(1 - p) * -30}px)`,
                }}
              >
                <span style={{ width: 150, fontSize: 20, letterSpacing: "0.2em", color: C.muted, fontWeight: 600 }}>
                  {k.toUpperCase()}
                </span>
                <span
                  style={{
                    fontSize: 30,
                    fontWeight: 700,
                    color: C.ink,
                    background: k === "Priority" ? "#f6efdc" : "#fff",
                    border: `1px solid ${k === "Priority" ? "#ead9ae" : C.line}`,
                    padding: "10px 20px",
                    borderRadius: 12,
                    letterSpacing: "-0.01em",
                  }}
                >
                  {v}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ position: "absolute", left: 980, top: 200, perspective: 1800 }}>
        <div
          style={{
            transform: `translateX(${(1 - e) * 200}px) rotateY(${-18 * (1 - e) - 6}deg) rotateX(${3}deg) translateY(${Math.sin(f / 30) * 6}px)`,
            transformOrigin: "0 50%",
            opacity: Math.min(1, e * 1.5),
            position: "relative",
            width: 1270 * S,
            height: 848 * S,
            borderRadius: 22,
            boxShadow: "0 60px 140px #14302738, 0 0 0 1px #14302712",
          }}
        >
          <Img src={shot("el_analysis")} style={{ width: 1270 * S, height: 848 * S, borderRadius: 18 }} />
          {[
            [30, 232, 1210, 238, hl1, "AI · fine-tuned model"],
            [30, 542, 1210, 238, hl2, "Policy · explicit rules"],
          ].map(([x, y, w, h, p, label]: any, i) => (
            <div
              key={i}
              style={{
                position: "absolute",
                left: x * S - 8,
                top: y * S - 6,
                width: w * S + 16,
                height: h * S + 12,
                borderRadius: 16,
                border: `3px solid ${i ? "#c79a2b" : C.green}`,
                background: i ? "#f1e5cb22" : "#22705a0d",
                opacity: p,
                transform: `scale(${1.04 - 0.04 * p})`,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  right: -14,
                  top: -22,
                  background: i ? "#c79a2b" : C.green,
                  color: "#fff",
                  fontFamily: FONT,
                  fontSize: 18,
                  fontWeight: 700,
                  padding: "7px 14px",
                  borderRadius: 9,
                  letterSpacing: "0.02em",
                }}
              >
                {label}
              </div>
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S5 · human in the loop ---------- */
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const cards = [
    { src: "el_review_after", w: 1270, h: 1266, x: 120, y: 300, s: 0.44, at: 18, label: "Confirm or correct" },
    { src: "el_forward", w: 1270, h: 612, x: 700, y: 360, s: 0.44, at: 92, label: "Move it forward" },
    { src: "el_history", w: 1270, h: 1014, x: 1290, y: 300, s: 0.44, at: 160, label: "Every change kept" },
  ];
  const active = f < 92 ? 0 : f < 160 ? 1 : 2;
  const steps = ["Queued", "In review", "Resolved"];
  const stepP = [ip(f, 30, 40), ip(f, 110, 120), ip(f, 178, 190)];
  return (
    <AbsoluteFill>
      <Background glow={[50, 15]} />
      <div style={{ position: "absolute", left: 120, top: 70 }}>
        <Eyebrow text="03 — HUMAN IN THE LOOP" start={2} />
        <Words text="People make the final call." start={6} size={64} style={{ marginTop: 22 }} highlight={["final", "call"]} />
      </div>
      {cards.map((c, i) => {
        const p = sp(f, c.at, 17, 1, 100);
        const isA = i === active;
        const dim = ip(f, c.at + 30, c.at + 50) * (isA ? 0 : 1);
        return (
          <div
            key={c.src}
            style={{
              position: "absolute",
              left: c.x,
              top: c.y,
              opacity: Math.min(1, p * 1.4),
              transform: `translateY(${(1 - p) * 120 + (isA ? -10 : 0)}px) scale(${(0.94 + 0.06 * p) * (isA ? 1.02 : 0.97)})`,
              transformOrigin: "50% 0",
              filter: `saturate(${1 - dim * 0.4})`,
            }}
          >
            <div
              style={{
                fontFamily: FONT,
                fontSize: 20,
                fontWeight: 700,
                color: isA ? C.green : C.muted,
                letterSpacing: "0.12em",
                marginBottom: 14,
              }}
            >
              {String(i + 1).padStart(2, "0")} · {c.label.toUpperCase()}
            </div>
            <Img
              src={shot(c.src)}
              style={{
                width: c.w * c.s,
                height: c.h * c.s,
                borderRadius: 16,
                boxShadow: isA ? "0 50px 120px #1430272e, 0 0 0 2px #22705a55" : "0 24px 60px #1430271a, 0 0 0 1px #14302712",
                opacity: 1 - dim * 0.35,
              }}
            />
          </div>
        );
      })}
      {/* lifecycle rail */}
      <div style={{ position: "absolute", left: 120, top: 965, display: "flex", alignItems: "center", gap: 18, fontFamily: FONT }}>
        {steps.map((s, i) => (
          <React.Fragment key={s}>
            <div
              style={{
                padding: "10px 22px",
                borderRadius: 999,
                fontSize: 22,
                fontWeight: 700,
                color: stepP[i] > 0.5 ? "#fff" : C.muted,
                background: stepP[i] > 0.5 ? (i === 2 ? C.deep : C.green) : "#fff",
                border: `1px solid ${C.line}`,
                transform: `scale(${1 + 0.08 * Math.sin(Math.PI * stepP[i])})`,
              }}
            >
              {s}
            </div>
            {i < 2 && (
              <div style={{ width: 90, height: 3, background: C.line, position: "relative", borderRadius: 3 }}>
                <div style={{ position: "absolute", inset: 0, width: `${stepP[i + 1] * 100}%`, background: C.green, borderRadius: 3 }} />
              </div>
            )}
          </React.Fragment>
        ))}
        <span style={{ marginLeft: 26, fontSize: 21, color: C.muted, fontWeight: 500, opacity: ip(f, 200, 216) }}>
          Append-only history · original prediction never overwritten
        </span>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S6 · batches ---------- */
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const W = 1130;
  const seq = ["import_preview", "import_prog_00", "import_prog_02", "import_prog_04", "import_prog_06", "import_prog_08", "import_prog_10", "import_done"];
  const i = Math.min(seq.length - 1, Math.floor(ip(f, 18, 118, 0, seq.length - 0.01, Easing.linear)));
  const e = sp(f, 0, 20, 1, 90);
  const z = ip(f, 26, 70);
  return (
    <AbsoluteFill>
      <Background glow={[30, 40]} />
      <div style={{ position: "absolute", left: 120, top: 300, width: 520 }}>
        <Eyebrow text="04 — DURABLE BATCHES" start={2} />
        <Words text={"Whole batches.\nSaved row by row."} start={6} size={64} style={{ marginTop: 26 }} highlight={["row"]} />
        <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
          <Chip start={40} size={22}>CSV · up to 100 complaints</Chip>
          <Chip start={50} size={22} dot={C.lime}>Survives refresh & restart</Chip>
          <Chip start={60} size={22} dot="#7aa58c">Retry failed rows</Chip>
        </div>
      </div>
      <div style={{ position: "absolute", left: 740, top: 205, perspective: 2000 }}>
        <div
          style={{
            transform: `translateX(${(1 - e) * 240}px) rotateY(${-10 * (1 - e) - 4}deg)`,
            transformOrigin: "0 50%",
            opacity: Math.min(1, e * 1.5),
          }}
        >
          <Window src={shot(seq[i])} w={W} zoom={1 + 0.22 * z} focus={[interpolate(z, [0, 1], [800, 930]), interpolate(z, [0, 1], [450, 430])]} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S7 · evidence ---------- */
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const stats = [
    { v: (p: number) => Math.round(9000 * p).toLocaleString("en-US"), l: "real CFPB complaints\nused for fine-tuning", at: 14 },
    { v: (p: number) => (88.9 * p).toFixed(1) + "%", l: "product accuracy on\nheld-out complaints", at: 30 },
    { v: (p: number) => "~" + (0.95 * p).toFixed(2) + "s", l: "mean inference\non an M1 MacBook", at: 46 },
    { v: (p: number) => Math.round(100 * p) + "%", l: "on-device. No external\nAI service sees the text", at: 62 },
  ];
  return (
    <AbsoluteFill>
      <Background dark glow={[60, 20]} />
      <div style={{ position: "absolute", left: 130, top: 140 }}>
        <Eyebrow text="05 — MEASURED, NOT PROMISED" start={2} dark />
        <Words text="Evidence you can audit." start={6} size={72} color="#fff" style={{ marginTop: 26 }} highlight={["audit"]} hlColor={C.lime} />
      </div>
      <div style={{ position: "absolute", left: 130, right: 130, top: 470, display: "flex", gap: 0 }}>
        {stats.map((s, i) => {
          const p = ip(f, s.at, s.at + 50, 0, 1, Easing.out(Easing.cubic));
          const o = ip(f, s.at, s.at + 12);
          return (
            <div
              key={i}
              style={{
                flex: 1,
                paddingLeft: i ? 44 : 0,
                borderLeft: i ? "1px solid #ffffff22" : "none",
                opacity: o,
                transform: `translateY(${(1 - o) * 30}px)`,
                fontFamily: FONT,
              }}
            >
              <div style={{ fontSize: 108, fontWeight: 800, color: i === 1 ? C.lime : "#fff", letterSpacing: "-0.05em", fontVariantNumeric: "tabular-nums" }}>
                {s.v(p)}
              </div>
              <div style={{ fontSize: 25, color: C.sage, marginTop: 14, lineHeight: 1.4, whiteSpace: "pre-line", fontWeight: 500 }}>{s.l}</div>
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          left: 130,
          right: 130,
          top: 830,
          paddingTop: 30,
          borderTop: "1px solid #ffffff1c",
          fontFamily: FONT,
          fontSize: 21,
          lineHeight: 1.6,
          color: "#9fb3a8",
          opacity: ip(f, 120, 140),
        }}
      >
        Reserved test set of 153 CFPB complaints · joint product + issue accuracy 54.2% · schema-validated output, invalid results go to review
        <br />
        Priority and routing are explicit rules · summaries are extractive · issue labels are confirmed by people
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S8 · outro ---------- */
const S8: React.FC = () => {
  const f = useCurrentFrame();
  const m = sp(f, 4, 14, 1, 110);
  const end = ip(f, 140, 165, 0, 1, Easing.linear);
  return (
    <AbsoluteFill>
      <Background glow={[50, 40]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 34, transform: `scale(${0.9 + 0.1 * m})`, opacity: Math.min(1, m * 1.6) }}>
          <BrandMark size={130} />
          <div style={{ fontFamily: FONT, fontSize: 112, fontWeight: 800, color: C.deep, letterSpacing: "-0.05em" }}>ComplaintIQ</div>
        </div>
        <Words
          text="Private, accountable complaint triage."
          start={18}
          size={44}
          weight={600}
          color={C.green}
          tracking={-0.02}
          style={{ marginTop: 40 }}
        />
        <div
          style={{
            marginTop: 70,
            fontFamily: FONT,
            fontSize: 21,
            color: C.muted,
            letterSpacing: "0.22em",
            fontWeight: 600,
            opacity: ip(f, 48, 66),
          }}
        >
          QWEN2.5 · QLORA · LLAMA.CPP METAL · FASTAPI · REACT · SQLITE
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: C.ivory, opacity: end }} />
    </AbsoluteFill>
  );
};

export const Reel: React.FC = () => (
  <AbsoluteFill style={{ background: C.ivory }}>
    <Fonts />
    <Scene from={0} dur={186} fadeIn={1}>
      <S1 />
    </Scene>
    <Scene from={180} dur={171}>
      <S2 />
    </Scene>
    <Scene from={345} dur={336}>
      <S3 />
    </Scene>
    <Scene from={675} dur={186}>
      <S4 />
    </Scene>
    <Scene from={855} dur={291}>
      <S5 />
    </Scene>
    <Scene from={1140} dur={156}>
      <S6 />
    </Scene>
    <Scene from={1290} dur={261}>
      <S7 />
    </Scene>
    <Scene from={1545} dur={165} fadeOut={1}>
      <S8 />
    </Scene>
    <Audio src={staticFile("mix.wav")} />
  </AbsoluteFill>
);
