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
        # Si on est en local, on cherche le fichier service_account.json
        return gspread.service_account(filename='service_account.json')
    
    # Si on est sur GitHub
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
        if len(td) < 4: return None
        return (td[0].get_text(strip=True), td[3].get_text(strip=True), 
                td[1].get_text(strip=True), td[2].get_text(strip=True))
    except:
        return None

def main():
    # Identifiants (GitHub Secrets ou Manuel)
    email = os.environ.get('MFP_EMAIL') or input('📧 Email MyFitnessPal : ')
    password = os.environ.get('MFP_PASSWORD') or getpass.getpass('🔑 Mot de passe : ')

    # Localisation Chrome
    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/usr/bin/google-chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    # Lancement identique à ton script qui marche
    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            page = browser.contexts[0].pages[0]

            print('🌐 Ouverture de MyFitnessPal...')
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)

            # ── TA LOGIQUE DE COOKIES (QUI MARCHE) ──
            print('🍪 Fermeture de la popup cookies...')
            try:
                # On essaie les deux IDs d'iframe connus au cas où ça change
                for iframe_id in ['#sp_message_iframe_1182771', '#sp_message_iframe_1164399']:
                    iframe = page.frame_locator(iframe_id)
                    for text in ['Accept All', 'Accepter tout', 'Accept', 'Accepter']:
                        try:
                            iframe.get_by_role('button', name=text).click(timeout=2000)
                            print(f'   ✅ Cookies acceptés ({text})')
                            break
                        except: pass
            except: pass

            # ── TA LOGIQUE CAPTCHA ──
            print('🤖 Résolution du captcha...')
            sb.solve_captcha()
            time.sleep(3)

            # ── LOGIN ──
            print('✍️ Saisie des identifiants...')
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', email)
            page.fill('#password', password)
            print('🔓 Connexion...')
            page.locator("button[type='submit']").dispatch_event('click')
            
            # Attente de redirection vers le journal
            time.sleep(5)
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='networkidle')

            # ── PARTIE GOOGLE SHEETS ──
            macros = scrape_diary(page)
            if macros:
                cal, prot, lip, glu = macros
                print(f"📊 Macros trouvées : {cal}kcal")
                
                gc = get_google_sheets_client()
                sh = gc.open("diete") # Vérifie que le nom est exact
                ws = sh.sheet1
                ws.update([[cal]], "D12")
                ws.update([[lip]], "L12")
                ws.update([[glu]], "M12")
                ws.update([[prot]], "C12")
                print("✅ Google Sheets mis à jour !")
            else:
                print("❌ Impossible de lire les macros sur la page.")

    finally:
        if hasattr(sb, 'quit'): sb.quit()
        elif hasattr(sb, 'stop'): sb.stop()

if __name__ == "__main__":
    main()
