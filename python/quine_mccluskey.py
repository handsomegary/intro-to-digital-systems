"""Exact, deterministic two-level sum-of-products minimization.

Quine-McCluskey generates prime implicants. Petrick's method then completes
the cover, including cases where essential prime implicants are insufficient.
The objective is fewest product terms, then fewest literals. Equal-cost
solutions are ordered lexicographically by their sorted 0/1/- patterns.

This is an educational exact solver, not a scalable synthesis tool. Both prime
generation and exact covering can require exponential time and memory.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from typing import Iterable, Sequence


def _validated_terms(values: Iterable[int], width: int, label: str) -> tuple[int, ...]:
    try:
        terms = tuple(values)
    except TypeError as error:
        raise TypeError(f"{label} must be an iterable of integers") from error
    for value in terms:
        if type(value) is not int:
            raise TypeError(f"{label} values must be integers, not {type(value).__name__}")
        if not 0 <= value < (1 << width):
            raise ValueError(f"{label} value {value} does not fit {width} variables")
    return tuple(sorted(set(terms)))


def _pattern(bits: int, mask: int, width: int) -> str:
    return "".join("-" if mask & (1 << bit) else str((bits >> bit) & 1)
                   for bit in reversed(range(width)))


def _covers(pattern: str, value: int) -> bool:
    return all(char == "-" or int(char) == ((value >> bit) & 1)
               for bit, char in enumerate(reversed(pattern)))


def _prime_patterns(width: int, allowed: tuple[int, ...],
                    required: tuple[int, ...]) -> tuple[str, ...]:
    # A cube is (fixed-one bits, don't-care mask); masked bits remain zero.
    current = {(value, 0) for value in allowed}
    primes: set[tuple[int, int]] = set()
    while current:
        combined: set[tuple[int, int]] = set()
        next_round: set[tuple[int, int]] = set()
        for bits, mask in current:
            for position in range(width):
                bit = 1 << position
                if (bits | mask) & bit:
                    continue
                partner = (bits | bit, mask)
                if partner in current:
                    combined.update(((bits, mask), partner))
                    next_round.add((bits, mask | bit))
        primes.update(current - combined)
        current = next_round
    patterns = (_pattern(bits, mask, width) for bits, mask in primes)
    # A prime covering only don't-cares is irrelevant to the required cover.
    return tuple(sorted(pattern for pattern in patterns
                        if any(_covers(pattern, value) for value in required)))


def _cover_key(indices: frozenset[int], primes: tuple[str, ...]) -> tuple:
    patterns = tuple(primes[index] for index in sorted(indices))
    return (len(indices), sum(len(p) - p.count("-") for p in patterns), patterns)


def _absorb(products: set[frozenset[int]],
            primes: tuple[str, ...]) -> set[frozenset[int]]:
    # X + XY = X: a strict superset costs more terms, so it cannot be optimal.
    survivors: list[frozenset[int]] = []
    for product in sorted(products, key=lambda item: _cover_key(item, primes)):
        if not any(earlier <= product for earlier in survivors):
            survivors.append(product)
    return set(survivors)


@dataclass(frozen=True)
class Result:
    """One exact minimum SOP and its prime-implicant chart.

    Patterns run from the most significant variable to the least significant:
    1 is positive, 0 is complemented, and - omits that variable. An empty
    implicants tuple denotes constant 0; a single all-dash pattern denotes 1.
    With zero variables the constant-1 pattern is the empty string.
    """

    num_vars: int
    minterms: tuple[int, ...]
    dont_cares: tuple[int, ...]
    prime_implicants: tuple[str, ...]
    essential_prime_implicants: tuple[str, ...]
    implicants: tuple[str, ...]

    @property
    def cost(self) -> tuple[int, int]:
        """Return (number of product terms, number of literals)."""
        return len(self.implicants), sum(p.count("0") + p.count("1")
                                        for p in self.implicants)

    def expression(self, variable_names: Sequence[str] | None = None) -> str:
        """Return an ASCII SOP using *, +, and a trailing prime for NOT."""
        if variable_names is None:
            names = tuple(chr(65 + index) if index < 26 else f"x{index}"
                          for index in range(self.num_vars))
        else:
            names = tuple(variable_names)
            if len(names) != self.num_vars:
                raise ValueError("one variable name is required per input bit")
            if any(not isinstance(name, str) or not name.isidentifier() for name in names):
                raise ValueError("variable names must be nonempty identifiers")
            if len(set(names)) != len(names):
                raise ValueError("variable names must be distinct")
        terms = ["*".join(name + ("'" if bit == "0" else "")
                          for name, bit in zip(names, pattern) if bit != "-") or "1"
                 for pattern in self.implicants]
        return " + ".join(terms) or "0"

    def evaluate(self, minterm: int) -> bool:
        """Evaluate the chosen implementation, including its don't-care choices."""
        value = _validated_terms((minterm,), self.num_vars, "input")[0]
        return any(_covers(pattern, value) for pattern in self.implicants)

    def to_dict(self) -> dict:
        """Return JSON-serializable results; chart columns are required minterms."""
        return {
            "num_vars": self.num_vars,
            "minterms": list(self.minterms),
            "dont_cares": list(self.dont_cares),
            "prime_implicants": list(self.prime_implicants),
            "essential_prime_implicants": list(self.essential_prime_implicants),
            "implicants": list(self.implicants),
            "expression": self.expression(),
            "cost": {"terms": self.cost[0], "literals": self.cost[1]},
            "prime_implicant_chart": {
                pattern: [value for value in self.minterms if _covers(pattern, value)]
                for pattern in self.prime_implicants
            },
        }


