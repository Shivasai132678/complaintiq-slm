import React from "react";
import { AbsoluteFill, Audio, Easing, Img, interpolate, staticFile, useCurrentFrame } from "remotion";
import { Background, BrandMark, C, Chip, Cursor, Eyebrow, FONT, Fonts, Scene, Window, Words, ip, shot, sp } from "./prims";

export const TOTAL = 2640; // 88 s
/* ---------- S0 · prepared for Veltris ---------- */
const S0: React.FC = () => {
  const f = useCurrentFrame();
  const a = sp(f, 4, 16, 1, 90);
  const move = ip(f, 46, 76);
  const x = ip(f, 52, 72);
  const cq = sp(f, 58, 15, 0.9, 120);
  return (
    <AbsoluteFill>
      <Background glow={[50, 50]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center" }}>
        <div
          style={{
            position: "absolute",
            top: 330,
            fontFamily: FONT,
            fontSize: 20,
            letterSpacing: "0.5em",
            fontWeight: 600,
            color: C.muted,
            opacity: ip(f, 10, 26) * (1 - move),
          }}
        >
          PREPARED FOR
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 60 * move,
            transform: `translateX(${-move * 0}px)`,
          }}
        >
          <Img
            src={staticFile("veltris-logo.png")}
            style={{
              width: interpolate(move, [0, 1], [820, 520]),
              opacity: Math.min(1, a * 1.4),
              filter: `blur(${(1 - a) * 12}px)`,
              transform: `scale(${0.92 + 0.08 * a})`,
            }}
          />
          <div
            style={{
              width: 140 * move,
              overflow: "hidden",
              display: "flex",
              justifyContent: "center",
              fontFamily: FONT,
              fontSize: 64,
              fontWeight: 300,
              color: C.sage,
              opacity: x,
            }}
          >
            ×
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 22,
              width: 520 * move,
              overflow: "hidden",
              opacity: Math.min(1, cq * 1.5),
              transform: `translateX(${(1 - cq) * 60}px)`,
            }}
          >
            <BrandMark size={96} />
            <div style={{ fontFamily: FONT, fontSize: 76, fontWeight: 800, color: C.deep, letterSpacing: "-0.05em" }}>
              ComplaintIQ
            </div>
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/* ---------- S3 · analyze ---------- */
const PR = ["pr_01", "pr_02", "pr_03", "pr_04", "pr_05", "pr_06", "pr_07"];
const RV = ["rv_00", "rv_02", "rv_04", "rv_06", "rv_08", "rv_10", "rv_13"];
const S3: React.FC = () => {
  const f = useCurrentFrame();
  const W = 1360;
  const k = W / 1600;
  const enter = sp(f, 4, 20, 1, 90);
  let src = "an_00";
  if (f >= 45) src = "an_01_hover";
  if (f >= 58) src = "an_02_filled";
  if (f >= 156) src = PR[Math.min(PR.length - 1, Math.floor((f - 156) / 7))];
  if (f >= 205) src = RV[Math.min(RV.length - 1, Math.floor((f - 205) / 6))];
  if (f >= 250) src = "case_new";
  // camera
  const zIn = ip(f, 62, 92);
  const zOut = ip(f, 118, 140);
  let zoom = 1 + 0.32 * zIn - 0.32 * zOut;
  let focus: [number, number] = [
    800 + (620 - 800) * (zIn - zOut),
    450 + (520 - 450) * (zIn - zOut),
  ];
  if (f >= 156 && f < 205) {
    const z = ip(f, 156, 180);
    zoom = 1 + 0.18 * z;
    focus = [800 - 60 * z, 450 + 60 * z];
  }
  if (f >= 205) {
    const z = ip(f, 212, 262);
    zoom = interpolate(z, [0, 1], [1.05, 1.42]);
    focus = [interpolate(z, [0, 1], [800, 720]), interpolate(z, [0, 1], [460, 600])];
  }
  // cursor path in CSS px
  const c1 = ip(f, 16, 44);
  const c2 = ip(f, 124, 150);
  let cx = interpolate(c1, [0, 1], [1050, 422]);
  let cy = interpolate(c1, [0, 1], [760, 380]);
  if (f >= 124) {
    cx = interpolate(c2, [0, 1], [422, 392]);
    cy = interpolate(c2, [0, 1], [380, 808]);
  }
  const press = f >= 152 ? ip(f, 152, 166, 0, 1, Easing.out(Easing.quad)) : f >= 54 && f < 70 ? ip(f, 54, 68, 0, 1, Easing.out(Easing.quad)) : 0;
  const curO = ip(f, 14, 22) * (1 - ip(f, 160, 168));
  return (
    <AbsoluteFill>
      <Background glow={[60, 25]} />
      <div style={{ position: "absolute", left: 120, top: 70, width: 1700, height: 120 }}>
        <Eyebrow text="01 — ANALYZE" start={6} />
        <Words text="Pick a complaint. Or paste your own." start={10} size={56} exitAt={150} style={{ position: "absolute", top: 44 }} />
        <Words text="Classified in about a second." start={166} size={56} highlight={["second"]} style={{ position: "absolute", top: 44 }} />
      </div>
      <div style={{ position: "absolute", left: 400, top: 230, perspective: 2200 }}>
        <div
          style={{
            transform: `translateY(${(1 - enter) * 160}px) rotateX(${(1 - enter) * 14}deg)`,
            opacity: Math.min(1, enter * 1.6),
            transformOrigin: "50% 100%",
          }}
        >
          <Window src={shot(src)} w={W} zoom={zoom} focus={focus}>
            <div style={{ position: "absolute", left: cx * k, top: cy * k }}>
              <Cursor x={0} y={0} press={press} opacity={curO} />
            </div>
          </Window>
        </div>
      </div>
      {/* callouts */}
      <div style={{ position: "absolute", left: 60, top: 300, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
        <Chip start={30} size={21} dot={C.lime} style={{ opacity: f > 150 ? 1 - ip(f, 150, 160) : undefined }}>
          One-click examples
        </Chip>
      </div>
      <div style={{ position: "absolute", left: 60, top: 300, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}>
        <Chip start={168} size={21} dot="#7aa58c">
          Queued durably
        </Chip>
        <Chip start={176} size={21} dot={C.leaf}>
          Fine-tuned Qwen2.5 on-device
        </Chip>
        <Chip start={232} size={21} dot={C.lime}>
          <span>
            Credit card <span style={{ color: C.muted, fontWeight: 500 }}>·</span> Fees or interest
          </span>
        </Chip>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S4 · policy ---------- */
const S4: React.FC = () => {
  const f = useCurrentFrame();
  const e = sp(f, 8, 18, 1, 80);
  const hl1 = ip(f, 46, 64);
  const hl2 = ip(f, 84, 102);
  const S = 0.7;
  const rows: [string, string, number][] = [
    ["Priority", "Medium", 64],
    ["Route to", "Card Services Team", 78],
    ["Reason", "Rule matched “refund”", 92],
  ];
  return (
    <AbsoluteFill>
      <Background glow={[75, 50]} />
      <div style={{ position: "absolute", left: 130, top: 220, width: 760 }}>
        <Eyebrow text="02 — TRANSPARENT POLICY" start={8} />
        <Words text={"Rules you can read.\nReasons you can see."} start={12} size={74} style={{ marginTop: 28 }} highlight={["see"]} />
        <div style={{ marginTop: 60, display: "flex", flexDirection: "column", gap: 18 }}>
          {rows.map(([k, v, s]) => {
            const p = sp(f, s, 16, 0.8, 140);
            return (
              <div key={k} style={{ display: "flex", alignItems: "center", gap: 26, fontFamily: FONT, opacity: p, transform: `translateX(${(1 - p) * -30}px)` }}>
                <span style={{ width: 150, fontSize: 20, letterSpacing: "0.2em", color: C.muted, fontWeight: 600 }}>{k.toUpperCase()}</span>
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
      <div style={{ position: "absolute", left: 980, top: 210, perspective: 1800 }}>
        <div
          style={{
            transform: `translateX(${(1 - e) * 200}px) rotateY(${-18 * (1 - e) - 6}deg) rotateX(3deg) translateY(${Math.sin(f / 30) * 6}px)`,
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
          {(
            [
              [30, 232, 1210, 238, hl1, "AI · fine-tuned model"],
              [30, 542, 1210, 238, hl2, "Policy · explicit rules"],
            ] as [number, number, number, number, number, string][]
          ).map(([x, y, w, h, p, label], i) => (
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

/* recreated app toast (same styling as the frontend) */
const Toast: React.FC<{ text: string; at: number; y: number }> = ({ text, at, y }) => {
  const f = useCurrentFrame();
  const p = sp(f, at, 15, 0.7, 150);
  if (f < at) return null;
  return (
    <div
      style={{
        position: "absolute",
        right: 70,
        bottom: y,
        display: "flex",
        alignItems: "center",
        gap: 14,
        background: C.deep,
        color: "#eef4ee",
        fontFamily: FONT,
        fontSize: 24,
        fontWeight: 600,
        padding: "16px 26px 16px 16px",
        borderRadius: 16,
        boxShadow: "0 24px 60px #14302744",
        opacity: Math.min(1, p * 1.5),
        transform: `translateY(${(1 - p) * 30}px) scale(${0.95 + 0.05 * p})`,
      }}
    >
      <span style={{ width: 34, height: 34, borderRadius: 99, background: C.lime, color: C.deep, display: "inline-flex", alignItems: "center", justifyContent: "center", fontSize: 20, fontWeight: 800 }}>✓</span>
      {text}
    </div>
  );
};


/* ---------- SX · knows its limits ---------- */
const OOS = ["oospr_03", "oospr_04", "oosrv_00", "oosrv_02", "oosrv_04", "oosrv_07"];
const SX: React.FC = () => {
  const f = useCurrentFrame();
  const W = 1140;
  const k = W / 1600;
  const enter = sp(f, 4, 20, 1, 90);
  let src = f < 26 ? "oos_01_hover" : "oos_02_filled";
  if (f >= 62) src = OOS[Math.min(OOS.length - 1, Math.floor((f - 62) / 6))];
  if (f >= 98) src = "oos_case";
  const c1 = ip(f, 14, 26);
  const c2 = ip(f, 34, 56);
  let cx = interpolate(c1, [0, 1], [700, 905]);
  let cy = interpolate(c1, [0, 1], [500, 380]);
  if (f >= 34) {
    cx = interpolate(c2, [0, 1], [905, 392]);
    cy = interpolate(c2, [0, 1], [380, 808]);
  }
  const press = f >= 24 && f < 34 ? ip(f, 24, 34) : f >= 58 ? ip(f, 58, 70, 0, 1, Easing.out(Easing.quad)) : 0;
  const curO = ip(f, 10, 16) * (1 - ip(f, 64, 70));
  const card = sp(f, 118, 16, 1, 100);
  const ring = ip(f, 140, 156);
  const S = 0.52;
  return (
    <AbsoluteFill>
      <Background glow={[70, 60]} />
      <div style={{ position: "absolute", left: 120, top: 250, width: 560 }}>
        <Eyebrow text="03 — KNOWS ITS LIMITS" start={8} />
        <Words text={"Off-topic?\nIt goes to a person."} start={12} size={64} style={{ marginTop: 24 }} highlight={["person"]} />
        <div style={{ marginTop: 44, display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start" }}>
          <Chip start={104} size={21} dot="#c79a2b">Model not run</Chip>
          <Chip start={114} size={21} dot={C.lime}>Reason recorded on the case</Chip>
          <Chip start={124} size={21} dot={C.leaf}>94% of unrelated test complaints caught</Chip>
        </div>
      </div>
      <div style={{ position: "absolute", left: 700, top: 150, perspective: 2000 }}>
        <div style={{ transform: `translateY(${(1 - enter) * 160}px) rotateX(${(1 - enter) * 12}deg)`, opacity: Math.min(1, enter * 1.6), transformOrigin: "50% 100%" }}>
          <Window src={shot(src)} w={W} zoom={1 + 0.12 * ip(f, 98, 130)} focus={[800 - 120 * ip(f, 98, 130), 450 + 120 * ip(f, 98, 130)]}>
            <div style={{ position: "absolute", left: cx * k, top: cy * k }}>
              <Cursor x={0} y={0} press={press} opacity={curO} />
            </div>
          </Window>
        </div>
      </div>
      {/* the original-analysis card lifts out of the page */}
      <div
        style={{
          position: "absolute",
          left: 1080,
          top: 380,
          width: 1270 * S,
          height: 1026 * S,
          opacity: Math.min(1, card * 1.5),
          transform: `translateY(${(1 - card) * 120}px) scale(${0.92 + 0.08 * card}) rotate(${(1 - card) * 3}deg)`,
          borderRadius: 18,
          boxShadow: "0 60px 140px #1430274a, 0 0 0 1px #14302714",
          background: "#fff",
        }}
      >
        <Img src={shot("el_oos_analysis")} style={{ width: 1270 * S, height: 1026 * S, borderRadius: 18 }} />
        <div
          style={{
            position: "absolute",
            left: 44 * S,
            top: 798 * S,
            width: 1186 * S,
            height: 150 * S,
            borderRadius: 12,
            border: "3px solid #c79a2b",
            opacity: ring,
            transform: `scale(${1.05 - 0.05 * ring})`,
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
/* ---------- S5 · human in the loop ---------- */
const S5: React.FC = () => {
  const f = useCurrentFrame();
  const cards = [
    { src: "el_review", w: 1270, h: 1200, x: 120, y: 300, s: 0.44, at: 22, label: "Confirm or correct" },
    { src: "el_forward", w: 1270, h: 612, x: 700, y: 360, s: 0.44, at: 104, label: "Move it forward" },
    { src: "el_history", w: 1270, h: 1014, x: 1290, y: 300, s: 0.44, at: 178, label: "Every change kept" },
  ];
  const active = f < 104 ? 0 : f < 178 ? 1 : 2;
  const steps = ["Queued", "In review", "Resolved"];
  const stepP = [ip(f, 30, 40), ip(f, 124, 134), ip(f, 196, 208)];
  // toasts slide out at the end of each beat
  const tOut = (a: number, b: number) => (f > b ? 1 - ip(f, b, b + 10) : 1);
  return (
    <AbsoluteFill>
      <Background glow={[50, 15]} />
      <div style={{ position: "absolute", left: 120, top: 70 }}>
        <Eyebrow text="04 — HUMAN IN THE LOOP" start={8} />
        <Words text="People make the final call." start={12} size={64} style={{ marginTop: 22 }} highlight={["final", "call"]} />
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
            <div style={{ fontFamily: FONT, fontSize: 20, fontWeight: 700, color: isA ? C.green : C.muted, letterSpacing: "0.12em", marginBottom: 14 }}>
              {String(i + 1).padStart(2, "0")} · {c.label.toUpperCase()}
            </div>
            <div
              style={{
                width: c.w * c.s,
                height: c.h * c.s,
                borderRadius: 16,
                overflow: "hidden",
                boxShadow: isA ? "0 50px 120px #1430272e, 0 0 0 2px #22705a55" : "0 24px 60px #1430271a, 0 0 0 1px #14302712",
                opacity: 1 - dim * 0.35,
                background: "#fff",
              }}
            >
              <Img src={shot(c.src)} style={{ width: c.w * c.s, display: "block" }} />
            </div>
          </div>
        );
      })}
      <div style={{ opacity: tOut(0, 98) }}>
        <Toast text="Classification confirmed" at={58} y={60} />
      </div>
      <div style={{ opacity: tOut(0, 172) }}>
        <Toast text="Note added to case history" at={128} y={60} />
        <Toast text="Moved to in review" at={138} y={140} />
      </div>
      <Toast text="Case resolved" at={204} y={60} />
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
        <span style={{ marginLeft: 26, fontSize: 21, color: C.muted, fontWeight: 500, opacity: ip(f, 220, 236) }}>
          Append-only history · original prediction never overwritten
        </span>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S6 · batches ---------- */
const IM = ["im_p00", "im_p02", "im_p04", "im_p06", "im_p08", "im_p15"];
const S6: React.FC = () => {
  const f = useCurrentFrame();
  const W = 1080;
  const fileFly = ip(f, 20, 46, 0, 1, Easing.bezier(0.5, 0, 0.2, 1));
  const ready = f >= 48;
  const pulse = ready ? sp(f, 48, 10, 0.6, 200) : 0;
  const win = sp(f, 62, 20, 1, 90);
  const src = f < 80 ? "im_01_ready" : IM[Math.min(IM.length - 1, Math.floor((f - 80) / 14))];
  const z = ip(f, 84, 120);
  return (
    <AbsoluteFill>
      <Background glow={[30, 40]} />
      <div style={{ position: "absolute", left: 120, top: 150, width: 560 }}>
        <Eyebrow text="05 — DURABLE BATCHES" start={8} />
        <Words text={"Drop in a CSV.\nSaved row by row."} start={12} size={62} style={{ marginTop: 24 }} highlight={["row"]} />
      </div>
      {/* upload zone with a file dropping in */}
      <div style={{ position: "absolute", left: 120, top: 520, width: 539, height: 239 }}>
        <div
          style={{
            width: 539,
            height: 239,
            borderRadius: 14,
            overflow: "hidden",
            boxShadow: "0 30px 70px #1430271f, 0 0 0 1px #14302712",
            transform: `scale(${1 + 0.03 * Math.sin(Math.PI * Math.min(1, pulse))})`,
            background: "#fff",
          }}
        >
          <Img src={shot(ready ? "el_upload_ready" : "el_upload_empty")} style={{ width: 539, height: 239 }} />
        </div>
        <div
          style={{
            position: "absolute",
            left: interpolate(fileFly, [0, 1], [520, 210]),
            top: interpolate(fileFly, [0, 1], [-260, 70]),
            transform: `rotate(${(1 - fileFly) * 14}deg) scale(${1 - 0.3 * fileFly})`,
            opacity: f < 18 ? 0 : 1 - ip(f, 44, 50),
            width: 118,
            height: 140,
            borderRadius: 14,
            background: "#fff",
            border: `1px solid ${C.line}`,
            boxShadow: "0 30px 60px #14302733",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            fontFamily: FONT,
          }}
        >
          <div style={{ width: 52, height: 62, borderRadius: 8, background: C.green, color: "#fff", fontWeight: 800, fontSize: 17, display: "flex", alignItems: "flex-end", justifyContent: "center", paddingBottom: 8 }}>
            CSV
          </div>
          <span style={{ fontSize: 15, color: C.muted, fontWeight: 600 }}>batch.csv</span>
        </div>
        <div style={{ marginTop: 30, display: "flex", gap: 12, flexWrap: "wrap" }}>
          <Chip start={60} size={19}>Up to 100 complaints</Chip>
          <Chip start={68} size={19} dot={C.lime}>Survives restarts</Chip>
          <Chip start={76} size={19} dot="#7aa58c">Retry failed rows</Chip>
        </div>
      </div>
      <div style={{ position: "absolute", left: 760, top: 190, perspective: 2000 }}>
        <div style={{ transform: `translateX(${(1 - win) * 300}px) rotateY(${-10 * (1 - win) - 4}deg)`, transformOrigin: "0 50%", opacity: Math.min(1, win * 1.5) }}>
          <Window src={shot(src)} w={W} zoom={1 + 0.2 * z} focus={[800 + 120 * z, 450 - 10 * z]} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S7 · overview on a laptop ---------- */
const S7: React.FC = () => {
  const f = useCurrentFrame();
  const e = sp(f, 6, 20, 1, 90);
  const LW = 1180; // screen width
  const LH = LW * 0.625;
  const k = LW / 3200; // full-page capture is 3200 px wide
  const scroll = ip(f, 40, 150, 0, 1, Easing.inOut(Easing.cubic)) * (3430 * k - LH) * 0.62;
  const side = sp(f, 30, 18, 1, 100);
  const ring = ip(f, 70, 90);
  return (
    <AbsoluteFill>
      <Background glow={[50, 30]} />
      <div style={{ position: "absolute", left: 120, top: 70 }}>
        <Eyebrow text="06 — OVERVIEW" start={8} />
        <Words text="See what needs you, at a glance." start={12} size={56} style={{ marginTop: 20 }} highlight={["glance"]} />
      </div>
      {/* laptop */}
      <div style={{ position: "absolute", left: 600, top: 215, transform: `translateY(${(1 - e) * 200}px)`, opacity: Math.min(1, e * 1.4) }}>
        <div style={{ width: LW + 36, padding: 18, paddingBottom: 26, background: "#1b1f1d", borderRadius: "28px 28px 10px 10px", boxShadow: "0 60px 120px #14302744" }}>
          <div style={{ width: LW, height: LH, overflow: "hidden", borderRadius: 6, background: "#fff", position: "relative" }}>
            <Img src={shot("pg_overview_full")} style={{ width: LW, position: "absolute", top: -scroll }} />
          </div>
        </div>
        <div style={{ width: LW + 160, marginLeft: -62, height: 22, background: "linear-gradient(#d9dcd8,#b9bdb8)", borderRadius: "0 0 22px 22px", boxShadow: "0 20px 40px #14302722" }}>
          <div style={{ width: 160, height: 8, margin: "0 auto", background: "#a9ada8", borderRadius: "0 0 8px 8px" }} />
        </div>
      </div>
      {/* floating sidebar with client branding */}
      <div
        style={{
          position: "absolute",
          left: 150,
          top: 250,
          transform: `translateX(${(1 - side) * -260}px) rotate(${-2 * side}deg)`,
          opacity: Math.min(1, side * 1.5),
        }}
      >
        <div style={{ width: 300, height: 1173, borderRadius: 18, overflow: "hidden", boxShadow: "0 40px 90px #1430274a", transform: "scale(0.66)", transformOrigin: "0 0" }}>
          <Img src={shot("el_sidebar")} style={{ width: 300 }} />
        </div>
        <div
          style={{
            position: "absolute",
            left: 7,
            top: 618,
            width: 184,
            height: 72,
            borderRadius: 10,
            border: `3px solid ${C.lime}`,
            opacity: ring,
            transform: `scale(${1.08 - 0.08 * ring})`,
          }}
        />
        <div style={{ position: "absolute", left: 214, top: 632, opacity: ring, transform: `translateX(${(1 - ring) * -20}px)` }}>
          <Chip start={70} size={18} dot={C.lime}>
            Prepared for Veltris
          </Chip>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/* ---------- S9 · outro ---------- */
const S9: React.FC = () => {
  const f = useCurrentFrame();
  const m = sp(f, 6, 14, 1, 110);
  const v = sp(f, 60, 16, 1, 100);
  const end = ip(f, 190, 210, 0, 1, Easing.linear);
  return (
    <AbsoluteFill>
      <Background glow={[50, 40]} />
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 34, transform: `scale(${0.9 + 0.1 * m}) translateY(${-40 * v}px)`, opacity: Math.min(1, m * 1.6) }}>
          <BrandMark size={130} />
          <div style={{ fontFamily: FONT, fontSize: 112, fontWeight: 800, color: C.deep, letterSpacing: "-0.05em" }}>ComplaintIQ</div>
        </div>
        <div style={{ transform: `translateY(${-40 * v}px)` }}>
          <Words text="Private, accountable complaint triage." start={20} size={44} weight={600} color={C.green} tracking={-0.02} style={{ marginTop: 36 }} />
        </div>
        <div style={{ marginTop: 40, display: "flex", alignItems: "center", gap: 30, opacity: Math.min(1, v * 1.5), transform: `translateY(${(1 - v) * 30}px)` }}>
          <span style={{ width: 120, height: 1, background: "#14302733" }} />
          <span style={{ fontFamily: FONT, fontSize: 18, letterSpacing: "0.4em", color: C.muted, fontWeight: 600 }}>PREPARED FOR</span>
          <Img src={staticFile("veltris-logo.png")} style={{ height: 70 }} />
          <span style={{ width: 120, height: 1, background: "#14302733" }} />
        </div>
        <div style={{ position: "absolute", bottom: 90, fontFamily: FONT, fontSize: 19, color: C.muted, letterSpacing: "0.22em", fontWeight: 600, opacity: ip(f, 90, 110) }}>
          QWEN2.5 · QLORA · LLAMA.CPP METAL · FASTAPI · REACT · SQLITE
        </div>
      </AbsoluteFill>
      <AbsoluteFill style={{ background: C.ivory, opacity: end }} />
    </AbsoluteFill>
  );
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

/* ---------- S7 · evidence ---------- */
const S8: React.FC = () => {
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
        <Eyebrow text="07 — MEASURED, NOT PROMISED" start={2} dark />
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
        Reserved test set of 153 CFPB complaints · joint product + issue accuracy 54.2% · scope gate sends 94% of unrelated test complaints to review
        <br />
        Priority and routing are explicit rules · summaries are extractive · issue labels are confirmed by people
      </div>
    </AbsoluteFill>
  );
};


const B = [0, 120, 378, 576, 966, 1164, 1404, 1710, 1932, 2100, 2430, 2640];
const OV = 22;
const seg = (i: number) => ({ from: B[i], dur: B[i + 1] - B[i] + (i < 10 ? OV : 0) });
export const Reel: React.FC = () => (
  <AbsoluteFill style={{ background: C.ivory }}>
    <Fonts />
    <Scene {...seg(0)} enter="fade"><S0 /></Scene>
    <Scene {...seg(1)} enter="fade"><S1 /></Scene>
    <Scene {...seg(2)} enter="circle"><S2 /></Scene>
    <Scene {...seg(3)} enter="up"><S3 /></Scene>
    <Scene {...seg(4)} enter="left"><S4 /></Scene>
    <Scene {...seg(5)} enter="up"><SX /></Scene>
    <Scene {...seg(6)} enter="left"><S5 /></Scene>
    <Scene {...seg(7)} enter="left"><S6 /></Scene>
    <Scene {...seg(8)} enter="up"><S7 /></Scene>
    <Scene {...seg(9)} enter="circle"><S8 /></Scene>
    <Scene {...seg(10)} enter="fade"><S9 /></Scene>
    <Audio src={staticFile("mix.wav")} />
  </AbsoluteFill>
);
