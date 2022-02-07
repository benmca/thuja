import math

from thuja.utils import cycle, round_half_down

"""
Individual tones may be represented as a midi note (MidiNote), a pitch class (PitchClass), or a
frequency (float).
"""

SCALE = 12
SEMITONES = "C_D_EF_G_A_B"  # black piano keys (sharps/flats) are underscores


class MidiNote:
    """
    Midi notes count 12 notes between each doubling of Hertz, at a baseline of midi 69 equalling
    frequency 440.0 Hertz (and thus, for example, 880.0 Hertz is equivalent to midi 81).

    This program only handles frequencies down to around 8.42 -- all frequencies below that are
    midi 0.

    There is no upper limit given here, although midi 135 is the maximum frequency human ears can
    detect.

    A MidiNote acts like an integer for certain operations, allowing you to do basic math with it.
    For example:

        >>> from thuja import sounds
        >>> note = sounds.MidiNote(84)
        >>> note.PitchClass()
        PitchClass('C6')
        >>> (note + 2).PitchClass()
        PitchClass('D6')
        >>> (note / 2).PitchClass()
        PitchClass('F#2')
    """

    def __init__(self, note:int):
        self.note = note

    def __repr__(self):
        return f"MidiNote({self.note})"

    def __int__(self):
        return self.note

    # alternative creation methods
    @staticmethod
    def from_frequency(frequency:float):
        """Converts a frequency in Hertz to a midi note."""
        if frequency == 0:  # silence
            return MidiNote(0)

        unrounded = MidiNote.offset + math.log2(frequency / MidiNote.hertz) * SCALE

        # return a minimum of 0, and always round 0.5 down:
        return MidiNote(max(0, round_half_down(unrounded)))

    @staticmethod
    def from_pitch_class(pitch_class:str):
        """
        Converts a pitch class notation to a midi note.

        converts pitch class name to midi note
        pitch class spec - [note name][s|f|n][octave]
        examples: b4, cs5, af8, an3
        """
        return PitchClass(str(pitch_class)).midi

    def to_pitch_class(self):
        """Returns the pitch class of the midi note as a string."""
        return f"{self.pitch}{self.octave}"

    # basic properties
    hertz:float = 440.0
    offset:int = 69

    @property
    def note(self):
        return self._note

    @note.setter
    def note(self, value:int):
        self._note = max(0, int(value))

    @property
    def frequency(self) -> float:
        """Returns the frequency of the note in Hertz."""
        if self.note == 0:
            return 0.0

        power = (self.note - self.offset) / SCALE
        return self.hertz * 2**power

    @property
    def octave(self) -> int:
        return (self.note // SCALE) - 1

    @property
    def pitch(self) -> str:
        return semitone_code(self.note)

    # magic methods

    def __add__(self, value:int):
        return MidiNote(self.note + int(value))

    def __iadd__(self, value:int):
        self._note = self._note + int(value)

    def __sub__(self, value:int):
        return MidiNote(self.note - int(value))

    def __isub__(self, value:int):
        self._note = self._note - int(value)

    def __mul__(self, value:int):
        return MidiNote(self.note * int(value))

    def __imul__(self, value:int):
        self._note = self._note * int(value)

    def __truediv__(self, value:int):
        return MidiNote(self.note // int(value))

    def __itruediv__(self, value:int):
        self._note = self.note // int(value)

    def __floordiv__(self, value:int):
        return self / value  # same as truediv

    def __ifloordiv__(self, value:int):
        self /= value  # same as itruediv


class PitchClass:
    """"""
    def __init__(self, pc:str):
        self._pc = str(pc)

    def __repr__(self):
        return f"PitchClass('{self.pitch}{self.octave}')"

    def __str__(self):
        return f"{self.pitch}{self.octave}"

    # alternative creation methods
    @staticmethod
    def from_frequency(frequency:float):
        """Converts a frequency in Hertz to a pitch class."""
        return PitchClass(MidiNote.from_frequency(frequency).to_pitch_class())

    @staticmethod
    def from_midi_note(note:int):
        """
        Converts a midi note to a pitch class notation.

        pitch class spec - [note name][s|f|n][octave]
        examples: b4, c#5, a♭8, a𝄫3
        """
        return PitchClass(MidiNote(note).to_pitch_class())

    def to_midi_note(self):
        """
        Converts a pitch class notation to a midi note integer.

        converts pitch class name to midi note
        pitch class spec - [note name][s|f|n][octave]
        examples: b4, cs5, af8, an3
        """
        if self.pitch == 'r':
            return MidiNote(0)

        note = semitone_int(self._pc)

        return (1 + self.octave) * 12 + note

    # properties
    @property
    def frequency(self) -> float:
        return MidiNote(self.to_midi_note()).frequency

    @property
    def octave(self) -> int:
        octave = 5  # default
        if len(self._pc) > len(self.pitch):
            octave = int(self._pc[len(self.pitch):])
        return octave

    @property
    def pitch(self) -> str:
        return semitone_code(semitone_int(self._pc))


def accidental_modifier(mark:str):
    "Accepts a mark (# or S, ♭ or F, 𝄫 or D) and returns the semitone interval (+1, -1, -2)."
    mark = str(mark)[0]
    accidentals = {
        '#':  1,    'S':  1,  # sharp
        '♭': -1,    'F': -1,  # flat
        '𝄫': -2,    'D': -2,  # double flat
        }
    if mark in accidentals:
        return accidentals[mark]
    return 0


def semitone_int(code:str) -> int:
    "Accepts a code and returns the semitone: C# -> 1."
    letter = code[0].upper()
    index = SEMITONES.index(letter)

    if len(code) > 1:
        index += accidental_modifier(code[1].upper())

    return cycle(index)


def semitone_code(index:int):
    "Accepts an integer and returns the semitone: 1 -> C#."
    index = cycle(index)

    code = SEMITONES[index]
    if code == '_':
        index = cycle(index - 1)
        code = SEMITONES[index] + '#'

    return code
