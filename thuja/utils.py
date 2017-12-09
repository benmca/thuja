import math
from collections import OrderedDict

pc_spec = list("cxdxefxgxaxb")


# Hertz = 440.0 * pow(2.0, (midi note - 69)/12);
#
# midi note = log(Hertz/440.0)/log(2) * 12 + 69;

def freq_to_midi_note(freq):
    val = math.log(freq/440.0)/math.log(2.0) * 12.0 + 69.0
    ret = 0
    if val > 0 and (val - int(val) > .5):
        ret = int(math.ceil(val))
    elif val > 0:
        ret = int(math.floor(val))
    return ret

def midinote_to_freq(midinote):
    ret = 440.0 * math.pow(2.0, (midinote - 69.0)/12.0)
    return ret

def pc_to_freq(pc, default_octave):
    """
    converts pitch class name to frequency
    pitch class spec - [note name][s|f|n][octave]
    examples: b4, cs5, af8, an3
    """
    if pc == 'r':
            return {"value" : 0, "octave" : 0}

    octave = default_octave

    midinote = int(pc_spec.index(pc[0]))

    if pc[len(pc)-1].isdigit():
            octave = int(pc[len(pc)-1])

    midinote += 12*(octave+1)

    if len(pc) >= 2:
            if pc[1] == 's':
                    midinote += 1
            if pc[1] == 'f':
                    midinote -= 1

    # print 'pc_to_freq: pitch index: ' + str(pitchindex)

    return {"value" : midinote_to_freq(midinote), "octave" : octave}

def freq_to_pc(freq, include_octave):
    """
    converts frequency to pitch class name
    pitch class spec - [note name][s|f|n][octave]
    examples: b4, cs5, af8, an3
    include_octave adds octave number to ret'd string
    """
    return midi_note_to_pc(freq_to_midi_note(freq), include_octave)


def midi_note_to_pc(midinote, include_octave=True):
    """
    converts midi note to pitch class name
    pitch class spec - [note name][s|f|n][octave]
    examples: b4, cs5, af8, an3
    """
    octave = int((midinote) / 12) - 1
    pcid = pc_spec[(midinote)%12]

    pc = ''
    if pcid == 'x':
        pc = pc_spec[((midinote)%12)-1] + 's'
    else:
        pc = pcid

    if include_octave:
        pc += str(octave)

    return pc

def pc_to_midi_note(pc, default_octave):
    """
    converts pitch class name to midi note
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


    return {"value" : pitchindex}


def add_rhythm(rhythm_string, modifier):
    return modify_rhythm(rhythm_string, modifier, True)


def subtract_rhythm(rhythm_string, modifier):
    return modify_rhythm(rhythm_string, modifier, False)

    #
    # multipliers = OrderedDict({'w':4,'h':2,'q':1,'e':.5,'s':.25})
    # strings = rhythm_string.split('+')
    # for s in strings:
    #     val = 0.0
    #     if multipliers.has_key(s[0]):
    #         val = (dur_of_quarter * multipliers[s[0]])
    #         if s.find("..") != -1:
    #             val = val*.25
    #         elif s.find('.') != -1:
    #             val = val*.5
    #     elif s.isdigit():
    #         whole = (dur_of_quarter * 4)
    #         mult = (1.0 / int(s))
    #         val = whole*mult
    #
    #     ret += val


def modify_rhythm(rhythm_string, modifier, add):
    val1 = rhythm_string_to_val(rhythm_string)
    val2 = rhythm_string_to_val(modifier)
    result = 0.0
    if add:
        result = val1 + val2
    elif val1 - val2 > 0:
        result = val1 - val2
    return val_to_rhythm_string(result)

def val_to_rhythm_string(val):
    multipliers = {4: 'w', 2: 'h', 1: 'q', .5: 'e', .25: 's'}
    mults_list = OrderedDict(sorted(multipliers.items(), key = lambda t : t[0], reverse=True))
    ret = ''
    for key in mults_list.keys():
        if val == 0:
            break
        if int(val / key) >= 2:
            ret += mults_list[key]
            val -= key
        elif int(val / key) >= 1:
            #special case - this could be a dotted case
            ret += mults_list[key]
            # remainder = (val / key) - int(val/key)
            remainder = val - key
            if remainder > 0 and key / remainder == 4:
                val -= remainder
                ret += '..'
            if remainder > 0 and key / remainder == 2:
                val -= remainder
                ret += '.'
            val -= key
        if val > 0 and len(ret) > 0 and ret[len(ret)-1] != '+':
            ret += '+'

    # if val > 0:

    return ret

def rhythm_string_to_val(rhythm_string):
    multipliers = {'w':4,'h':2,'q':1,'e':.5,'s':.25}
    strings = rhythm_string.split('+')
    val = 0.0
    for s in strings:
        if s[0] in multipliers.keys():
            val += multipliers[s[0]]
            if s.find("..") != -1:
                val += val*.25
            elif s.find('.') != -1:
                val += val*.5
        elif s.isdigit():
            whole = 4
            mult = (1.0 / int(s))
            val += whole*mult

    return val


def rhythm_to_duration(rhythm_string, tempo):
    #print 'rtd: ' + rhythm_string
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
        if s[0] in multipliers.keys():
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

def dur_of_quarter(tempo):
    return 60.0 / tempo

def quarter_duration_to_tempo(dur):
    return 60 * (1/dur)

