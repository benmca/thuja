from thuja.itemstream import notetypes
from thuja.itemstream import streammodes
from thuja.itemstream import Itemstream
from thuja.generator import Generator
from thuja.generator import keys
from collections import OrderedDict
from thuja import utils
import copy
import ctcsound
the_tempo = 120

rhythms = Itemstream(
    'e e q e s s s s s s e e e e q q'.split(),
    streammode=streammodes.sequence,
    tempo=the_tempo,
    notetype=notetypes.rhythm)

amps = Itemstream([1])

pitches = Itemstream('a4 c e r a4 a a c a4 g r a4 a a a r'.split(),
    streammode=streammodes.heap,
    notetype=notetypes.pitch
)

g = Generator(
    streams=OrderedDict([
        (keys.instrument, 1),
        (keys.rhythm, rhythms),
        (keys.duration, Itemstream([.1])),
        (keys.amplitude, 1),
        (keys.frequency, pitches),
        (keys.pan, 45),
        (keys.distance, 10),
        (keys.percent, .1),
        ("channel", 1)
    ]),
    pfields=None,
    gen_lines = [';sine\n',
               'f 1 0 16384 10 1\n',
               ';saw',
               'f 2 0 256 7 0 128 1 0 -1 128 0\n',
               ';pulse\n',
               'f 3 0 256 7 1 128 1 0 -1 128 -1\n']
)
g.time_limit=120

g2 = copy.deepcopy(g)
g2.streams[keys.rhythm] = Itemstream(['e'],'sequence', tempo=the_tempo, notetype=notetypes.rhythm)
g2.streams[keys.frequency] = Itemstream(['a3']*8+'a3 c d e r r r r'.split(), notetype=notetypes.pitch)
g2.streams[keys.pan] = Itemstream([0,90], 'sequence')
g2.streams[keys.distance] = Itemstream([1], 'sequence')
g2.streams[keys.percent] = Itemstream([0], 'sequence')
g2.streams[keys.amplitude] = Itemstream([.25])
g.add_generator(g2)


g.generate_notes()

g.end_lines = ['i99 0 ' + str(g.score_dur+10) + '\n']

with open ("sine+midiout+channelparam-pulse.orc", "r") as f:
    orc_string=f.read()
score_string = g.generate_score_string()
with open ("test.sco", "w") as sco:
    sco.write(score_string)
cs = ctcsound.Csound()
# cs.SetMIDIOutput('0')
cs.setOption('-odac')
# cs.SetOption('-v')
# cs.SetOption('-M0'    )
cs.setOption('-Q1')
cs.setOption('--midi-devices=out')
cs.setOption('-b64')
cs.setOption('-B64')
cs.compileOrc(orc_string)
cs.readScore(score_string)

cs.start()
cs.perform()
cs.reset()
# while cs.PerformKsmps() == 0:
#     pass

# cs.Stop()
#
# ret = cs.compile_("csound", "-o", "dac", "-Q", "0", "-b", "64", "-B", "64", "examples/02-a.orc", "examples/02-a.sco")
# if ret == ctcsound.CSOUND_SUCCESS:
#     cs.perform()
#     cs.reset()


# perfThread = csnd6.CsoundPerformanceThread(cs)
# perfThread.Play()
# cs.Start()             # When compiling from strings, this call is necessary before doing any performing
#
# t = csnd6.CsoundPerformanceThread(cs)  # Create a new CsoundPerformanceThread, passing in the Csound object
# t.Play()              # starts the thread, which is now running separately from the main thread. This
#                       # call is asynchronous and will immediately return back here to continue code
#                       # execution.
# t.Join()              # Join will wait for the other thread to complete. If we did not call Join(),
#                       # after t.Play() returns we would immediate move to the next line, c.Stop().
#                       # That would stop Csound without really giving it time to run.
#
# cs.Stop()              # stops Csound
# cs.Cleanup()           # clean up Csound; this is useful if you're going to reuse a Csound instance
