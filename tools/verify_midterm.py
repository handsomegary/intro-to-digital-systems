"""Exhaustively check the handwritten midterm designs using the standard library.

The independent cube enumerator checks small minimum-SOP claims without using
the accompanying Quine-McCluskey implementation. Arithmetic references use
Python integers; the circuits use individual bits and full-adder equations.
"""
from itertools import combinations, product
import json


def bits(number, width):
    return tuple((number >> i) & 1 for i in reversed(range(width)))


def cube_covers(pattern, number):
    return all(p == '-' or int(p) == bit
               for p, bit in zip(pattern, bits(number, len(pattern))))


def exact_cubes(width, on, dc=()):
    """Enumerate all 3**width cubes and every prime-cover cardinality needed."""
    on, allowed = set(on), set(on) | set(dc)
    valid = {}
    for symbols in product('01-', repeat=width):
        pattern = ''.join(symbols)
        covered = {n for n in range(1 << width) if cube_covers(pattern, n)}
        if covered <= allowed and covered & on:
            valid[pattern] = covered
    primes = {p: s for p, s in valid.items()
              if not any(s < larger for larger in valid.values())}
    for terms in range(1, len(primes) + 1):
        candidates = [cover for cover in combinations(primes, terms)
                      if on <= set().union(*(primes[p] for p in cover))]
        if candidates:
            literal_count = min(sum(width-p.count('-') for p in cover)
                                for cover in candidates)
            best = [cover for cover in candidates
                    if sum(width-p.count('-') for p in cover) == literal_count]
            return primes, (terms, literal_count), best
    raise AssertionError('No cover for nonempty on-set')


def original_q1(a, b, c, d, e, f):
    f1 = (a and c and not d) or (b and d) or (a and b and c)
    f2 = ((a and c and not d) or (b and d) or (c and not e and f)
          or (d and not e and f) or (not a and c and e and f)
          or (not a and e and f))
    f3 = (((not c or e or not f) and (a or d or not f)
           and (a or not e or not f)) or (a and not c and f)
          or (b and d and not f) or (a and e and f)
          or (not b and not c and not e) or (not c and not e and f)
          or (not c and not d and not e))
    return bool((f1 or not f2) and (f2 or f3) and f2)


def full_adder(a, b, carry):
    return a ^ b ^ carry, (a & b) | (a & carry) | (b & carry)


def quotient_bit(c, b):
    c2, c1, c0 = bits(c, 3)
    return c2 | (c1 & c0) | (c1 & b)


def divide_five_cells(value, width):
    """The first cell starts with the two most significant input bits."""
    assert 0 <= value < (1 << width) and width >= 3
    remainder = value >> (width - 2)
    quotient = 0
    cells = []
    for position in reversed(range(width - 2)):
        bit = (value >> position) & 1
        q = quotient_bit(remainder, bit)
        x = 2 * remainder + bit
        remainder = x - 5 * q
        assert 0 <= remainder <= 4
        quotient = 2 * quotient + q
        cells.append((position, q))
    return quotient, remainder, cells


def decimal_remainder_from_three_adders(remainder, quotient_lsb):
    r2, r1, r0 = bits(remainder, 3)
    d0, k1 = full_adder(r0, quotient_lsb, 0)
    d1, k2 = full_adder(r1, 0, k1)
    d2, d3 = full_adder(r2, quotient_lsb, k2)
    return d0 + 2*d1 + 4*d2 + 8*d3


def bcd_converter(value):
    remaining = value
    digits = []
    counts = []
    for width in (13, 10, 7):
        quotient, remainder, cells = divide_five_cells(remaining, width)
        digits.append(decimal_remainder_from_three_adders(remainder, quotient & 1))
        remaining = quotient >> 1
        counts.append(len(cells))
    assert 0 <= remaining <= 8
    digits.append(remaining)
    return digits, counts


