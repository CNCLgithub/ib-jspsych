import marimo

__generated_with = "0.13.15"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import json
    import numpy as np
    import polars as pl
    import altair as alt
    from collections.abc import Callable
    from functools import partial

    alt.theme.enable("carbong100")
    return Callable, alt, json, np, partial, pl


@app.cell
def _():
    exp = "target-ensemble"
    version = "2025-06-09_W96KtK-v2-all"
    return exp, version


@app.cell
def _(exp, json, np, pl, version):
    col_count_schema = {"scene": pl.UInt8, "count": pl.Int64}
    # repair version name for manifest; is the same for main and swapped experiments
    _version = (
        version.replace("-swapped", "").replace("-batch2", "").replace("-all", "")
    )
    with open(f"data/{exp}-{_version}-manifest.json", "r") as file:
        manifest = json.load(file)

    gt_counts_raw = manifest["counts"]
    nscenes = len(gt_counts_raw)
    gt_counts = pl.DataFrame(
        {"scene": np.arange(nscenes) + 1, "count": gt_counts_raw},
        schema=col_count_schema,
    )
    gt_counts
    return


@app.cell
def _(pl):
    parent = pl.Enum(["Grouped", "Alone"])
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
    return count_schema, notice_schema, parent


@app.cell
def _(count_schema, notice_schema, parent, pl):
    def load_behavior(path: str):
        noticed_df = (
            pl.read_csv(path + "_noticed.csv", schema=notice_schema)
            .with_columns(
                parent=pl.when(pl.col("grouped"))
                .then(pl.lit("Grouped"))
                .otherwise(pl.lit("Alone"))
                .cast(parent)
            )
            .select(pl.all().exclude("grouped"))
        )

        count_df = pl.read_csv(
            path + "_counts.csv", schema=count_schema
        ).with_columns(order=pl.col("order").rank().over("uid"))

        return (noticed_df, count_df)
    return (load_behavior,)


@app.cell
def dataload(exp, load_behavior, version):
    main_noticed, main_count = load_behavior(f"data/{exp}-{version}")
    ctrl_noticed, ctrl_count = load_behavior(f"data/{exp}-{version}-swapped")
    return ctrl_noticed, main_noticed


@app.cell
def _(pl):
    def notice_metric(df: pl.DataFrame):
        noticed_by_group = (
            df.group_by("parent").agg(pl.mean("noticed")).sort("parent")
        )
        grouped, alone = noticed_by_group["noticed"]
        return alone - grouped
    return (notice_metric,)


@app.cell
def _(Callable, notice_metric, partial, pl):
    def difference_metric(metric: Callable, a: pl.DataFrame, b: pl.DataFrame):
        return metric(a) - metric(b)


    diff_notice_metric = partial(difference_metric, notice_metric)
    diff_notice_metric.__doc__ = "The difference in noticing differences"
    return (diff_notice_metric,)


@app.cell
def _(Callable, np, pl):
    def ordinary_by_subj(df: pl.DataFrame):
        sample = (
            df.group_by("uid")
            .agg(pl.all())
            .sample(fraction=1.0, with_replacement=True)
            .explode(pl.all().exclude("uid"))
        )
        return sample


    def bootstrap(
        metric: Callable,
        a: pl.DataFrame,
        b: pl.DataFrame,
        rng: Callable,
        steps: int = 10000,
    ):
        samples = np.zeros(steps)
        for i in range(steps):
            samples[i] = metric(rng(a), rng(b))

        return samples
    return bootstrap, ordinary_by_subj


@app.cell
def _(
    bootstrap,
    ctrl_noticed,
    diff_notice_metric,
    main_noticed,
    np,
    ordinary_by_subj,
):
    samples = bootstrap(
        diff_notice_metric, main_noticed, ctrl_noticed, ordinary_by_subj
    )
    pval = np.mean(samples < 0.0)
    return pval, samples


@app.cell
def _(alt, pl, samples):
    _df = pl.DataFrame({"samples": samples})
    alt.Chart(_df).mark_bar().encode(
        alt.X("samples:Q").bin(maxbins=40),
        y="count()",
    ).properties(title="Main Exp - Ctrl Exp")
    return


@app.cell
def _(mo, pval):
    mo.md(f"""p-value = {pval}""")
    return


@app.cell
def _(main_noticed, pl):
    print(
        main_noticed.group_by("parent")
        .agg(pl.col("noticed").mean(), pl.len())
        .sort("parent")
    )
    return


@app.cell
def _(ctrl_noticed, pl):
    print(
        ctrl_noticed.group_by("parent")
        .agg(pl.col("noticed").mean(), pl.len())
        .sort("parent")
    )
    return


if __name__ == "__main__":
    app.run()
