import numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt, fftconvolve
SR=48000; DUR=88.0; N=int(SR*DUR)
rng=np.random.default_rng(7)
t=np.arange(N)/SR
L=np.zeros(N); R=np.zeros(N)
def lp(x,fc,o=2): return sosfilt(butter(o,fc,'low',fs=SR,output='sos'),x)
def hp(x,fc,o=2): return sosfilt(butter(o,fc,'high',fs=SR,output='sos'),x)
def bp(x,lo,hi): return sosfilt(butter(2,[lo,hi],'band',fs=SR,output='sos'),x)
def mtof(m): return 440*2**((m-69)/12)
def add(buf,start,sig,gain=1.0):
    i=int(start*SR); j=min(N,i+len(sig))
    if i>=N: return
    buf[i:j]+=sig[:j-i]*gain
def env_adsr(n,a,d,s,r):
    e=np.ones(n)*s; A=int(a*SR); D=int(d*SR); Rr=int(r*SR)
    A=min(A,n); e[:A]=np.linspace(0,1,A)
    D=min(D,n-A); e[A:A+D]=np.linspace(1,s,D)
    if Rr< n: e[-Rr:]*=np.linspace(1,0,Rr)
    return e
BPM=100; beat=60/BPM; bar=4*beat
# chords (midi) Dmaj9, Bm9, Gmaj9, Asus
chords=[[50,57,62,66,69,76],[47,54,62,66,69,73],[43,55,62,66,69,74],[45,52,61,64,69,71]]
def pad_note(f,dur):
    n=int(dur*SR); tt=np.arange(n)/SR; s=np.zeros(n)
    for det in (-0.08,0,0.07):
        ph=rng.random()
        ff=f*2**(det/12)
        s+= ((tt*ff+ph)%1*2-1)   # saw
    s=lp(s,1800); return s*env_adsr(n,1.2,0.5,0.8,1.4)
# pad across whole piece
seg=2*bar
k=0; st=0.0
while st<DUR-0.5:
    ch=chords[k%4]; d=min(seg+1.2,DUR-st)
    for m in ch:
        p=pad_note(mtof(m),d)*0.035
        pan=rng.uniform(-0.6,0.6)
        add(L,st,p*(1-pan)/1.0); add(R,st,p*(1+pan)/1.0)
    st+=seg; k+=1
# intro filter sweep: attenuate highs early
GROOVE_START=19.2; END_GROOVE=81.0
# kick
def kick():
    n=int(0.45*SR); tt=np.arange(n)/SR
    f=48+90*np.exp(-tt*30); ph=2*np.pi*np.cumsum(f)/SR
    return np.sin(ph)*np.exp(-tt*7)
def hat(open_=False):
    n=int((0.18 if open_ else 0.05)*SR); x=hp(rng.standard_normal(n),7000)
    return x*np.exp(-np.arange(n)/SR*(18 if open_ else 70))
def pluck(f):
    n=int(0.5*SR); tt=np.arange(n)/SR
    s=np.sin(2*np.pi*f*tt)+0.4*np.sin(2*np.pi*2*f*tt)+0.15*np.sin(2*np.pi*3*f*tt)
    return s*np.exp(-tt*9)
def bass(f,d):
    n=int(d*SR); tt=np.arange(n)/SR
    s=np.sin(2*np.pi*f*tt)+0.3*np.sin(2*np.pi*2*f*tt)
    return lp(s,400)*env_adsr(n,0.01,0.1,0.8,0.08)
K=kick()
b=GROOVE_START; i=0
while b<END_GROOVE-0.01:
    pos=i%4
    if pos in (0,2): add(L,b,K,0.42); add(R,b,K,0.42)
    h=hat(pos==3); add(L,b+beat/2,h,0.05); add(R,b+beat/2,h,0.07)
    if pos in (1,3): 
        sn=bp(rng.standard_normal(int(0.2*SR)),900,5000)*np.exp(-np.arange(int(0.2*SR))/SR*22)
        add(L,b,sn,0.05); add(R,b,sn,0.05)
    b+=beat; i+=1
# bass + arp follow chords from groove start
st=GROOVE_START
while st<END_GROOVE-0.01:
    ci=int(st//seg)%4; ch=chords[ci]
    root=mtof(ch[0]-12)
    for q in range(8):
        add(L,st+q*beat/2*2, bass(root,beat*0.9),0.16); add(R,st+q*beat/2*2,bass(root,beat*0.9),0.16)
        if q>=4: break
    arp=[ch[3]+12,ch[4]+12,ch[5]+12,ch[4]+12]
    for q in range(16):
        tq=st+q*beat/2
        if tq>=END_GROOVE: break
        p=pluck(mtof(arp[q%4]))
        pan=0.5 if q%2 else -0.5
        add(L,tq,p,0.035*(1-pan)); add(R,tq,p,0.035*(1+pan))
        # echo
        add(L,tq+beat*0.75,p,0.012*(1+pan)); add(R,tq+beat*0.75,p,0.012*(1-pan))
    st+=bar
# whoosh transitions
def whoosh(d=1.0,rev=False):
    n=int(d*SR); x=rng.standard_normal(n); tt=np.linspace(0,1,n)
    out=np.zeros(n); 
    # moving bandpass via chunks
    chunks=40
    for c in range(chunks):
        a=c*n//chunks; z=(c+1)*n//chunks
        fc=300+6000*(tt[a] if not rev else 1-tt[a])
        out[a:z]=bp(x[a:z],fc*0.7,min(fc*1.4,20000))
    e=np.sin(np.pi*tt)**2
    return out*e
for tr in [4.0,12.6,19.2,32.2,38.8,46.8,57.0,64.4,70.0,81.0]:
    w=whoosh(0.9); add(L,tr-0.6,w,0.12); add(R,tr-0.6,w[::-1]*0+w,0.10)
# impacts
def impact():
    n=int(2.5*SR); tt=np.arange(n)/SR
    s=np.sin(2*np.pi*(40+60*np.exp(-tt*12))*tt)*np.exp(-tt*3)
    sh=hp(rng.standard_normal(n),4000)*np.exp(-tt*2.5)*0.15
    return s+sh
for tr,g in [(4.0,0.3),(12.6,0.38),(70.0,0.3),(81.0,0.45)]:
    im=impact(); add(L,tr,im,g); add(R,tr,im,g)
# outro chord bell
for m in [62,66,69,74,78]:
    n=int(5*SR); tt=np.arange(n)/SR; s=np.sin(2*np.pi*mtof(m)*tt)*np.exp(-tt*1.2)
    add(L,81.1,s,0.03); add(R,81.15,s,0.03)
# reverb
ir_n=int(2.2*SR); irt=np.arange(ir_n)/SR
irL=rng.standard_normal(ir_n)*np.exp(-irt*3.2); irR=rng.standard_normal(ir_n)*np.exp(-irt*3.2)
irL=lp(irL,6000); irR=lp(irR,6000)
wetL=fftconvolve(L,irL)[:N]*0.012; wetR=fftconvolve(R,irR)[:N]*0.012
L=L+wetL; R=R+wetR
# master fade
fade=np.ones(N); fi=int(0.8*SR); fade[:fi]=np.linspace(0,1,fi); fo=int(2.5*SR); fade[-fo:]=np.linspace(1,0,fo)
L*=fade; R*=fade
m=max(np.abs(L).max(),np.abs(R).max()); L/=m; R/=m
sf.write('music3.wav',np.stack([L,R],1)*0.89,SR)
print('ok')
