from selenium import webdriver
from selenium.webdriver.common.by import By
import csv
import time
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
load_dotenv()

EMAIL = os.environ.get('EMAIL')
PASSWORD = os.environ.get('PASSWORD')
LOGIN_URL = "https://tidio.com/panel/login"
DATA_SOURCES_URL = "https://tidio.com/panel/lyro-ai/data-sources/added?item_type=qa"




driver = webdriver.Chrome()
driver.get(LOGIN_URL)
wait = WebDriverWait(driver, 15)  # max 15 sekund czekania
email_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[aria-label="Email input field"]')))
email_input.send_keys(EMAIL)
time.sleep(3)
password_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[aria-label="Password input field"]')))
password_input.send_keys(PASSWORD)
time.sleep(5)
submit_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]')))
submit_button.click()
time.sleep(5)
driver.get(DATA_SOURCES_URL)
time.sleep(5)
driver.find_element(By.CSS_SELECTOR, 'a[aria-label="Page 13"]').click()
time.sleep(5)

data = []
indeks = 1
while True:
    # ZBIERAJ PYTANIA I ODPOWIEDZI Z DANEJ STRONY
    entries = driver.find_elements(By.CSS_SELECTOR, "tr[data-testid^='table-row-']")
    for entry in entries:
        question = entry.find_element(By.CSS_SELECTOR, "td p:first-of-type").text
        entry.find_element(By.XPATH, "./td[2]").click()
        time.sleep(3)
        answer = driver.find_element(By.CSS_SELECTOR, "form div[role='textbox'] div[data-slate-node='element']").text
        data.append([question.replace('\n', ' ').replace(',', ' '), answer.replace('\n', ' ').replace(',', ' ')])
        print(indeks)
        indeks += 1
    break
    # # SZUKAJ LINKU rel="next" I PRZECHODŹ DALEJ
    # try:
    #     next_link = driver.find_element(By.CSS_SELECTOR, 'a[rel="next"]')
    #     next_link.click()
    #     time.sleep(3)
    # except:
    #     break  # Nie ma następnej strony, kończymy

with open('tidio_datasources_export.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Question', 'Answer'])
    writer.writerows(data)

driver.quit()
