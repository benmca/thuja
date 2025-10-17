import random
import sys
from operator import truediv

from thuja.streamkeys import StreamKey, keys
from thuja.itemstream import Itemstream
from thuja.itemstream import notetypes

from thuja.event import Event
from thuja import utils
from collections import OrderedDict
import copy
import funcsigs
import threading
import time


class NoteGenerator:

    def __init__(self, note_limit=0,
                 start_time=0.0,
                 streams=None,
                 pfields=None,
                 post_processes=[],
                 init_context=None,
                 gen_lines=[]):
        """
        Initializes a Generator object.ˆ

        Parameters:
            note_limit (int): The maximum number of notes to generate. Defaults to 16.
            start_time (float): The starting time of the generator. Defaults to 0.0.
            streams (OrderedDict): A dictionary of streams. Defaults to None.
            pfields (list): A list of parameter fields. Defaults to None.
            post_processes (list): A list of post-processing functions to be applied after
                generating notes. Defaults to an empty list.
            init_context (dict): An initial context for the generator, designed to be leveraged by post_processes but
                can be referenced wherever. Defaults to an empty dictionary.
            gen_lines (list): A list of strings (csound score events) to append to generated score string. Defaults to an empty list.
        """
        self.start_time = start_time
        self.streams = None
        if isinstance(streams, OrderedDict):
            self.streams = streams
        elif streams is not None:
            self.streams = OrderedDict(streams)
        self.note_limit = note_limit

        self.cur_time = 0.0
        # absolute time limit
        self.time_limit = 0
        # in cases where this is a child generator, and the start time is offset by the parent's start time,
        #   generator_dur can be used to set a relative time limit after that offset occurs in generate_notes
        self.generator_dur = 0

        self.gen_lines = gen_lines
        self.note_count = 0
        self.notes = []
        self.end_lines = []
        self.score_dur = 0

        self.pfields = pfields
        if pfields is None:
            if self.streams is not None:
                self.pfields = list(self.streams.keys())
                self.pfields.insert(1, keys.start_time)

        # a place to put stuff to refer to in callables
        if init_context is not None:
            self.context = init_context
        else:
            self.context = {}

        # an array of callables, called in sequence after each note is initialized.
        self.post_processes = post_processes

        self.generators = []

    def with_streams(self, streams):
        if isinstance(streams, OrderedDict):
            self.streams = streams
        if streams is None:
            pass
        else:
            self.streams = OrderedDict(streams)

    def with_pfields(self, pfields):
        self.pfields = pfields
        return self

    def deepcopy(self):
        result = copy.deepcopy(self)
        result.streams = OrderedDict()
        for k, v in self.streams.items():
            # setattr(result, k, deepcopy(v, memo))
            result.streams.__setitem__(k, copy.deepcopy(v))
        return result

    def update_stream(self, key, stream):
        self.streams[key] = stream
        return self

    def generate_score(self, filename=None):
        self.note_count = 0
        self.notes = []
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

    def clear_notes(self):
        self.note_count = 0
        self.notes = []
        self.score_dur = 0

    def generate_notes(self):
        self.note_count = 0
        self.cur_time = self.start_time
        ret_lines = []
        self.notes = []

        # todo - audit this, but looks like I intended note_limit to trump time_limit
        while (self.note_limit > 0 and (self.note_count < self.note_limit)) or (self.time_limit > 0):
        # we've got options - this condition says whichever one we get to first wins
        # while (self.note_limit > 0 and (self.note_count < self.note_limit)) or ((self.time_limit > 0) and self.cur_time < self.time_limit):
            note = Event(pfields=self.pfields, start_time=self.cur_time)
            note_is_chording = False
            rhythm = None


            # for each key in the stream e.g. instr, dur, amp, freq, etc.
            for key in self.streams.keys():
                # rhythm is a special case. We deal with this case below.
                if key is keys.rhythm:
                    continue
                # 2025.03.23 old comment: this could be a literal or ItemStream
                # 2025.03.23 Streams are either ItemStreams, callables (lambdas, i.e. dur = .5*rhythm) or string or float literals
                #   todo: validate that you aren't breaking this in Line initialization from a literal. It simplifies to
                #       make everything either an itemstream or callable.

                if not isinstance(self.streams[key], Itemstream) and not callable(self.streams[key]):
                #     # first case: if it's not an itemstream or callable, assume it's a literal.
                #     # 2025.03.25 This case isn't reachable given current ctor of ItemStream- should we do anything with this i.e. log?
                #   2025.03.25 This case --is--reachable if you call Generator ctor with list of duples, like the old examples do.
                    note.pfields[key] = self.streams[key]

                elif isinstance(self.streams[key], Itemstream):
                    # second  case: itemstream.  Get the next value, if it's a dictionary it's a special case to support mapping streams specifically.
                    value = self.streams[key].get_next_value()

                    # support mapping stream - more tests needed here.
                    # i.e.  [{"rhy": "h", "indx": 5.54}, {"rhy": "h", "indx": 6.67}, {"rhy": "h", "indx": 8.0}]
                    #   2025.03.25: I think this is old - you decided not to support mappings this way. They are special configs on the item stream.
                    #           todo or: is this what the mapping lists look like after ctor of an item stream is called with
                    #                   mapping_keys and mapping_lists set?
                    #       this is a different flavor of mapping keys though. Here you can use simple mapping to say
                    #           "every time it's an either: - make it loud" or " - map it to a given sound" etc. This shouldn't be called mapping
                    #            todo write an example leveraging this.

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
                        # if not a dict, set the value.
                        note.pfields[key] = value

                    # in get_next_value, the stream may be processing a list. there should only be one list (one item to chord from) at a time,
                    #   or else weird (and maybe fun) stuff will happen.
                    if self.streams[key].is_chording:
                        note_is_chording = True


            # if we are not chording, move time forward by the rhythm value and save it.
            if not note_is_chording:
                if rhythm is not None:
                    # in this case, rhythm was set by the mapping dictionary case above.
                    self.cur_time = self.cur_time + rhythm
                    note.rhythm = rhythm
                elif note.rhythm is not None:
                    # 2025.03.23: in this case..... note.rhythm has somehow been set. This may be a remnant of an example
                    #   where the rhythm was set by a callable before this condition.
                    self.cur_time = self.cur_time + note.rhythm
                elif keys.rhythm in self.streams and self.streams[keys.rhythm] is not None:
                    # 2024.01.31 added this clause instead of this being the default.
                    #   test_generator was tripping here. A todo might be to be prescriptive in checking that
                    #   if rhy isn't set in post_processes OR here, we should error out.
                    # 2025.03.23: another old comment ^^
                    #   todo: write some tests targeting the specific cases we want to support.
                    rhythm = self.streams[keys.rhythm].get_next_value()
                    self.cur_time = self.cur_time + rhythm
                    note.rhythm = rhythm
            else:
                # 2025.03.12 Trying to set rhythm in chording scenarioes, so that post_processes or callables can refer to rhythm.
                # ..adapted from Itemstream.get next value.
                # if isinstance(self.streams[keys.rhythm].tempo, list):
                #     note.rhythm = utils.rhythm_to_duration(self.streams[keys.rhythm].values[self.streams[keys.rhythm].index][self.streams[keys.rhythm].chording_index],
                #                                    self.tempo[self.streams[keys.rhythm].note_count % len(self.tempo)])
                # else:
                if isinstance(self.streams[keys.rhythm].values[self.streams[keys.rhythm].index], list):
                    print("in chording case, rhythm stream must be a flat list - current value is a list (Nested list case)")
                    assert False

                # here, we handle the case of tempo changing over time via list. Same logic as 'if isinstance(self.tempo, list):'
                # case in Itemstream
                tempo = self.streams[keys.rhythm].tempo

                if isinstance(self.streams[keys.rhythm].tempo, list):
                    tempo = self.streams[keys.rhythm].tempo[self.streams[keys.rhythm].note_count % len(self.streams[keys.rhythm].tempo)]

                note.rhythm = utils.rhythm_to_duration(self.streams[keys.rhythm].values[self.streams[
                    keys.rhythm].index], tempo)


            # 2024.01.07 - not sure if this is an issue, but I'm changing this so callables can access rhythm
            #   did I think we would want to do post-processing BEFORE curtime is set or something?

            for key in self.streams.keys():
                # this could be a literal or ItemStream
                if callable(self.streams[key]):
                    value = self.streams[key](note)
                    note.pfields[key] = value

            # the note is fully initialized. Run the list of post process in order.
            for item in self.post_processes:
                if callable(item):
                    if len(funcsigs.signature(item).parameters) > 1:
                        item(note, self.context)
                    else:
                        item(note)

            # 2025.03.31: moving this back to precede post_processing
            #           legacy comments below:
            # after setting primitives and ItemStream-driven values, evaluate lambdas / callables in streams.
            # 2025.03.23 This is biased towards cases where we know we'd want to eval callables after post-processes.
            # for key in self.streams.keys():
            #     # this could be a literal or ItemStream
            #     if callable(self.streams[key]):
            #         value = self.streams[key](note)
            #         note.pfields[key] = value

            # Enforce time limit.
            if self.cur_time > self.time_limit > 0:
                break
            else:
                ret_lines.append(str(note) + "\n")
                self.notes.append(str(note) + "\n")
                self.note_count += 1
                # update the duration of the score.
                if (note.pfields[keys.start_time] + note.pfields[keys.duration]) > self.score_dur:
                    self.score_dur = (note.pfields[keys.start_time] + note.pfields[keys.duration])

        for g in self.generators:
            # for any child generator, we make a few assumptions. One, the start time of the child is relative
            #   to the parent.
            #   Second, that the parent's limits should always fall to children if they are not set.
            #   If the child's time_limit is set, it's treated as absolute time limit, despite the fact the start time
            #   is relative to the parent. For this case, we introduce the generator_duration, which is a cue to this
            #   condition that the time_limit can be set relative to the start_time.
            #   2025.04.01 - I type this out as a note for myself, to make these side effects more explicit.
            if g.generator_dur > 0:
                g.time_limit = g.start_time + g.generator_dur
                # assume here that g.start_time is absolute and should not be offset.
            else:
                g.start_time += self.start_time
            if self.time_limit > 0 and g.time_limit == 0:
                g.time_limit = self.time_limit
            if self.note_limit > 0 and g.note_limit == 0:
                g.note_limit = self.note_limit
            g.generate_notes()
            self.notes.extend(g.notes)
            if g.score_dur > self.score_dur:
                self.score_dur = g.score_dur


        # sort by start time - remember, these are string representations of the note.
        self.notes.sort(key=lambda note:float(note.split()[1]))

        return self

    def add_generator(self, other):
        if isinstance(other, NoteGenerator):
            self.generators.append(other)

    def add_bars_to_starttime(self, bars=1, beats=0, num=4, denom=4, tempo=120):
        beat_duration = 60.0 / tempo
        self.start_time += (beat_duration * num * bars) + (beat_duration * beats)

    def generate_score_string(self):
        retstring = ""
        for x in range(len(self.gen_lines)):
            retstring += self.gen_lines[x] + '\n'
        for y in range(len(self.notes)):
            retstring += self.notes[y]
        for x in range(len(self.end_lines)):
            retstring += self.end_lines[x] + '\n'
        return retstring

    def send_gens_to_udp(self, sock, UDP_IP="127.0.0.1", UDP_PORT=8088):
        for x in range(len(self.gen_lines)):
            sock.sendto(("&" + self.gen_lines[x]).encode(), (UDP_IP, UDP_PORT))

    def send_notes_to_udp(self, sock, UDP_IP="127.0.0.1", UDP_PORT=8088):
        for x in range(len(self.notes)):
            sock.sendto(("&" + self.notes[x]).encode(), (UDP_IP, UDP_PORT))

    def tempo(self):
        return self.streams[keys.rhythm].tempo

    def set_streams_to_seed(self, seed):
        for s in self.streams.values():
            if isinstance(s, Itemstream):
                s.set_seed(seed)


