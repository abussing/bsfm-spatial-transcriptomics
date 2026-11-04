#!/usr/bin/env python3
"""Freeze the animal-level recurrent spatial-expression panel.

Selection is genotype-blind and uses the primary GP screen quantity only.
Technical replicate sections are collapsed to the animal before recurrence is
counted.  The auxiliary random-location held-out score is reported but is not a
gate because it is absent for part of the authenticated reused-fit branch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main(args: argparse.Namespace) -> None:
    source = args.animal_summary.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(source)
    required = {"gene", "celltype", "animal", "spatial_fraction", "heldout_gain"}
    if not required.issubset(data.columns):
        raise RuntimeError(f"missing columns: {sorted(required - set(data.columns))}")

    animals = int(data["animal"].nunique())
    if animals != args.expected_animals:
        raise RuntimeError(f"expected {args.expected_animals} animals, found {animals}")
    passing = data[data["spatial_fraction"] >= args.spatial_fraction].copy()
    support = (
        passing.groupby(["gene", "celltype"], as_index=False)
        .agg(
            qualifying_animals=("animal", "nunique"),
            median_spatial_fraction=("spatial_fraction", "median"),
            median_heldout_gain=("heldout_gain", "median"),
            heldout_animals=("heldout_gain", "count"),
        )
    )
    best = (
        support.sort_values(
            ["gene", "qualifying_animals", "median_spatial_fraction", "celltype"],
            ascending=[True, False, False, True],
        )
        .groupby("gene", as_index=False)
        .head(1)
    )
    panel = best[best["qualifying_animals"] >= args.minimum_animals].copy()
    panel = panel.sort_values("gene").reset_index(drop=True)
    panel.insert(0, "gene_index", np.arange(len(panel), dtype=int))
    panel["selection_rule"] = (
        f"spatial_fraction>={args.spatial_fraction:g} in >="
        f"{args.minimum_animals}/{animals} distinct animals in at least one cell type"
    )
    panel.to_csv(output / "FROZEN_GENE_PANEL.csv", index=False)

    sensitivity = []
    for threshold in (0.05, 0.10, 0.15, 0.20, 0.25):
        counts = (
            data[data["spatial_fraction"] >= threshold]
            .groupby(["gene", "celltype"])["animal"]
            .nunique()
            .groupby("gene")
            .max()
        )
        for recurrence in (2, 3, 4, 6, 8, 10):
            sensitivity.append(
                {
                    "spatial_fraction_threshold": threshold,
                    "minimum_animals": recurrence,
                    "genes": int((counts >= recurrence).sum()),
                }
            )
    pd.DataFrame(sensitivity).to_csv(output / "PANEL_THRESHOLD_SENSITIVITY.csv", index=False)

    report = {
        "status": "PASS",
        "source": str(source),
        "source_sha256": sha256(source),
        "selection_is_genotype_blind": True,
        "unit_of_recurrence": "distinct animal, not section",
        "animals": animals,
        "spatial_fraction_definition": "GP signal variance / (GP signal variance + white-noise variance)",
        "spatial_fraction_threshold": args.spatial_fraction,
        "minimum_animals": args.minimum_animals,
        "qualification": "at least one of MIC/Mic, AST, OGC",
        "heldout_gain_used_for_selection": False,
        "heldout_reason": (
            "Random-location heldout gain is an auxiliary screen and is missing for "
            "part of the authenticated reused-fit branch; treating missing values as "
            "failures removes canonical microglial genes and biases the panel."
        ),
        "genes": int(len(panel)),
        "best_celltype_counts": panel["celltype"].value_counts().sort_index().to_dict(),
        "gene_order": panel["gene"].tolist(),
        "outputs": ["FROZEN_GENE_PANEL.csv", "PANEL_THRESHOLD_SENSITIVITY.csv"],
    }
    (output / "GENE_PANEL_CONTRACT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--animal-summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--spatial-fraction", type=float, default=0.10)
    parser.add_argument("--minimum-animals", type=int, default=2)
    parser.add_argument("--expected-animals", type=int, default=15)
    main(parser.parse_args())
