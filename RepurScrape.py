import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os

#this is a scraoer I made for a different project for tokusatsu show data, i am repurposing it here
LIST_URL = 'https://www.imdb.com/list/ls546064851/?sort=list_order,asc'
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def extract_title_ids(obj):
    ids = []
    if isinstance(obj, dict):
        if 'id' in obj and obj.get('id').startswith('tt'):
            ids.append(obj['id'])
        for v in obj.values():
            ids.extend(extract_title_ids(v))
    elif isinstance(obj, list):
        for item in obj:
            ids.extend(extract_title_ids(item))
    return ids

def scrape_imdb_ids(list_url):
    imdb_ids = []
    page = 1
    while True:
        url = f"{list_url}&page={page}"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            break
        soup = BeautifulSoup(response.content, 'html.parser')
        script_tag = soup.find('script', id='__NEXT_DATA__')
        if not script_tag:
            break
        try:
            data = json.loads(script_tag.string)
        except json.JSONDecodeError:
            break
        page_ids = extract_title_ids(data)
        if not page_ids:
            break
        imdb_ids.extend(page_ids)
        page += 1
        if len(page_ids) < 100:
            break
        time.sleep(0.5)
    imdb_ids = list(dict.fromkeys(imdb_ids))
    return imdb_ids

def get_title_details(imdb_id):
    url = f'https://www.imdb.com/title/{imdb_id}/'
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
    except requests.RequestException:
        return None
    match = re.search(r'<script type="application/ld\+json">\s*({.*?})\s*</script>', response.text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return None

    title = data.get('name')
    original_title = None
    if 'alternateName' in data and data['alternateName'] != title:
        original_title = data['alternateName']

    directors = []
    if data.get('director'):
        for d in data['director']:
            name = d.get('name')
            if name:
                directors.append(name)

    writers = []
    if data.get('creator'):
        for c in data['creator']:
            if c.get('@type') == 'Person' and c.get('name'):
                writers.append(c.get('name'))

    info = {
        'id': imdb_id,
        'title': title,
        'original_title': original_title,
        'year': data.get('datePublished'),
        'mpa_rating': data.get('contentRating'),
        'duration': data.get('duration'),
        'genres': ', '.join(data.get('genre', [])) if isinstance(data.get('genre'), list) else data.get('genre'),
        'keywords': data.get('keywords'),
        'directors': ', '.join(directors) if directors else None,
        'writers': ', '.join(writers) if writers else None,
        'description': data.get('description'),
        'poster': data.get('image'),
        'aggregateRating': data.get('aggregateRating', {}).get('ratingValue'),
        'reviewCount': data.get('aggregateRating', {}).get('ratingCount'),
        'trailer_url': data.get('trailer', {}).get('embedUrl') if data.get('trailer') else None
    }
    return info

#that is the end of the reused code, here is the new stuff to get a blob instead of the csv/cleaning
def main():
    os.makedirs("data",exist_ok=True)
    imdb_ids = scrape_imdb_ids(LIST_URL)
    if not imdb_ids:
        print("No IMDb IDs found.")
        return
    all_texts = []
    for i, imdb_id in enumerate(imdb_ids, start=1):
        details = get_title_details(imdb_id)
        if details:
            snippet = (
                f"Title: {details['title']} ({details['year']})\n"
                f"Original: {details.get('original_title')}\n"
                f"Genres: {details.get('genres')}\n"
                f"Directors: {details.get('directors')}\n"
                f"Writers: {details.get('writers')}\n"
                f"MPA Rating: {details.get('mpa_rating')}\n"
                f"Keywords: {details.get('keywords')}\n"
                f"Description: {details.get('description')}\n"
                f"Rating: {details.get('aggregateRating')} ({details.get('reviewCount')} reviews)\n"
                "--------------------------------------------\n"
            )
            all_texts.append(snippet)
            print(f"Processed {i}/{len(imdb_ids)}: {details['title']}")
        else:
            print(f"Failed to get details for {imdb_id}")
        time.sleep(0.5)
    with open("data/raw_blob.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(all_texts))
    
    print("\nRaw_blob.txt created")

if __name__ == '__main__':
    main()