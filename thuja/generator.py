from thuja.itemstream import Itemstream
from thuja.new_event import NewEvent
from thuja import utils


class StreamKey:

    def __init__(self):
        # the usual suspects
        self.instrument = 'instr'
        self.start_time = 'start_time'
        self.duration = 'dur'
        self.rhythm = 'rhy'
        self.amplitude = 'amp'
        self.frequency = 'freq'

        # support loopindx
        self.index = 'indx'

        # locsig support
        self.pan = 'pan'
        self.distance = 'dist'
        self.percent = 'pct'



class Generator:

    def __init__(self, note_limit=16,
                 start_time=0.0,
                 streams=None,
                 pfields=None,
                 post_processes=[],
                 init_context={},
                 gen_lines=[]):

        self.start_time = start_time
        self.streams = streams
        self.note_limit = note_limit

        self.cur_time = 0.0
        self.time_limit = 0

        self.gen_lines = gen_lines
        self.note_count = 0
        self.notes = []
        self.end_lines = []
        self.score_dur = 0

        self.pfields = pfields
        if self.pfields is None:
            self.pfields = list(self.streams.keys())
            self.pfields.insert(1, keys.start_time)

        # a place to put stuff to refer to in callables - not sure best way forward here
        self.context = init_context
        self.post_processes = post_processes
        self.generators = []


    def update_stream(self, key, stream):
        self.streams[key] = stream
        return self

    def generate_score(self, filename=None):
        self.note_count = 0
        self.cur_time = self.start_time

        f = None
        if filename is not None:
            f = open(filename, 'w')

        for gendx in range(len(self.gen_lines)):
            if f is None:
                print(self.gen_lines[gendx] + "\n")
            else:
                f.writelines(self.gen_lines[gendx] + "\n")

        for x in range(len(self.notes)):
            if f is None:
                print(self.notes[x])
            else:
                f.writelines(self.notes[x])

        for x in range(len(self.end_lines)):
            if f is None:
                print(self.end_lines[x] + "\n")
            else:
                f.writelines(self.end_lines[x] + "\n")

        if f is not None:
            f.close()
        return self

    def generate_notes(self):
        self.note_count = 0
        self.cur_time = self.start_time
        ret_lines = []

        while (self.note_limit > 0 and (self.note_count < self.note_limit)) or (self.time_limit > 0):
            note = NewEvent(pfields=self.pfields)
            note.pfields[keys.start_time] = self.cur_time

            # todo - validate we're ok to roll: we have at least an instr and rhythm
            note_is_chording = False
            rhythm = None
            for key in self.streams.keys():
                if key is keys.rhythm:
                    continue
                # this could be a literal or ItemStream
                if not isinstance(self.streams[key], Itemstream) and not callable(self.streams[key]):
                    note.pfields[key] = self.streams[key]
                elif isinstance(self.streams[key], Itemstream):
                    value = self.streams[key].get_next_value()

                    # support mapping stream
                    # i.e.  [{"rhy": "h", "indx": 5.54}, {"rhy": "h", "indx": 6.67}, {"rhy": "h", "indx": 8.0}]
                    if isinstance(value, dict):
                        for item in value.keys():
                            if item == keys.rhythm:
                                rhythm = utils.rhythm_to_duration(value[item], self.streams[key].tempo)
                            elif item == "freq":
                                result = utils.pc_to_freq(value[item], self.streams[key].current_octave)
                                self.streams[item].current_octave = result["octave"]
                                note.pfields[item] = result["value"]
                            else:
                                note.pfields[item] = value[item]
                    else:
                        note.pfields[key] = value

                    if self.streams[key].is_chording:
                        note_is_chording = True

            for item in self.post_processes:
                if callable(item):
                    # 9.2.2017 - I don't see why we were passing context back, when caller would have a ref already
                    # item(note, self.context)
                    item(note)

            if not note_is_chording:
                if rhythm is not None:
                    self.cur_time = self.cur_time + rhythm
                    note.rhythm = rhythm
                elif note.rhythm is not None:
                    self.cur_time = self.cur_time + note.rhythm
                else:
                    rhythm = self.streams[keys.rhythm].get_next_value()
                    self.cur_time = self.cur_time + rhythm
                    note.rhythm = rhythm

            # after setting primitives and ItemStream-driven values, evaluate functions
            for key in self.streams.keys():
                # this could be a literal or ItemStream
                if callable(self.streams[key]):
                    value = self.streams[key](note)
                    note.pfields[key] = value

            if self.time_limit > 0 and self.cur_time > self.time_limit:
                break
            else:
                ret_lines.append(str(note) + "\n")
                self.notes.append(str(note) + "\n")
                self.note_count += 1
                if (note.pfields[keys.start_time] + note.pfields[keys.duration]) > self.score_dur:
                    self.score_dur = (note.pfields[keys.start_time] + note.pfields[keys.duration])

        for generator in self.generators:
            generator.start_time += self.start_time
            if self.time_limit > 0 and generator.time_limit == 0:
                generator.time_limit = self.time_limit
            if self.note_limit > 0 and generator.note_limit == 0:
                generator.note_limit = self.note_limit
            generator.generate_notes()
            self.notes.extend(generator.notes)
            if generator.score_dur > self.score_dur:
                self.score_dur = generator.score_dur

        return self

    def add_generator(self, other):
        if isinstance(other, Generator):
            self.generators.append(other)

    def add_bars_to_starttime(self, bars=1, beats=0, num=4, denom=4, tempo=120):
        beat_duration = 60.0/tempo
        self.start_time += (beat_duration*num*bars)+(beat_duration*beats)

    def generate_score_string(self):
        retstring = ""
        for x in range(len(self.gen_lines)):
            retstring += self.gen_lines[x]
        for y in range(len(self.notes)):
            retstring += self.notes[y]
        for x in range(len(self.end_lines)):
            retstring += self.end_lines[x]
        return retstring

keys = StreamKey()