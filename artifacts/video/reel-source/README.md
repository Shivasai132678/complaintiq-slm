# ComplaintIQ product reel (source)

57-second 1080p30 motion reel built with Remotion from real captures of the ComplaintIQ frontend
(running locally with the fine-tuned Qwen2.5-1.5B GGUF; the analyzed complaint was classified live in 0.79 s).

- `src/Reel.tsx` — composition: 8 scenes (challenge, brand, analyze, policy, human review, batches, evidence, outro)
- `audio/gen.py` — voice-over (Kokoro TTS, voice `af_heart`)
- `audio/music.py` — original synthesized music bed; `audio/mix.py` — VO placement, ducking, mix
- Screenshots go in `public/shots/`, fonts (Inter) in `public/fonts/`, final mix in `public/mix.wav`

Render: `npx remotion render src/index.ts ComplaintIQReel out/ComplaintIQ_Product_Reel.mp4 --crf=16`
