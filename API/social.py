import re
import uuid
import time
import random
import requests
from datetime import datetime
from CONFIG.config import UA, USER_AGENTS


def _xor_encode(text):
    key = "webapp1.0+202106"
    result = []
    for i, char in enumerate(text):
        result.append(chr(ord(char) ^ ord(key[i % len(key)])))
    return ''.join(result)


def _get_followers_range(count):
    if count < 1000: return '0-999'
    elif count < 2000: return '1k-1.9k'
    elif count < 3000: return '2k-2.9k'
    elif count < 4000: return '3k-3.9k'
    elif count < 5000: return '4k-4.9k'
    elif count < 6000: return '5k-5.9k'
    elif count < 7000: return '6k-6.9k'
    elif count < 8000: return '7k-7.9k'
    elif count < 9000: return '8k-8.9k'
    elif count < 10000: return '9k-9.9k'
    elif count < 100000: return '10k-99k'
    elif count < 200000: return '100k-199k'
    elif count < 300000: return '200k-299k'
    elif count < 400000: return '300k-399k'
    elif count < 500000: return '400k-499k'
    elif count < 600000: return '500k-599k'
    elif count < 700000: return '600k-699k'
    elif count < 800000: return '700k-799k'
    elif count < 900000: return '800k-899k'
    elif count < 1000000: return '900k-999k'
    else: return '1m+'


def _calculate_account_age(create_timestamp):
    try:
        if create_timestamp and create_timestamp > 0:
            created = datetime.fromtimestamp(create_timestamp)
            age = datetime.now() - created
            years = age.days // 365
            months = (age.days % 365) // 30
            if years > 0: return f"{years} year(s) {months} month(s)"
            elif months > 0: return f"{months} month(s)"
            else: return f"{age.days} day(s)"
    except:
        pass
    return "Unknown"


def _search_tiktok_inbox(sess, access_token, cid):
    try:
        headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-AnchorMailbox": f"CID:{cid}",
        }
        payload = {
            "Cvid": str(uuid.uuid4()),
            "Scenario": {"Name": "owa.react"},
            "TimeZone": "UTC",
            "TextDecorations": "Off",
            "EntityRequests": [{
                "EntityType": "Message",
                "ContentSources": ["Exchange"],
                "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}}]},
                "From": 0,
                "Query": {"QueryString": "tiktok"},
                "Size": 50,
                "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
            }]
        }
        r = sess.post("https://outlook.live.com/search/api/v2/query", json=payload, headers=headers, timeout=20)
        if r.status_code != 200:
            return None

        search_text = r.text
        tiktok_senders = [
            "no-reply@shop.tiktok.com", "notification@service.tiktok.com",
            "noreply@account.tiktok.com", "register@account.tiktok.com", "no-reply@tiktok.com"
        ]
        tiktok_count = sum(search_text.count(s) for s in tiktok_senders)
        if tiktok_count == 0:
            return None

        username_patterns = [
            r'(?i)this\s+email\s+was\s+generated\s+for\s+@?([a-zA-Z0-9_\.]{2,30})',
            r'(?i)Hi\s+@?([a-zA-Z0-9_\.]{2,30})',
            r'(?i)Hello\s+@?([a-zA-Z0-9_\.]{2,30})',
            r'@([a-zA-Z0-9_\.]{2,30})'
        ]
        username = None
        for pattern in username_patterns:
            match = re.search(pattern, search_text)
            if match:
                pot = match.group(1)
                if not any(x in pot.lower() for x in ['tiktok', 'mail', 'email', 'hotmail', 'outlook']):
                    username = pot
                    break

        return {"emails_count": tiktok_count, "username": username}
    except:
        return None


