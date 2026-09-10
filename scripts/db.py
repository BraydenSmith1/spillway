"""db.py — one place that knows how to reach the database."""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


def url():
    return (
        f"postgresql+psycopg2://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}"
        f"@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
    )


engine = create_engine(url(), pool_pre_ping=True)


def query(sql, **params):
    """Run SQL, get a pandas DataFrame back."""
    import pandas as pd
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn, params=params)


def execute(sql, **params):
    """Run SQL that returns nothing (CREATE, INSERT, DELETE)."""
    with engine.begin() as conn:
        conn.execute(text(sql), params)


if __name__ == "__main__":
    print(query("SELECT version() AS v, now() AS t"))