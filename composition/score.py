from composition.itemstream import Itemstream
from composition.event import Event
import utils

#import utils
class Score:
    """"""

    #----------------------------------------------------------------------
    def __init__(self, rhythmstream, streams, note_limit = 16):
        """Constructor"""
        self.starttime = 0.0
        self.curtime = self.starttime
        self.streams = streams
        self.instr = 1
        self.rhythmstream = rhythmstream
        self.durstream = rhythmstream
        self.note_limit = note_limit
        self.note_count = 0
        self.time_limit = 0
        self.gen_lines = []
        self.notes = []
        self.end_lines = []
        self.score_dur = 0
        
    def generate_score(self, filename = None):
        self.note_count = 0
        self.curtime = self.starttime
        f = None
        if filename != None:
            f = open(filename, 'w')
        
        for gendx in range(len(self.gen_lines)):
            if f == None:
                print(self.gen_lines[gendx] + "\n")
            else:
                f.writelines(self.gen_lines[gendx] + "\n")
        
        for x in range(len(self.notes)):
            if f == None:
                print(self.notes[x])
            else:
                f.writelines(self.notes[x])
            
        for x in range(len(self.end_lines)):
            if f == None:
                print(self.end_lines[x] + "\n")
            else:
                f.writelines(self.end_lines[x] + "\n")
                
        #while self.note_count < self.note_limit:
            #note = [self.instr, self.curtime, self.durstream.get_next_value()]
            #note_is_chording = False
            #for j in range(len(self.streams)):
                #val = self.streams[j].get_next_value()
                #if self.streams[j].is_chording:
                    #note_is_chording = True
                #note.append(val)
            #if not note_is_chording:
                #self.curtime = self.curtime + self.rhythmstream.get_next_value()
                
            #line = "i"
            #for x in range(len(note)):
                #line = line + (str(note[x]) + " ")
            #if f == None:
                #print(line)
            #else:
                #f.writelines(line + "\n")
                    
            #self.note_count = self.note_count + 1
        if f != None:
            f.close()

    def generate_notes(self):
        self.note_count = 0
        self.curtime = self.starttime
        ret_lines = []
        
        #for gendx in range(len(self.gen_lines)):
            #ret_lines.append(self.gen_lines[gendx])
            #self.notes.append(self.gen_lines[gendx])
        while self.note_count < self.note_limit:
            note = Event()
            note.instr = self.instr
            note.starttime = self.curtime
            note.dur = self.durstream.get_next_value()
            #note = [self.instr, self.curtime, self.durstream.get_next_value()]
            
            note_is_chording = False
            rhythm = None
            for j in range(len(self.streams)):
                # todo - make a stream subclass handle rhythm, pitch and rhythm/indx duties by implementing
                #   get_next_value. It's a special kind of event that has this cross-pfield relationship,
                #   loopindx case is one example. Interval case needs to be explored as well.
                val = self.streams[j].get_next_value()

                #do special case for tuple here - note should be a dictionary of fixed keys so we can special case/set things like rhythm, dur, pitch and starttime
                if(isinstance(val, dict)):
                    for item in val.iterkeys():
                        if(item == "rhy"):
                            rhythm = utils.rhythm_to_duration(val[item], self.streams[j].tempo)
                        if(item == "dur"):
                            note.dur = val[item]
                        if(item == "indx"):
                            note.indx = val[item]
                        if(item == "freq"):
                            result = utils.pc_to_freq(val[item], self.streams[j].current_octave)
                            self.streams[j].current_octave = result["octave"]
                            note.freq = result["value"]
                else:
                    note.pfields.append(str(val))
                            
                if self.streams[j].is_chording:
                    note_is_chording = True
            if not note_is_chording:
                if rhythm != None:
                    self.curtime = self.curtime + rhythm
                else:
                    self.curtime = self.curtime + self.rhythmstream.get_next_value()

            #line = "i"
            #for x in range(len(note)):
                #line = line + (str(note[x]) + " ")
                
            ret_lines.append(str(note) + "\n")
            self.notes.append(str(note) + "\n")
                    
            self.note_count = self.note_count + 1
            if((note.starttime + note.dur) > self.score_dur):
                self.score_dur = (note.starttime + note.dur)

        return ret_lines
    

    def generate_score_string(self):
        retstring = ""
        for x in range(len(self.gen_lines)):
            retstring += self.gen_lines[x]
        for y in range(len(self.notes)):
            retstring += self.notes[y]
        for x in range(len(self.end_lines)):
            retstring += self.end_lines[x]
        return retstring
