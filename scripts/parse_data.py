#!/usr/bin/env python3

import os
import json
import argparse
import numpy as np
import polars as pl


count_schema = {
    "uid": pl.UInt16,
    "scene": pl.UInt8,
    "count": pl.UInt8,
    "rt": pl.Float32,
    "order": pl.UInt8,
}

notice_schema = {
    "uid": pl.UInt16,
    "scene": pl.UInt8,
    "grouped" : pl.Boolean,
    "noticed" : pl.Boolean,
    "description" : pl.String,
    "rt": pl.Float32,
    "order": pl.UInt8,
}

def parse_count_response(results: dict, raw):
    scene = raw.get("trial_id", None)
    count = raw.get("response", None)
    rt = raw.get("rt", None)
    order = raw.get("trial_index", None)
    results["scene"].append(scene)
    results["count"].append(count)
    results["rt"].append(rt)
    results["order"].append(order)

def parse_notice_response(results: dict, raw):
    scene = raw.get("trial_id", None)
    noticed = raw.get("response", None) == 0
    rt = raw.get("rt", None)
    order = raw.get("trial_index", None)
    results["scene"] = [scene]
    results["grouped"] = raw.get("parent", None) == "ensemble"
    results["noticed"] = [noticed]
    results["rt"] = [rt]
    results["order"] = [order]
    if not noticed:
        results["description"] = ['']

def parse_notice_desc(results: dict, raw):
    desc = raw.get("response", None)["Q0"]
    results["description"] = [desc]


def parse_subj_data(timeline: dict, idx: int):
    # look for the start of the experimental trials
    exp_start = 0
    for i, step in enumerate(timeline):
        if step.get("type", None) == "comp_quiz" and step.get("correct", False):
            exp_start = i + 2  # two ahead
            break

    timeline = timeline[exp_start:-1]  # last step is the exit page
    counts = {k: [] for k in count_schema.keys()}
    noticed = {}

    for exp_trial in timeline:
        tt = exp_trial.get("trial_type", None)
        if tt == 'html-slider-response':
            parse_count_response(counts, exp_trial)
        elif tt == 'html-button-response':
            parse_notice_response(noticed, exp_trial)
        elif tt == 'survey-text':
            parse_notice_desc(noticed, exp_trial)

    counts["uid"] = idx
    noticed["uid"] = idx
    return (
        pl.DataFrame(counts, schema=count_schema),
        pl.DataFrame(noticed, schema=notice_schema),
    )


def main():
    parser = argparse.ArgumentParser(
        description="Parses JATOS data",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("dataset", type=str, help="Which scene dataset to use")
    args = parser.parse_args()
    raw = []
    with open(args.dataset, "r") as f:
        for (i, subj) in enumerate(f):
            try:
                raw.append(json.loads(subj))
            except:
                print(f'Could not interpret entry {i}')

    counts  = pl.DataFrame(schema=count_schema)
    noticed = pl.DataFrame(schema=notice_schema)
    for idx, subj in enumerate(raw):
        (c, n) = parse_subj_data(subj, idx)
        counts.vstack(c, in_place=True)
        noticed.vstack(n, in_place=True)

    print(counts)
    print(noticed)
    result_out = os.path.dirname(args.dataset)
    perf_out = os.path.basename(args.dataset).replace(".txt", "_counts.csv")
    noticed_out = os.path.basename(args.dataset).replace(
        ".txt", "_noticed.csv"
    )
    counts.write_csv(f"{result_out}/{perf_out}")
    noticed.write_csv(f"{result_out}/{noticed_out}")


if __name__ == "__main__":
    main()
