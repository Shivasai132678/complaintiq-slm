import json, soundfile as sf
from kokoro_onnx import Kokoro
k = Kokoro("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")
V="af_heart"
lines = [
 "Every day, financial companies receive thousands of complaints. Each one is a customer's story, and most are still sorted by hand.",
 "Meet Complaint I.Q. Private complaint intelligence that runs entirely on your own machine.",
 "Pick a complaint, or paste your own. A fine-tuned Kwen model reads it, right on the laptop.",
 "In about a second, the case is classified by product and issue, and ready for review.",
 "Priority and routing follow transparent rules, and every suggestion shows the reason behind it.",
 "Your team stays in control. Confirm or correct the labels, add notes, and resolve the case, with every change kept in an append-only history.",
 "Drop in a CSV, and whole batches are processed one row at a time, safe through refreshes and restarts.",
 "The overview shows what needs attention right now, across every product and status.",
 "Fine-tuned on nine thousand real C.F.P.B. complaints, with eighty-nine percent product accuracy on held-out data. And nothing ever leaves the device.",
 "Complaint I.Q. Private, accountable complaint triage. Prepared for Veltris.",
]
meta=[]
for i,t in enumerate(lines):
    s,sr=k.create(t,voice=V,speed=1.03,lang="en-us")
    sf.write(f"v2_{i}.wav",s,sr); meta.append(round(len(s)/sr,2))
print(meta, sum(meta))

# Line added for the out-of-scope scene (saved as v3_x1.wav)
EXTRA = "When a complaint is outside what the model knows, it doesn't guess. It goes straight to a person, with the reason shown."
