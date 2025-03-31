class StreamKey:

    instrument = 'instr'
    start_time = 'start_time'
    duration = 'dur'
    rhythm = 'rhy'
    amplitude = 'amp'
    frequency = 'freq'

    # support loopindx
    index = 'indx'

    # locsig support
    pan = 'pan'
    distance = 'dist'
    percent = 'pct'

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


keys = StreamKey()
