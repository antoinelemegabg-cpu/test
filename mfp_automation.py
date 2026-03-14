import gspread
from google.oauth2.service_account import Credentials
import json
import os
import sys

# Valeurs de test
calorie, proteine, lipide, glucide = "1234", "55", "66", "77"

print("🚀 TEST GOOGLE SHEETS via Secret GitHub")

try:
    # 1. On récupère le secret depuis les variables d'environnement
    # GitHub stocke les secrets dans os.environ
    secret_json = os.environ.get("GOOGLE_CREDENTIALS")

    if not secret_json:
        print("\n❌ ERREUR : Le secret 'GOOGLE_CREDENTIALS' est vide ou introuvable.")
        print("💡 Solution : Tape la commande suivante dans ton terminal avant de relancer :")
        print("export GOOGLE_CREDENTIALS='ton_json_complet_ici'")
        sys.exit(1)

    # 2. Setup Google Auth
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = json.loads(secret_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gc = gspread.authorize(creds)

    # 3. Accès au sheet
    print("📂 Ouverture du tableur 'diete'...")
    sh = gc.open("diete")
    ws = sh.sheet1

    # 4. Envoi des données
    print("✍️ Mise à jour des cellules...")
    ws.update([[calorie]], "D12")
    ws.update([[lipide]], "L12")
    ws.update([[glucide]], "M12")
    ws.update([[proteine]], "C12")

    print("\n✅ RÉUSSI : Ton Google Sheet a été mis à jour !")

except Exception as e:
    print(f"\n❌ ÉCHEC : {e}")
python test_sheets_final.py