def minimize(num_vars: int, minterms: Iterable[int],
             dont_cares: Iterable[int] = ()) -> Result:
    """Find an exact minimum SOP; duplicate entries are normalized to sets.

    num_vars must be a nonnegative integer (not bool). The on-set and don't-care
    set must be disjoint, with integer entries from 0 through 2**num_vars - 1.
    All other minterms are required zeros. Width is explicit, never inferred
    from the largest listed minterm. For an empty on-set, return constant 0.
    """
    if type(num_vars) is not int:
        raise TypeError("num_vars must be an integer, not bool or a real number")
    if num_vars < 0:
        raise ValueError("num_vars must be nonnegative")
    on = _validated_terms(minterms, num_vars, "minterms")
    dc = _validated_terms(dont_cares, num_vars, "dont_cares")
    if set(on) & set(dc):
        raise ValueError("minterms and dont_cares must be disjoint")
    if not on:
        return Result(num_vars, on, dc, (), (), ())

    primes = _prime_patterns(num_vars, tuple(sorted(set(on) | set(dc))), on)
    chart = {value: frozenset(index for index, pattern in enumerate(primes)
                             if _covers(pattern, value)) for value in on}
    essentials = frozenset(next(iter(options)) for options in chart.values()
                           if len(options) == 1)
    # Multiply the remaining coverage clauses, absorbing redundant products.
    clauses = {options for options in chart.values() if not options & essentials}
    products = {frozenset()}
    for clause in sorted(clauses, key=lambda item: (len(item), tuple(sorted(item)))):
        products = _absorb({product | {index}
                            for product in products for index in clause}, primes)
    covers = {product | essentials for product in products}
    chosen = min(covers, key=lambda item: _cover_key(item, primes))
    return Result(num_vars, on, dc, primes,
                  tuple(primes[index] for index in sorted(essentials)),
                  tuple(primes[index] for index in sorted(chosen)))


def _parse_terms(tokens: list[str]) -> list[int]:
    return [int(piece, 10) for token in tokens for piece in token.replace(",", " ").split()]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-vars", type=int, required=True, metavar="N")
    parser.add_argument("--minterms", nargs="*", default=[], metavar="M",
                        help="required ones; decimal values separated by spaces or commas")
    parser.add_argument("--dont-cares", nargs="*", default=[], metavar="D",
                        help="optional minterms that may be either zero or one")
    parser.add_argument("--json", action="store_true", help="print machine-readable results")
    args = parser.parse_args(argv)
    try:
        result = minimize(args.num_vars, _parse_terms(args.minterms), _parse_terms(args.dont_cares))
    except (TypeError, ValueError) as error:
        parser.error(str(error))
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        print(f"Variables: {result.num_vars} (leftmost is most significant)")
        print(f"Minterms: {list(result.minterms)}")
        print(f"Don't-cares: {list(result.dont_cares)}")
        print("Prime implicants (pattern: covered required minterms):")
        for pattern, covered in result.to_dict()["prime_implicant_chart"].items():
            suffix = " [essential]" if pattern in result.essential_prime_implicants else ""
            print(f"  {pattern or '(zero variables)'}: {covered}{suffix}")
        if not result.prime_implicants:
            print("  none needed")
        print(f"Minimum SOP: {result.expression()}")
        print(f"Cost: {result.cost[0]} terms, {result.cost[1]} literals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
