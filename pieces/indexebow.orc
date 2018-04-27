sr=44100
ksmps=1000
nchnls=2

ga1 init 0
ga2 init 0




instr 1
idur = p3
iamp = p4*100
ipitch = p5
ipan = p6
idist = p7
ipct = p8
indx = p9
iorigdur = p10
iendx = indx + iorigdur

kamp	linen	iamp, .001, idur, .1
ktime   line    indx, idur , iendx

al, ar	diskin	"/Users/ben/Music/_toSort/Ebow Tone Row.1.wav", ipitch, indx
;al  sndwarp kamp, ktime, 1, 3, 0, 4410, 882, 15, 1, 1

al=al*kamp

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

endin