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
        # On cherche les cellules de résumé en bas du tableau
        td = soup.find_all('td', class_='first')
        if not td:
             print("⚠️ Structure HTML non reconnue.")
             return None
        # Cal, Prot, Lip, Glu (ordre basé sur ta logique)
        return (td[0].get_text(strip=True), td[3].get_text(strip=True), 
                td[1].get_text(strip=True), td[2].get_text(strip=True))
    except Exception as e:
        print(f"❌ Erreur scraping: {e}")
        return None

def main():
    email = os.environ.get('MFP_EMAIL') or input('📧 Email : ')
    password = os.environ.get('MFP_PASSWORD') or getpass.getpass('🔑 Password : ')

    # Detection Chrome
    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/usr/bin/google-chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    # On lance en headless pour GitHub
    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            page = browser.contexts[0].pages[0]

            print('🌐 Accès MyFitnessPal...')
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded')
            
            # --- FIX COOKIES : On force la suppression de la bannière ---
            print('🍪 Suppression des cookies...')
            try:
                # On essaie de cliquer sur accepter si l'iframe est là
                iframe = page.frame_locator('iframe[id^="sp_message_iframe"]')
                iframe.get_by_role("button", name=["Accepter", "Accept", "Accept All"]).click(timeout=5000)
                print("✅ Cookies acceptés.")
            except:
                # Si le clic échoue, on force la suppression de l'élément HTML pour libérer l'écran
                page.evaluate('() => { document.querySelectorAll(\'[id^="sp_message_container"]\').forEach(el => el.remove()); }')
                print("⚠️ Bannière cookies masquée par script.")

            # Gestion Captcha
            sb.solve_captcha()
            
            print('✍️ Saisie des identifiants...')
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', email)
            page.fill('#password', password)
            
            # On utilise dispatch_event('click') qui contourne les interceptions d'iframe
            page.locator("button[type='submit']").dispatch_event('click')

            print('⏳ Attente redirection...')
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
                print(f"✅ Terminé ! Macros : {cal}kcal, {prot}p")

    except Exception as e:
        print(f"❌ Erreur : {e}")
    finally:
        # Fermeture sécurisée sans erreur d'attribut
        try:
            if 'browser' in locals(): browser.close()
            # On stoppe seleniumbase proprement
            if hasattr(sb, 'stop'): sb.stop()
            elif hasattr(sb, 'quit'): sb.quit()
        except:
            pass
        print("👋 Session terminée.")

if __name__ == "__main__":
    main()
