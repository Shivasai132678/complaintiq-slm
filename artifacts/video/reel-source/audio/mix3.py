# Mix for the 88 s reel: VO clip name and start time (s); music from music3.py.
import numpy as np, soundfile as sf
from scipy.signal import resample_poly, butter, sosfilt
SR=48000; N=int(88.0*SR)
music,_=sf.read('music3.wav')
clips=[('v2_0',4.3),('v2_1',13.0),('v2_2',19.5),('v2_3',25.6),('v2_4',32.5),('v3_x1',39.1),('v2_5',47.1),('v2_6',57.3),('v2_7',64.7),('v2_8',70.3),('v2_9',81.6)]
vo=np.zeros(N)
for name,s in clips:
    d,sr=sf.read(f'{name}.wav'); d=resample_poly(d,2,1)
    a=np.where(np.abs(d)>0.01)[0]; d=d[max(0,a[0]-480):a[-1]+2400]
    k=int(s*SR); vo[k:k+len(d)]+=d[:N-k]
vo=sosfilt(butter(2,90,'high',fs=SR,output='sos'),vo)
env=(np.abs(vo)>0.005).astype(float)
env=np.convolve(env,np.ones(int(0.25*SR))/int(0.25*SR),'same'); env=np.clip(env*3,0,1)
env=np.convolve(env,np.ones(int(0.3*SR))/int(0.3*SR),'same')
mix=music*(1-0.55*env)[:,None]*0.55+np.stack([vo,vo],1)/np.abs(vo).max()*0.9
mix/=np.abs(mix).max()/0.95
sf.write('mix3_raw.wav',mix,SR)  # then: ffmpeg -i mix3_raw.wav -af loudnorm=I=-15:TP=-1.5:LRA=9 mix.wav