def _get_tiktok_profile(sess, username, email=None):
    try:
        import secrets
        secret = secrets.token_hex(16)
        xor_email = _xor_encode(email) if email else ""
        iid = str(random.randint(1, 10**19))
        device_id = str(random.randint(1, 10**19))

        params = {
            "request_tag_from": "h5", "fixed_mix_mode": "1", "mix_mode": "1",
            "account_param": xor_email, "scene": "1", "device_platform": "android",
            "aid": "1233", "app_name": "musical_ly", "version_code": "370805",
            "ts": str(round(random.uniform(1.2, 1.6) * 100000000) * -1),
            "iid": iid, "device_id": device_id,
        }
        cookies = {
            "passport_csrf_token": secret,
            "passport_csrf_token_default": secret,
            "install_id": iid
        }
        headers = {
            'user-agent': random.choice(USER_AGENTS),
            'x-ss-req-ticket': str(int(time.time() * 1000)),
            'passport-sdk-version': '19',
        }

        response = requests.get(
            "https://api16-normal-c-useast1a.tiktokv.com/passport/account/info/v2/",
            params=params, cookies=cookies, headers=headers, timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('data') and data['data'].get('username'):
                u = data['data']
                return {
                    'username': u.get('username', ''),
                    'full_name': u.get('screen_name', ''),
                    'id': u.get('user_id', ''),
                    'bio': u.get('bio_description', ''),
                    'followers': u.get('follower_count', 0),
                    'following': u.get('following_count', 0),
                    'friends': u.get('mplatform_followers_count', 0),
                    'likes': u.get('total_favorited', 0),
                    'videos': u.get('aweme_count', 0),
                    'verified': u.get('verified', False),
                    'private': u.get('secret', False),
                    'avatar_url': u.get('avatar_larger', {}).get('url_list', [''])[0],
                    'create_time': u.get('create_time', 0),
                    'language': u.get('language', 'Unknown'),
                    'region': u.get('region', 'Unknown')
                }
        return None
    except:
        return None


def _get_tiktok_profile_web(username):
    try:
        import json as _json
        headers = {'user-agent': UA, 'accept': 'text/html,application/xhtml+xml'}
        response = requests.get(f"https://www.tiktok.com/@{username}", headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            html = response.text
            profile_data = {'username': username, 'followers': 0, 'following': 0, 'likes': 0,
                           'videos': 0, 'verified': False, 'full_name': '', 'bio': '', 'private': False}
            m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__" type="application/json">(.*?)</script>', html, re.DOTALL)
            if m:
                try:
                    data = _json.loads(m.group(1))
                    ud = data.get('__DEFAULT_SCOPE__', {}).get('webapp.user-detail', {}).get('userInfo', {})
                    user = ud.get('user', {})
                    stats = ud.get('stats', {})
                    profile_data['followers'] = stats.get('followerCount', 0)
                    profile_data['following'] = stats.get('followingCount', 0)
                    profile_data['likes'] = stats.get('heartCount', 0)
                    profile_data['videos'] = stats.get('videoCount', 0)
                    profile_data['verified'] = user.get('verified', False)
                    profile_data['full_name'] = user.get('nickname', '')
                    profile_data['bio'] = user.get('signature', '')
                    profile_data['avatar_url'] = user.get('avatarLarger', '')
                    profile_data['private'] = user.get('privateAccount', False)
                except:
                    pass
            return profile_data if profile_data['followers'] > 0 else None
        return None
    except:
        return None


def _search_instagram_inbox(sess, access_token, cid):
    try:
        headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "X-AnchorMailbox": f"CID:{cid}",
        }
        payload = {
            "Cvid": str(uuid.uuid4()),
            "Scenario": {"Name": "owa.react"},
            "TimeZone": "UTC",
            "TextDecorations": "Off",
            "EntityRequests": [{
                "EntityType": "Message",
                "ContentSources": ["Exchange"],
                "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}}]},
                "From": 0,
                "Query": {"QueryString": "instagram"},
                "Size": 50,
                "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
            }]
        }
        r = sess.post("https://outlook.live.com/search/api/v2/query", json=payload, headers=headers, timeout=20)
        if r.status_code != 200:
            return None

        search_text = r.text
        instagram_senders = [
            "no-reply@mail.instagram.com", "security@mail.instagram.com",
            "help@mail.instagram.com", "noreply@instagram.com"
        ]
        instagram_count = sum(search_text.count(s) for s in instagram_senders)
        if instagram_count == 0:
            return None

        username_patterns = [
            r'(?i)Hi\s+@?([a-zA-Z0-9_\.]{2,30})',
            r'(?i)Hello\s+@?([a-zA-Z0-9_\.]{2,30})',
            r'@([a-zA-Z0-9_\.]{2,30})',
            r'(?i)account\s+@?([a-zA-Z0-9_\.]{2,30})'
        ]
        username = None
        for pattern in username_patterns:
            match = re.search(pattern, search_text)
            if match:
                pot = match.group(1)
                if not any(x in pot.lower() for x in ['instagram', 'mail', 'email', 'hotmail', 'outlook']):
                    username = pot
                    break

        return {"emails_count": instagram_count, "username": username}
    except:
        return None


def _get_instagram_profile(username):
    try:
        url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
        headers = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Origin": "https://www.instagram.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest"
        }
        try:
            import httpx
            with httpx.Client(http2=True, headers=headers, timeout=10.0) as session:
                data = session.get(url).json()
        except:
            data = requests.get(url, headers=headers, timeout=10.0).json()

        user = data.get('data', {}).get('user', {})
        if not user:
            return None

        return {
            'username': user.get('username', ''),
            'full_name': user.get('full_name', ''),
            'user_id': user.get('id', ''),
            'bio': user.get('biography', ''),
            'followers': user.get('edge_followed_by', {}).get('count', 0),
            'following': user.get('edge_follow', {}).get('count', 0),
            'posts': user.get('edge_owner_to_timeline_media', {}).get('count', 0),
            'private': user.get('is_private', False),
            'verified': user.get('is_verified', False),
            'professional': user.get('is_professional_account', False),
            'category': user.get('category_name', 'N/A'),
            'email': user.get('business_email') or user.get('public_email') or 'N/A',
            'phone': user.get('business_phone_number') or user.get('public_phone_number') or 'N/A',
            'external_url': user.get('external_url', 'N/A'),
            'profile_pic': user.get('profile_pic_url', '')
        }
    except:
        return None
