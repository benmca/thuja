sr=44100
ksmps=10
nchnls=1

instr 1
idur = p3
iamp = p4 * 16000
ipitch = p5

kamp    linen   iamp, idur*.1, idur, idur*.1
acar    oscili  kamp, ipitch, 1

out acar
endin

