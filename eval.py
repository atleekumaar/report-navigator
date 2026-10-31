#!/usr/bin/env python3
"""
eval.py — Evaluate predicted answers against gold standard.

Computes the P5 competition metrics:
  Score = 0.75 * EM + 0.25 * CitationAcc

Usage:
    python eval.py --gold data/questions_with_answers.jsonl --pred data/predicted_answers.jsonl
    python eval.py   # uses defaults
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def load_jsonl(path: Path) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items
