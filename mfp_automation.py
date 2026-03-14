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
        if len(td) < 4: 
            print("⚠️ Données non trouvées. Vérifie si la page est bien chargée.")
            return None
        return (td[0].get_text(strip=True), td[3].get_text(strip=True), 
                td[1].get_text(strip=True), td[2].get_text(strip=True))
    except Exception as e:
        print(f"❌ Erreur scraping : {e}")
        return None

def main():
    email = os.environ.get('MFP_EMAIL') or input('📧 Email : ')
    password = os.environ.get('MFP_PASSWORD') or getpass.getpass('🔑 Password : ')

    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/usr/bin/google-chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    # Initialisation de SeleniumBase CDP
    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            page = browser.contexts[0].pages[0]

            print('🌐 Connexion MyFitnessPal...')
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded')
            
            # --- SOLUTION AU TIMEOUT : Supprimer les cookies de force ---
            print('🍪 Neutralisation de la bannière cookies...')
            page.evaluate('() => { const el = document.querySelector("[id^=\'sp_message_container\']"); if(el) el.remove(); }')
            time.sleep(1)

            # Résoudre le captcha si besoin
            sb.solve_captcha()
            
            print('✍️ Saisie des identifiants...')
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', email)
            page.fill('#password', password)
            
            # Utilisation de dispatch_event pour cliquer même si c'est "obstrué"
            print('🔓 Clic sur Connexion...')
            page.locator("button[type='submit']").dispatch_event('click')

            # Attendre la redirection
            page.wait_for_url('**/food/diary**', timeout=30000)
            time.sleep(5) 

            macros = scrape_diary(page)
            if macros:
                cal, prot, lip, glu = macros
                gc = get_google_sheets_client()
                sh = gc.open("diete")
                ws = sh.sheet1
                ws.update([[cal]], "D12")
                ws.update([[lip]], "L12")
                ws.update([[glu]], "M12")
                ws.update([[prot]], "C12")
                print(f"✅ RÉUSSI : {cal} kcal envoyées à Google Sheets.")

    except Exception as e:
        print(f"❌ ERREUR : {e}")
    finally:
        # Fermeture sécurisée sans AttributeError
        try:
            if 'browser' in locals(): browser.close()
            # On vérifie si sb a la méthode stop (seleniumbase récent) ou quit
            if hasattr(sb, 'stop'): sb.stop()
            elif hasattr(sb, 'quit'): sb.quit()
        except:
            pass
        print("👋 Session terminée.")

if __name__ == "__main__":
    main()
