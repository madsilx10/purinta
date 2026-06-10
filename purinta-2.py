import os
import sys
import json
import time

from eth_account import Account
from eth_account.messages import encode_defunct
from curl_cffi import requests

def load_env(path=".env"):
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip()
    except FileNotFoundError:
        pass

load_env()




BASE_URL = "https://tribal-campaign.purinta.xyz"
X_API_URL = "https://api.twitter.com/1.1"

BANNER = "+--------------------------------------------------+"
BANNER_TITLE = "|              PURINTA AIRDROP BOT               |"
BANNER_BOTTOM = "+--------------------------------------------------+"

def banner():
    print(BANNER)
    print(BANNER_TITLE)
    print(BANNER_BOTTOM)

def log(msg, t="+"): print(f"[{t}] {msg}")

# ── Config ──────────────────────────────────────────────

def load_config():
    cfg = {}
    with open("config.txt") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                cfg[k.strip()] = v.strip()
    referral_url = cfg.get("REFERRAL_URL", "")
    # Extract referrer wallet dari referral URL — ambil invite code
    referral_code = referral_url.rstrip("/").split("/")[-1]
    return referral_url, referral_code

def load_wallets():
    wallets = []
    with open("data.txt") as f:
        content = f.read()
    blocks = content.split("---")
    for block in blocks:
        lines = [l.strip() for l in block.strip().splitlines() if l.strip() and not l.strip().startswith("#")]
        if len(lines) >= 3:
            wallets.append({
                "handle": lines[0],
                "auth_token": lines[1],
                "ct0": lines[2],
            })
    return wallets

def load_privkeys():
    keys = []
    # PRIVKEY_FIRST dulu
    first = os.getenv("PRIVKEY_FIRST")
    if first and first != "0x":
        keys.append(first)
    i = 1
    while True:
        k = os.getenv(f"PRIVKEY_{i}")
        if not k:
            break
        if k != "0x":
            keys.append(k)
        i += 1
    return keys

# ── SIWE ────────────────────────────────────────────────

def siwe_sign(privkey, wallet_address):
    message = (
        f"tribal-campaign.purinta.xyz wants you to sign in with your Ethereum account:\n"
        f"{wallet_address}\n\n"
        f"Sign in to Purinta Tribal Campaign\n\n"
        f"URI: https://tribal-campaign.purinta.xyz\n"
        f"Version: 1\n"
        f"Chain ID: 1\n"
        f"Nonce: {int(time.time())}\n"
        f"Issued At: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}"
    )
    msg = encode_defunct(text=message)
    signed = Account.sign_message(msg, private_key=privkey)
    return signed.signature.hex()

# ── Turnstile (curl_cffi passive bypass) ────────────────

def get_session():
    sess = requests.Session(impersonate="chrome")
    return sess

# ── Purinta API ─────────────────────────────────────────

def purinta_create_session(sess, wallet, handle, signature, referrer_wallet):
    # Get turnstile token first via passive
    log("Fetching Turnstile token...")
    try:
        r = sess.get(
            f"{BASE_URL}/join",
            headers={
                "Referer": BASE_URL,
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            },
            timeout=30
        )
        # Coba ambil turnstile token dari cookie atau response
        turnstile_token = r.cookies.get("cf_clearance", "")
        if not turnstile_token:
            # Fallback: pakai empty string, mungkin passive langsung lolos
            turnstile_token = ""
        log(f"Turnstile: {'got token' if turnstile_token else 'no token, trying anyway'}", "@")
    except Exception as e:
        log(f"Turnstile fetch error: {e}", "!")
        turnstile_token = ""

    payload = {
        "wallet": wallet,
        "handle": handle,
        "signature": signature,
        "turnstileToken": turnstile_token,
        "referrerWallet": referrer_wallet,
    }

    r = sess.post(
        f"{BASE_URL}/api/session/create",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/join",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        },
        timeout=30
    )
    return r.json()

def purinta_verify_tweet(sess, wallet, handle, tweet_url):
    payload = {
        "wallet": wallet,
        "handle": handle,
        "tweetUrl": tweet_url,
    }
    r = sess.post(
        f"{BASE_URL}/api/verify-tweet",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/join",
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        },
        timeout=30
    )
    return r.json()

# ── Twitter API ──────────────────────────────────────────

