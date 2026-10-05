import numpy as np, soundfile as sf, json
from scipy.signal import resample_poly, butter, sosfilt
SR=48000; N=int(80.0*SR)
music,_=sf.read('music2.wav')
starts=[4.3,13.0,19.5,25.6,32.5,39.1,49.3,56.7,62.3,73.6]
vo=np.zeros(N); meta=[]
for i,s in enumerate(starts):
    d,sr=sf.read(f'/root/reel/vo/v2_{i}.wav'); d=resample_poly(d,2,1)
    a=np.where(np.abs(d)>0.01)[0]; d=d[max(0,a[0]-480):a[-1]+2400]
    k=int(s*SR); vo[k:k+len(d)]+=d[:N-k]; meta.append((s,round(s+len(d)/SR,2)))
vo=sosfilt(butter(2,90,'high',fs=SR,output='sos'),vo)
env=(np.abs(vo)>0.005).astype(float)
w=int(0.25*SR); env=np.convolve(env,np.ones(w)/w,'same'); env=np.clip(env*3,0,1)
env=np.convolve(env,np.ones(int(0.3*SR))/int(0.3*SR),'same')
mus=music*(1-0.55*env)[:,None]*0.55
mix=mus+np.stack([vo,vo],1)/np.abs(vo).max()*0.9
mix/=np.abs(mix).max()/0.95
sf.write('mix2_raw.wav',mix,SR); print(meta)
