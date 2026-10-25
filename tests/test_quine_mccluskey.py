"""Independent exhaustive checks of the educational exact SOP minimizer."""

from functools import lru_cache
from itertools import product
import json
from pathlib import Path
import random
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
from quine_mccluskey import minimize


@lru_cache(maxsize=None)
def all_cubes(width):
    """Enumerate every ternary cube directly, without combining minterms."""
    cubes = []
    for pattern in product("01-", repeat=width):
        covered = 0
        for value in range(1 << width):
            binary = format(value, f"0{width}b") if width else ""
            if all(p == "-" or p == bit for p, bit in zip(pattern, binary)):
                covered |= 1 << value
        cubes.append(("".join(pattern), covered, sum(p != "-" for p in pattern)))
    return tuple(cubes)


def brute_force_cost(width, on, dc):
    """Solve set cover over ALL valid cubes with a coverage-state DP oracle.

    This does not use prime generation, essential selection, Petrick products,
    or any helper from the implementation under test.
    """
    required = sum(1 << value for value in on)
    allowed = required | sum(1 << value for value in dc)
    best = {0: (0, 0)}
    for _, covered, literals in all_cubes(width):
        contribution = covered & required
        if not contribution or covered & ~allowed:
            continue
        for state, (terms, count) in list(best.items()):
            target = state | contribution
            cost = (terms + 1, count + literals)
            if target not in best or cost < best[target]:
                best[target] = cost
    return best[required]


class QuineMcCluskeyTests(unittest.TestCase):
    def assert_correct(self, width, on, dc):
        result = minimize(width, on, dc)
        self.assertEqual(result.cost, brute_force_cost(width, on, dc))
        on, dc = set(on), set(dc)
        for value in range(1 << width):
            if value not in dc:
                self.assertEqual(result.evaluate(value), value in on,
                                 (width, on, dc, result.implicants, value))
        self.assertLessEqual(set(result.essential_prime_implicants), set(result.implicants))
        self.assertLessEqual(set(result.implicants), set(result.prime_implicants))
        return result

    def test_all_partially_specified_functions_through_three_variables(self):
        # At width 3 this covers 3**8 = 6561 on/off/don't-care assignments.
        for width in range(4):
            for values in product(range(3), repeat=1 << width):
                on = tuple(i for i, value in enumerate(values) if value == 1)
                dc = tuple(i for i, value in enumerate(values) if value == 2)
                with self.subTest(width=width, on=on, dc=dc):
                    self.assert_correct(width, on, dc)

    def test_seeded_four_variable_functions(self):
        rng = random.Random(202310)
        for _ in range(160):
            values = [rng.randrange(3) for _ in range(16)]
            on = tuple(i for i, value in enumerate(values) if value == 1)
            dc = tuple(i for i, value in enumerate(values) if value == 2)
            self.assert_correct(4, on, dc)

    def test_prime_generation_against_all_cube_enumeration(self):
        rng = random.Random(112)
        for _ in range(80):
            values = [rng.randrange(3) for _ in range(16)]
            on = tuple(i for i, value in enumerate(values) if value == 1)
            dc = tuple(i for i, value in enumerate(values) if value == 2)
            required = sum(1 << value for value in on)
            allowed = required | sum(1 << value for value in dc)
            cubes = [(pattern, covered) for pattern, covered, _ in all_cubes(4)
                     if covered & required and not covered & ~allowed]
            primes = sorted(pattern for pattern, covered in cubes
                            if not any(covered != other and covered & other == covered
                                       for _, other in cubes))
            self.assertEqual(list(minimize(4, on, dc).prime_implicants), primes)

    def test_cover_without_any_essential_prime(self):
        result = self.assert_correct(3, (0, 1, 2, 5, 6, 7), ())
        self.assertEqual(result.essential_prime_implicants, ())
        self.assertEqual(result.cost, (3, 6))

    def test_exam_five_variable_example(self):
        on = (5, 13, 15, 19, 22, 23, 24, 26)
        dc = (0, 3, 7, 8, 12, 16, 18, 21, 27, 30, 31)
        result = self.assert_correct(5, on, dc)
        self.assertEqual(result.cost, (3, 8))

    def test_constants_and_explicit_width(self):
        self.assertEqual(minimize(4, ()).expression(), "0")
        self.assertEqual(minimize(4, (), range(16)).cost, (0, 0))
        self.assertEqual(minimize(4, range(16)).implicants, ("----",))
        self.assertEqual(minimize(4, (0,), range(1, 16)).expression(), "1")
        self.assertEqual(minimize(4, (0,)).expression(), "A'*B'*C'*D'")
        self.assertEqual(minimize(0, ()).expression(), "0")
        self.assertEqual(minimize(0, (0,)).implicants, ("",))
        self.assertEqual(minimize(0, (0,)).expression(), "1")
        self.assertEqual(minimize(0, (), (0,)).cost, (0, 0))

    def test_duplicates_order_and_generators(self):
        expected = minimize(3, (0, 1, 2, 5, 6, 7))
        self.assertEqual(minimize(3, (7, 2, 0, 7, 1, 5, 6)), expected)
        self.assertEqual(minimize(3, (value for value in (7, 6, 5, 2, 1, 0))), expected)
        self.assertEqual(minimize(2, (0, 0), (1, 1)), minimize(2, (0,), (1,)))

    def test_invalid_inputs(self):
        for width in (True, False, 2.0, "2", None):
            with self.subTest(width=width), self.assertRaises(TypeError):
                minimize(width, ())
        with self.assertRaises(ValueError):
            minimize(-1, ())
        for terms in ((True,), (1.0,), ("1",), (None,)):
            with self.subTest(terms=terms), self.assertRaises(TypeError):
                minimize(2, terms)
            with self.assertRaises(TypeError):
                minimize(2, (), terms)
        for terms in ((-1,), (4,)):
            with self.assertRaises(ValueError):
                minimize(2, terms)
            with self.assertRaises(ValueError):
                minimize(2, (), terms)
        with self.assertRaises(TypeError):
            minimize(2, None)
        with self.assertRaises(ValueError):
            minimize(2, (1,), (1,))
        with self.assertRaises(ValueError):
            minimize(0, (1,))
        with self.assertRaises(TypeError):
            minimize(2, (0,)).evaluate(True)
        with self.assertRaises(ValueError):
            minimize(2, (0,)).evaluate(4)

    def test_variable_names_and_serialization(self):
        result = minimize(2, (1, 3))
        self.assertEqual(result.expression(("high", "low")), "low")
        for names in (("a",), ("a", "a"), ("a", "not valid"), ("a", 2)):
            with self.assertRaises(ValueError):
                result.expression(names)
        record = json.loads(json.dumps(result.to_dict()))
        self.assertEqual(record["cost"], {"terms": 1, "literals": 1})
        self.assertEqual(record["prime_implicant_chart"], {"-1": [1, 3]})

    def test_cli(self):
        command = [sys.executable, str(ROOT / "python/quine_mccluskey.py"),
                   "--num-vars", "3", "--minterms", "0,1,2", "5", "6", "7", "--json"]
        first = subprocess.run(command, check=True, capture_output=True, text=True)
        second = subprocess.run(command, check=True, capture_output=True, text=True)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(json.loads(first.stdout)["cost"], {"terms": 3, "literals": 6})
        invalid = subprocess.run(command[:-1] + ["--dont-cares", "0"],
                                 capture_output=True, text=True)
        self.assertEqual(invalid.returncode, 2)
        self.assertIn("must be disjoint", invalid.stderr)


if __name__ == "__main__":
    unittest.main()
