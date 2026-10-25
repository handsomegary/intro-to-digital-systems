# Exact Quine-McCluskey minimizer

`quine_mccluskey.py` is an independent English rewrite of the course demonstration. It uses Python 3.10 or newer and only the standard library. It has no NumPy dependency, random input, preallocated implicant limit, or hidden input-width inference.

The rewrite implements the complete two-level sum-of-products workflow:

1. Combine adjacent cubes to generate prime implicants.
2. Construct the prime-implicant chart for required minterms.
3. Select essential prime implicants.
4. Solve every remaining chart column exactly using Petrick's method and absorption.
5. Minimize the number of product terms, then the total literal count. For equal costs, choose the lexicographically first sorted tuple of patterns, using ordinary string order (`-`, `0`, `1`).

The source demonstration stopped at the remaining chart and left Petrick's method as an exercise. Essential implicants alone need not implement the function. This rewrite completes that step and reports both the complete prime chart and the selected minimum cover. It does not claim to minimize a multilevel circuit, delay, or physical gate area.

## Command line

From the repository root:

```sh
python python/quine_mccluskey.py --num-vars 5 --minterms 5,13,15,19,22,23,24,26 --dont-cares 0,3,7,8,12,16,18,21,27,30,31
```

This is midterm Question 3. Its minimum cost is three product terms and eight literals. Add `--json` to receive a machine-readable result. Decimal lists may use commas or spaces. If `--minterms` is omitted or empty, the function has no required ones and the minimum implementation is constant zero.

An example requiring nonessential prime implicants is:

```sh
python python/quine_mccluskey.py --num-vars 3 --minterms 0,1,2,5,6,7 --json
```

This function has no essential prime implicants. An exact minimum still has three terms and six literals.

## Python API

When the `python` directory is on the import path:

```python
from quine_mccluskey import minimize

result = minimize(3, [0, 1, 2, 5, 6, 7])
print(result.expression())
print(result.implicants)
print(result.cost)           # (3, 6)
print(result.evaluate(0))    # True
record = result.to_dict()
```

The result is immutable. It contains `num_vars`, normalized `minterms` and `dont_cares`, `prime_implicants`, `essential_prime_implicants`, and the selected `implicants`. `to_dict()` also includes the chart and an ASCII expression. `expression(variable_names)` accepts distinct identifier names, one per variable. Default names are `A` through `Z`, then `x26`, `x27`, and so on.

Pattern characters run from the most significant input bit to the least significant. For example, `1-0` means `A*C'`. A dash removes a literal. In expressions, `*` means AND, `+` means OR, and a trailing apostrophe means NOT. The chart includes required-one columns; don't-cares may enlarge cubes but need not be covered. A prime containing only don't-cares is omitted as irrelevant to the required cover.

## Input and edge-case rules

- Width is explicit and must be a nonnegative integer. Boolean values and floating-point values are rejected.
- All minterms are integers in `0 .. 2**num_vars - 1`. Values outside this range are rejected; width never changes to accommodate them.
- Duplicate entries within either set are deduplicated. An entry appearing in both the on-set and the don't-care set is an error.
- Unlisted minterms are required zeros. A don't-care can evaluate to either zero or one in the chosen implementation.
- Constant zero has no product terms, cost `(0, 0)`, and an empty `implicants` tuple.
- Constant one has one zero-literal product term, cost `(1, 0)`, and a single all-dash pattern.
- Zero variables are supported: the only input assignment is minterm `0`. Its constant-one pattern is the empty string, so its selected cover is `("",)`. This differs from the empty cover `()` for constant zero.

## Verification and limits

Run the tests from the repository root:

```sh
python -m unittest discover -s tests -p test_quine_mccluskey.py -v
```

The independent oracle enumerates all ternary cubes directly and solves their coverage problem by dynamic programming. It does not reuse the minimizer's combination, prime-selection, or Petrick routines. Tests exhaust all partially specified Boolean functions through three variables, add deterministic four-variable cases, check the five-variable exam problem, compare prime sets, and verify truth tables, constants, invalid inputs, and deterministic CLI output.

Exact Boolean minimization can require exponential time and memory. This implementation is intended for small educational problems. It never silently substitutes a heuristic result or declares an incomplete cover optimal. A large case may take a long time or exhaust available resources; use an established synthesis tool when scalability matters.
