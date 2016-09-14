import random
import math
import audiolazy

from composition import itemstream

random.seed()
class PitchQueue:
    curdx = 0
    rhythm_stream = itemstream.itemstream(['e', 'q', 's', 'q', 's', 's', 's'],'heap', tempo=120)
    rhythm_stream.notetype = 'rhythm'

    def __init__(self):
        self.items = []
        self.max_size = 8

    def isEmpty(self):
        return self.items == []

    def enqueue(self, item):
        if len(self.items) >= self.max_size:
            self.dequeue()
        self.items.append(item)
        print 'enqueue: ' + str(item) + ', items: ' + str(self.items)

    def dequeue(self):
        return self.items.pop(0)

    def size(self):
        return len(self.items)

    def get_random_pitch(self, arg):
        x = 0.0
        if len(self.items) > 1:
            x = self.items[random.randint(0, len(self.items) - 1)]
        return x

    def get_next_pitch(self, arg):
        x = 0.0        
        if len(self.items) > 0:
            x = self.items[self.curdx % len(self.items)]
        self.curdx = self.curdx + 1
        return x
    def get_next_dur(self, arg):
        return self.rhythm_stream.get_next_value()
    def reverse(self, arg):
        self.items.reverse()
        print 'reverse'

    def inverse(self, arg):
        new_items = []
        new_items.append(self.items[0])
        for x in range(1, len(self.items)):
            iprev_notenum  = int(audiolazy.freq2midi(self.items[x-1]))
            inotenum = int(audiolazy.freq2midi(self.items[x]))
            delta = iprev_notenum - inotenum
            new_notenum = int(audiolazy.freq2midi(new_items[x-1])) + delta
            new_freq = audiolazy.midi2freq(new_notenum)
            new_items.append(new_freq)
        self.items = new_items
        print self.items



    def half_temp(self, arg):
        self.rhythm_stream.tempo = (self.rhythm_stream.tempo * .5)
        print 'HALF tempo: ' + str(self.rhythm_stream.tempo)

    def double_temp(self, arg):
        self.rhythm_stream.tempo = (self.rhythm_stream.tempo * 2)
        print 'DOUBLE tempo: ' + str(self.rhythm_stream.tempo)

pitches = PitchQueue()
pitches.items = [261.625564, 277.166995, 293.656484]
pitches.inverse(0)