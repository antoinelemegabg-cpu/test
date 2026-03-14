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
        print("❌ Secret GOOGLE_CREDENTIALS absent.")
        sys.exit(1)
    creds_dict = json.loads(secret_json)
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def scrape_diary(page):
    print('🕷️ Scraping des données...')
    html = page.content()
    soup = bs(html, 'lxml')
    try:
        td = soup.find_all('td', class_='first')
        if not td: return None
        # Cal, Prot, Lip, Glu (ordre habituel MFP)
        return (td[0].get_text(strip=True), td[3].get_text(strip=True), 
                td[1].get_text(strip=True), td[2].get_text(strip=True))
    except:
        return None

def main():
    email = os.environ.get('MFP_EMAIL') or input('📧 Email : ')
    password = os.environ.get('MFP_PASSWORD') or getpass.getpass('🔑 Password : ')

    # Localisation Chrome pour GitHub Actions
    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/usr/bin/google-chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    # On garde sb_cdp pour le captcha
    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            page = browser.contexts[0].pages[0]

            print('🌐 Ouverture MyFitnessPal...')
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)

            # ── TA LOGIQUE DE COOKIES (RÉ-INSTALLÉE) ──
            print('🍪 Fermeture de la popup cookies...')
            # On liste les IDs possibles d'iframe pour être sûr
            for frame_id in ['#sp_message_iframe_1182771', '#sp_message_iframe_1164399']:
                try:
                    iframe = page.frame_locator(frame_id)
                    for text in ['Accept All', 'Accepter tout', 'Accept', 'Accepter']:
                        btn = iframe.get_by_role('button', name=text)
                        if btn.count() > 0:
                            btn.click(timeout=3000)
                            print(f'   ✅ Cookies acceptés ({text})')
                            break
                except: continue

            # Captcha
            print('🤖 Résolution captcha...')
            sb.solve_captcha()
            time.sleep(3)

            # Saisie identifiants
            print('✍️ Saisie des identifiants...')
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', email)
            page.fill('#password', password)
            
            # ── TA LOGIQUE DE CLIC (DISPATCH) ──
            print('🔓 Connexion...')
            page.locator("button[type='submit']").dispatch_event('click')

            # Attente redirection
            time.sleep(5)
            # On s'assure d'être sur la bonne page pour le scrap
            if "diary" not in page.url:
                page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='networkidle')

            # Scraping & Sheets
            macros = scrape_diary(page)
            if macros:
                cal, prot, lip, glu = macros
                print(f"✅ Données récupérées : {cal} kcal")
                gc = get_google_sheets_client()
                sh = gc.open("diete")
                ws = sh.sheet1
                ws.update([[cal]], "D12")
                ws.update([[lip]], "L12")
                ws.update([[glu]], "M12")
                ws.update([[prot]], "C12")
                print("📊 Google Sheets mis à jour !")

    except Exception as e:
        print(f"❌ Erreur : {e}")
    finally:
        # Correction de l'AttributeError quit/stop
        try:
            if hasattr(sb, 'stop'): sb.stop()
            elif hasattr(sb, 'quit'): sb.quit()
        except: pass
        print("👋 Session terminée.")

if __name__ == "__main__":
    main()