def main():
    q1_on = set()
    for n in range(64):
        a, b, c, d, e, f = bits(n, 6)
        expected = bool((a and c and not d) or (b and d))
        assert original_q1(a, b, c, d, e, f) == expected
        if expected:
            q1_on.add(n)
    q1_primes, q1_cost, _ = exact_cubes(6, q1_on)
    assert q1_cost == (2, 5)

    s1, s2 = {0, 3, 6, 11, 13, 15}, {1, 2, 5, 14}
    s3, s4 = {0, 5, 7, 9, 11, 15}, {1, 3, 13, 14}
    q2_on, q2_dc = set(), set()
    def possibilities(n, on, dc):
        return {1} if n in on else {0, 1} if n in dc else {0}
    for n in range(16):
        outputs = {a & b for a in possibilities(n, s1, s2)
                   for b in possibilities(n, s3, s4)}
        if outputs == {1}:
            q2_on.add(n)
        elif outputs == {0, 1}:
            q2_dc.add(n)
    assert q2_on == {0, 11, 15}
    assert q2_dc == {1, 3, 5, 13, 14}
    assert not q2_on & q2_dc

    q3_on = {5, 13, 15, 19, 22, 23, 24, 26}
    q3_dc = {0, 3, 7, 8, 12, 16, 18, 21, 27, 30, 31}
    q3_primes, q3_cost, q3_covers = exact_cubes(5, q3_on, q3_dc)
    assert q3_cost == (3, 8)
    expected_covers = {
        frozenset(('0-1-1', '1-0-0', '1--1-')),
        frozenset(('0-1-1', '1--1-', '--000')),
    }
    assert {frozenset(c) for c in q3_covers} == expected_covers
    for n in range(32):
        a, b, c, d, e = bits(n, 5)
        actual = bool((a and d) or (a and not c and not e)
                      or (not a and c and e))
        if n not in q3_dc:
            assert actual == (n in q3_on)

    # Q4's declared convention: return index i for a[i]=1, i=0,...,6.
    for active in (None, *range(7)):
        a = [int(i == active) for i in range(7)]
        b2 = a[4] | a[5] | a[6]
        b1 = a[2] | a[3] | a[6]
        b0 = a[1] | a[3] | a[5]
        assert 4*b2 + 2*b1 + b0 == (0 if active is None else active)

    mux_cases = 0
    for words in product(range(4), repeat=3):
        for selected in range(3):
            select = [int(i == selected) for i in range(3)]
            value = sum((int(any(select[i] and ((words[i] >> bit) & 1)
                                 for i in range(3)))) << bit for bit in range(2))
            assert value == words[selected]
            mux_cases += 1
    q6_zeros = []
    for n in range(8):
        a, b, c = bits(n, 3)
        from_decoder = n in {0, 3, 6}
        from_pos = ((a or b or not c) and (a or not b or c)
                    and (not a or b or c) and (not a or b or not c)
                    and (not a or not b or not c))
        assert from_decoder == from_pos
        if not from_decoder:
            q6_zeros.append(n)
    assert q6_zeros == [1, 2, 4, 5, 7]
    for data in range(2):
        for selection in (0, 1, 2, 4, 8):
            actual = tuple(data & ((selection >> i) & 1) for i in range(4))
            expected = tuple(data if selection == 1 << i else 0 for i in range(4))
            assert actual == expected
    negative_table = {n: format(n % 32, '05b') for n in range(-1, -17, -1)}
    for n, representation in negative_table.items():
        assert int(representation, 2) - 32 == n

    for c, b in product(range(5), range(2)):
        assert quotient_bit(c, b) == int(2*c+b >= 5)
    for width in range(3, 14):
        for value in range(1 << width):
            q, r, cells = divide_five_cells(value, width)
            assert (q, r) == divmod(value, 5)
            assert len(cells) == width - 2
            assert decimal_remainder_from_three_adders(r, q & 1) == value % 10
    for value in range(8192):
        digits, counts = bcd_converter(value)
        assert counts == [11, 8, 5]
        assert all(0 <= digit <= 9 for digit in digits)
        assert sum(digit * 10**i for i, digit in enumerate(digits)) == value

    comparisons = 0
    for width in range(1, 9):
        def signed(x):
            return x-(1 << width) if x & (1 << (width-1)) else x
        for a, b in product(range(1 << width), repeat=2):
            sa, sb = a >> (width-1), b >> (width-1)
            actual = ((not sa and sb) or ((sa == sb) and a > b))
            assert bool(actual) == (signed(a) > signed(b))
            comparisons += 1

    print(json.dumps({
        'status': 'PASS', 'q1_assignments': 64, 'q1_minimum_cost': q1_cost,
        'q2_on': sorted(q2_on), 'q2_dont_cares': sorted(q2_dc),
        'q3_prime_count': len(q3_primes), 'q3_minimum_cost': q3_cost,
        'q3_all_minimum_covers': q3_covers, 'mux_cases': mux_cases,
        'decoder_zero_indices': q6_zeros, 'bcd_inputs': 8192,
        'bcd_unit_cell_counts': [11, 8, 5], 'signed_comparisons': comparisons,
        'scope': 'Static Boolean and arithmetic correctness; no gate-delay model.'
    }, indent=2))


if __name__ == '__main__':
    main()
