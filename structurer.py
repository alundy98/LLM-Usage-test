import json
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file  
import os
import numpy as np
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
DATA = BASE_DIR/ "data" / "raw_blob.txt"
#switches the pipeline from mock to using real credits
USE_MOCK =False
client = None
if not USE_MOCK:
    from openai import OpenAI
    endpoint = os.getenv("OPENAI_ENDPOINT")
    api_key = os.getenv("OPENAI_API_KEY")
    if not endpoint or not api_key:
        raise RuntimeError("Missing OPENAI_ENDPOINT or OPENAI_API_KEY in environment")
    client = OpenAI(base_url=endpoint, api_key=api_key)

def read_blob(file_path = DATA):
    if not file_path.exists():
        raise FileNotFoundError(f"{file_path} does not exist.")
    
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

#I kepy having out of range float errors when testing JSON compliance, so this is fix
def safe_float(value):
    try:
        f = float(value)
        if not np.isfinite(f):
            return None
        return f
    except (ValueError, TypeError):
        return None

def blob_json_con(blob: str):
    
    schema = {
        "id": "IMDb ID of the title",
        "title": "Movie or series title",
        "summary": "Short description/plot",
        "year": "Release year if known",
        "genres": "List or string of genres",
        "directors": "List of directors",
        "writers": "List of writers",
        "aggregateRating": "Average user rating (float)",
        "reviewCount": "Number of user reviews (integer)",
        "source_url": "IMDb URL",
        "extracted_at": "Timestamp of extraction"
    }


    prompt = f"""
    You are a JSON generator.
    I will provide you with a blob of text containing movie and series details.
    Your task is to extract the relevant information and format it as a JSON array of objects.
    each object MUST strictly follow this schema:
    {json.dumps(schema, indent=2)}

    Input data:
    {blob}
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    raw_output = response.choices[0].message.content

    try:
        parsed = json.loads(raw_output)
    except json.JSONDecoderError as e:
        raise ValueError("Failed to parse JSON output from the model.") from e
    
    for obj in parsed:
        obj['extracted_at'] = datetime.utcnow().isoformat() + "Z"

    return parsed

#Testing the function:
if __name__ == "__main__":
    blob = read_blob()
    structured_data = blob_json_con(blob)
    print(f"Extracted {len(structured_data)} records.")
    print("First record:\n", json.dumps(structured_data[0], indent=2))