import React from "react";
import { AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import {
  BrandMark, C, Card, Chip, Cursor, Eyebrow, FONT, Flow, Icon, MONO, Scene, Stream, Toast, Window, Words,
  Background, ip, loadFonts, shot, sp,
} from "./prims";

loadFonts();

/* Scene cuts (frames @30fps) — matched to audio/music.py CUTS and the voice-over in audio/vo.py */
const B = [0, 150, 330, 780, 1170, 1440, 1770, 2010, 2310, 2490, 2730, 2880];
export const TOTAL = B[B.length - 1]; // 96 s
const OV = 18;
const seg = (i: number) => ({ from: B[i], dur: B[i + 1] - B[i] + (i < B.length - 2 ? OV : 0) });

/* ---------- shared flow node ---------- */
const FlowNode: React.FC<{
  x: number; y: number; w?: number; h?: number; icon: string; title: string; sub: string; detail?: string;
  appear: number; at: number; dark?: boolean; accent?: string;
}> = ({ x, y, w = 236, h = 128, icon, title, sub, detail, appear, at, dark, accent = C.green }) => {
  const f = useCurrentFrame();
  const a = sp(f, appear, 16, 0.8, 140);
  const on = f >= at;
  const lit = ip(f, at, at + 10);
  const pulse = f >= at ? ip(f, at, at + 26) : 0;
  const det = ip(f, at + 4, at + 20);
  const bg = dark ? `rgba(255,255,255,${0.04 + 0.05 * lit})` : "#fff";
  const border = dark ? (on ? accent : "#ffffff22") : on ? accent : C.line;
  return (
    <div style={{ position: "absolute", left: x - w / 2, top: y - h / 2, width: w, opacity: Math.min(1, a * 1.4), transform: `translateY(${(1 - a) * 30}px) scale(${0.9 + 0.1 * a})` }}>
      <div
        style={{
          position: "absolute", left: -6, top: -6, width: w + 12, height: h + 12, borderRadius: 26,
          border: `2px solid ${accent}`, opacity: pulse > 0 ? 1 - pulse : 0, transform: `scale(${1 + pulse * 0.12})`,
        }}
      />
      <div
        style={{
          width: w, height: h, borderRadius: 22, background: bg, border: `${on ? 2 : 1}px solid ${border}`,
          boxShadow: dark ? (on ? `0 0 60px ${accent}44` : "none") : on ? `0 30px 70px ${accent}2e, 0 0 0 4px ${accent}14` : "0 18px 40px #1c39241a",
          padding: "20px 20px", boxSizing: "border-box", display: "flex", flexDirection: "column", gap: 10, fontFamily: FONT,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 44, height: 44, borderRadius: 12, display: "flex", alignItems: "center", justifyContent: "center",
              background: on ? accent : dark ? "#ffffff12" : "#eef3ec",
            }}
          >
            <Icon name={icon} size={26} color={on ? (dark ? C.deeper : "#fff") : dark ? C.sage : C.green} />
          </div>
          <div style={{ fontSize: 22, fontWeight: 800, color: dark ? "#fff" : C.ink, letterSpacing: "-0.02em", lineHeight: 1.1 }}>{title}</div>
        </div>
        <div style={{ fontSize: 17, fontWeight: 500, color: dark ? C.sage : C.muted, lineHeight: 1.3 }}>{sub}</div>
      </div>
      {detail && (
        <div
          style={{
            marginTop: 14, fontFamily: MONO, fontSize: 15, color: dark ? C.lime : C.green, textAlign: "center",
            opacity: det, transform: `translateY(${(1 - det) * 8}px)`, whiteSpace: "nowrap",
          }}
        >
          {detail}
        </div>
      )}
    </div>
  );
};

const curve = (x1: number, y1: number, x2: number, y2: number) => {
  const mx = (x1 + x2) / 2;
  return `M ${x1} ${y1} C ${mx} ${y1} ${mx} ${y2} ${x2} ${y2}`;
};

/* ================= S1 · intro ================= */
const S1: React.FC = () => {
  const f = useCurrentFrame();
  const m = sp(f, 26, 13, 1, 120);
  const ring = ip(f, 30, 70);
  const wipe = ip(f, 40, 70);
  const parts = Array.from({ length: 46 }).map((_, i) => {
    const ang = (i * 137.5 * Math.PI) / 180;
    const r0 = 500 + ((i * 97) % 380);
    const p = ip(f, 0, 30 + (i % 7), 0, 1, Easing.in(Easing.cubic));
    return { x: Math.cos(ang) * r0 * (1 - p), y: Math.sin(ang) * r0 * (1 - p) * 0.62, o: (1 - ip(f, 26, 34)) * Math.min(1, f / 8) };
  });
  return (
    <AbsoluteFill>
      <Background dark glow={[50, 48]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        {parts.map((p, i) => (
          <div key={i} style={{ position: "absolute", width: 6, height: 6, borderRadius: 9, background: i % 3 ? C.lime : C.mint, opacity: p.o * 0.8, transform: `translate(${p.x}px, ${p.y}px)` }} />
        ))}
        <div style={{ position: "absolute", width: 300, height: 300, borderRadius: 999, border: `2px solid ${C.lime}`, opacity: ring > 0 && ring < 1 ? 1 - ring : 0, transform: `scale(${0.4 + ring * 2.4})` }} />
        <div style={{ position: "absolute", width: 1000, height: 1000, borderRadius: 999, background: "radial-gradient(circle, #35866a3a, transparent 60%)", opacity: m }} />
        <div style={{ display: "flex", alignItems: "center", gap: 44, transform: `translateX(${(1 - wipe) * 250}px)` }}>
          <div style={{ transform: `scale(${m}) rotate(${(1 - m) * -20}deg)` }}>
            <BrandMark size={170} />
          </div>
          <div style={{ clipPath: `inset(-10px ${(1 - wipe) * 100}% -10px 0)` }}>
            <div style={{ fontFamily: FONT, fontSize: 138, fontWeight: 800, color: "#fff", letterSpacing: "-0.05em", lineHeight: 1 }}>ComplaintIQ</div>
            <div style={{ fontFamily: FONT, fontSize: 22, letterSpacing: "0.44em", color: C.sage, fontWeight: 600, marginTop: 18, opacity: ip(f, 58, 80) }}>
              LOCAL COMPLAINT INTELLIGENCE
            </div>
          </div>
        </div>
        <div style={{ position: "absolute", bottom: 110, display: "flex", alignItems: "center", gap: 26, opacity: ip(f, 86, 106), transform: `translateY(${ip(f, 86, 106, 16, 0)}px)` }}>
          <span style={{ width: 90, height: 1, background: "#ffffff30" }} />
          <span style={{ fontFamily: FONT, fontSize: 16, letterSpacing: "0.4em", color: C.sage, fontWeight: 600 }}>PREPARED FOR</span>
          <Img src={staticFile("veltris-logo-light.png")} style={{ height: 46 }} />
          <span style={{ width: 90, height: 1, background: "#ffffff30" }} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ================= S2 · the problem ================= */
const SNIPPETS = [
  "I was charged a $39 late fee even though my payment posted before the due date.",
  "My credit report shows a collection account I never opened.",
  "The bank placed a hold on my deposit and the money is still not available.",
  "My statement shows the same $120 purchase twice.",
  "I disputed it a month ago and the incorrect account is still there.",
  "I've been charged interest on my 0% APR card for three months.",
  "There is an unauthorized charge on my credit card statement.",
  "Nobody can tell me where my transfer went.",
];
const S2: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Background glow={[78, 40]} />
      <AbsoluteFill style={{ left: 1000, width: 860, perspective: 1600 }}>
        <div style={{ transform: "rotateY(-18deg) rotateX(6deg)", transformOrigin: "left center" }}>
          {Array.from({ length: 14 }).map((_, i) => {
            const y = 1200 - ((f * 3.4 + i * 150) % (14 * 150));
            const appear = ip(f, 2 + i * 3, 18 + i * 3);
            return (
              <div
                key={i}
                style={{
                  position: "absolute", left: i % 2 ? 150 : 0, top: y - 200, width: 620, background: "#fff", borderRadius: 18,
                  padding: "22px 26px", border: `1px solid ${C.line}`, boxShadow: "0 22px 50px #1c39241a", fontFamily: FONT,
                  opacity: appear * (0.5 + 0.5 * Math.sin((i + 1) * 1.7) ** 2),
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 14, letterSpacing: "0.2em", color: C.muted, fontWeight: 600 }}>COMPLAINT #{4821 + i * 37}</span>
                  <span style={{ fontSize: 14, color: "#8a6a2a", background: C.amberBg, borderRadius: 7, padding: "3px 10px", fontWeight: 600 }}>Unsorted</span>
                </div>
                <div style={{ fontSize: 22, color: C.ink, lineHeight: 1.4 }}>{SNIPPETS[i % SNIPPETS.length]}</div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: `linear-gradient(90deg, ${C.ivory} 0%, ${C.ivory} 46%, ${C.ivory}00 64%)` }} />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${C.ivory} 0%, transparent 14%, transparent 86%, ${C.ivory} 100%)` }} />
      <div style={{ position: "absolute", left: 140, top: 270 }}>
        <Eyebrow text="THE CHALLENGE" start={4} />
        <Words text={"Every complaint is\na customer's story."} start={8} size={92} style={{ marginTop: 30 }} highlight={["story"]} />
        <Words text="Most are still sorted by hand." start={78} size={44} weight={600} color={C.muted} tracking={-0.025} style={{ marginTop: 34 }} />
        <div style={{ marginTop: 44, display: "flex", gap: 14 }}>
          <Chip start={108} dot={C.amber}>Slow</Chip>
          <Chip start={116} dot={C.amber}>Inconsistent</Chip>
          <Chip start={124} dot={C.amber}>Hard to audit</Chip>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ================= S3 · the pipeline flow ================= */
const NODES = [
  { x: 200, y: 400, icon: "doc", title: "Complaint", sub: "Customer narrative", detail: "first 2,000 characters", at: 12 },
  { x: 510, y: 560, icon: "shield", title: "Scope gate", sub: "Supported product?", detail: "card · credit report · bank", at: 55 },
  { x: 820, y: 400, icon: "chip", title: "Qwen3-4B", sub: "Fine-tuned · local GPU", detail: "llama.cpp CUDA · ~0.2 s", at: 140 },
  { x: 1130, y: 560, icon: "check", title: "Label check", sub: "Strict schema", detail: "9 allowed product/issue pairs", at: 215 },
  { x: 1440, y: 400, icon: "rules", title: "Policy rules", sub: "Priority + routing", detail: "explicit, readable reasons", at: 272 },
  { x: 1730, y: 560, icon: "folder", title: "Case", sub: "Ready for review", detail: "original prediction kept", at: 335 },
];
const NW = 236;
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const edges = NODES.slice(0, -1).map((n, i) => curve(n.x + NW / 2, n.y, NODES[i + 1].x - NW / 2, NODES[i + 1].y));
  const branch = `M ${NODES[1].x} ${NODES[1].y + 64} C ${NODES[1].x} ${NODES[1].y + 150} ${NODES[1].x} ${NODES[1].y + 150} ${NODES[1].x} ${NODES[1].y + 214}`;
  // one continuous route for the throughput stream (passes behind the node cards)
  const route = NODES.map((n, i) => (i === 0 ? `M ${n.x - NW / 2} ${n.y} L ${n.x + NW / 2} ${n.y}` : `${edges[i - 1].replace(/^M [^C]+/, "")} L ${n.x + NW / 2} ${n.y}`)).join(" ");
  const push = ip(f, 0, 470, 1, 1.05, Easing.linear);
  return (
    <AbsoluteFill>
      <Background glow={[50, 40]} />
      <div style={{ position: "absolute", left: 110, top: 80 }}>
        <Eyebrow text="HOW IT WORKS" start={4} />
        <Words text="From complaint to case, in one flow." start={8} size={60} style={{ marginTop: 22 }} highlight={["one", "flow"]} />
      </div>
      <AbsoluteFill style={{ transform: `scale(${push})`, transformOrigin: "50% 55%" }}>
        <svg width={1920} height={1080} style={{ position: "absolute" }}>
          <Stream d={route} from={360} every={13} travel={150} color={C.leaf} r={5} />
          {edges.map((d, i) => (
            <Flow key={i} d={d} draw={[6 + i * 6, 40 + i * 6]} run={[NODES[i].at + 6, NODES[i + 1].at]} />
          ))}
          <Flow d={edges[0]} draw={[0, 1]} run={[72, 100]} color={C.amber} base="transparent" />
          <Flow d={branch} draw={[40, 70]} run={[100, 132]} color={C.amber} dashed />
        </svg>
        {NODES.map((n, i) => (
          <FlowNode key={i} {...n} appear={4 + i * 5} />
        ))}
        <FlowNode x={NODES[1].x} y={NODES[1].y + 290} icon="person" title="Needs review" sub="Off-topic · model not run" appear={44} at={132} accent={C.amber} />
        <div style={{ position: "absolute", left: NODES[1].x + 50, top: NODES[1].y + 120, fontFamily: FONT, fontSize: 16, fontWeight: 700, color: C.amber, letterSpacing: "0.14em", opacity: ip(f, 100, 115) }}>
          OUT OF SCOPE
        </div>
        <div style={{ position: "absolute", left: 1610, top: 720, opacity: ip(f, 345, 362), transform: `translateY(${ip(f, 345, 362, 12, 0)}px)` }}>
          <Chip start={345} dot={C.lime} size={20}>
            Human review
          </Chip>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ================= S4 · analyze (real UI) ================= */
const STEPS_X = [307, 511, 714, 918];
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const W = 1300;
  const k = W / 1600;
  const enter = sp(f, 2, 20, 1, 90);
  let src = "an_empty";
  if (f >= 50) src = "an_filled";
  if (f >= 104) src = "an_p_01";
  if (f >= 250) src = "case";
  // camera
  let zoom = 1 + 0.22 * ip(f, 20, 46) - 0.22 * ip(f, 56, 80);
  let focus: [number, number] = [800 - 260 * (ip(f, 20, 46) - ip(f, 56, 80)), 450 - 40 * (ip(f, 20, 46) - ip(f, 56, 80))];
  if (f >= 104 && f < 250) {
    const z = ip(f, 104, 130);
    zoom = 1 + 0.32 * z;
    focus = [800 - 90 * z, 450 + 80 * z];
  }
  if (f >= 250) {
    const z = ip(f, 262, 300);
    zoom = 1 + 0.55 * z;
    focus = [800 - 210 * z, 450 + 250 * z];
  }
  // cursor (CSS px of the 1600-wide page)
  const c1 = ip(f, 18, 44);
  const c2 = ip(f, 64, 94);
  let cx = interpolate(c1, [0, 1], [1150, 414]);
  let cy = interpolate(c1, [0, 1], [720, 386]);
  if (f >= 64) {
    cx = interpolate(c2, [0, 1], [414, 386]);
    cy = interpolate(c2, [0, 1], [386, 818]);
  }
  const press = f >= 46 && f < 64 ? ip(f, 46, 60) : f >= 96 && f < 112 ? ip(f, 96, 110) : 0;
  const curO = ip(f, 14, 20) * (1 - ip(f, 104, 110));
  const stepAt = [104, 140, 195, 225, 250];
  return (
    <AbsoluteFill>
      <Background glow={[65, 30]} />
      <div style={{ position: "absolute", left: 110, top: 70, width: 1700, height: 130 }}>
        <Eyebrow text="01 — ANALYZE" start={6} />
        <Words text="Pick an example. Or paste your own." start={10} size={56} exitAt={150} style={{ position: "absolute", top: 44 }} />
        <Words text="Classified in about a third of a second." start={168} size={56} highlight={["third", "second"]} style={{ position: "absolute", top: 44 }} />
      </div>
      <div style={{ position: "absolute", left: 540, top: 205, perspective: 2200 }}>
        <div style={{ transform: `translateY(${(1 - enter) * 160}px) rotateX(${(1 - enter) * 14}deg)`, opacity: Math.min(1, enter * 1.6), transformOrigin: "50% 100%" }}>
          <Window src={shot(src)} w={W} zoom={zoom} focus={focus}>
            {f >= 104 && f < 250 &&
              STEPS_X.map((x, i) => {
                const active = f >= stepAt[i] && f < stepAt[i + 1];
                const done = f >= stepAt[i + 1];
                const p = ip(f, stepAt[i], stepAt[i] + 8);
                return (
                  <div
                    key={i}
                    style={{
                      position: "absolute", left: x * k, top: 514 * k, width: 191 * k, height: 94 * k, borderRadius: 10 * k,
                      border: `${2.5 * k}px solid ${done ? C.leaf : C.green}`, background: done ? "#e9f3e6cc" : "#22705a10",
                      opacity: active || done ? p : 0, boxShadow: active ? `0 0 ${30 * k}px #22705a55` : "none",
                    }}
                  >
                    {done && (
                      <div style={{ position: "absolute", right: 8 * k, top: 8 * k, width: 22 * k, height: 22 * k, borderRadius: 99, background: C.green, color: "#fff", fontSize: 14 * k, fontWeight: 800, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: FONT }}>
                        ✓
                      </div>
                    )}
                  </div>
                );
              })}
            {f >= 250 && (
              <div
                style={{
                  position: "absolute", left: 722 * k, top: 595 * k, width: 162 * k, height: 38 * k, borderRadius: 99,
                  border: `${2.5 * k}px solid ${C.green}`, opacity: ip(f, 300, 312), transform: `scale(${1.3 - 0.3 * ip(f, 300, 312)})`,
                }}
              />
            )}
            <div style={{ position: "absolute", left: cx * k, top: cy * k }}>
              <Cursor x={0} y={0} press={press} opacity={curO} />
            </div>
          </Window>
        </div>
      </div>
      <div style={{ position: "absolute", left: 70, top: 300, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start", opacity: 1 - ip(f, 98, 106) }}>
        <Chip start={30} size={20} dot={C.lime}>One-click examples</Chip>
        <Chip start={38} size={20}>Or paste a narrative</Chip>
      </div>
      <div style={{ position: "absolute", left: 70, top: 300, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
        <Chip start={112} size={20} dot="#7aa58c">Saved to a durable queue</Chip>
        <Chip start={146} size={20} dot={C.leaf}>Fine-tuned Qwen3-4B</Chip>
        <Chip start={198} size={20} dot={C.amber}>Policy rules applied</Chip>
        <Chip start={290} size={20} dot={C.lime}>
          <span>Credit card <span style={{ color: C.muted }}>·</span> Fees or interest</span>
        </Chip>
        <Chip start={304} size={20} dot={C.green}>0.36 s · on this computer</Chip>
      </div>
    </AbsoluteFill>
  );
};

/* ================= S5 · policy + scope gate ================= */
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const a = sp(f, 6, 18, 1, 90);
  const b = sp(f, 138, 16, 1, 100);
  const dimA = ip(f, 140, 160);
  return (
    <AbsoluteFill>
      <Background glow={[40, 60]} />
      <div style={{ position: "absolute", left: 110, top: 70, height: 140, width: 1700 }}>
        <Eyebrow text="02 — TRANSPARENT BY DESIGN" start={4} />
        <Words text="The model predicts. Rules explain the rest." start={8} size={56} exitAt={136} highlight={["explain"]} style={{ position: "absolute", top: 44 }} />
        <Words text="Off-topic? It goes straight to a person." start={146} size={56} highlight={["person"]} style={{ position: "absolute", top: 44 }} />
      </div>
      <Card
        src={shot("el_analysis")}
        iw={1270}
        ih={864}
        scale={0.66}
        style={{
          left: 150, top: 250, opacity: Math.min(1, a * 1.5) * (1 - 0.35 * dimA),
          transform: `translateY(${(1 - a) * 120}px) scale(${1 - 0.06 * dimA}) rotate(${-1.2 * dimA}deg)`,
        }}
        rings={[
          { x: 30, y: 232, w: 1210, h: 262, p: ip(f, 22, 38), label: "AI · fine-tuned model" },
          { x: 30, y: 560, w: 1210, h: 250, p: ip(f, 62, 78), color: C.amber, label: "Policy · explicit rules" },
        ]}
      />
      <Card
        src={shot("el_oos_analysis")}
        iw={1270}
        ih={1042}
        scale={0.62}
        style={{ left: 1000, top: 230, opacity: Math.min(1, b * 1.5), transform: `translateX(${(1 - b) * 300}px) rotate(${(1 - b) * 4}deg)` }}
        rings={[{ x: 52, y: 826, w: 1166, h: 130, p: ip(f, 176, 192), color: C.amber, label: "Model not run · scope gate" }]}
      />
      <div style={{ position: "absolute", left: 150, top: 880, display: "flex", gap: 14 }}>
        <Chip start={84} size={19} dot={C.amber}>Rule matched “refund”</Chip>
        <Chip start={92} size={19}>Card Services Team</Chip>
      </div>
    </AbsoluteFill>
  );
};

/* ================= S6 · human in the loop ================= */
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const cards = [
    { src: "el_review_done", w: 1270, h: 1286, x: 110, y: 270, s: 0.43, at: 20, label: "Confirm or correct" },
    { src: "el_forward", w: 1270, h: 684, x: 694, y: 330, s: 0.43, at: 112, label: "Move it forward" },
    { src: "el_history", w: 1270, h: 778, x: 1278, y: 300, s: 0.43, at: 168, label: "Every change kept" },
  ];
  const active = f < 112 ? 0 : f < 168 ? 1 : 2;
  const steps = ["Queued", "In review", "Resolved"];
  const stepP = [ip(f, 30, 40), ip(f, 132, 142), ip(f, 196, 208)];
  return (
    <AbsoluteFill>
      <Background glow={[50, 15]} />
      <div style={{ position: "absolute", left: 110, top: 70 }}>
        <Eyebrow text="03 — HUMAN IN THE LOOP" start={6} />
        <Words text="People make the final call." start={10} size={60} style={{ marginTop: 22 }} highlight={["final", "call"]} />
      </div>
      {cards.map((c, i) => {
        const p = sp(f, c.at, 17, 1, 100);
        const isA = i === active;
        const dim = ip(f, c.at + 30, c.at + 50) * (isA ? 0 : 1);
        return (
          <div
            key={c.src}
            style={{
              position: "absolute", left: c.x, top: c.y, opacity: Math.min(1, p * 1.4),
              transform: `translateY(${(1 - p) * 120 + (isA ? -10 : 0)}px) scale(${(0.94 + 0.06 * p) * (isA ? 1.02 : 0.97)})`, transformOrigin: "50% 0",
            }}
          >
            <div style={{ fontFamily: FONT, fontSize: 19, fontWeight: 700, color: isA ? C.green : C.muted, letterSpacing: "0.12em", marginBottom: 14 }}>
              {String(i + 1).padStart(2, "0")} · {c.label.toUpperCase()}
            </div>
            <div
              style={{
                width: c.w * c.s, height: c.h * c.s, borderRadius: 16, overflow: "hidden", background: "#fff", opacity: 1 - dim * 0.35,
                boxShadow: isA ? "0 50px 120px #1430272e, 0 0 0 2px #22705a55" : "0 24px 60px #1430271a, 0 0 0 1px #14302712",
              }}
            >
              <Img src={shot(c.src)} style={{ width: c.w * c.s, display: "block" }} />
            </div>
          </div>
        );
      })}
      <Toast text="Review saved · decision recorded" at={66} out={124} style={{ right: 70, bottom: 60 }} />
      <Toast text="Moved to in review" at={136} out={186} style={{ right: 70, bottom: 60 }} />
      <Toast text="Case resolved" at={200} style={{ right: 70, bottom: 60 }} />
      <div style={{ position: "absolute", left: 110, top: 965, display: "flex", alignItems: "center", gap: 18, fontFamily: FONT }}>
        {steps.map((s, i) => (
          <React.Fragment key={s}>
            <div
              style={{
                padding: "10px 22px", borderRadius: 999, fontSize: 21, fontWeight: 700, border: `1px solid ${C.line}`,
                color: stepP[i] > 0.5 ? "#fff" : C.muted, background: stepP[i] > 0.5 ? (i === 2 ? C.deep : C.green) : "#fff",
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
        <span style={{ marginLeft: 26, fontSize: 20, color: C.muted, fontWeight: 500, opacity: ip(f, 226, 242) }}>Append-only history · original prediction never overwritten</span>
      </div>
    </AbsoluteFill>
  );
};

/* ================= S7 · batches + overview ================= */
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const W = 1240;
  const fly = ip(f, 8, 40, 0, 1, Easing.bezier(0.5, 0, 0.2, 1));
  const win = sp(f, 4, 20, 1, 90);
  const swap = ip(f, 118, 136);
  const src = f < 52 ? "im_preview" : "im_done";
  const zIm = ip(f, 56, 84) * (1 - swap);
  const zOv = ip(f, 140, 230, 0, 1, Easing.inOut(Easing.cubic));
  const zoom = 1 + 0.2 * zIm + 0.1 * zOv;
  const focus: [number, number] = swap < 1 ? [800 - 140 * zIm, 450 + 30 * zIm] : [800 - 40 * zOv, 450 - 40 * zOv];
  return (
    <AbsoluteFill>
      <Background glow={[30, 40]} />
      <div style={{ position: "absolute", left: 110, top: 230, width: 520, height: 300 }}>
        <Eyebrow text={swap < 0.5 ? "04 — DURABLE BATCHES" : "05 — OVERVIEW"} start={4} />
        <Words text={"Drop in a CSV.\nEvery row saved."} start={8} size={60} exitAt={116} highlight={["saved"]} style={{ position: "absolute", top: 46 }} />
        <Words text={"See what needs\nyou, at a glance."} start={126} size={60} highlight={["glance"]} style={{ position: "absolute", top: 46 }} />
      </div>
      <div style={{ position: "absolute", left: 110, top: 560, display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start", opacity: 1 - swap }}>
        <Chip start={50} size={19} dot={C.lime}>Survives restarts</Chip>
        <Chip start={58} size={19}>Retry failed rows</Chip>
        <Chip start={66} size={19} dot="#7aa58c">Up to 100 complaints</Chip>
      </div>
      <div style={{ position: "absolute", left: 110, top: 560, display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start", opacity: swap }}>
        <Chip start={140} size={19} dot={C.lime}>Lifecycle at a glance</Chip>
        <Chip start={148} size={19}>Includes reviewer corrections</Chip>
      </div>
      <div style={{ position: "absolute", left: 620, top: 210, perspective: 2000 }}>
        <div style={{ transform: `translateX(${(1 - win) * 300}px) rotateY(${-10 * (1 - win) - 3}deg)`, transformOrigin: "0 50%", opacity: Math.min(1, win * 1.5) }}>
          <Window src={shot(src)} w={W} zoom={zoom} focus={focus} layers={[{ src: shot("ov"), opacity: swap }]} />
        </div>
      </div>
      {/* CSV file dropping into the window */}
      <div
        style={{
          position: "absolute", left: interpolate(fly, [0, 1], [1500, 1000]), top: interpolate(fly, [0, 1], [-200, 520]),
          transform: `rotate(${(1 - fly) * 16}deg) scale(${1 - 0.35 * fly})`, opacity: f < 6 ? 0 : 1 - ip(f, 38, 46),
          width: 120, height: 144, borderRadius: 14, background: "#fff", border: `1px solid ${C.line}`, boxShadow: "0 30px 60px #14302733",
          display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, fontFamily: FONT,
        }}
      >
        <div style={{ width: 54, height: 64, borderRadius: 8, background: C.green, color: "#fff", fontWeight: 800, fontSize: 17, display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: 8 }}>CSV</div>
        <span style={{ fontSize: 15, color: C.muted, fontWeight: 600 }}>batch.csv</span>
      </div>
    </AbsoluteFill>
  );
};

/* ================= S8 · training (dark) ================= */
const LOSS: [number, number][] = [
  [10, 0.4728], [20, 0.1945], [30, 0.0846], [40, 0.0701], [50, 0.0657], [60, 0.0598], [70, 0.0664], [80, 0.0609], [90, 0.0695], [100, 0.0655],
  [120, 0.0644], [140, 0.054], [160, 0.0467], [180, 0.0573], [200, 0.0461], [220, 0.0478], [240, 0.0537], [260, 0.0588], [280, 0.0545], [300, 0.0496],
  [320, 0.0427], [340, 0.0532], [360, 0.0541], [380, 0.0548], [400, 0.0517], [420, 0.0579], [440, 0.0472], [460, 0.0536], [480, 0.0442], [500, 0.0463],
  [520, 0.0427], [540, 0.0457], [560, 0.0576], [580, 0.0512], [600, 0.0481], [620, 0.044], [640, 0.0379], [660, 0.043], [680, 0.0509], [700, 0.045],
  [720, 0.0451], [740, 0.0439], [760, 0.0411], [780, 0.0456], [800, 0.0423], [820, 0.0475], [840, 0.0409], [860, 0.0438], [880, 0.0473], [900, 0.0453],
  [920, 0.0511], [940, 0.0529], [950, 0.0377],
];
const TRAIN = [
  { x: 240, icon: "archive", title: "CFPB complaints", sub: "70,162 prepared", at: 22 },
  { x: 600, icon: "chip", title: "Qwen3-4B", sub: "4-bit QLoRA · r 16", at: 62 },
  { x: 960, icon: "bolt", title: "RTX 4070", sub: "950 steps · 1 h 58 m", at: 102 },
  { x: 1320, icon: "package", title: "GGUF Q4_K_M", sub: "merged · 2.5 GB", at: 142 },
  { x: 1680, icon: "server", title: "llama.cpp", sub: "CUDA · serves the app", at: 182 },
];
const S8: React.FC = () => {
  const f = useCurrentFrame();
  const Y = 380;
  const edges = TRAIN.slice(0, -1).map((n, i) => `M ${n.x + 125} ${Y} L ${TRAIN[i + 1].x - 125} ${Y}`);
  // loss chart
  const X0 = 240, X1 = 1680, Y0 = 640, Y1 = 930;
  const px = (s: number) => X0 + (s / 950) * (X1 - X0);
  const py = (l: number) => Y1 - (l / 0.5) * (Y1 - Y0);
  const d = LOSS.map(([s, l], i) => `${i ? "L" : "M"} ${px(s).toFixed(1)} ${py(l).toFixed(1)}`).join(" ");
  const dp = ip(f, 60, 250, 0, 1, Easing.inOut(Easing.cubic));
  const idx = Math.min(LOSS.length - 1, Math.floor(dp * (LOSS.length - 1)));
  const area = `${d} L ${X1} ${Y1} L ${X0} ${Y1} Z`;
  const chartO = ip(f, 40, 60);
  return (
    <AbsoluteFill>
      <Background dark glow={[50, 30]} />
      <div style={{ position: "absolute", left: 110, top: 70 }}>
        <Eyebrow text="06 — UNDER THE HOOD" start={4} dark />
        <Words text="Trained here. Runs here." start={8} size={60} color="#fff" style={{ marginTop: 22 }} highlight={["here"]} hlColor={C.lime} />
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        {edges.map((e, i) => (
          <Flow key={i} d={e} draw={[10 + i * 8, 40 + i * 8]} run={[TRAIN[i].at + 4, TRAIN[i + 1].at]} color={C.lime} base="#ffffff22" />
        ))}
        <g opacity={chartO}>
          {[0.1, 0.2, 0.3, 0.4].map((v) => (
            <g key={v}>
              <line x1={X0} x2={X1} y1={py(v)} y2={py(v)} stroke="#ffffff12" />
              <text x={X0 - 14} y={py(v) + 5} fill="#ffffff55" fontFamily={FONT} fontSize={14} textAnchor="end">{v.toFixed(1)}</text>
            </g>
          ))}
          <line x1={X0} x2={X1} y1={Y1} y2={Y1} stroke="#ffffff30" />
          <clipPath id="reveal">
            <rect x={X0} y={Y0 - 20} width={(X1 - X0) * dp} height={Y1 - Y0 + 40} />
          </clipPath>
          <path d={area} fill="url(#lossfill)" clipPath="url(#reveal)" />
          <defs>
            <linearGradient id="lossfill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor={C.lime} stopOpacity={0.28} />
              <stop offset="1" stopColor={C.lime} stopOpacity={0} />
            </linearGradient>
          </defs>
          <path d={d} fill="none" stroke={C.lime} strokeWidth={3} strokeLinejoin="round" clipPath="url(#reveal)" />
          {dp > 0 && (
            <g transform={`translate(${px(LOSS[idx][0])} ${py(LOSS[idx][1])})`}>
              <circle r={16} fill={C.lime} opacity={0.2} />
              <circle r={7} fill={C.lime} />
            </g>
          )}
        </g>
      </svg>
      {TRAIN.map((n, i) => (
        <FlowNode key={i} x={n.x} y={Y} w={250} h={124} icon={n.icon} title={n.title} sub={n.sub} appear={6 + i * 6} at={n.at} dark accent={C.lime} />
      ))}
      <div style={{ position: "absolute", left: X0, top: Y0 - 70, fontFamily: FONT, opacity: chartO, display: "flex", alignItems: "baseline", gap: 22 }}>
        <span style={{ fontSize: 17, letterSpacing: "0.22em", color: C.sage, fontWeight: 700 }}>TRAINING LOSS</span>
        <span style={{ fontFamily: MONO, fontSize: 22, color: "#fff" }}>
          step {String(LOSS[idx][0]).padStart(3, " ")} · loss {LOSS[idx][1].toFixed(3)}
        </span>
      </div>
      <div style={{ position: "absolute", left: X0, top: Y1 + 22, fontFamily: FONT, fontSize: 17, color: "#9fb3a8", opacity: ip(f, 220, 240) }}>
        Effective batch 16 · about 15,200 of 70,162 training complaints seen (≈ 1/5 epoch) · LoRA adapter merged, then quantized
      </div>
    </AbsoluteFill>
  );
};

/* ================= S9 · architecture ================= */
const S9: React.FC = () => {
  const f = useCurrentFrame();
  const box = sp(f, 4, 20, 1, 90);
  const P = { ui: [380, 620], api: [800, 620], llm: [1230, 450], db: [1230, 800] } as const;
  const e1 = `M ${P.ui[0] + 125} ${P.ui[1]} L ${P.api[0] - 125} ${P.api[1]}`;
  const e1b = `M ${P.api[0] - 125} ${P.api[1] + 20} L ${P.ui[0] + 125} ${P.ui[1] + 20}`;
  const e2 = curve(P.api[0] + 125, P.api[1] - 20, P.llm[0] - 125, P.llm[1]);
  const e3 = curve(P.api[0] + 125, P.api[1] + 20, P.db[0] - 125, P.db[1]);
  const block = ip(f, 96, 112);
  const cross = ip(f, 110, 124);
  return (
    <AbsoluteFill>
      <Background glow={[40, 55]} />
      <div style={{ position: "absolute", left: 110, top: 70 }}>
        <Eyebrow text="07 — PRIVATE BY ARCHITECTURE" start={4} />
        <Words text="Everything stays on this computer." start={8} size={60} style={{ marginTop: 22 }} highlight={["this", "computer"]} />
      </div>
      <div
        style={{
          position: "absolute", left: 150, top: 290, width: 1330, height: 680, borderRadius: 36, border: `2px dashed ${C.green}88`,
          background: "#ffffff55", opacity: box, transform: `scale(${0.96 + 0.04 * box})`,
        }}
      >
        <div style={{ position: "absolute", left: 30, top: -16, background: C.ivory, padding: "0 14px", fontFamily: FONT, fontSize: 16, fontWeight: 700, letterSpacing: "0.24em", color: C.green }}>
          THIS COMPUTER · 127.0.0.1
        </div>
      </div>
      <svg width={1920} height={1080} style={{ position: "absolute" }}>
        <Flow d={e1} draw={[20, 40]} packet={false} />
        <Flow d={e2} draw={[30, 52]} packet={false} />
        <Flow d={e3} draw={[36, 58]} packet={false} />
        <Stream d={e1} from={40} every={22} travel={40} color={C.leaf} />
        <Stream d={e1b} from={70} every={22} travel={40} color={C.lime} />
        <Stream d={e2} from={52} every={18} travel={44} color={C.leaf} />
        <Stream d={e3} from={58} every={26} travel={44} color={C.leaf} />
        {/* blocked route to the cloud */}
        <path d="M 1480 560 L 1650 560" stroke={C.amber} strokeWidth={3} strokeDasharray="4 10" opacity={block} />
        <g transform="translate(1565 560)" opacity={cross}>
          <circle r={26} fill={C.amberBg} stroke={C.amber} strokeWidth={2.5} />
          <path d="M -9 -9 L 9 9 M 9 -9 L -9 9" stroke={C.amber} strokeWidth={4} strokeLinecap="round" />
        </g>
      </svg>
      <FlowNode x={P.ui[0]} y={P.ui[1]} w={250} icon="browser" title="React UI" sub="Your browser" appear={10} at={20} />
      <FlowNode x={P.api[0]} y={P.api[1]} w={250} icon="server" title="FastAPI" sub="Durable job queue" appear={16} at={36} />
      <FlowNode x={P.llm[0]} y={P.llm[1]} w={250} icon="chip" title="llama-server" sub="Qwen3-4B · CUDA" appear={22} at={52} />
      <FlowNode x={P.db[0]} y={P.db[1]} w={250} icon="db" title="SQLite" sub="Cases · history · backups" appear={28} at={58} />
      <div style={{ position: "absolute", left: 1660, top: 480, display: "flex", flexDirection: "column", alignItems: "center", gap: 12, opacity: block, fontFamily: FONT }}>
        <div style={{ opacity: 0.55 }}>
          <Icon name="cloud" size={110} color={C.muted} />
        </div>
      </div>
      <div style={{ position: "absolute", left: 1580, top: 640, display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-start" }}>
        <Chip start={98} size={20} dot={C.amber}>No cloud</Chip>
        <Chip start={120} size={20} dot={C.amber}>No external API</Chip>
      </div>
    </AbsoluteFill>
  );
};

/* ================= S10 · evidence (dark) ================= */
const S10: React.FC = () => {
  const f = useCurrentFrame();
  const stats = [
    { v: (p: number) => (90.8 * p).toFixed(1) + "%", l: "product accuracy\n153 held-out complaints", at: 14, hl: true },
    { v: (p: number) => Math.round(204 * p) + " ms", l: "mean inference\non an RTX 4070", at: 40 },
    { v: (p: number) => (58.8 * p).toFixed(1) + "%", l: "product + issue\nboth correct", at: 66 },
    { v: (p: number) => String(Math.round(0 * p)), l: "invalid replies\n3,000 newest complaints", at: 92 },
  ];
  const bars = [
    { name: "Baseline · TF-IDF", v: 88.2 },
    { name: "Qwen2.5-1.5B · fine-tuned", v: 88.9 },
    { name: "Qwen3-4B · fine-tuned", v: 90.8, hl: true },
  ];
  return (
    <AbsoluteFill>
      <Background dark glow={[60, 20]} />
      <div style={{ position: "absolute", left: 130, top: 80 }}>
        <Eyebrow text="08 — MEASURED, NOT PROMISED" start={2} dark />
        <Words text="Evidence you can audit." start={6} size={64} color="#fff" style={{ marginTop: 22 }} highlight={["audit"]} hlColor={C.lime} />
      </div>
      <div style={{ position: "absolute", left: 130, right: 130, top: 300, display: "flex" }}>
        {stats.map((s, i) => {
          const p = ip(f, s.at, s.at + 45, 0, 1, Easing.out(Easing.cubic));
          const o = ip(f, s.at, s.at + 12);
          return (
            <div key={i} style={{ flex: 1, paddingLeft: i ? 40 : 0, borderLeft: i ? "1px solid #ffffff22" : "none", opacity: o, transform: `translateY(${(1 - o) * 30}px)`, fontFamily: FONT }}>
              <div style={{ fontSize: 92, fontWeight: 800, color: s.hl ? C.lime : "#fff", letterSpacing: "-0.05em", fontVariantNumeric: "tabular-nums" }}>{s.v(p)}</div>
              <div style={{ fontSize: 22, color: C.sage, marginTop: 10, lineHeight: 1.4, whiteSpace: "pre-line", fontWeight: 500 }}>{s.l}</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 130, top: 620, width: 1660, fontFamily: FONT }}>
        <div style={{ fontSize: 17, letterSpacing: "0.22em", color: C.sage, fontWeight: 700, marginBottom: 22, opacity: ip(f, 110, 124) }}>
          PRODUCT ACCURACY · SAME 153 RESERVED COMPLAINTS
        </div>
        {bars.map((b, i) => {
          const p = ip(f, 116 + i * 12, 170 + i * 12, 0, 1, Easing.out(Easing.cubic));
          return (
            <div key={b.name} style={{ display: "flex", alignItems: "center", gap: 24, marginBottom: 16, opacity: ip(f, 112 + i * 12, 124 + i * 12) }}>
              <div style={{ width: 330, fontSize: 21, color: b.hl ? "#fff" : C.sage, fontWeight: b.hl ? 700 : 500 }}>{b.name}</div>
              <div style={{ flex: 1, height: 30, background: "#ffffff0d", borderRadius: 8, position: "relative" }}>
                <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: `${b.v * p}%`, background: b.hl ? C.lime : "#ffffff40", borderRadius: 8 }} />
              </div>
              <div style={{ width: 110, fontSize: 24, fontWeight: 800, color: b.hl ? C.lime : "#fff", fontVariantNumeric: "tabular-nums" }}>{(b.v * p).toFixed(1)}%</div>
            </div>
          );
        })}
      </div>
      <div style={{ position: "absolute", left: 130, right: 130, top: 925, paddingTop: 22, borderTop: "1px solid #ffffff1c", fontFamily: FONT, fontSize: 17, lineHeight: 1.6, color: "#8fa79a", opacity: ip(f, 170, 190) }}>
        Q4_K_M GGUF in the app. 10-class accuracy on the 3,000-row 2026 test set: 64.5% for the unquantized adapter (59.7% vs 64.7% for GGUF vs adapter on 300 rows).
        <br />
        Priority and routing are explicit rules · summaries are extractive · people confirm every case.
      </div>
    </AbsoluteFill>
  );
};

/* ================= S11 · outro ================= */
const S11: React.FC = () => {
  const f = useCurrentFrame();
  const m = sp(f, 4, 14, 1, 110);
  const v = sp(f, 50, 16, 1, 100);
  const end = ip(f, 128, 150, 0, 1, Easing.linear);
  return (
    <AbsoluteFill>
      <Background glow={[50, 40]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 34, transform: `scale(${0.9 + 0.1 * m}) translateY(${-30 * v}px)`, opacity: Math.min(1, m * 1.6) }}>
          <BrandMark size={124} glow={false} />
          <div style={{ fontFamily: FONT, fontSize: 112, fontWeight: 800, color: C.deep, letterSpacing: "-0.05em" }}>ComplaintIQ</div>
        </div>
        <div style={{ transform: `translateY(${-30 * v}px)` }}>
          <Words text="Private, accountable complaint triage." start={16} size={44} weight={600} color={C.green} tracking={-0.02} style={{ marginTop: 34 }} />
        </div>
        <div style={{ marginTop: 34, display: "flex", alignItems: "center", gap: 30, opacity: Math.min(1, v * 1.5), transform: `translateY(${(1 - v) * 30}px)` }}>
          <span style={{ width: 120, height: 1, background: "#14302733" }} />
          <span style={{ fontFamily: FONT, fontSize: 17, letterSpacing: "0.4em", color: C.muted, fontWeight: 600 }}>PREPARED FOR</span>
          <Img src={staticFile("veltris-logo.png")} style={{ height: 62 }} />
          <span style={{ width: 120, height: 1, background: "#14302733" }} />
        </div>
        <div style={{ position: "absolute", bottom: 80, fontFamily: FONT, fontSize: 18, color: C.muted, letterSpacing: "0.22em", fontWeight: 600, opacity: ip(f, 70, 90) }}>
          QWEN3-4B · QLORA · LLAMA.CPP CUDA · FASTAPI · REACT · SQLITE
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: C.ivory, opacity: end }} />
    </AbsoluteFill>
  );
};

export const Reel: React.FC = () => (
  <AbsoluteFill style={{ background: C.deeper }}>
    <Scene {...seg(0)} enter="fade"><S1 /></Scene>
    <Scene {...seg(1)} enter="circle"><S2 /></Scene>
    <Scene {...seg(2)} enter="up"><S3 /></Scene>
    <Scene {...seg(3)} enter="left"><S4 /></Scene>
    <Scene {...seg(4)} enter="up"><S5 /></Scene>
    <Scene {...seg(5)} enter="left"><S6 /></Scene>
    <Scene {...seg(6)} enter="up"><S7 /></Scene>
    <Scene {...seg(7)} enter="circle"><S8 /></Scene>
    <Scene {...seg(8)} enter="zoom"><S9 /></Scene>
    <Scene {...seg(9)} enter="circle"><S10 /></Scene>
    <Scene {...seg(10)} enter="fade"><S11 /></Scene>
    <Audio src={staticFile("mix.wav")} />
  </AbsoluteFill>
);
