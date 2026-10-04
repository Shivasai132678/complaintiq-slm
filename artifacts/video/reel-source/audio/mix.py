import numpy as np, soundfile as sf, json
from scipy.signal import resample_poly, butter, sosfilt
SR=48000; N=int(57.0*SR)
music,_=sf.read('music.wav')
starts=[0.6,6.4,11.9,22.8,28.9,38.3,43.4,52.3]
vo=np.zeros(N)
meta=[]
for i,s in enumerate(starts):
    d,sr=sf.read(f'/root/reel/vo/af_heart_{i}.wav')
    d=resample_poly(d,2,1)
    # trim silence
    a=np.where(np.abs(d)>0.01)[0]; d=d[max(0,a[0]-480):a[-1]+2400]
    k=int(s*SR); vo[k:k+len(d)]+=d[:N-k]
    meta.append({'i':i,'start':s,'end':round(s+len(d)/SR,2)})
vo=sosfilt(butter(2,90,'high',fs=SR,output='sos'),vo)
# duck envelope
env=(np.abs(vo)>0.005).astype(float)
w=int(0.25*SR); env=np.convolve(env,np.ones(w)/w,'same'); env=np.clip(env*3,0,1)
w2=int(0.3*SR); env=np.convolve(env,np.ones(w2)/w2,'same')
duck=1-0.55*env
mus=music*duck[:,None]*0.55
voc=vo/np.abs(vo).max()*0.9
mix=mus+np.stack([voc,voc],1)
mix/=np.abs(mix).max()/0.95
sf.write('mix_raw.wav',mix,SR)
print(json.dumps(meta))
