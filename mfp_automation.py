import os
import sys
import time
from seleniumbase import SB

def run_sync():
    # 1. Récupération des identifiants depuis les secrets GitHub
    email = os.environ.get('MFP_EMAIL')
    password = os.environ.get('MFP_PASSWORD')

    if not email or not password:
        print("❌ ERREUR : Les secrets MFP_EMAIL ou MFP_PASSWORD sont vides.")
        sys.exit(1)

    # 2. Lancement de SeleniumBase avec le mode Anti-Détection (UC)
    # On utilise context manager "with" pour s'assurer que le navigateur se ferme bien
    with SB(uc=True, headless=True, slow_mode=True) as sb:
        try:
            print("🚀 Démarrage du navigateur...")
            url = "https://www.myfitnesspal.com/account/login"
            sb.uc_open_with_reconnect(url, 4)
            
            # Petit temps d'attente pour laisser passer Cloudflare
            time.sleep(5)
            sb.save_screenshot("screenshot_1_page_chargement.png")

            # 3. Tentative de connexion
            print("🔑 Tentative de connexion...")
            
            # On attend que le champ email soit visible
            if sb.is_element_visible('input#email'):
                sb.type('input#email', email)
                sb.type('input#password', password)
                sb.save_screenshot("screenshot_2_champs_remplis.png")
                
                sb.click('button[type="submit"]')
                print("Wait... redirection après login.")
                time.sleep(10)
            else:
                print("⚠️ Champ login non trouvé. Possible blocage Cloudflare (Vérifie le screenshot_1).")

            # 4. Vérification finale
            sb.save_screenshot("screenshot_3_apres_login.png")
            
            if