class Line(NoteGenerator):

    def __init__(self):
        super().__init__()
        self.streams=OrderedDict([
            (keys.instrument, Itemstream([1])),
            (keys.duration, Itemstream([1])),
            (keys.rhythm, Itemstream(['q'], notetype=notetypes.rhythm)),
            (keys.amplitude, Itemstream([1])),
            (keys.frequency, Itemstream([1])),
            (keys.pan, Itemstream([45])),
            (keys.distance, Itemstream([10])),
            (keys.percent, Itemstream([.01]))
        ])
        self.pfields=[
            keys.instrument,
            keys.start_time,
            keys.duration,
            keys.amplitude,
            keys.frequency,
            keys.pan,
            keys.distance,
            keys.percent
        ]

        self.gen_lines = [';sine\n',
                               'f 1 0 16384 10 1\n',
                               ';saw',
                               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
                               ';pulse\n',
                               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
        self.note_limit = 0


    def set_stream(self, k, v):
        if isinstance(v, Itemstream):
            self.streams[k] = v
        elif isinstance(v, str):
            self.streams[k] = Itemstream(v.split())
        elif isinstance(v, list):
            self.streams[k] = Itemstream(v)
        elif callable(v):
            self.streams[k] = v

        else:
            # assume this is an single item string and pass value through to ItemStream
            self.streams[k] = Itemstream(v)

    def with_rhythm(self, v):
        self.rhythms(v)
        return self

    # for brevity, pfield setters
    # 2024.05.27: for rhythms, I added this safeguard since I seem to forget to set all the things for rhythms to
    #   be generated as I work through the fluent interface.
    def rhythms(self, v):
        if isinstance(v, str) or isinstance(v, list):
            self.set_stream(StreamKey().rhythm, Itemstream(v, notetype=notetypes.rhythm))
        elif isinstance(v, Itemstream):
            # don't assume this is notetypes==rhythm - this could be numbers
            # v.notetype = notetypes.rhythm
            self.set_stream(StreamKey().rhythm, v)
        else:
            raise Exception("rhythm not set - supply ItemStream, string, or list")
        return self

    def with_tempo(self, x):
        return self.tempo(x)

    def tempo(self, x):
        self.streams[keys.rhythm].tempo = x
        return self

    def with_instr(self, v):
        return self.instr(v)

    def instr(self, v):
        self.set_stream(StreamKey().instrument, v)
        return self


    def with_duration(self, v):
        return self.durs(v)

    def durs(self, v):
        self.set_stream(StreamKey().duration, v)
        return self

    def with_amps(self, v):
        return self.amps(v)

    def amps(self, v):
        self.set_stream(StreamKey().amplitude, v)
        return self

    def with_pitches(self, v):
        return self.pitches(v)

    def pitches(self, v):
        if isinstance(v, str) or isinstance(v, list):
            self.set_stream(StreamKey().frequency, Itemstream(v, notetype=Notetypes().pitch))
        elif isinstance(v, Itemstream):
            v.notetype = notetypes.pitch
            self.set_stream(StreamKey().frequency, v)
        else:
            raise Exception("pitches not set - supply ItemStream, string, or list")
        return self

    def with_freqs(self, v):
        return self.freqs(v)

    def freqs(self, v):
        self.set_stream(StreamKey().frequency, v)
        return self

    def with_pan(self, v):
        return self.pan(v)

    def pan(self, v):
        self.set_stream(StreamKey().pan, v)
        return self

    def with_dist(self, v):
        return self.dist(v)

    def dist(self, v):
        self.set_stream(StreamKey().distance, v)
        return self

    def with_percent(self, v):
        return self.pct(v)

    def pct(self, v):
        self.set_stream(StreamKey().percent, v)
        return self

    def randomize(self):
        seed = random.Random().randint(0, sys.maxsize)
        self.set_streams_to_seed(seed)
        print(str(seed))
        return self

    def with_index(self, v):
        return self.index(v)

    def index(self, v):
        self.set_stream(StreamKey().index, v)
        return self


    def setup_index_params_with_file(self, filename):
        self.set_stream('orig_rhythm', .01)
        self.set_stream('inst_file', ['\"' + filename + '\"'])
        self.set_stream('fade_in', .0001)
        self.set_stream('fade_out', .01)
        self.pfields += [keys.index, 'orig_rhythm', 'inst_file', 'fade_in', 'fade_out']
        return self

    def g(self):
        self.generate_notes()
        return self


class NoteGeneratorThread(threading.Thread):

    def __init__(self, g, cs, cpt, sleep_interval=.0001):
        self.g = g
        self.cs = cs
        self.cpt = cpt
        self.sleep_interval = sleep_interval
        self.stop_event = threading.Event()
        self.thread = threading.Thread.__init__(self)
        self.lock = threading.Lock()
        return

    def run(self):
        g = self.g
        cs = self.cs
        cpt = self.cpt
        sleep_interval = self.sleep_interval
        g.thread_started = True

        # automatically generate notes if not already generated
        # if g.notes is None or len(g.notes) < 1:
        #     g.generate_notes()

        arbitrary_score_time = 0
        while not self.stop_event.is_set():
            score_time = cs.scoreTime()
            # if arbitrary_score_time < g.time_limit:
                # print("window: scoretime: " + str(arbitrary_score_time) + ", to " + str(arbitrary_score_time + sleep_interval))
            # print("score time: " + str(score_time))

            if(self.lock.locked() == False):
                self.lock.acquire()
                # for note in [note for note in g.notes if float(note.split()[1]) >= arbitrary_score_time and float(note.split()[1]) < (arbitrary_score_time + sleep_interval)]:
                for note in [note for note in g.notes if
                             float(note.split()[1]) >= arbitrary_score_time and float(note.split()[1]) < (
                                     score_time)]:
                    # print(str(note))
                    n = note.split()
                    n[1] = '0.0'
                    new_note = '\t'.join(n)
                    cpt.inputMessage(new_note)
                self.lock.release()
            arbitrary_score_time = score_time
            time.sleep(sleep_interval)

        self.stop_event.clear()

    def gen(self):
        print(str(len(self.g.notes)) + " pre-copy.")
        temp = self.g.deepcopy()
        temp.generate_notes()
        print(str(len(temp.notes)) + " generated. Copying...")
        self.lock.acquire()
        self.g.notes = temp.notes
        self.lock.release()
        print(str(len(self.g.notes)) + " post-copy.")

        pass

