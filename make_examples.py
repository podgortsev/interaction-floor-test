#!/usr/bin/env python3
"""
make_examples.py - writes two small example inputs for floor_test.py.

    python make_examples.py
    python floor_test.py examples/clean.csv
    python floor_test.py examples/contaminated.csv

Both are synthetic. In clean.csv the three neutral pairs sit at zero and one
audited pair really compounds. In contaminated.csv one neutral pair interacts,
the way a lexical instrument does, so the audited results cannot be read.
"""

import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "examples")


def write(name, pairs, n=150, seed=7):
    rng = random.Random(seed)
    path = os.path.join(OUT, name)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair", "kind", "item", "none", "a", "b", "both"])
        for pair, kind, inter in pairs:
            for i in range(n):
                base = rng.gauss(0, 1)
                w.writerow([pair, kind, f"case{i:03d}",
                            round(base + rng.gauss(0, .3), 4),
                            round(base - .3 + rng.gauss(0, .3), 4),
                            round(base - .3 + rng.gauss(0, .3), 4),
                            round(base - .6 + inter + rng.gauss(0, .3), 4)])
    print(f"wrote {path}")


def main():
    os.makedirs(OUT, exist_ok=True)
    floors = [("cycling_x_bread", "floor", 0.0),
              ("dog_x_guitar", "floor", 0.0),
              ("tea_x_books", "floor", 0.0)]
    audited = [("screen_reader_x_age", "social", -0.4),
               ("adhd_x_deaf", "social", 0.0)]
    write("clean.csv", floors + audited)
    write("contaminated.csv",
          floors[:2] + [("tea_x_books", "floor", 0.5)] + audited)


if __name__ == "__main__":
    main()
