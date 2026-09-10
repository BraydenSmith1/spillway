import pandas as pd, glob

f = sorted(glob.glob("data/raw/sced_60day/*.parquet"))[0]
df = pd.read_parquet(f)
print(df.columns.tolist())
print(df.head(3).T)