from pytrends.request import TrendReq
import pandas as pd
import time
import requests
import os
import json
from datetime import datetime
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()

AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
AIRTABLE_TABLE_NAME = 'trend_signals'
AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')

if not AIRTABLE_BASE_ID or not AIRTABLE_API_KEY:
    raise ValueError("Missing AIRTABLE_BASE_ID or AIRTABLE_API_KEY in environment variables")

def delete_old_records():
    """Delete records older than 14 days from Airtable."""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }

    # Calculate date 14 days ago
    threshold_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

    # Step 1: Query records older than 2 weeks
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    params = {
        'filterByFormula': f"IS_BEFORE({{date}}, '{threshold_date}')",
        'pageSize': 100
    }

    def get_old_records():
        old_record_ids = []
        offset = None
        while True:
            if offset:
                params['offset'] = offset
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            for record in data.get('records', []):
                old_record_ids.append(record['id'])
            offset = data.get('offset')
            if not offset:
                break
        return old_record_ids

    # Step 2: Delete records in batches (max 10 per request)
    def delete_records(record_ids):
        for i in range(0, len(record_ids), 10):
            batch = record_ids[i:i+10]
            delete_url = f"{url}"
            payload = {'records': batch}
            response = requests.delete(delete_url, headers=headers, json=payload)
            response.raise_for_status()

    old_records = get_old_records()
    if old_records:
        delete_records(old_records)
        print(f"Deleted {len(old_records)} records older than {threshold_date}.")
    else:
        print("No records older than 2 weeks to delete.")

def upload_to_airtable(trendy_keywords_dict):
    """Upload trending keywords to Airtable."""
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    upload_date = datetime.now().strftime('%Y-%m-%d')
    
    for keyword, score in trendy_keywords_dict.items():
        # Create Google Trends source URL
        time.sleep(0.5)  # Short wait before processing results
        encoded_keyword = keyword.replace(' ', '%20')
        source_url = f"https://trends.google.com/trends/explore?q={encoded_keyword}&geo=PL"
        
        payload = {
            "fields": {
                "date": upload_date,
                "platform": "Google Trends",
                "keyword": keyword,
                "score": float(score/10),
                "source_url": source_url
            }
        }
        print(json.dumps(payload, indent=2))
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Uploaded: {keyword} with score {float(score/10)}")
        except requests.exceptions.RequestException as e:
            print(f"Failed to upload {keyword}: {e}")

# Delete old records first
delete_old_records()

# Initialize connection (Polish language and CEST timezone)
pytrends = TrendReq(hl='pl-PL', tz=120)

seed_keywords = [
    "remont mieszkania",
    "remont domu", 
    "malowanie ścian",
    "malowanie sufitu",
    "przygotowanie ścian do malowania",
    "jak pomalować ściany",
    "farba do salonu",
    "farba do kuchni",

    "farba do wnętrz",
    "jak wybrać farbę",
    "kolory farb do wnętrz",
    "farby do pokoju dziecięcego",
    "farby odporne na wilgoć",
    "malowanie pokoju",
    "malowanie mebli",
    "tapetowanie ścian",
    "dekoracja wnętrz",
    "renowacja ścian",
    "jak zrobić remont",
    "tanie farby do malowania",
    "profesjonalne malowanie"
]

trendy_keywords = {}

for kw in seed_keywords:
    print(f"Processing keyword: {kw}")
    try:
        time.sleep(90)  # Wait to avoid being blocked
        pytrends.build_payload([kw], cat=0, timeframe='now 7-d', geo='PL', gprop='')
        related_queries = pytrends.related_queries()
        
        if kw in related_queries:
            top = related_queries[kw]['top']
            if top is not None:
                for _, row in top.iterrows():
                    keyword = row['query']
                    score = row['value']
                    trendy_keywords[keyword] = score * 0.75

            rising = related_queries[kw]['rising']
            if rising is not None:
                for _, row in rising.iterrows():
                    keyword = row['query']
                    score = row['value']
                    trendy_keywords[keyword] = score * 1.25
        

        
    except Exception as e:
        print(f"Error processing {kw}: {e}")
        continue

print(f"Found {len(trendy_keywords)} trending keywords")
print("Trending keywords:", trendy_keywords)

# Upload to Airtable
if trendy_keywords:
    print(trendy_keywords)
    upload_to_airtable(trendy_keywords)
    print("Upload to Airtable completed!")
else:
    print("No trending keywords found to upload.")
