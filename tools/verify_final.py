"""Verify the final-exam door controller without external simulation tools.

The gate equations, transition-table oracle, and bit-level incrementer are
implemented separately. All checks use Python's standard library.
"""

from itertools import product
import json

CLOSED, OPENING, OPEN, CLOSING = 0b00, 0b01, 0b11, 0b10
WIDTH = 13
TICKS = 5000


def state_gates(state, detect, done, terminal, reset=0):
    """Evaluate the two sum-of-products state-DFF input circuits."""
    s1, s0 = (state >> 1) & 1, state & 1
    high = ((s1 & s0)
            | ((1 - s1) & s0 & done)
            | (s1 & (1 - s0) & (1 - detect) & (1 - done)))
    low = detect | (s0 & ((1 - s1) | (1 - terminal)))
    return (((1 - reset) & high) << 1) | ((1 - reset) & low)


def transition_table(state, detect, done, terminal, reset=0):
    """Independent behavioral oracle derived from the six operation rules."""
    if reset:
        return CLOSED
    if state == CLOSED:
        return OPENING if detect else CLOSED
    if state == OPENING:
        return OPEN if done else OPENING
    if state == OPEN:
        return CLOSING if not detect and terminal else OPEN
    if state == CLOSING:
        if detect:  # A person takes priority over a simultaneous endpoint pulse.
            return OPENING
        return CLOSED if done else CLOSING
    raise ValueError("Not a two-bit state")


def outputs(state):
    s1, s0 = (state >> 1) & 1, state & 1
    return (1 - s1) & s0, s1 & (1 - s0)


def terminal_gates(count):
    """The four AND gates in the 4999 decoder, including input inversions."""
    c = [(count >> bit) & 1 for bit in range(WIDTH)]
    g3 = c[12] & (1 - c[11]) & (1 - c[10]) & c[9]
    g2 = c[8] & c[7] & (1 - c[6]) & (1 - c[5])
    g1 = (1 - c[4]) & (1 - c[3]) & c[2] & c[1]
    return g3 & g2 & g1 & c[0]


def counter_gates(count, enable):
    """Thirteen XOR/AND/DFF cells with combinational carry recurrence."""
    carry = 1
    new_count = 0
    for bit in range(WIDTH):
        q = (count >> bit) & 1
        d = enable & (q ^ carry)
        new_count |= d << bit
        carry &= q
    return new_count


def clock_edge(state, count, detect, done, reset=0):
    """Simultaneous state and counter update from the pre-edge register values."""
    terminal = terminal_gates(count)
    s1, s0 = (state >> 1) & 1, state & 1
    enable = ((1 - reset) & s1 & s0 & (1 - detect) & (1 - terminal))
    return (state_gates(state, detect, done, terminal, reset),
            counter_gates(count, enable))


def behavioral_edge(state, count, detect, done, reset=0):
    """Arithmetic reference, with timer reset conditions stated directly."""
    terminal = count == TICKS - 1
    next_state = transition_table(state, detect, done, terminal, reset)
    if reset or state != OPEN or detect or terminal:
        next_count = 0
    else:
        next_count = count + 1
    return next_state, next_count


