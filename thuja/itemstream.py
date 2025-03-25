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
        # 2025.03.23: todo resolve this with calls to ItemStream ctor.

        # if string, assume it's space-delimited items when creating item-streams
        if values and isinstance(values, str):
            self.values = values.split()
        if values and isinstance(values, list):
            self.values = values
        else:
            # assume this is an atomic item - single item stream.
            self.values = [values]

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

    def set_seed(self, seed):
        self.rand = random.Random()
        if seed is None:
            self.seed = self.rand.random()
        else:
            self.seed = seed
        self.rand.seed(self.seed)

    def get_next_value(self):
        ret = None

        # this first case is for chording. If the current item is a list (i.e. [e3, g, b] for a minor triad),
        #   this stream click forward through the list, setting is_chording to true in the process.
        #   the generator calling get_next_value will keep the other pfields constant (including rhythm)
        #   until is_chording is false.  For example, the start time of each of the chorded notes stays the same
        #   until is_chording is false.
        if isinstance(self.values[self.index], list):
            if not self.is_chording:
                # initial case - we flip to true and set the chording index to 0
                self.is_chording = True
                self.chording_index = 0

            # you can make chords of any type, not just pitch.
            if self.notetype == notetypes.number:
                ret = self.values[self.index][self.chording_index]
            elif self.notetype == notetypes.pitch:
                result = utils.pc_to_freq(self.values[self.index][self.chording_index], self.current_octave)
                ret = result["value"]
                self.current_octave = result["octave"]
            elif self.notetype == notetypes.path:
                ret = '"' + self.values[self.index][self.chording_index] + '"'
                pass
            elif self.notetype == notetypes.rhythm:
                if isinstance(self.tempo, list):
                    ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index],
                                                   self.tempo[self.note_count % len(self.tempo)])
                else:
                    ret = utils.rhythm_to_duration(self.values[self.index][self.chording_index], self.tempo)

            # job done, increment the chording_index - the index in the list
            self.chording_index = self.chording_index + 1

            if self.chording_index == len(self.values[self.index]):
                # the terminal case
                self.is_chording = False
                self.chording_index = 0

                # done with the list, we'll increment the index according to the streammode.
                #   this is copypasta'd below -
                #
                #   todo
                #    refactorrefactorrefactorrefactorrefactorrefactorrefactorrefactorrefactor
                #    refactorrefactorrefactorrefactorrefactorrefactorrefactorrefactorrefactor
                #    this into one method.

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
                        # there's probably a way to do this that's more concise, but it's clear what serial
                        #   operation is happening here.
                        self.index = self.rand.randrange(0, len(self.values))
                        if not (self.index in self.heapdict):
                            added = True
                            self.heapdict.add(self.index)
                elif self.streammode == streammodes.random:
                    self.index = self.rand.randrange(0, len(self.values))

        elif isinstance(self.values[self.index], Itemstream):
            # nested stream case
            # todo - work through nested itemstream until 'complete' then move ahead to next item.
            # 2025.03.23 until I implement this, this stream will be return None in this case.
            self.is_chording = False
            pass
        else:
            # proactively setting this to False.  I don't think this actually needs to happen, but at one point it
            #   probably addressed a hole in this algorithm.
            self.is_chording = False

            # default case - just give me the next value in the stream.
            #   todo refactor - this is the same as one of the conditions above.
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

            #   todo
            #    refactorrefactorrefactorrefactorrefactorrefactorrefactorrefactorrefactor
            #    refactorrefactorrefactorrefactorrefactorrefactorrefactorrefactorrefactor
            #    this into one method.

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
