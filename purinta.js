const fs = require('fs');
const path = require('path');
const { ethers } = require('ethers');
const readline = require('readline');

// ── Utils ─────────────────────────────────────────────
const log = (msg, t = '+') => console.log(`[${t}] ${msg}`);
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

function banner() {
  console.log('+--------------------------------------------------+');
  console.log('|              PURINTA AIRDROP BOT                |');
  console.log('+--------------------------------------------------+');
}

// ── Load .env ─────────────────────────────────────────
function loadEnv(p = '.env') {
  const env = {};
  try {
    fs.readFileSync(p, 'utf8').split('\n').forEach(line => {
      line = line.trim();
      if (line && !line.startsWith('#') && line.includes('=')) {
        const [k, ...rest] = line.split('=');
        env[k.trim()] = rest.join('=').trim();
      }
    });
  } catch {}
  return env;
}

// ── Load config.txt ───────────────────────────────────
function loadConfig() {
  const cfg = {};
  fs.readFileSync('config.txt', 'utf8').split('\n').forEach(line => {
    line = line.trim();
    if (line && !line.startsWith('#') && line.includes('=')) {
      const [k, ...rest] = line.split('=');
      cfg[k.trim()] = rest.join('=').trim();
    }
  });
  return cfg.REFERRAL_URL || '';
}

// ── Load data.txt ─────────────────────────────────────
function loadWallets() {
  const content = fs.readFileSync('data.txt', 'utf8');
  return content.split('---').map(block => {
    const lines = block.split('\n')
      .map(l => l.trim())
      .filter(l => l && !l.startsWith('#'));
    if (lines.length < 3) return null;
    return { handle: lines[0], authToken: lines[1], ct0: lines[2] };
  }).filter(Boolean);
}

// ── Load privkeys from .env ───────────────────────────
function loadPrivkeys(env) {
  const keys = [];
  if (env['PRIVKEY_FIRST']) keys.push(env['PRIVKEY_FIRST']);
  let i = 1;
  while (env[`PRIVKEY_${i}`]) {
    keys.push(env[`PRIVKEY_${i}`]);
    i++;
  }
  return keys;
}

// ── SIWE Sign ─────────────────────────────────────────
async function siweSign(privkey, walletAddress, handle) {
  const message =
    `tribal-campaign.purinta.xyz wants you to sign in for the Purinta tribal campaign.\n\n` +
    `Wallet: ${walletAddress}\n` +
    `X handle: @${handle}\n\n` +
    `Signing this message does not authorize any transaction.`;
  const wallet = new ethers.Wallet(privkey);
  const signature = await wallet.signMessage(message);
  return signature;
}

// ── Purinta session/create ────────────────────────────
async function purintaCreate(wallet, handle, signature, referrerWallet) {
  const payload = { wallet, handle, signature, turnstileToken: '', referrerWallet };
  const res = await fetch('https://tribal-campaign.purinta.xyz/api/session/create', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': 'https://tribal-campaign.purinta.xyz',
      'Referer': 'https://tribal-campaign.purinta.xyz/join',
      'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    },
    body: JSON.stringify(payload),
  });
  return res.json();
}

// ── Purinta verify-tweet ──────────────────────────────
async function purintaVerifyTweet(wallet, handle, tweetUrl) {
  const payload = { wallet, handle, tweetUrl };
  const res = await fetch('https://tribal-campaign.purinta.xyz/api/verify-tweet', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Origin': 'https://tribal-campaign.purinta.xyz',
      'Referer': 'https://tribal-campaign.purinta.xyz/join',
      'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
    },
    body: JSON.stringify(payload),
  });
  return res.json();
}

