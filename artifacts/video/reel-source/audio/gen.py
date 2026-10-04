import json, sys, soundfile as sf
from kokoro_onnx import Kokoro
k = Kokoro("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")
voice = sys.argv[1] if len(sys.argv) > 1 else "af_heart"
lines = [
 "Every financial complaint is a customer's story. Most teams still sort them by hand.",
 "Meet Complaint I.Q. Complaint intelligence that runs entirely on your Mac.",
 "Paste a complaint, and a fine-tuned Kwen model classifies the product and the issue in about a second. No cloud. No A.P.I. Nothing leaves the device.",
 "Priority and routing follow transparent rules, and every suggestion shows its reason.",
 "Your team stays in control. Confirm or correct each case, add notes, and resolve it, with every change kept in an append-only history.",
 "Import whole batches. Processing is durable, one row at a time.",
 "Trained on nine thousand real C.F.P.B. complaints, with eighty-nine percent product accuracy on held-out data.",
 "Complaint I.Q. Private, accountable complaint triage.",
]
meta = []
for i, t in enumerate(lines):
    s, sr = k.create(t, voice=voice, speed=1.04, lang="en-us")
    sf.write(f"{voice}_{i}.wav", s, sr)
    meta.append({"i": i, "text": t, "sec": round(len(s)/sr, 2)})
print(json.dumps(meta, indent=0)); print("total", sum(m["sec"] for m in meta))
