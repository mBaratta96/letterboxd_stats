import pandas as pd

def read_watched_films(df: pd.DataFrame, path: str) -> pd.DataFrame:
    df_profile = pd.read_csv(path)
    df['watched'] = df['title'].isin(df_profile['Name'])
    return df
