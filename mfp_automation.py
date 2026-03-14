cat > mfp_login.py << 'EOF'
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp
import getpass
import time
import glob

email    = input('📧 Email MyFitnessPal : ')
password = getpass.getpass('🔑 Mot de passe (masqué) : ')

# Trouve le chromium installé par Playwright
chrome_paths = glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True) + \
               glob.glob('/home/codespace/.cache/ms-playwright/**/chrome-linux64/chrome', recursive=True) + \
               glob.glob('/root/.cache/ms-playwright/**/chrome', recursive=True)

chrome_path = chrome_paths[0] if chrome_paths else None
print(f'🔍 Chrome trouvé : {chrome_path}')

print('\n🚀 Lancement du navigateur...')
sb = sb_cdp.Chrome(headless=False, xvfb=True, browser_executable_path=chrome_path)
endpoint_url = sb.get_endpoint_url()

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp(endpoint_url)
    context = browser.contexts[0]
    page = context.pages[0]

    # ── ÉTAPE 1 : Charger la page ─────────────────────────────────────────────
    print('🌐 Ouverture de MyFitnessPal...')
    page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded', timeout=60000)
    time.sleep(3)
    page.screenshot(path='screenshot_1_login_page.png')
    print('📸 Screenshot 1 sauvegardé')

    # ── ÉTAPE 2 : Accepter les cookies ────────────────────────────────────────
    print('🍪 Fermeture de la popup cookies...')
    try:
        iframe = page.frame_locator('#sp_message_iframe_1182771')
        for text in ['Accept All', 'Accepter tout', 'Accept', 'Accepter']:
            try:
                iframe.get_by_role('button', name=text).click(timeout=3000)
                print(f'🍪 Cookies acceptés ({text})')
                time.sleep(2)
                break
            except Exception:
                pass
    except Exception:
        print('   (pas de popup cookies)')

    page.screenshot(path='screenshot_2_after_cookies.png')
    print('📸 Screenshot 2 sauvegardé')

    # ── ÉTAPE 3 : Résoudre le captcha ─────────────────────────────────────────
    print('🤖 Résolution du captcha Cloudflare...')
    sb.solve_captcha()
    time.sleep(3)
    page.screenshot(path='screenshot_3_after_captcha.png')
    print('📸 Screenshot 3 sauvegardé')

    # ── ÉTAPE 4 : Remplir les identifiants ────────────────────────────────────
    print('✍️  Saisie des identifiants...')
    page.wait_for_selector('#email', timeout=15000)
    page.fill('#email', email)
    time.sleep(0.5)
    page.fill('#password', password)
    time.sleep(0.5)
    page.screenshot(path='screenshot_4_form_filled.png')
    print('📸 Screenshot 4 sauvegardé')

    # ── ÉTAPE 5 : Connexion ───────────────────────────────────────────────────
    print('🔓 Connexion en cours...')
    page.locator("button[type='submit']").dispatch_event('click')

    connecte = False
    try:
        page.wait_for_url('**/home**', timeout=15000)
        connecte = True
    except Exception:
        try:
            page.wait_for_selector('nav', timeout=5000)
            connecte = True
        except Exception:
            pass

    time.sleep(2)
    page.screenshot(path='screenshot_5_result.png')
    print('📸 Screenshot 5 sauvegardé')
    print(f'   URL finale : {page.url}')

    print()
    if connecte:
        print('✅ SUCCÈS — Connecté à MyFitnessPal !')
    else:
        print('❌ ÉCHEC — Connexion échouée.')
        print('   👆 Ouvre screenshot_5_result.png pour voir ce qui bloque.')

sb.quit()
print('\n👋 Navigateur fermé.')
EOF
python mfp_login.py
