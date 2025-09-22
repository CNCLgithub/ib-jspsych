import marimo

__generated_with = "0.14.12"
app = marimo.App(width="medium")


@app.cell
def _(ctrl_ex_rate, ctrl_noticed, main_ex_rate, main_noticed, mo, np):
    mo.md(
        f"""
    Count for Unswapped = {main_noticed.height}

    Count for Swapped = {ctrl_noticed.height}

    Exclusion Rate for Unswapped = {np.round(main_ex_rate * 100, decimals=1)}%

    Exclusion Rate for Swapped = {np.round(ctrl_ex_rate * 100, decimals=1)}%
    """
    )
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import json
    import numpy as np
    import polars as pl
    from collections.abc import Callable
    from functools import partial
    return json, np, pl


@app.cell
def _():
    exp = "target-ensemble"
    version = "2025-06-09_W96KtK-v2-preregistered"
    return exp, version


@app.cell
def _(pl):
    Parent = pl.Enum(["Grouped", "Alone"])
    Color = pl.Enum(["Light", "Dark"])
    Model = pl.Enum(["Full", "Just AC", "Crowding"])


    notice_schema = {
        "uid": pl.UInt16,
        "scene": pl.UInt8,
        "grouped": pl.Boolean,
        "noticed": pl.Boolean,
        "description": pl.String,
        "rt": pl.Float32,
        "order": pl.UInt8,
    }
    count_schema = {
        "uid": pl.UInt16,
        "scene": pl.UInt8,
        "count": pl.Int64,
        "rt": pl.Float32,
        "order": pl.UInt8,
    }
    return Color, Parent, count_schema, notice_schema


@app.cell
def _(exp, json, np, pl, version):
    col_count_schema = {"scene": pl.UInt8, "count": pl.Int64}
    # repair version name for manifest; is the same for main and swapped experiments
    base_version = (
        version.replace("-swapped", "")
        .replace("-batch2", "")
        .replace("-all", "")
        .replace("-replication", "")
        .replace("-v2", "")
        .replace("-preregistered", "")
    )

    with open(f"data/{exp}-{base_version}-manifest.json", "r") as file:
        manifest = json.load(file)

    gt_counts_raw = manifest["counts"]
    nscenes = len(gt_counts_raw)

    gt_counts = pl.DataFrame(
        {"scene": np.arange(nscenes) + 1, "count": gt_counts_raw},
        schema=col_count_schema,
    )
    return gt_counts, nscenes


@app.cell
def _(Parent, nscenes, pl):
    trial_design = pl.DataFrame(
        [
            [scene + 1, par]
            for par in ["Grouped", "Alone"]
            for scene in range(nscenes)
        ],
        schema={"scene": pl.UInt8, "parent": Parent},
        orient="row",
    )
    return (trial_design,)


@app.cell
def _(mo):
    PARAMS = mo.md(
        """
        - Screen notice responses: {screen_notice}
        - Minimum performance threshold: {perf_thresh}
        """
    ).batch(
        screen_notice=mo.ui.switch(
            value=True,
        ),
        perf_thresh=mo.ui.slider(
            start=0, stop=10, step=0.25, value=2.0, show_value=True
        ),
    )
    return (PARAMS,)


@app.cell
def _(PARAMS):
    PARAMS
    return


@app.cell
def _(
    PARAMS,
    Parent,
    count_schema,
    gt_counts,
    notice_schema,
    pl,
    trial_design,
):
    hit_list = ["split", "merge", "two", "2", "appear", "extra", "new"]


    def clean_hit(desc: str):
        return any(substring in desc for substring in hit_list)


    def calc_performance(df: pl.DataFrame):
        """Calculates the average absolute tracking error per subject"""
        count_errors = (
            df.rename({"count": "measured"})
            .select(["uid", "scene", "measured"])
            .join(gt_counts, on="scene", how="left")
            .with_columns(error=abs(pl.col("count") - pl.col("measured")))
            .group_by("uid")
            .agg(pl.col("error").mean())
        )
        return count_errors


    def exclude_subjects(notice: pl.DataFrame, counts: pl.DataFrame):
        """Excludes subjects that have an average absolute error > `ERROR_THRESH`"""
        perf = calc_performance(counts)
        passed = perf.filter(pl.col("error") < PARAMS.value["perf_thresh"]).select(
            "uid"
        )
        n_original = perf.select(pl.len()).item()
        n_passed = passed.select(pl.len()).item()
        ex_rate = (n_original - n_passed) / n_original
        # take first 120 subjects
        passed = passed.join(notice, on="uid", how="left").head(n=120)
        return (passed, ex_rate)


    def load_behavior(path: str):
        print(path)
        # Load bounce count data
        count_df = pl.read_csv(
            path + "_counts.csv", schema=count_schema
        ).with_columns(order=pl.col("order").rank().over("uid"))

        # Load notice data
        noticed_raw = pl.read_csv(path + "_noticed.csv", schema=notice_schema)
        # Exclude subjects that count poorly
        noticed_df, ex_rate = exclude_subjects(noticed_raw, count_df)
        # Optionally, filter out responses by description
        if PARAMS.value["screen_notice"]:
            noticed_df = noticed_df.with_columns(
                noticed=pl.when(pl.col("noticed"))
                .then(
                    pl.col("description").map_elements(
                        clean_hit, return_dtype=pl.Boolean
                    )
                )
                .otherwise(False),
            )
        # Add factor and design columns
        noticed_df = noticed_df.with_columns(
            parent=pl.when(pl.col("grouped"))
            .then(pl.lit("Grouped"))
            .otherwise(pl.lit("Alone"))
            .cast(Parent)
        ).select(pl.all().exclude("grouped"))
        noticed_df = trial_design.join(
            noticed_df, on=["scene", "parent"], how="left"
        ).fill_null(0.0)

        return (noticed_df, ex_rate)
    return (load_behavior,)


@app.cell
def _(Color, exp, load_behavior, pl, version):
    main_noticed, main_ex_rate = load_behavior(f"data/{exp}-{version}")
    main_noticed = main_noticed.with_columns(color=pl.lit("Light").cast(Color))
    ctrl_noticed, ctrl_ex_rate = load_behavior(f"data/{exp}-{version}-swapped")
    ctrl_noticed = ctrl_noticed.with_columns(color=pl.lit("Dark").cast(Color))

    all_noticed = pl.concat([main_noticed, ctrl_noticed])
    return ctrl_ex_rate, ctrl_noticed, main_ex_rate, main_noticed


@app.cell
def _(ctrl_noticed, mo):
    mo.ui.table(ctrl_noticed)
    return


@app.cell
def _(ctrl_noticed):
    print(ctrl_noticed.select("uid").unique())
    return


if __name__ == "__main__":
    app.run()
