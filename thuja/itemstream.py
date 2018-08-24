from thuja import utils
import random
import time

class Notetypes:
    """Values for initialization of notetype attribute of Itemstreams

    Attributes:
        rhythm: stream uses rhythm-string notation and stream tempo to generate numeric rhythm values.
        pitch: stream uses pitch-class notation (ie: c4, cs, cf) to generate numeric frequency values.
        number: stream uses numbers to generate numeric rhythm values.
    """

    def __init__(self):
        self.rhythm = 'rhythm'
        self.pitch = 'pitch'
        self.number = 'number'
        self.path = 'path'


class Streammodes:
    """Values for initialization of streammode attribute of Itemstreams

    Attributes:
        sequence: stream will generate values in sequence.
        random: for each call to get_next_value(), stream will return a random item from values.
        heap: for each call to get_next_value(), stream will return a random item from values. No value is
            repeated until all others have been returned.
    """

    def __init__(self):
        self.sequence = 'sequence'
        self.heap = 'heap'
        self.random = 'random'


streammodes = Streammodes()
notetypes = Notetypes()


class Itemstream:
    """A container for streams of musical data.

    Attributes:
        values: (:obj:`list` of :obj:`str`):
        streammode (str): See Streammode doc. Default is streammodes.sequence
        notetype (str): See Notetype doc. Default is notetypes.number
        tempo=120 (int): tempo value used in streams generating rhythms
        tag (str, optional): optional tag for identifying the stream
        mapping_keys (:obj:`dict` of :obj:`str`):
        mapping_lists=None
    """

    def __init__(self, values=None,
                 streammode=streammodes.sequence,
                 notetype=notetypes.number,
                 tempo=120,
                 tag='',
                 mapping_keys=None,
                 mapping_lists=None,
                 seed=int(time.time())):

        """Constructor"""
        self.values = values
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
        self.note_count = 0
        self.tag = tag

        self.current_value = None
        # save seed to repeat random operations
        self.seed = seed
        self.rand = random.Random()
        self.rand.seed(self.seed)

        assert not isinstance(values, str)

        if mapping_keys is not None and mapping_lists is not None:
            self.values = []
            map_length = 0
            map_index = 0
            # find the longest list
            for x in range(len(mapping_lists)):
                if len(mapping_lists[x]) > map_length:
                    map_length = len(mapping_lists[x])
                    map_index = x

            for i in range(map_length):
                item = {}
                for keydx in range(len(mapping_keys)):
                    key = mapping_keys[keydx]
                    item[key] = mapping_lists[keydx][i % len(mapping_lists[keydx])]
                self.values.append(item)

    def get_next_value(self):
        ret = None
        # global myScore

        if isinstance(self.values[self.index], list):
            if not self.is_chording:
                # initial case
                self.is_chording = True
                self.chording_index = 0
            if self.notetype == notetypes.number:
                ret = self.values[self.index][self.chording_index]
            elif self.notetype == notetypes.pitch:
                result = utils.pc_to_freq(self.values[self.index][self.chording_index], self.current_octave)
                ret = result["value"]
                self.current_octave = result["octave"]
            elif self.notetype == notetypes.path:
                # ret = '"' + result["value"] + '"'
                ret = '"' + "hi" + '"'
                pass
            elif self.notetype == notetypes.rhythm:
                if isinstance(self.tempo, list):
                    ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index],
                                                   self.tempo[self.note_count % len(self.tempo)])
                else:
                    ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index], self.tempo)
            # consider adding a duple type for loopindx...
            # elif self.notetype == 'duple':
            #     if isinstance(self.tempo, list):
            #         ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index],
            #                                        self.tempo[self.note_count % len(self.tempo)])
            #     else:
            #         ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index], self.tempo)

            ## we need a way to say dur = rhythm * 2

            self.chording_index = self.chording_index + 1
            if self.chording_index == len(self.values[self.index]):
                self.is_chording = False
                self.chording_index = 0
                if self.streammode == streammodes.sequence:
                    if self.index < len(self.values) - 1:
                        self.index = self.index + 1
                    else:
                        self.index = 0
                elif self.streammode == streammodes.heap:
                    added = False
                    if len(self.heapdict) == len(self.values):
                        self.heapdict.clear()
                    while not added:
                        self.index = self.rand.randrange(0, len(self.values))
                        if (self.index in self.heapdict) == False:
                            added = True
                            self.heapdict.add(self.index)
                elif self.streammode == streammodes.random:
                    self.index = self.rand.randrange(0, len(self.values))

        elif isinstance(self.values[self.index], Itemstream):
            self.is_chording = False
            # nested stream case
            pass
        else:
            self.is_chording = False
            # default case
            if self.notetype == notetypes.number:
                ret = self.values[self.index]
            elif self.notetype == notetypes.path:
                # ret = '"' + result["value"] + '"'
                ret = '"' + self.values[self.index] + '"'
            elif self.notetype == notetypes.pitch:
                result = utils.pc_to_freq(self.values[self.index], self.current_octave)
                ret = result["value"]
                self.current_octave = result["octave"]
            elif self.notetype == notetypes.rhythm:
                if isinstance(self.tempo, list):
                    ret = utils.rhythm_to_duration(self.values[self.index],
                                                   self.tempo[self.note_count % len(self.tempo)])
                elif callable(self.tempo):
                    ret = utils.rhythm_to_duration(self.values[self.index],
                                                   self.tempo())
                else:
                    ret = utils.rhythm_to_duration(self.values[self.index], self.tempo)

            if self.streammode == streammodes.sequence:
                if self.index < len(self.values) - 1:
                    self.index = self.index + 1
                else:
                    self.index = 0
            elif self.streammode == streammodes.heap:
                added = False
                if len(self.heapdict) == len(self.values):
                    self.heapdict.clear()

                while not added:
                    self.index = self.rand.randrange(0, len(self.values))
                    if not (self.index in self.heapdict):
                        added = True
                        self.heapdict.add(self.index)

            elif self.streammode == streammodes.random:
                self.index = self.rand.randrange(0, len(self.values))
                pass

        self.note_count += 1
        self.current_value = ret
        return ret
