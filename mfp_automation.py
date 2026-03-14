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
    """Authentification via la variable d'environnement."""
    secret_json = os.environ.get("GOOGLE_CREDENTIALS")
    if not secret_json:
        print("\n❌ ERREUR : Le secret 'GOOGLE_CREDENTIALS' est introuvable.")
        sys.exit(1)
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(secret_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)

def scrape_diary(page):
    """Extrait les macros depuis le HTML de la page."""
    print('🕷️ Scraping des données MyFitnessPal...')
    html = page.content()
    soup = bs(html, 'lxml')

    try:
        td = soup.find_all('td', class_='first')
        # On nettoie les chaînes (retrait des espaces/caractères spéciaux)
        calorie  = td[0].string.strip() if td[0].string else "0"
        lipide   = td[1].string.strip() if td[1].string else "0"
        glucide  = td[2].string.strip() if td[2].string else "0"
        proteine = td[3].string.strip() if td[3].string else "0"
        
        print(f'   ✅ Données trouvées : Cal:{calorie}, Prot:{proteine}, Lip:{lipide}, Glu:{glucide}')
        return calorie, proteine, lipide, glucide
    except Exception as e:
        print(f"❌ Erreur lors de l'extraction : {e}")
        return None

def main():
    # 1. Identifiants
    email = input('📧 Email MyFitnessPal : ')
    password = getpass.getpass('🔑 Mot de passe : ')

    # 2. Configuration Navigateur
    chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
                   glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True)
    chrome_path = chrome_paths[0] if chrome_paths else None

    print('\n🚀 Lancement de la session sécurisée...')
    sb = sb_cdp.Chrome(headless=False, xvfb=True, browser_executable_path=chrome_path)
    endpoint_url = sb.get_endpoint_url()

    try:
        with sync_playwright() as p:
            browser = p.chromium.connect_over_cdp(endpoint_url)
            context = browser.contexts[0]
            page = context.pages[0]

            # --- ÉTAPE : CONNEXION ---
            print('🌐 Accès à MyFitnessPal...')
            page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded')
            
            # Résolution Captcha
            print('🤖 Vérification Cloudflare...')
            sb.solve_captcha()
            time.sleep(2)

            # Login
            print('✍️  Saisie des identifiants...')
            page.wait_for_selector('#email', timeout=15000)
            page.fill('#email', email)
            page.fill('#password', password)
            page.locator("button[type='submit']").dispatch_event('click')

            # Attente de la redirection vers le journal
            page.wait_for_url('**/food/diary**', timeout=20000)
            print('🔓 Connexion réussie !')
            time.sleep(5) # Attente du rendu des chiffres

            # --- ÉTAPE : SCRAPING ---
            macros = scrape_diary(page)

            # --- ÉTAPE : EXPORT GOOGLE SHEETS ---
            if macros:
                cal, prot, lip, glu = macros
                gc = get_google_sheets_client()
                print("📂 Ouverture du tableur 'diete'...")
                sh = gc.open("diete")
                ws = sh.sheet1

                print("✍️ Mise à jour des cellules (D12, L12, M12, C12)...")
                ws.update([[cal]], "D12")
                ws.update([[lip]], "L12")
                ws.update([[glu]], "M12")
                ws.update([[prot]], "C12")
                print("\n✅ MISSION TERMINÉE : Données synchronisées !")

    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE : {e}")
    finally:
        sb.quit()

if __name__ == "__main__":
    main()
