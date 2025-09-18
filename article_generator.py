import os, json, requests, numpy as np
from datetime import datetime
from openai import OpenAI
from style_guide import MY_STYLE_GUIDE

from dotenv import load_dotenv
load_dotenv()

# ---------- CONFIG ----------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
AIRTABLE_TOKEN = os.environ.get("AIRTABLE_API_KEY")
BASE_ID = os.environ.get("AIRTABLE_BASE_ID")

client = OpenAI(api_key=OPENAI_API_KEY)
headers = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

# ---------- HELPERS ----------

def fetch_table(table, filter_formula=None):
    """Fetch up to 50 rows from any Airtable table"""
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table}"
    params = {"maxRecords": 50}
    if filter_formula:
        params["filterByFormula"] = filter_formula
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return [r["fields"] for r in res.json().get("records", [])]

def fetch_product_lines():
    rows = fetch_table("products")
    return [r.get("line") for r in rows if r.get("line")]

def fetch_backlog():
    return fetch_table("content_backlog")

def get_backlog_summary(backlog):
    """Return only title, target_audinece, and linked_products from backlog rows"""
    return [
        {
            "title": item.get("title", ""),
            "target_audinece": item.get("target_audinece", ""),
            "linked_products": item.get("linked_products", "")
        }
        for item in backlog
    ]

def fetch_selected_products(selected_lines):
    if not selected_lines:
        return []
    # Build filterByFormula: OR({line}="A",{line}="B")
    ors = ",".join([f'{{line}}="{line}"' for line in selected_lines])
    formula = f'OR({ors})'
    return fetch_table("products", filter_formula=formula)

def cosine(a, b):
    a = np.array(a); b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

def semantic_faq_search(keywords, top_k=5):
    """Find closest FAQ rows using cosine similarity on stored embeddings"""
    query = " ".join(keywords)
    q_emb = client.embeddings.create(
        model="text-embedding-3-small", input=query
    ).data[0].embedding

    res = requests.get(f"https://api.airtable.com/v0/{BASE_ID}/faq_queries", headers=headers)
    res.raise_for_status()
    records = res.json()["records"]

    scored = []
    for r in records:
        f = r["fields"]
        if "Embedding" not in f: 
            continue
        emb = json.loads(f["Embedding"])
        sim = cosine(q_emb, emb)
        scored.append((sim, f))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored[:top_k]]

def plan_initial(user_prompt):
    prompt = f"""
User wants: "{user_prompt}"
You can use two data sources: products and trends.

Return JSON like:
{{"products_needed": true/false, "trends_needed": true/false}}
"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)

def extract_keywords_and_products(user_prompt, product_lines, trends, backlog):
    prompt = f"""
User wants: "{user_prompt}".

Here are available product lines:
{json.dumps(product_lines)}

Here are recent content_backlog items:
{json.dumps(backlog)}
UNDER NO CIRCUMSTANCES should you repeat any topic already present in backlog.

Here are current trends:
{json.dumps(trends)}

1) Select 1–3 product lines that fit this topic
2) List 3–5 keywords for FAQ search

Return JSON like:
{{
  "selected_product_lines": ["line1","line2"],
  "faq_keywords": ["keyword1","keyword2","keyword3"]
}}
"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)



def write_article(user_prompt, products, trends, faqs, backlog):
    prompt = f"""
You are writing a new article.

User task: "{user_prompt}"

Use this data:
Products: {json.dumps(products)}
Trends: {json.dumps(trends)}
FAQs: {json.dumps(faqs)}

Follow these style rules:
{MY_STYLE_GUIDE}

UNDER NO CIRCUMSTANCES should you repeat any topic already present in backlog.
Backlog items: {backlog}

Return JSON only:
{{
  "title": "Short clear title (max 10 words)",
  "target_audience": "Who it is for",
  "linked_products": "Comma-separated product names",
  "content": "Full article text"
}}
"""
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)

def add_to_backlog(title, target_audience, linked_products, content):
    url = f"https://api.airtable.com/v0/{BASE_ID}/content_backlog"
    data = {
        "fields": {
            "title": title,
            "status": "draft",
            "target_audience": target_audience,
            "linked_products": linked_products,
            "created": datetime.now().strftime("%Y-%m-%d"),
            "content": content
        }
    }

    res = requests.post(
        url, 
        headers={**headers, "Content-Type": "application/json"}, 
        json=data
    )
    res.raise_for_status()
    return res.json()

# ---------- MAIN FLOW ----------

def generate_article():
    user_prompt = "Napisz artykuł blogowy na temat związany z remontem/renowacją i przynajmniej jednym z produktów z tabeli produkty. Artykuł zostanie umieszczony na stronie: primacol.com. Ta marka zajmuje się produkcją farb oraz impregnatów i chemii użytkowej. To ma być na pierwszym miejscu artyków a nie reklama produktu. Całość ma być po angielsku."
    plan = plan_initial(user_prompt)
    trends = fetch_table("trends") if plan.get("trends_needed") else []
    backlog = fetch_backlog()
    backlog_summary = get_backlog_summary(backlog)

    # NEW: first only get product lines
    product_lines = fetch_product_lines()

    # LLM chooses product lines + FAQ keywords
    selection = extract_keywords_and_products(user_prompt, product_lines, trends, backlog_summary)
    selected_lines = selection["selected_product_lines"]
    faq_keywords = selection["faq_keywords"]

    # Now fetch full products only for those lines
    products = fetch_selected_products(selected_lines)

    # Semantic FAQ search
    faqs = semantic_faq_search(faq_keywords, top_k=5)

    # Generate article
    article = write_article(user_prompt, products, trends, faqs, backlog_summary)

    # Save to backlog
    add_to_backlog(
        title=article["title"],
        target_audience=article["target_audience"],
        linked_products=article["linked_products"],
        content=article["content"]
    )

    return article


# ---------- RUN EXAMPLE ----------

if __name__ == "__main__":
    result = generate_article()
    print("\n✅ ARTICLE GENERATED:\n")
    print("Title:", result["title"])
    print("Target Audience:", result["target_audience"])
    print("Linked Products:", result["linked_products"])
    print("\nContent:\n", result["content"])