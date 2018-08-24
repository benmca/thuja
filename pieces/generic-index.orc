sr=96000
ksmps=10
nchnls=2

ga1 init 0
ga2 init 0

gatrack1 init 0
gatrack2 init 0
gatrack3 init 0
gatrack4 init 0


instr 1
idur = p3
iamp = p4*10
ipitch = p5
ipan = p6
idist = p7
ipct = p8
indx = p9
iorigdur = p10
Spath = p11
itrack = p12
;inumchannels = p12

iendx = indx + iorigdur

kamp	linen	iamp, .001, idur, .001
ktime   line    indx, idur , iendx
al	diskin	Spath, ipitch, indx
al=al*kamp

if (itrack == 1) then
    gatrack1=al
elseif (itrack == 2) then
    gatrack2=al
elseif (itrack == 3) then
    gatrack3 = al
elseif (itrack == 4) then
    gatrack4=al
endif

al, ar  locsig	al, ipan, idist, ipct
ar1, ar2	locsend
		outs	al, ar

ga1=ga1+ar1
ga2=ga2+ar2

endin

instr 99
klin 	linseg  p4, p3, p4
kamp	linseg	1, p3, 1
a1	reverb2	ga1, klin, 1
a2	reverb2	ga2, klin, 1
	outs	a1*kamp,a2*kamp
ga1=0
ga2=0

fout "track1.wav", -1, gatrack1
fout "track2.wav", -1, gatrack2
fout "track3.wav", -1, gatrack3
fout "track4.wav", -1, gatrack4

gatrack1 = 0
gatrack2 = 0
gatrack3 = 0
gatrack4 = 0

endin