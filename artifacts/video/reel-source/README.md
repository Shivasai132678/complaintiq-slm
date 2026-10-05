# ComplaintIQ product reel (source)

88-second (v3, prepared for Veltris) 1080p30 motion reel built with Remotion from real captures of the ComplaintIQ frontend
(running locally with the fine-tuned Qwen2.5-1.5B GGUF; the analyzed complaint was classified live in 1.28 s).

- `src/Reel.tsx` — composition: 11 scenes (Veltris intro, challenge, brand, analyze, policy, out-of-scope handling, human review, batches, overview, evidence, outro); primitives in `src/prims.tsx`
- `audio/gen2.py` — voice-over (Kokoro TTS, voice `af_heart`)
- `audio/music3.py` — original synthesized music bed; `audio/mix3.py` — VO placement, ducking, mix
- Screenshots go in `public/shots/`, fonts (Inter) in `public/fonts/`, final mix in `public/mix.wav`

Render: `npx remotion render src/index.ts ComplaintIQReel out/ComplaintIQ_Product_Reel_Veltris.mp4 --crf=16`
