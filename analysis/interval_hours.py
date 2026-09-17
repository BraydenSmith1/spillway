"""
interval_hours.py — how many hours does one SCED row represent?

Do not hardcode this. ERCOT changed SCED cadence at RTC+B:

    through 2025-12-04    96 runs/day    15-minute intervals   (MW / 4)
    from   2025-12-10    ~290 runs/day    5-minute intervals   (MW / 12)

Assuming 5 minutes across a window that spans the boundary understates
pre-RTC energy by a factor of three. Percentages survive it (the factor
cancels between numerator and denominator) but every MWh, GWh and TWh
figure does not.

Usage — join your per-day aggregate to this and multiply MW by `hrs`:

    from analysis.interval_hours import interval_hours_sql
    sql = f'''
        WITH {interval_hours_sql(FILES)},
             daily AS (SELECT "SCED Timestamp"::DATE AS day, SUM(HSL) AS mw ...)
        SELECT SUM(mw * hrs) AS mwh
        FROM daily JOIN interval_hours USING (day)
    '''

Deriving it from the data rather than a constant keeps it correct through any
future cadence change too.
"""


def interval_hours_sql(files, name="interval_hours"):
    """SQL CTE mapping each date to the hours one SCED row covers.

    `files` may be a glob string or a list of them — whatever read_parquet
    accepts.
    """
    src = repr(files if isinstance(files, str) else list(files))
    return (f"{name} AS (\n"
            f'    SELECT "SCED Timestamp"::DATE AS day,\n'
            f'           24.0 / COUNT(DISTINCT "SCED Timestamp") AS hrs\n'
            f"    FROM read_parquet({src})\n"
            f"    GROUP BY 1\n"
            f")")
