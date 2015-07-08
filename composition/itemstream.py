import utils
import random

class itemstream:
    """"""
    def __init__(self, initstream, streammode = 'sequence', notetype = 'number', tempo = 120):
        """Constructor"""
        self.values = initstream
        self.index = 0
        self.streammode = streammode
        self.notetype = notetype
        self.heapdict = set()
        
        # used for rhythm streams
        self.tempo = tempo
        # used for pitches etc
        self.is_chording = False
        self.chording_index = 0
        self.current_octave = 0
        self.note_count = 0;

    def get_next_value(self):
        ret = None
        if isinstance(self.values[self.index],list):
            if self.is_chording == False:
                #initial case
                self.is_chording = True
                self.chording_index = 0
            if self.notetype == 'number':
                ret = self.values[self.index][self.chording_index]
            elif self.notetype == 'pitch':
                result = utils.pc_to_freq(self.values[self.index][self.chording_index], self.current_octave)
                ret = result["value"]
                self.current_octave = result["octave"]
            elif self.notetype == 'rhythm':
                if isinstance(self.tempo, list):
                    ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index], self.tempo[self.note_count % len(self.tempo)])
                else:
                    ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index], self.tempo)
            
            self.chording_index = self.chording_index + 1
            if self.chording_index == len(self.values[self.index]):
                self.is_chording = False
                self.chording_index = 0
                if self.streammode == "sequence":
                    if self.index < len(self.values)-1:
                        self.index = self.index + 1
                    else:
                        self.index = 0
                elif self.streammode == "heap":
                    added = False
                    if len(self.heapdict) == len(self.values):
                        self.heapdict.clear()
                    while not added:
                        self.index = random.randrange(0,len(self.values))
                        if (self.index in self.heapdict) == False:
                            added = True
                            self.heapdict.add(self.index)
                elif self.streammode == "random":
                    self.index = random.randrange(0,len(self.values))
        
        elif isinstance(self.values[self.index], itemstream):
            self.is_chording = False
            # nested stream case
            pass
        else:
            self.is_chording = False
            # default case
            if self.notetype == 'number':
                ret = self.values[self.index]
            elif self.notetype == 'pitch':
                result = utils.pc_to_freq(self.values[self.index], self.current_octave)
                ret = result["value"]
                self.current_octave = result["octave"]
            elif self.notetype == 'rhythm':
                if isinstance(self.tempo, list):
                    ret = utils.rhythm_to_duration(self.values[self.index], self.tempo[self.note_count % len(self.tempo)])
                else:
                    ret = utils.rhythm_to_duration(self.values[self.index], self.tempo)
            
            if self.streammode == "sequence":
                if self.index < len(self.values)-1:
                    self.index = self.index + 1
                else:
                    self.index = 0
            elif self.streammode == "heap":
                added = False
                if len(self.heapdict) == len(self.values):
                    self.heapdict.clear()
                    
                while not added:
                    self.index = random.randrange(0,len(self.values))
                    if (self.index in self.heapdict) == False:
                        added = True
                        self.heapdict.add(self.index)
                
            elif self.streammode == "random":
                self.index = random.randrange(0,len(self.values))

        self.note_count += 1
        return ret