// ── Post Tweet ────────────────────────────────────────
async function postTweet(authToken, ct0, text) {
  const payload = {
    variables: {
      tweet_text: text,
      dark_request: false,
      media: { media_entities: [], possibly_sensitive: false },
      semantic_annotation_ids: [],
    },
    features: {
      tweetypie_unmention_optimization_enabled: true,
      responsive_web_edit_tweet_api_enabled: true,
      graphql_is_translatable_rweb_tweet_is_translatable_enabled: true,
      view_counts_everywhere_api_enabled: true,
      longform_notetweets_consumption_enabled: true,
      responsive_web_twitter_article_tweet_consumption_enabled: false,
      tweet_awards_web_tipping_enabled: false,
      longform_notetweets_rich_text_read_enabled: true,
      longform_notetweets_inline_media_enabled: true,
      responsive_web_graphql_exclude_directive_enabled: true,
      verified_phone_label_enabled: false,
      freedom_of_speech_not_reach_fetch_enabled: true,
      standardized_nudges_misinfo: true,
      tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled: true,
      responsive_web_graphql_skip_user_profile_image_extensions_enabled: false,
      responsive_web_graphql_timeline_navigation_enabled: true,
      interactive_text_enabled: true,
      responsive_web_text_conversations_enabled: false,
      responsive_web_enhance_cards_enabled: false,
    },
    queryId: 'SoVnbfCycZ7fERGCwpZkYA',
  };

  const res = await fetch('https://api.twitter.com/graphql/SoVnbfCycZ7fERGCwpZkYA/CreateTweet', {
    method: 'POST',
    headers: {
      'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
      'cookie': `auth_token=${authToken}; ct0=${ct0}`,
      'x-csrf-token': ct0,
      'content-type': 'application/json',
      'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
      'x-twitter-auth-type': 'OAuth2Session',
      'x-twitter-client-language': 'en',
      'origin': 'https://x.com',
      'referer': 'https://x.com/',
    },
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  try {
    return data.data.create_tweet.tweet_results.result.rest_id;
  } catch {
    log(`Tweet error: ${JSON.stringify(data)}`, '!');
    return null;
  }
}

// ── Run per akun ──────────────────────────────────────
async function runAccount(idx, privkey, walletData) {
  const { handle, authToken, ct0 } = walletData;
  log(`=== Akun ${idx + 1}: @${handle} ===`, '@');

  const wallet = new ethers.Wallet(privkey);
  const walletAddress = wallet.address;
  log(`Wallet: ${walletAddress}`);

  // Referrer wallet dari privkey pertama (index 0)
  const env = loadEnv();
  const privkeys = loadPrivkeys(env);
  const referrerWallet = new ethers.Wallet(privkeys[0]).address;

  log('Signing SIWE...');
  const signature = await siweSign(privkey, walletAddress, handle);

  log('Creating Purinta session...');
  let sessionResp;
  try {
    sessionResp = await purintaCreate(walletAddress, handle, signature, referrerWallet);
    log(`Session response: ${JSON.stringify(sessionResp)}`, '@');
  } catch (e) {
    log(`Session error: ${e.message}`, '!');
    return false;
  }

  const code = sessionResp?.code;
  if (!code) {
    log('Gagal dapat code!', '!');
    return false;
  }
  log(`Code: ${code}`);

  const inviteLink = `https://tribal-campaign.purinta.xyz/invite/${code}`;
  const tweetText = `I just joined House Kami. "Mirror the chain."\n\nCode: ${code}\n\nJoin my tribe: ${inviteLink}\n\n@purintaxyz`;
  log(`Tweet:\n${tweetText}`, '@');

  log('Posting tweet...');
  const tweetId = await postTweet(authToken, ct0, tweetText);
  if (!tweetId) {
    log('Gagal post tweet!', '!');
    return false;
  }
  const tweetUrl = `https://x.com/${handle}/status/${tweetId}`;
  log(`Tweet URL: ${tweetUrl}`);

  log('Verifying tweet...');
  let verifyResp;
  try {
    verifyResp = await purintaVerifyTweet(walletAddress, handle, tweetUrl);
    log(`Verify response: ${JSON.stringify(verifyResp)}`, '@');
  } catch (e) {
    log(`Verify error: ${e.message}`, '!');
    return false;
  }

  if (verifyResp?.passed) {
    log(`✓ Akun @${handle} berhasil!`, '+');
    if (verifyResp.discordLinkToken) log(`Discord Token: ${verifyResp.discordLinkToken}`);
    return true;
  } else {
    log(`Verify gagal: ${JSON.stringify(verifyResp)}`, '!');
    return false;
  }
}

// ── Menu ──────────────────────────────────────────────
async function main() {
  banner();

  const env = loadEnv();
  const wallets = loadWallets();
  const privkeys = loadPrivkeys(env);

  if (!wallets.length) { log('data.txt kosong!', '!'); return; }
  if (!privkeys.length) { log('.env kosong!', '!'); return; }
  if (wallets.length !== privkeys.length) {
    log(`Jumlah wallet (${wallets.length}) != privkey (${privkeys.length})`, '!');
    return;
  }

  log(`Total akun: ${wallets.length}`);
  console.log('\n[1] Jalanin 1 akun');
  console.log('[2] Semua akun');
  console.log('[3] Dari akun X sampai selesai\n');

  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const ask = (q) => new Promise(r => rl.question(q, r));

  const choice = await ask('Pilih: ');

  if (choice === '1') {
    const n = parseInt(await ask(`Nomor akun (1-${wallets.length}): `)) - 1;
    await runAccount(n, privkeys[n], wallets[n]);
  } else if (choice === '2') {
    for (let i = 0; i < wallets.length; i++) {
      await runAccount(i, privkeys[i], wallets[i]);
      if (i < wallets.length - 1) await sleep(3000);
    }
  } else if (choice === '3') {
    const start = parseInt(await ask(`Mulai dari akun ke (1-${wallets.length}): `)) - 1;
    for (let i = start; i < wallets.length; i++) {
      await runAccount(i, privkeys[i], wallets[i]);
      if (i < wallets.length - 1) await sleep(3000);
    }
  } else {
    log('Pilihan invalid!', '!');
  }

  rl.close();
}

main().catch(e => { log(e.message, '!'); process.exit(1); });
