from pytrends.request import TrendReq
import pandas as pd
import time
import requests
import os
from datetime import datetime
from datetime import timedelta

pytrends = TrendReq(hl='pl-PL', tz=120)

pytrends.build_payload(["farba"], cat=0, timeframe='now 7-d', geo='PL', gprop='')
related_queries = pytrends.related_queries()
print(related_queries)