def tweet_post(auth_token, ct0, text):
    sess = requests.Session(impersonate="chrome")
    headers = {
        "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
        "cookie": f"auth_token={auth_token}; ct0={ct0}",
        "x-csrf-token": ct0,
        "content-type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en",
        "origin": "https://x.com",
        "referer": "https://x.com/",
    }
    payload = {
        "variables": {
            "tweet_text": text,
            "dark_request": False,
            "media": {"media_entities": [], "possibly_sensitive": False},
            "semantic_annotation_ids": [],
        },
        "features": {
            "tweetypie_unmention_optimization_enabled": True,
            "responsive_web_edit_tweet_api_enabled": True,
            "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
            "view_counts_everywhere_api_enabled": True,
            "longform_notetweets_consumption_enabled": True,
            "responsive_web_twitter_article_tweet_consumption_enabled": False,
            "tweet_awards_web_tipping_enabled": False,
            "longform_notetweets_rich_text_read_enabled": True,
            "longform_notetweets_inline_media_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "freedom_of_speech_not_reach_fetch_enabled": True,
            "standardized_nudges_misinfo": True,
            "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "interactive_text_enabled": True,
            "responsive_web_text_conversations_enabled": False,
            "responsive_web_enhance_cards_enabled": False,
        },
        "queryId": "SoVnbfCycZ7fERGCwpZkYA",
    }
    r = sess.post(
        "https://api.twitter.com/graphql/SoVnbfCycZ7fERGCwpZkYA/CreateTweet",
        json=payload,
        headers=headers,
        timeout=30
    )
    data = r.json()
    try:
        tweet_id = data["data"]["create_tweet"]["tweet_results"]["result"]["rest_id"]
        return tweet_id
    except Exception:
        log(f"Tweet error: {data}", "!")
        return None

# ── Main flow per akun ───────────────────────────────────

def run_account(idx, privkey, wallet_data, referrer_wallet, referral_url):
    handle = wallet_data["handle"]
    auth_token = wallet_data["auth_token"]
    ct0 = wallet_data["ct0"]

    log(f"=== Akun {idx+1}: @{handle} ===", "@")

    # Derive wallet address
    account = Account.from_key(privkey)
    wallet_address = account.address
    log(f"Wallet: {wallet_address}")

    # SIWE sign
    log("Signing SIWE message...")
    signature = siwe_sign(privkey, wallet_address)

    # curl_cffi session
    sess = get_session()

    # Session create
    log("Creating Purinta session...")
    try:
        resp = purinta_create_session(sess, wallet_address, handle, signature, referrer_wallet)
        log(f"Session response: {json.dumps(resp)}", "@")
        code = resp.get("code", "")
        if not code:
            log("Gagal dapat code dari session/create!", "!")
            return False
        log(f"Code: {code}")
    except Exception as e:
        log(f"Session create error: {e}", "!")
        return False

    # Construct tweet text
    invite_link = f"{BASE_URL}/invite/{code}"
    tweet_text = f'I just joined House Kami. "Mirror the chain."\n\nCode: {code}\n\nJoin my tribe: {invite_link}\n\n@purintaxyz'
    log(f"Tweet text:\n{tweet_text}", "@")

    # Post tweet
    log("Posting tweet...")
    tweet_id = tweet_post(auth_token, ct0, tweet_text)
    if not tweet_id:
        log("Gagal post tweet!", "!")
        return False
    tweet_url = f"https://x.com/{handle}/status/{tweet_id}"
    log(f"Tweet URL: {tweet_url}")

    # Verify tweet
    log("Verifying tweet...")
    try:
        verify_resp = purinta_verify_tweet(sess, wallet_address, handle, tweet_url)
        log(f"Verify response: {json.dumps(verify_resp)}", "@")
        if verify_resp.get("passed"):
            log(f"✓ Akun @{handle} berhasil!", "+")
            discord_token = verify_resp.get("discordLinkToken", "")
            if discord_token:
                log(f"Discord Link Token: {discord_token}")
            return True
        else:
            log(f"Verify gagal: {verify_resp}", "!")
            return False
    except Exception as e:
        log(f"Verify error: {e}", "!")
        return False

# ── Menu ─────────────────────────────────────────────────

def main():
    banner()

    referral_url, referral_code = load_config()
    wallets = load_wallets()
    privkeys = load_privkeys()

    if not wallets:
        log("wallets.txt kosong!", "!")
        return
    if not privkeys:
        log(".env kosong!", "!")
        return
    if len(wallets) != len(privkeys):
        log(f"Jumlah wallet ({len(wallets)}) != privkey ({len(privkeys)})", "!")
        return

    # Referrer wallet = wallet dari privkey pertama
    referrer_account = Account.from_key(privkeys[0])
    referrer_wallet = referrer_account.address
    log(f"Referrer wallet: {referrer_wallet}")
    log(f"Total akun: {len(wallets)}")

    print()
    print("[1] Jalanin 1 akun")
    print("[2] Semua akun")
    print("[3] Dari akun X sampai selesai")
    print()
    choice = input("Pilih: ").strip()

    if choice == "1":
        idx = int(input(f"Nomor akun (1-{len(wallets)}): ").strip()) - 1
        run_account(idx, privkeys[idx], wallets[idx], referrer_wallet, referral_url)

    elif choice == "2":
        for i in range(len(wallets)):
            run_account(i, privkeys[i], wallets[i], referrer_wallet, referral_url)
            if i < len(wallets) - 1:
                time.sleep(3)

    elif choice == "3":
        start = int(input(f"Mulai dari akun ke (1-{len(wallets)}): ").strip()) - 1
        for i in range(start, len(wallets)):
            run_account(i, privkeys[i], wallets[i], referrer_wallet, referral_url)
            if i < len(wallets) - 1:
                time.sleep(3)

    else:
        log("Pilihan invalid!", "!")

if __name__ == "__main__":
    main()
