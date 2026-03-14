cat > login.py << 'EOF'
from playwright.sync_api import sync_playwright
from seleniumbase import sb_cdp
import glob, time, os

def login():
    email = os.environ.get('MFP_EMAIL')
    password = os.environ.get('MFP_PASSWORD')
    
    # Cherche Chrome selon l'environnement (Codespace ou GitHub Actions)
    paths = glob.glob('/home/runner/.cache/ms-playwright/**/chrome', recursive=True) + \
            glob.glob('/home/codespace/.cache/ms-playwright/**/chrome', recursive=True)
    chrome_path = paths[0] if paths else None

    sb = sb_cdp.Chrome(headless=True, xvfb=True, browser_executable_path=chrome_path)
    
    p = sync_playwright().start()
    browser = p.chromium.connect_over_cdp(sb.get_endpoint_url())
    page = browser.contexts[0].pages[0]
    
    print('🌐 Connexion à MyFitnessPal...')
    page.goto('https://www.myfitnesspal.com/fr/food/diary', wait_until='domcontentloaded')
    
    # Supprime la bannière cookies si elle existe
    page.evaluate('() => document.getElementById("sp_message_container_1182771")?.remove()')
    
    print('🤖 Résolution du captcha...')
    sb.solve_captcha()

    page.wait_for_selector('#email', timeout=15000)
    page.fill('#email', email)
    page.fill('#password', password)
    page.locator("button[type='submit']").click(force=True)

    page.wait_for_url('**/food/diary*', timeout=30000)
    time.sleep(5)
    return page, sb
EOF
