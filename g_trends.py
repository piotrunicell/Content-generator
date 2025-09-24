from pytrends.request import TrendReq
import pandas as pd
import time
import requests
import os
import json
from datetime import datetime
from datetime import timedelta
from dotenv import load_dotenv
import logging

def main(): 
    load_dotenv()

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID')
    AIRTABLE_TABLE_NAME = 'trends'
    AIRTABLE_API_KEY = os.environ.get('AIRTABLE_API_KEY')

    if not AIRTABLE_BASE_ID or not AIRTABLE_API_KEY:
        raise ValueError("Missing AIRTABLE_BASE_ID or AIRTABLE_API_KEY in environment variables")

    def delete_old_records():
        """Delete records older than 10 days from Airtable."""
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }

        threshold_date = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')

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
            msg = f"Deleted {len(old_records)} records older than {threshold_date}."
            logger.info(msg); print(msg)
        else:
            msg = "No records older than 10 days to delete."
            logger.info(msg); print(msg)

    def upload_to_airtable(trendy_keywords_dict, country):
        """Upload trending keywords to Airtable."""
        headers = {
            "Authorization": f"Bearer {AIRTABLE_API_KEY}",
            "Content-Type": "application/json"
        }
        
        url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
        upload_date = datetime.now().strftime('%Y-%m-%d')

        geo = "GB" if country == "UK" else country

        for keyword, score in trendy_keywords_dict.items():
            time.sleep(0.5)  # avoid hitting API too fast
            encoded_keyword = keyword.replace(' ', '%20')
            source_url = f"https://trends.google.com/trends/explore?q={encoded_keyword}&geo={geo}"
            
            payload = {
                "fields": {
                    "date": upload_date,
                    "platform": "Google Trends",
                    "country": country,
                    "keyword": keyword,
                    "score": float(score/10),
                    "source_url": source_url
                }
            }
            msg = json.dumps(payload, indent=2)
            logger.info(msg); print(msg)
            try:
                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()
                msg = f"Uploaded: {keyword} ({country}) with score {float(score/10)}"
                logger.info(msg); print(msg)
            except requests.exceptions.RequestException as e:
                msg = f"Failed to upload {keyword} ({country}): {e}"
                logger.info(msg); print(msg)

    # Step 1: Delete old records
    delete_old_records()

    # Step 2: Seed queries
    search_queries = {
        "PL": [
            # "remont mieszkania",
            # "remont domu", 
            # "malowanie ścian",
            # "malowanie sufitu",
            # "przygotowanie ścian do malowania",
            # "jak pomalować ściany",
            # "farba do salonu",
            # "farba do kuchni",
            # "farba do wnętrz",
            # "jak wybrać farbę",
            # "kolory farb do wnętrz",
            # "farby do pokoju dziecięcego",
            # "farby odporne na wilgoć",
            # "malowanie pokoju",
            # "malowanie mebli",
            # "tapetowanie ścian",
            # "dekoracja wnętrz",
            # "renowacja ścian",
            # "jak zrobić remont",
            # "tanie farby do malowania",
            "profesjonalne malowanie"
        ],
        "UK": [
            # "home renovation",
            # "DIY wall painting",
            # "decorative wall finishes",
            # "interior paint trends",
            # "wall texture paint",
            # "eco-friendly wall paint",
            # "decorative plaster",
            # "chalk paint furniture",
            # "microcement walls",
            # "concrete effect paint",
            # "wood protection oil",
            # "decking stain",
            # "wall colour ideas 2025",
            # "popular living room colours",
            # "bathroom waterproof paint",
            # "kitchen wall paint trends",
            # "furniture upcycling paint",
            # "wall stencils",
            # "modern wall design ideas",
            "sustainable home decor"
        ],
        "DE": [
            # "Wohnung renovieren",
            # "Wände streichen",
            # "Dekorative Wandgestaltung",
            # "Farbtrends Innenräume",
            # "Wandfarbe Ideen",
            # "Ökologische Wandfarbe",
            # "Dekorputz",
            # "Möbel mit Kreidefarbe streichen",
            # "Mikrozement Wände",
            # "Betonoptik Farbe",
            # "Holzschutz Öl",
            # "Terrassenlasur",
            # "Wohnzimmer Farbe Trends",
            # "Badezimmer Wandfarbe",
            # "Küche Wandfarbe",
            # "Möbel Upcycling Farbe",
            # "Wandschablonen",
            # "Moderne Wandgestaltung",
            "Nachhaltige Wohnideen"
        ]
    }

    # Step 3: Init pytrends
    pytrends = TrendReq(hl='pl-PL', tz=120)

    # Step 4: Collect trends
    trendy_keywords = {}

    for country, keywords in search_queries.items():
        geo = "GB" if country == "UK" else country
        trendy_keywords[country] = {}

        msg = f"=== Processing country: {country} ==="
        logger.info(msg); print(msg)

        for kw in keywords:
            msg = f"Processing keyword: {kw}"
            logger.info(msg); print(msg)
            try:
                time.sleep(120)  # long wait to avoid block
                pytrends.build_payload([kw], cat=0, timeframe='now 7-d', geo=geo, gprop='')
                related_queries = pytrends.related_queries()

                if kw in related_queries:
                    top = related_queries[kw]['top']
                    if top is not None:
                        for _, row in top.iterrows():
                            keyword = row['query']
                            score = row['value']
                            trendy_keywords[country][keyword] = score * 0.75

                    rising = related_queries[kw]['rising']
                    if rising is not None:
                        for _, row in rising.iterrows():
                            keyword = row['query']
                            score = row['value']
                            trendy_keywords[country][keyword] = score * 1.25

            except Exception as e:
                msg = f"Error processing {kw}: {e}"
                logger.info(msg); print(msg)
                continue

        msg = f"Found {len(trendy_keywords[country])} trending keywords for {country}"
        logger.info(msg); print(msg)

    # Step 5: Upload results
    for country, trends in trendy_keywords.items():
        if trends:
            msg = f"Uploading {len(trends)} keywords for {country}"
            logger.info(msg); print(msg)
            upload_to_airtable(trends, country)
            msg = f"Upload to Airtable completed for {country}"
            logger.info(msg); print(msg)
        else:
            msg = f"No trending keywords found for {country}"
            logger.info(msg); print(msg)

if __name__ == "__main__":
    main()
