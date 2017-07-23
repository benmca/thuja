
dev = pow(2, (1.0/12.0))
pc_spec = list("axbcxdxefxgx")

def steps_to_freq(steps):
    return pow(dev,steps)*27.5


def pc_to_freq(pc, default_octave):
    """
    converts pitch class name to frequency
    pitch class spec - [note name][s|f|n][octave]
    examples: b4, cs5, af8, an3
    """
    if pc == 'r':
            return {"value" : 0, "octave" : 0}

    octave = default_octave

    pitchindex = int(pc_spec.index(pc[0]))

    if pc[len(pc)-1].isdigit():
            octave = int(pc[len(pc)-1])

    pitchindex += 12*octave

    if len(pc) >= 2:
            if pc[1] == 's':
                    pitchindex += 1
            if pc[1] == 'f':
                    pitchindex -= 1

    return {"value" : steps_to_freq(pitchindex), "octave" : octave}


def rhythm_to_duration(rhythm_string, tempo):
    print 'rtd: ' + rhythm_string
    """
    converts rhythm string to frequency
    rhythm string spec - [w|h|q|e|s][.][.]
    rhythm strings can be concatented with +
    examples: w, q+w, e.+h+s, s..
    """
    ret = 0.0
    dur_of_quarter = 60.0 / tempo
    #todo - triplet case
    multipliers = {'w':4,'h':2,'q':1,'e':.5,'s':.25}


    strings = rhythm_string.split('+')

    for s in strings:
        val = 0.0
        if multipliers.has_key(s[0]):
            val = (dur_of_quarter * multipliers[s[0]])
            if s.find("..") != -1:
                val = val*.25
            elif s.find('.') != -1:
                val = val*.5
        elif s.isdigit():
            whole = (dur_of_quarter * 4)
            mult = (1.0 / int(s))
            val = whole*mult

        ret += val
    return ret

def quarter_duration_to_tempo(dur):
    return 60 * (1/dur)

