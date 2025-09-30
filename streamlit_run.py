import streamlit as st
import pandas as pd
import os
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

# Supabase credentials will come from Modal secrets later
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="IMDB Data Dashboard", layout="wide")
st.title("IMDB Data Dashboard")

@st.cache_data(ttl=600)
def get_records(limit=50):
    response = supabase.table("imdb_titles").select("*").order("extracted_at", desc=True).limit(limit).execute()
    data = response.data
    if data:
        df = pd.DataFrame(data)
        for col in ['genres', 'directors', 'writers']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else "")
        return df
    return pd.DataFrame()

# Sidebar filter
st.sidebar.header("Filters")
limit = st.sidebar.slider("Num Records", 50, 300, 50, step=10)
df = get_records(limit)

# Display data and charts
st.subheader(f"Latest {len(df)} Titles")
st.dataframe(df)

if not df.empty and 'aggregateRating' in df.columns:
    st.subheader("aggregateRating Distribution")
    st.bar_chart(df['aggregateRating'])

if not df.empty and "year" in df.columns:
    st.subheader("Num Titles per Year")
    st.bar_chart(df["year"].value_counts().sort_index())

if not df.empty and 'genres' in df.columns:
    from collections import Counter
    genre_list = []
    for g in df['genres']:
        genre_list.extend([x.strip() for x in g.split(",") if x.strip()])
    top_genres = pd.DataFrame(Counter(genre_list).most_common(10), columns=["Genre", "Count"])
    st.subheader("Popular Genres")
    st.bar_chart(top_genres.set_index("Genre"))

if not df.empty and 'writers' in df.columns:
    from collections import Counter
    writer_list = []
    for w in df['writers']:
        writer_list.extend([x.strip() for x in w.split(",") if x.strip()])
    top_writers = pd.DataFrame(Counter(writer_list).most_common(15), columns=["Writer", "Count"])
    st.subheader("Most popular Writers")
    st.bar_chart(top_writers.set_index("Writer"))

if not df.empty and 'reviewCount' in df.columns and 'title' in df.columns:
    st.subheader("Most Popular Shows (by Review Count)")
    top_shows = df[['title', 'reviewCount']].dropna().sort_values(by='reviewCount', ascending=False).head(15)
    st.bar_chart(top_shows.set_index("title")['reviewCount'])