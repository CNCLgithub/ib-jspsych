import marimo

__generated_with = "0.13.8"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import numpy as np
    import polars as pl
    import altair as alt

    alt.theme.enable("carbong100")
    return (pl,)


@app.cell
def versioning():
    exp = "target-ensemble"
    version = "pilot-v1"
    return exp, version


@app.cell
def _(exp, pl):
    col_count_schema = {"scene": pl.UInt8, "count": pl.Int64}
    gt_counts = pl.read_csv(
        f"data/{exp}_collision_counts.csv", schema=col_count_schema
    )
    return (gt_counts,)


@app.cell
def notice(exp, pl, version):
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
    noticed_df = (
        pl.read_csv(f"data/{exp}-{version}_noticed.csv", schema=notice_schema)
        .with_columns(
            parent=pl.when(pl.col("grouped"))
            .then(pl.lit("Grouped"))
            .otherwise(pl.lit("Alone"))
            .cast(parent)
        )
        .select(pl.all().exclude("grouped"))
    )
    return (noticed_df,)


@app.cell
def counts(exp, pl, version):
    count_schema = {
        "uid": pl.UInt16,
        "scene": pl.UInt8,
        "count": pl.Int64,
        "rt": pl.Float32,
        "order": pl.UInt8,
    }
    count_df = (
        pl.read_csv(f"data/{exp}-{version}_counts.csv", schema=count_schema)
        .with_columns(order = pl.col('order').rank().over('uid'))
    )
    print(count_df)
    return (count_df,)


@app.cell
def _(noticed_df):
    noticed_df
    return


@app.cell
def _(count_df, gt_counts, pl):
    count_errors = (
        count_df.rename({"count": "measured"})
        #.filter(pl.col('order') == pl.col('order').max().over('uid'))
        .select(["uid", "scene", "measured"])
        .join(gt_counts, on="scene", how="left")
        .with_columns(error=abs(pl.col("count") - pl.col("measured")))
        .group_by('uid')
        .agg(pl.col('error').mean())
    )
    print(count_errors)
    return (count_errors,)


@app.cell
def _(count_errors, noticed_df, pl):
    noticed_and_perf = (
        noticed_df.join(count_errors, on="uid")
        .group_by("noticed", "parent")
        .agg(pl.mean("error"), pl.len())
        .sort("noticed", "parent")
    )
    print(noticed_and_perf)
    return


@app.cell
def _(noticed_df, pl):
    noticed_by_group = (
        noticed_df.group_by("parent")
        .agg(pl.mean("noticed"), pl.len())
        .sort("parent")
    )
    print(noticed_by_group)
    return


@app.cell
def _(noticed_df, pl):
    noticed_by_scene = (
        noticed_df.group_by("scene", "parent")
        .agg(pl.mean("noticed"), pl.len())
        .sort("scene", "parent")
    )
    return (noticed_by_scene,)


@app.cell
def _(mo, noticed_by_scene):
    mo.ui.table(noticed_by_scene)
    return


if __name__ == "__main__":
    app.run()
