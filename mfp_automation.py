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
        if not td:
             print("⚠️ Structure HTML non reconnue ou page vide.")
             return None
        return (td[0].get_text(strip=True), td[3].get_text(strip=True), 
                td[1].get_text(strip=True), td[2].get_text(strip=True))
    except Exception as e:
        print(f"❌ Erreur scraping: {e}")
        return None

def main():
    email = os.environ.get('MFP_EMAIL') or input('📧 Email : ')
    password = os.environ.get('MFP_PASSWORD') or getpass.getpass('🔑 Password : ')

    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/usr/bin/google-chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            page = browser.contexts[0].pages[0]

            print('🌐 Accès MyFitnessPal...')
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded')
            
            # --- FIX COOKIES : On force la suppression des éléments bloquants ---
            print('🍪 Neutralisation des cookies...')
            try:
                # Tentative de clic standard sur l'iframe
                iframe = page.frame_locator('iframe[id^="sp_message_iframe"]')
                iframe.get_by_role("button", name=["Accepter", "Accept", "Accept All"]).click(timeout=5000)
            except:
                # Si ça échoue, on supprime carrément les bannières via JavaScript
                page.evaluate('() => { document.querySelectorAll(\'[id^="sp_message_container"]\').forEach(el => el.remove()); }')
                print("⚠️ Bannières cookies supprimées par injection JS.")

            # Gestion Captcha via SeleniumBase
            sb.solve_captcha()
            
            print('✍️ Saisie des identifiants...')
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', email)
            page.fill('#password', password)
            
            # --- FIX CLIC : On utilise dispatch_event pour ignorer les obstacles visuels ---
            print('🔓 Tentative de connexion...')
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
                print(f"✅ Succès ! Données envoyées : {cal} kcal.")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")
    finally:
        # Nettoyage sécurisé
        try:
            if 'browser' in locals(): browser.close()
            # On utilise une méthode de fermeture plus universelle pour sb
            if hasattr(sb, 'stop'): sb.stop()
            elif hasattr(sb, 'quit'): sb.quit()
        except:
            pass
        print("👋 Session terminée.")

if __name__ == "__main__":
    main()
