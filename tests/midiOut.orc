sr=44100
ksmps=2
nchnls=2

ga1 init 0
ga2 init 0





instr 1  ;Turned on by MIDI notes on channel 1

  ifund  = 12 * (log(p5/220)/log(2))+57 
  ivel =	127
  idur = 1

print ifund

  ;chord with single key
  noteondur 	1, ifund,   ivel, idur

endin

