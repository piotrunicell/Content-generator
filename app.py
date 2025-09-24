from flask import Flask, request, jsonify
import threading
from dotenv import load_dotenv
import os
import logging

load_dotenv()

import get_products
import g_trends
import article_generator

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] %(levelname)s in %(module)s: %(message)s')


# Wrap get_products main logic
def run_get_products():
    try:
        get_products.main()
    except Exception as e:
        print("Error in get_products:", e)

# Wrap g_trends main logic
def run_g_trends():
    try:
        g_trends.main()
    except Exception as e:
        print("Error in g_trends:", e)

@app.route('/')
def health_check():
    return jsonify({"status": "API is running"})

@app.route('/scrape_products', methods=['POST'])
def scrape_products():
    print("Starting product scraping...")
    threading.Thread(target=run_get_products).start()
    return jsonify({"status": "Product scraping started"}), 202

@app.route('/update_trends', methods=['POST'])
def update_trends():
    threading.Thread(target=run_g_trends).start()
    return jsonify({"status": "Google Trends update started"}), 202

@app.route('/generate_article', methods=['POST'])
def generate_article():
    try:
        article = article_generator.generate_article()
        return jsonify(article)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
