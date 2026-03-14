# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Thuja is a Python module for algorithmic composition that uses Csound for audio generation. It generates Csound score (.sco) files through two core abstractions:

- **Itemstreams**: Define sequences of values for any p-field (parameter field) in a Csound score event
- **NoteGenerators**: Collections of Itemstreams plus configuration that drive Csound score creation

The library is inspired by Rick Taube's Common Music 1.x and enables both static composition and realtime/live coding.

## Development Commands

### Testing
```bash
cd tests
sh runUnitTests.sh
```
Or directly:
```bash
cd tests
python -m unittest discover
```

### Installation
```bash
pip install -r requirements.txt
```

Note: Csound must be installed separately from https://csound.com/download.html

## Core Architecture

### Two-Layer Generation Model

The fundamental pattern in Thuja is a **generator loop** that iterates through Itemstreams:

1. `NoteGenerator.generate_notes()` runs a loop requesting the next note
2. For each note, the generator queries each Itemstream for its `get_next_value()`
3. Itemstreams wrap around when exhausted, creating cyclical patterns
4. Different Itemstream lengths create polyrhythmic/polymetric effects

### Key Classes and Their Roles

**thuja/itemstream.py**:
- `Itemstream`: Core sequence container with three `streammode` options:
  - `sequence`: values returned in order
  - `random`: random selection from values
  - `heap`: random without repetition until all values used
- Three `notetype` values determine value interpretation:
  - `pitch`: scientific pitch notation → frequencies (e.g., 'c4', 'cs3', 'bf2')
  - `rhythm`: rhythmic notation → durations (e.g., 'w', 'h', 'q', 'e', 's' for whole/half/quarter/eighth/sixteenth notes, plus dotted notation and addition like 'w+q')
  - `number`: raw numeric values
- Pitch notation supports octave persistence (if octave omitted, uses last specified)
- Rhythm notation uses tempo attribute (default 120 bpm) to calculate actual durations
- Supports mapping lists for post-processes that set multiple pfields simultaneously

**thuja/notegenerator.py**:
- `NoteGenerator`: Base class managing note generation lifecycle
- `Line`: Convenience subclass with fluent API (`.with_rhythm()`, `.with_pitches()`, etc.)
- Supports nested child generators that inherit parent timing constraints
- `post_processes`: List of callables invoked after each note's pfields are populated
- Lambda support: Any stream can be a callable instead of an Itemstream (receives note object, called after post_processes)
- `pfields`: Ordered list defining which p-fields each note contains
- `streams`: OrderedDict mapping pfield names to Itemstreams or callables
- Key timing attributes:
  - `start_time`: When this generator starts
  - `note_limit`: Max notes to generate
  - `time_limit`: Absolute time limit
  - `generator_dur`: Relative duration (for child generators with offset start times)

**thuja/event.py**:
- `Event`: Represents a single note with its pfield dictionary
- Contains `rhythm` attribute and start_time
- `__str__()` formats as Csound score line (tab-delimited i-statement)

**thuja/streamkeys.py**:
- `StreamKey`: Defines standard pfield key constants
- Common keys: `instrument`, `start_time`, `duration`, `rhythm`, `amplitude`, `frequency`, `pan`, `distance`, `percent`, `index`
- Import via `from thuja.streamkeys import keys`

**thuja/csound_utils.py**:
- Provides Csound integration via ctcsound library
- `play_csound()`: Main function to play a generator with a .orc file
- `init_csound_with_orc()` and `init_csound_with_csd()`: Initialize Csound instances
- Handles score string generation and Csound performance

### Special Patterns

**Chording**: Nested lists in pitch Itemstreams create chords:
```python
pitches = Itemstream(['a2', 'b', ['e', 'b'], 'c3'])  # Third value is a chord
```

**Rests**: Use 'r' in pitch streams to create rests

**Tuple Streams**: Itemstreams can contain dicts with multiple keys, allowing synchronized pfield values:
```python
tuplestream = Itemstream([
    {keys.rhythm: "h", "indx": .769},
    {keys.rhythm: "q", "indx": 1.95}
])
# In generator: ('rhy|indx', tuplestream)
```

**Callables**: Duration or other pfields can be lambdas that reference the note:
```python
streams=OrderedDict([
    (keys.duration, lambda note: note.rhythm * 2)
])
```

**Nested Generators**: Create hierarchical musical structures:
```python
parent.add_generator(child_generator)
```
Children inherit parent's timing constraints (start_time, time_limit, note_limit).

**Deep Copying**: `NoteGenerator.deepcopy()` replicates the generator but NOT its children (generators list is cleared).

## File Organization

- `thuja/`: Core module with 7 main files
- `examples/`: Demonstration files (best current documentation per README)
- `examples/NoteGenerator/`: Additional generator examples
- `tests/`: Unit tests covering itemstreams, generators, utils
- `doc/`: Contains `Overview.md` with verbose walkthrough of the mental model

## Change History

- **[HISTORY.md](HISTORY.md)**: Significant changes, decisions, and context behind work done on this codebase. Updated each session.

## Experimental / Proposals

- **[LinkFollowerProposal.md](LinkFollowerProposal.md)**: Architecture proposal for syncing NoteGeneratorThread to Ableton Link. Thuja follows Link tempo; Phase 2 adds quantized regeneration at beat/bar boundaries.

## Experimental Prompts

- **[REVIEW_PROMPT.md](REVIEW_PROMPT.md)**: Structured code review prompt. Use this at the start of a review session to drive an interactive, opinionated review of architecture, code quality, tests, and performance.

## Important Notes

- Csound score format uses tab-delimited p-fields starting with 'i' prefix
- `gen_lines`: List of function table definitions (f-statements) prepended to score
- `end_lines`: List of score lines appended after generated notes (commonly reverb instrument)
- `score_dur`: Automatically calculated total duration after `generate_notes()`
- The library uses OrderedDict to maintain pfield ordering in generated scores
- Random operations in Itemstreams use seeded random generators for reproducibility
