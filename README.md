# Introduction to Digital Systems

An independent English reconstruction of the Academic Year 112 midterm and final examinations, with each question immediately followed by a worked solution. The archive also includes a rewritten exact Quine-McCluskey minimizer.

**[Read the combined questions and solutions](exam-solutions.pdf)**, or edit [main.tex](main.tex). All logic gates, state diagrams, and block diagrams are drawn in editable LaTeX/TikZ.

## Contents

| Material | Coverage |
| --- | --- |
| [Midterm](exams/midterm-112.tex) | All ten questions, including all three parts of Question 9: Boolean simplification, don't-cares, encoders, mux/demux, decoder maxterms, two's complement, division, BCD conversion, and signed comparison. |
| [Final](exams/final-112.tex) | The complete automatic-door design: state diagram, next-state and output equations, gate-level control, and an expanded five-second timer. |
| [Python minimizer](python/README.md) | Deterministic prime generation, essential implicants, and exact Petrick cover selection with don't-cares. |

Academic Year 112 corresponds to 2023-2024; the supplied sheets do not specify exact examination dates. The midterm's printed weights total **140%**, while the final has one **100%** problem. The weights are retained rather than silently normalized. There are no simulation-software-only questions in these two sheets, so every question is included.

The supplied solutions were checked as fallible references. Corrections include the Question 2 minterm index, the decoder's maxterm list, the division-by-five quotient logic, full-adder bit weights, and mislabeled signed-comparison outputs. Ambiguous encoder indexing is stated explicitly. The final's initialization condition is an added implementation assumption, clearly separated from its two operational sensor inputs.

## Run the Python program

The program requires Python 3.10 or newer and the standard library only:

```sh
python python/quine_mccluskey.py --num-vars 5 --minterms 5,13,15,19,22,23,24,26 --dont-cares 0,3,7,8,12,16,18,21,27,30,31
```

Add `--json` for structured output. The input width is explicit. The program minimizes product-term count first and literal count second, with deterministic tie-breaking. It completes the nonessential-prime selection that was left as an exercise in the source demonstration. See the [API, edge cases, and algorithm limits](python/README.md). Exact minimization can take exponential time and memory; the implementation is intended for small educational functions.

## Rebuild from a fresh download

Reading the PDF needs no development environment. Rebuilding requires Python 3.10+, XeLaTeX, the standard LaTeX mathematics/TikZ packages, and the TeX Gyre and Latin Modern fonts. There are no dependencies on the original local course folders or a circuit-simulation application.

On Debian or Ubuntu:

```sh
sudo apt-get update
sudo apt-get install texlive-xetex texlive-latex-extra texlive-science fonts-texgyre
```

From the repository root:

```sh
python tools/verify_archive.py
python tools/run_checks.py
python tools/build.py --publish
```

The last command performs two XeLaTeX passes and updates the combined PDF. Logs and intermediate files remain under the ignored `.build/` directory. With MiKTeX, install required packages beforehand: automatic package installation is disabled during the build. Use `--engine` to select an executable if XeLaTeX is not on your command search path.

For a single-chapter preview:

```sh
python tools/build.py --chapter midterm-112
python tools/build.py --chapter final-112
```

To inspect the generated PDF text and metadata as well:

```sh
python -m pip install pypdf
python tools/verify_archive.py --pdf
```

## Verification

[GitHub Actions](../../actions) checks the source archive, runs the Python verification, and rebuilds the book on Linux. The independent checks include:

- Exact cube enumeration for the small minimum-SOP exam answers and direct truth-table checks for the combinational designs.
- All 8,192 thirteen-bit inputs to the 24-cell BCD converter, plus division and three-full-adder arithmetic checks.
- All pairs of signed operands for widths one through eight: 87,380 comparisons.
- The door controller's state transitions, timer bit circuitry, timeout, retriggering, closing obstruction, and simultaneous detection/endpoint cases.
- An independent minimizer oracle covering every partially specified function through three variables, additional four-variable cases, and the five-variable exam example.

These tests validate Boolean and synchronous functional behavior. They do not model gate propagation delays or certify physical hardware. The rendered book is also checked for clipped equations, unreadable labels, overlapping wires, and omitted question material.

## Source and publication policy

[source-coverage.json](source-coverage.json) accounts for the five specifically requested source files using anonymous identifiers. The question sheets, reference-answer PDF/DOCX, photograph, and original demonstration program remain local. Unrelated loose exercises and diagram working files are outside the requested exam scope.

**Original question PDFs and original source images are not uploaded.** The only permitted public PDF is the rebuilt combined book. Public prose, code comments, diagram labels, and PDF metadata are in English, and no private local path or personal identity mapping is included. All sources needed to rebuild the published material are present in this repository.

This is an independent study edition, not an official course publication or answer key.
