#class itemstream:
    #item = None
    #curItem = None
    #isChording, isTop, endOfSequence = 0,0,0
    #indx = 0
    #modifier = "SEQUENCE"
    #state = "CUR"
    #itemStream = []
    #def __init__(self, *args):
        #if(len(args) == 1)
           #self.itemStream = args[0] 
        #else:
            #for x in args:
                #if(isinstance(x,ItemStream)):
                    #self.itemStream.append(x)
                #elif(isinstance(x,list)):
                                    
                #else:
                    #self.itemStream = x
                    #self.itemStream.append(self)
    
    #def addItemStream(itemStream)
        #self.itemStream.append(itemStream)       
       
    #def resetStreams()
        #indx = 0 
import utils
import random
import score
########################################################################
class itemstream:
    """"""

    #----------------------------------------------------------------------
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
                
        return ret

########################################################################

    
            
#rhythms = itemstream(['q.','q.','q'],'heap', tempo=240)
#rhythms.notetype = 'rhythm'
#amps = itemstream([1])
#pitches = itemstream(['c3','e',['c','e','g'],'c4','e',['c','e','g']])
#pitches.notetype = 'pitch'

#s = score.score(rhythms,[amps,pitches], note_limit=120)
#s.gen_lines = [';sine','f 1 0 16384 10 1',';saw','f 2 0 256 7 0 128 1 0 -1 128 0',';pulse','f 3 0 256 7 1 128 1 0 -1 128 -1']
#s.durstream = itemstream([.1])
##s.generate_score("/Users/benmca/Documents/src/sandbox/python/test.sco")
##s.generate_score()
#s.generate_notes()

#rhythms = itemstream(['e.','e.','e'],'heap', tempo=440)
#rhythms.notetype = 'rhythm'
#s.rhythmstream = rhythms
##reset time
#s.starttime = 0.0
#s.curtime = s.starttime
#s.generate_notes()
##for x in s.notes:
    ##print(x)
    
#s.generate_score("/Users/benmca/Documents/src/sandbox/python/test.sco")
    
    
    