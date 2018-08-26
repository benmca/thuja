sr=44100
ksmps=1
nchnls=2

ga1 init 0
ga2 init 0




instr 1 ;sine

; convert incoming freq to midinote
;int n = (int) ( ( 12 * log(f / 220.0) / log(2.0) ) + 57.01 );
ifreq = int(p5)
if_over_220 = ifreq/220
i1 = log(if_over_220)
i2 = log(2.0)
isolution = ( ( (12 * i1) / i2 ) + 57.01 )
inotenum = int(isolution)




idur = p3
iamp = p4 * 16000
ipitch = p5
ipan = p6
idist = p7
ipct = p8
ichannel = p9

;convert scalar 0 > 1 to velocity value 0 > 127
iamp_midi = p4
ivelocity = int(127*iamp_midi)

noteondur2   ichannel, inotenum, ivelocity, p3-.1


kamp    linen   iamp, idur*.1, idur, idur*.4
;kamp    linen   iamp, .02, idur, idur*.5
;amod    oscili  1000, ipitch, 1
;acar    oscili  kamp, ipitch+amod, 1
;acar    oscili  kamp, ipitch+amod, 1
acar    oscili  kamp, ipitch, 1

a1, a2  locsig  acar, ipan, idist, ipct
ar1, ar2  locsend
outs a1, a2
ga1 = ga1+ar1
ga2 = ga2+ar2


endin

instr 3 ;sine
idur = p3
iamp = p4 * 16000
ipitch = p5
ipan = p6
idist = p7
ipct = p8

kamp    linen   iamp, idur*.01, idur, idur*.01
;kamp    linen   iamp, .02, idur, idur*.5
;amod    oscili  1000, ipitch, 1
;acar    oscili  kamp, ipitch+amod, 1
;acar    oscili  kamp, ipitch+amod, 1
acar    oscili  kamp, ipitch, 1

a1, a2  locsig  acar, ipan, idist, ipct
ar1, ar2  locsend
outs a1, a2
ga1 = ga1+ar1
ga2 = ga2+ar2

endin

instr 99 
a1  reverb  ga1, 1
a2  reverb  ga2, 1
outs  a1,a2
ga1=0
ga2=0
endin