def main():
    transition_cases = 0
    for state, detect, done, terminal, reset in product(
            range(4), (0, 1), (0, 1), (0, 1), (0, 1)):
        expected = transition_table(state, detect, done, terminal, reset)
        assert state_gates(state, detect, done, terminal, reset) == expected
        op, cl = outputs(expected)
        assert not (op and cl)
        transition_cases += 1

    counter_cases = 0
    for count in range(1 << WIDTH):
        assert terminal_gates(count) == int(count == TICKS - 1)
        for enable in (0, 1):
            expected = ((count + 1) % (1 << WIDTH)) if enable else 0
            assert counter_gates(count, enable) == expected
            counter_cases += 1

    # Only OPEN can have nonzero timer contents in a normally initialized
    # run. All other states are also tested against every reachable counter
    # value to check that their timer clears unconditionally.
    combined_cases = 0
    for state, count, detect, done in product(
            range(4), range(TICKS), (0, 1), (0, 1)):
        actual = clock_edge(state, count, detect, done)
        expected = behavioral_edge(state, count, detect, done)
        assert actual == expected, (state, count, detect, done, actual, expected)
        if actual[0] != OPEN:
            assert actual[1] == 0
        combined_cases += 1

    # Reset overrides every state, detector value and endpoint pulse, and
    # clears every possible 13-bit timer pattern, including unused patterns.
    reset_cases = 0
    for state, count, detect, done in product(
            range(4), range(1 << WIDTH), (0, 1), (0, 1)):
        assert clock_edge(state, count, detect, done, reset=1) == (CLOSED, 0)
        reset_cases += 1

    # Startup and fully-closed invariance, including irrelevant Done pulses.
    state, count = CLOSED, 0
    for done in (0, 1, 0, 1):
        state, count = clock_edge(state, count, 0, done)
        assert (state, count, outputs(state)) == (CLOSED, 0, (0, 0))

    # Detection starts opening; input D cannot cancel opening before Done.
    state, count = clock_edge(state, count, 1, 0)
    assert (state, count, outputs(state)) == (OPENING, 0, (1, 0))
    for detect in (0, 1, 0):
        state, count = clock_edge(state, count, detect, 0)
        assert (state, count) == (OPENING, 0)
    state, count = clock_edge(state, count, 0, 1)
    assert (state, count) == (OPEN, 0)

    # Entry is time zero. The first 4999 absent samples cannot start closing.
    for tick in range(1, TICKS):
        state, count = clock_edge(state, count, 0, 0)
        assert (state, count) == (OPEN, tick)
        assert outputs(state) == (0, 0)
    state, count = clock_edge(state, count, 0, 0)
    assert (state, count, outputs(state)) == (CLOSING, 0, (0, 1))

    # A person while closing immediately changes the post-edge output to OP.
    for done in (0, 1):
        reopened = clock_edge(CLOSING, 0, 1, done)
        assert reopened == (OPENING, 0)
        assert outputs(reopened[0]) == (1, 0)
        # The prior closing Done pulse is not reused as an opening endpoint.
        assert clock_edge(*reopened, 0, 0) == (OPENING, 0)
        assert clock_edge(*reopened, 0, 1) == (OPEN, 0)

    # No detection: stay in motion until the correct endpoint pulse.
    assert clock_edge(CLOSING, 0, 0, 0) == (CLOSING, 0)
    assert clock_edge(CLOSING, 0, 0, 1) == (CLOSED, 0)

    # Detection wins on the timeout edge, regardless of an irrelevant Done.
    for done in (0, 1):
        assert clock_edge(OPEN, TICKS - 1, 1, done) == (OPEN, 0)
    state, count = clock_edge(OPEN, TICKS - 1, 1, 0)
    for tick in range(1, TICKS):
        state, count = clock_edge(state, count, 0, 0)
        assert (state, count) == (OPEN, tick)
    assert clock_edge(state, count, 0, 0) == (CLOSING, 0)

    # Persistent detection always clears the timer. Intermediate detections
    # also restart it; an endpoint pulse does not affect an already open door.
    for count in (0, 1, 173, 4998, 4999):
        assert clock_edge(OPEN, count, 1, 0) == (OPEN, 0)
        assert clock_edge(OPEN, count, 1, 1) == (OPEN, 0)
    assert clock_edge(OPEN, 173, 0, 1) == (OPEN, 174)

    print(json.dumps({
        "status": "PASS",
        "state_input_combinations": transition_cases,
        "counter_bit_circuit_cases": counter_cases,
        "combined_reachable_count_cases": combined_cases,
        "reset_state_count_input_cases": reset_cases,
        "timer_clock_hz": 1000,
        "absence_samples_until_close": TICKS,
        "nominal_delay_seconds": TICKS / 1000,
        "state_flip_flops": 2,
        "counter_flip_flops": WIDTH,
        "trace_checks": [
            "closed invariance",
            "opening until endpoint",
            "exact 5000-sample timeout",
            "detection on timeout edge",
            "full restart interval",
            "reopen while closing",
            "simultaneous detection and closing endpoint",
            "closing completion",
            "persistent detection",
            "irrelevant endpoint inputs",
            "output mutual exclusion",
        ],
        "scope": "Ideal synchronous classroom circuit; no simulator required."
    }, indent=2))


if __name__ == "__main__":
    main()
