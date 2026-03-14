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

def main():
    email = os.environ.get('MFP_EMAIL') or input('📧 Email : ')
    password = os.environ.get('MFP_PASSWORD') or getpass.getpass('🔑 Password : ')

    # TA LOGIQUE DE RECHERCHE CHROME
    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/usr/bin/google-chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    # TON LANCEMENT DE NAVIGATEUR
    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    with sync_playwright() as p:
        browser = p.chromium.connect_over_cdp(endpoint_url)
        page = browser.contexts[0].pages[0]

        # ── TA LOGIQUE EXACTE DE CONNEXION ───────────────────────────────────
        print('🌐 Ouverture de MyFitnessPal...')
        page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded', timeout=60000)
        time.sleep(3)

        print('🍪 Fermeture de la popup cookies...')
        try:
            # On teste l'ID de ton script
            iframe = page.frame_locator('#sp_message_iframe_1182771')
            for text in ['Accept All', 'Accepter tout', 'Accept', 'Accepter']:
                try:
                    iframe.get_by_role('button', name=text).click(timeout=3000)
                    print(f'   ✅ Cookies acceptés ({text})')
                    time.sleep(2)
                    break
                except: pass
        except: print('   (pas de popup cookies)')

        print('🤖 Résolution du captcha...')
        sb.solve_captcha()
        time.sleep(3)

        print('✍️ Saisie des identifiants...')
        page.wait_for_selector('#email', timeout=15000)
        page.fill('#email', email)
        page.fill('#password', password)

        print('🔓 Connexion en cours...')
        # ICI : Ton fameux dispatch_event qui marche
        page.locator("button[type='submit']").dispatch_event('click')
        
        # Attente de la redirection vers le journal (le but final)
        time.sleep(5)
        if "diary" not in page.url:
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='networkidle')

        # ── PARTIE EXTRACTION ET SHEETS ──────────────────────────────────────
        print('🕷️ Scraping des données...')
        html = page.content()
        soup = bs(html, 'lxml')
        try:
            td = soup.find_all('td', class_='first')
            if td and len(td) >= 4:
                cal, prot, lip, glu = td[0].get_text(strip=True), td[3].get_text(strip=True), td[1].get_text(strip=True), td[2].get_text(strip=True)
                
                print(f"📊 Données : {cal} kcal. Envoi vers Google Sheets...")
                gc = get_google_sheets_client()
                sh = gc.open("diete")
                ws = sh.sheet1
                ws.update([[cal]], "D12")
                ws.update([[lip]], "L12")
                ws.update([[glu]], "M12")
                ws.update([[prot]], "C12")
                print("✅ Terminé avec succès !")
            else:
                print("❌ Impossible de trouver les données sur la page du journal.")
        except Exception as e:
            print(f"❌ Erreur Sheets/Scraping : {e}")

    # NETTOYAGE FINAL
    try:
        if hasattr(sb, 'stop'): sb.stop()
        elif hasattr(sb, 'quit'): sb.quit()
    except: pass

if __name__ == "__main__":
    main()
