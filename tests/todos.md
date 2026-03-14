# Test Coverage Gaps - Thuja

This document identifies features in the Thuja codebase that lack test coverage.

**NOTE:** After analyzing real compositions in `../csound-pieces/thuja-ep/`, many of these "untested" features are HEAVILY USED in practice. This makes regression testing even more critical.

## Major Untested Features

### **Itemstream**
1. **Streammode 'random'** - Only 'sequence' and 'heap' are tested, but 'random' mode exists
2. **Chording (nested lists)** - The README and docs mention chord notation like `['e', 'b']` but there are no tests for this critical feature
3. **Rests ('r')** - Documented in README but never tested
4. **Path notetype** - Exists in code (itemstream.py:153-155, 213-215) but completely untested
5. **Tempo as callable** - Code supports `callable(self.tempo)` (itemstream.py:224-226) but not tested
6. **Tempo as list** - Tested in generators, but not isolated Itemstream behavior
7. **set_seed() method** - Exists for reproducibility but not tested
8. **Octave persistence** - Documented behavior where octave persists between pitches (e.g., 'c4 d e' → c4, d4, e4)
9. **String input handling** - Constructor handles space-delimited strings but not tested

### **NoteGenerator Core**
1. **Time limits** - `time_limit` and `generator_dur` attributes exist but are never tested
2. **Child generator inheritance** - Test exists but doesn't assert anything:
   ```python
   def test_child_generators(self):
       # ... creates generators ...
       melody_left.add_generator(melody_right)
       pass  # No assertions!
   ```
3. **deepcopy() method** - Documented in CLAUDE.md as important (doesn't copy children) but not tested
4. **deepcopy_tree() method** - Copies including children, not tested
5. **generate_score() with file output** - Has filename parameter but only string generation is tested
6. **clear_notes() method** - Not tested
7. **add_bars_to_starttime()** - Musical time calculation helper, not tested
8. **UDP methods** - `send_gens_to_udp()` and `send_notes_to_udp()` completely untested
9. **set_streams_to_seed()** - Propagates seeds to all streams for reproducibility, not tested
10. **Context with 2-parameter post_processes** - Code checks for `funcsigs.signature()` to handle `(note, context)` but only single-param tested

### **Line Class**
The entire fluent API is essentially untested:
- All `with_*` methods (with_instr, with_duration, with_amps, with_pitches, with_freqs, with_pan, with_dist, with_percent, with_tempo, with_index)
- `randomize()` - Sets random seed across all streams
- `setup_index_params_with_file()` - Configures for audio file playback
- `g()` - Shorthand for `generate_notes()`

### **NoteGeneratorThread**
The entire threading/real-time class (notegenerator.py:536-595) is completely untested

### **csound_utils**
All Csound integration is untested:
- `init_csound_with_orc()`
- `init_csound_with_csd()`
- `play_csound()`

### **Event Class**
Never directly tested (only used implicitly in generators)

## Critical Missing Tests (High Priority)

Based on analysis of ~60 real compositions in `csound-pieces/thuja-ep/`:

### **EXTREMELY CRITICAL - Used in Nearly Every Piece:**

1. **time_limit** - Used in almost EVERY piece examined (pitch_generation.py:44, index_study_1_respiration.py:139/157/164/171, etc.)
   - Currently NO tests verify time_limit stops generation correctly
   - This is a primary compositional tool

2. **deepcopy()** - Used extensively for creating variations (index_study_1_respiration.py:141/147/159, 2024.05.27.py:64/75)
   - Critical for composition workflow
   - NO tests verify it actually works or that children are excluded

3. **Chording (nested lists)** - chapel_october_2022_chorale.py:79 uses `[['c','e','g'],['f','a','c'],...]`
   - Zero test coverage despite being a documented, used feature

4. **Post-processes with 2-param signature** - Used in EVERY complex piece (wigout.py:91, index_study_1_respiration.py:119)
   - `def post_process(note, context):` pattern is ubiquitous
   - Only 1-param lambdas tested

5. **set_streams_to_seed()** - Used for reproducible random generation (2024.05.27.py:74/77)
   - Critical for generative music reproducibility
   - Completely untested

### **HIGH PRIORITY - Frequently Used:**

6. **Rests ('r')** - pitch_generation.py:19 has `'c5 g f g r c4 g f g r'.split()`
   - Documented, used, untested

7. **Random streammode** - wigout.py:67, 2024.05.27.py:72 use `streammode=streammodes.random`
   - One of 3 modes, frequently used, never tested

8. **Child generator inheritance** - index_study_1_respiration.py:175-178, 2024.05.27.py:83-85
   - Test skeleton exists but has NO assertions
   - Used for layering musical textures

9. **set_stream() on Line class** - Used to add custom pfields (266.py:84-91, 2024.05.27.py:55-59)
   - Core fluent API method, untested

10. **Heap streammode edge cases** - Used extensively (2024.05.27.py:69, index_study_1_respiration.py:152)
    - Tested in basic form, but exhaustion/refill cycle not verified

### **MEDIUM PRIORITY - Occasionally Used:**

11. **NoteGeneratorThread** - Real-time performance (jams.py:73-75)
12. **seed parameter on Itemstream** - wigout.py:125, chapel_october:127
13. **Octave persistence in pitch notation** - Implicit in all pitch usage
14. **Lambda streams** - Heavily used but only tested via integration, not isolated

## Pattern Analysis

**Your tests cover the happy path of the core generation loop well, but don't test the compositional tools that make Thuja useful for actual composition.**

Real-world usage reveals:
- **deepcopy()** is essential for creating variations (texture1 = copy.deepcopy(pulse_l) pattern)
- **time_limit** is the primary way to control piece duration
- **Post-processes with context** are used for complex transformations
- **Chording** enables harmonic structures
- **Rests** create rhythmic space
- **Random modes** with seeded reproducibility are core to generative workflow

## Recommendations (Priority Order)

1. **time_limit tests** - Verify note generation stops at time_limit (integration test)
2. **deepcopy() tests** - Verify streams are copied, children excluded, notes cleared
3. **Chording tests** - Nested lists produce multiple simultaneous notes
4. **Post-process context tests** - Two-parameter signature with context dict
5. **set_streams_to_seed() tests** - Verify all streams get seeded, reproducibility
6. **Rests tests** - 'r' produces frequency=0 or skipped notes
7. **Random streammode tests** - Values are random, seed produces same sequence
8. **Child generator tests** - Add assertions to existing test, verify inheritance
9. **set_stream() tests** - Line class fluent API for custom pfields
10. **Heap exhaustion tests** - Verify all values used before repeat

## Real-World Usage Patterns Observed

From analyzing ~60 compositions:

**Common compositional workflow:**
```python
# 1. Create a base generator
base = Line().with_rhythm(...).with_pitches(...)

# 2. Make copies for variations
texture1 = base.deepcopy()
texture2 = base.deepcopy()

# 3. Modify each copy
texture1.start_time = 16
texture2.streams[keys.pan] = 80

# 4. Use time_limit for structure
texture1.time_limit = 60
texture2.time_limit = 90

# 5. Layer them
base.add_generator(texture1)
base.add_generator(texture2)

# 6. Generate with reproducible randomness
base.set_streams_to_seed(seed)
base.generate_notes()
```

**None of this workflow is tested**, yet it's how the library is actually used.
