# to convert the real or mock json into pandas dataframe
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
from pathlib import Path
import numpy as np #having issues catching inf values in df con
from supabase import create_client, Client
#importing mock and real functions froms structurer to make as simple as possible to switch
from structurer import blob_json_con, read_blob
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
TABLE_NAME = "imdb_titles"

def make_json_completely_safe(obj):
    if isinstance(obj, dict):
        return {k: make_json_completely_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_completely_safe(v) for v in obj]
    elif isinstance(obj, (float, np.floating)):
        if not np.isfinite(obj):
            return None
        return float(obj)
    else:
        return obj

def load_json_to_df(USE_MOCK = 'False'):
    blob = read_blob()
    json_data = blob_json_con(blob)

    df = pd.DataFrame(json_data)
# Ensure list/array columns are proper lists
    for col in ['genres', 'directors', 'writers']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: x if isinstance(x, list) else [])

# Convert numeric columns to floats and replace invalids
    for col in ['aggregateRating', 'reviewCount']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            df[col] = df[col].replace([np.inf, -np.inf], np.nan)
            df[col] =df[col].where(pd.notnull(df[col]),None)
    df['extracted_at'] = datetime.utcnow().isoformat() + "Z"
    if 'year' in df.columns:
        df['year'] = pd.to_numeric(df['year'], errors='coerce').astype("Int64")  # keep as nullable integer
        df['year'] = df['year'].where(df['year'].notnull(), None)

    df = df.where(pd.notnull(df), None)
    return df

def insert_data_to_supabase(df):
    data = df.to_dict(orient='records')
    supabase.table(TABLE_NAME).upsert(data, on_conflict="title").execute()
    print(f"Inserted {len(data)} records into {TABLE_NAME} table.")
        
#test function i had gpt generate
if __name__ == "__main__":
    print("Testing loader.py with mock JSON...")
    try:
        df = load_json_to_df(USE_MOCK=False)
        records = df.to_dict(orient='records')
        records = [make_json_completely_safe(r) for r in records]
        supabase.table(TABLE_NAME).insert(records).execute()
        print(f"Loaded {len(df)} records into DataFrame successfully!")
        print("First record preview:")
        print(df.iloc[0].to_dict())
    except Exception as e:
        print("Error during loading mock JSON:", e)