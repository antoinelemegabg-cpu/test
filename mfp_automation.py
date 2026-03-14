import os
import sys
import json
import time
import glob
import getpass
import gspread
from google.oauth2.service_account import Credentials
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp
from bs4 import BeautifulSoup as bs

def get_google_sheets_client():
    secret_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not secret_json:
        print("❌ ERREUR : Secret GOOGLE_CREDENTIALS manquant.")
        sys.exit(1)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(secret_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def scrape_diary(page):
    print('🕷️ Scraping des données...')
    html = page.content()
    soup = bs(html, 'lxml')
    try:
        td = soup.find_all('td', class_='first')
        if len(td) < 4: return None
        return (td[0].string.strip(), td[3].string.strip(), 
                td[1].string.strip(), td[2].string.strip())
    except:
        return None

def main():
    # Gestion des identifiants (Auto via secrets ou Manuel)
    email = os.environ.get('MFP_EMAIL') or input('📧 Email : ')
    password = os.environ.get('MFP_PASSWORD') or getpass.getpass('🔑 Password : ')

    # Détection Chrome pour Codespaces/Ubuntu
    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/usr/bin/google-chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    # Headless=True est OBLIGATOIRE pour GitHub Actions
    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            page = browser.contexts[0].pages[0]

            print('🌐 Connexion MyFitnessPal...')
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded')
            
            sb.solve_captcha()
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', email)
            page.fill('#password', password)
            page.click("button[type='submit']")

            page.wait_for_url('**/food/diary**', timeout=20000)
            time.sleep(5) 

            macros = scrape_diary(page)
            if macros:
                cal, prot, lip, glu = macros
                gc = get_google_sheets_client()
                sh = gc.open("diete") # Assure-toi que le nom est exact
                ws = sh.sheet1
                ws.update([[cal]], "D12")
                ws.update([[lip]], "L12")
                ws.update([[glu]], "M12")
                ws.update([[prot]], "C12")
                print("✅ Données synchronisées !")
    finally:
        sb.quit()

if __name__ == "__main__":
    main()
