import sys
import os

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import ast
import asyncio
import functools
import html
import json
import logging
import math
import operator
import os.path
import platform
import re
import time
import traceback
from datetime import datetime
from io import BytesIO
from urllib.parse import quote_plus
import warnings

import httpx
import psutil
import qrcode
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning)
import keep_alive

BOT_START_TIME = time.time()
load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID", "")
BOT_NAME = os.getenv("BOT_NAME", "QR Generator Pro")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@Qr_Generator_Pro_Robot")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID", "")
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL", "")

DATA_FILE = "users.json"
CONFIG_FILE = "bot_config.json"
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# ─── Sleek Minimalist Custom Emojis for Primary Headers & Badges ───
CUSTOM_EMOJIS = {
    "crown": '<tg-emoji emoji-id="6325564362522104416">👑</tg-emoji>',
    "diamond": '<tg-emoji emoji-id="6325717349257187998">💎</tg-emoji>',
    "card": '<tg-emoji emoji-id="5445353829304387411">💳</tg-emoji>',
    "sparkle": '<tg-emoji emoji-id="6325413811033477368">✨</tg-emoji>',
    "shield": '<tg-emoji emoji-id="6325790127478018778">🛡️</tg-emoji>',
    "server": '<tg-emoji emoji-id="6325332404223350181">🖥️</tg-emoji>',
    "gear": '<tg-emoji emoji-id="6325849814638531007">⚙️</tg-emoji>',
    "zap": '<tg-emoji emoji-id="6325415120998502570">⚡</tg-emoji>',
    "storage": '<tg-emoji emoji-id="5445221832074483553">💾</tg-emoji>',
    "bot": '<tg-emoji emoji-id="6325569336094232734">🤖</tg-emoji>',
    "money": '<tg-emoji emoji-id="6325444137797554944">💰</tg-emoji>',
    "coin": '<tg-emoji emoji-id="5377505475015235101">🪙</tg-emoji>',
    "check": '<tg-emoji emoji-id="6325382986053193737">✅</tg-emoji>',
    "cross": '<tg-emoji emoji-id="6325844463109280731">❌</tg-emoji>',
    "user": '<tg-emoji emoji-id="6307777408300753473">👤</tg-emoji>',
    "gem": '<tg-emoji emoji-id="6205965994528086727">💠</tg-emoji>',
}


def ce(key: str, fallback: str = "") -> str:
    """Return custom emoji tag if defined, otherwise return clean fallback."""
    return CUSTOM_EMOJIS.get(key, fallback)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ─── Database & State Persistence (Thread-Safe & Atomic) ───


def load_json(filepath: str, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return default
    return default


def atomic_save_json(filepath: str, data):
    """Atomically write data to filepath using a temporary file to avoid corrupting data on crash."""
    tmp_path = f"{filepath}.tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    except Exception as e:
        logger.error(f"Failed to atomically save {filepath}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


user_data = load_json(DATA_FILE, {})
bot_config = load_json(
    CONFIG_FILE, {"maintenance": False, "total_generated": 0, "blacklist": []}
)
if "rate_limit_seconds" not in bot_config:
    bot_config["rate_limit_seconds"] = 0.5
if "artificial_delay_seconds" not in bot_config:
    bot_config["artificial_delay_seconds"] = 0.0
if "blacklist" not in bot_config:
    bot_config["blacklist"] = []

_blacklist_set: set[int] = set()


def update_blacklist_cache():
    """Maintain O(1) set for zero-overhead blacklist verification."""
    global _blacklist_set
    bl = bot_config.get("blacklist", [])
    s = set()
    for x in bl:
        try:
            s.add(int(x))
        except (ValueError, TypeError):
            pass
    _blacklist_set = s


update_blacklist_cache()


def is_blacklisted(uid) -> bool:
    """Instant O(1) lookup checking if user is permanently blacklisted."""
    if not uid:
        return False
    try:
        return int(uid) in _blacklist_set
    except (ValueError, TypeError):
        return False

db_dirty = False


def save_db():
    global db_dirty
    db_dirty = True


async def db_writer_loop():
    global db_dirty
    while True:
        try:
            await asyncio.sleep(5)
            if db_dirty:
                db_dirty = False
                users_snapshot = dict(user_data)
                config_snapshot = dict(bot_config)
                await asyncio.to_thread(atomic_save_json, DATA_FILE, users_snapshot)
                await asyncio.to_thread(atomic_save_json, CONFIG_FILE, config_snapshot)
            clean_rate_limit_cache()
            cleanup_cache_dir()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in db_writer_loop: {e}")


ADMIN_IDS_SET: set[str] = set()


def reload_admin_ids():
    global ADMIN_IDS_SET
    if ADMIN_ID:
        ADMIN_IDS_SET = {a.strip() for a in str(ADMIN_ID).split(",") if a.strip()}
    else:
        ADMIN_IDS_SET = set()


reload_admin_ids()


def is_admin(uid: int | str | None) -> bool:
    if uid is None:
        return False
    return str(uid).strip() in ADMIN_IDS_SET


# Conversation States
WAITING_UPI, WAITING_NAME = range(2)
WAITING_BROADCAST_MSG = 10
WAITING_EDIT_NAME = 40
WAITING_EDIT_UPI = 41
WAITING_DEFAULT_NOTE = 42
WAITING_CFG_BOT_NAME = 50
WAITING_CFG_BOT_USERNAME = 51
WAITING_CFG_SUPPORT = 52
WAITING_CFG_LOG_CHANNEL = 53
WAITING_CFG_FORCE_SUB = 54
WAITING_CFG_RATELIMIT = 55
WAITING_CFG_DELAY = 56


def update_env(key: str, value: str):
    """Safely update a key in the .env file with backslash and newline sanitization."""
    global ADMIN_ID
    env_path = ".env"
    lines = []
    found = False
    clean_val = str(value).replace("\r", "").replace("\n", "").strip().rstrip("\\")
    clean_val = clean_val.replace('"', '\\"')
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f'{key}="{clean_val}"\n'
            found = True
            break
    if not found:
        lines.append(f'{key}="{clean_val}"\n')
    tmp_env = f"{env_path}.tmp"
    with open(tmp_env, "w", encoding="utf-8") as f:
        f.writelines(lines)
    os.replace(tmp_env, env_path)
    if key == "ADMIN_ID":
        ADMIN_ID = clean_val
        reload_admin_ids()


# Rate limiter: {user_id: last_command_time}
_rate_limit: dict[int, float] = {}


def clean_rate_limit_cache():
    """Purge stale entries older than 1 hour to prevent unbounded memory growth."""
    now = time.time()
    cutoff = now - 3600
    stale = [uid for uid, t in list(_rate_limit.items()) if t < cutoff]
    for uid in stale:
        _rate_limit.pop(uid, None)


def slow_and_rate_limited(func):
    """Enforces rate limiting and prevents spamming."""

    @functools.wraps(func)
    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        if not update or not update.effective_user:
            return await func(update, context, *args, **kwargs)

        uid = update.effective_user.id

        # Admins are exempt from rate limit and delays
        if is_admin(uid):
            return await func(update, context, *args, **kwargs)

        now = time.time()
        last = _rate_limit.get(uid, 0)
        is_cb = bool(update.callback_query)

        try:
            cfg_limit = float(bot_config.get("rate_limit_seconds", 0.5))
            if math.isnan(cfg_limit) or math.isinf(cfg_limit) or cfg_limit < 0:
                cfg_limit = 0.5
        except (ValueError, TypeError):
            cfg_limit = 0.5

        limit = 0.3 if is_cb else cfg_limit
        if limit > 0 and (now - last < limit):
            remaining = max(0.1, round(limit - (now - last), 1))
            if is_cb:
                try:
                    await update.callback_query.answer(
                        f"⚠️ Please wait {remaining}s.",
                        show_alert=False,
                    )
                except Exception:
                    pass
            elif update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        f"⚠️ <b>Slow down!</b> Please wait {remaining}s between commands.",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass
            return

        try:
            delay = float(bot_config.get("artificial_delay_seconds", 0.0))
            if math.isnan(delay) or math.isinf(delay) or delay < 0:
                delay = 0.0
        except (ValueError, TypeError):
            delay = 0.0

        if delay > 0:
            await asyncio.sleep(delay)

        _rate_limit[uid] = time.time()
        return await func(update, context, *args, **kwargs)

    return wrapper


async def enforce_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    """Enforce access control: First verifies blacklist, then force subscription."""
    if not update.effective_user:
        return True

    uid = update.effective_user.id
    if is_admin(uid):
        return True

    # 1. Blacklist check ALWAYS runs first regardless of force sub configuration
    if is_blacklisted(uid):
        if update.callback_query:
            try:
                await update.callback_query.answer(
                    "⛔️ You are permanently banned.", show_alert=True
                )
            except Exception:
                pass
        elif update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "⛔️ <b>You are permanently banned from using this bot.</b>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        return False

    # 2. Check Force Subscription if configured
    if not FORCE_SUB_CHANNEL:
        return True

    try:
        member = await ctx.bot.get_chat_member(
            chat_id=FORCE_SUB_CHANNEL, user_id=uid
        )
        if member.status in ["left", "kicked"]:
            clean_ch = FORCE_SUB_CHANNEL.strip()
            channel_url = None
            if clean_ch.startswith("@"):
                channel_url = f"https://t.me/{clean_ch.lstrip('@')}"
            elif clean_ch.startswith("https://"):
                channel_url = clean_ch
            else:
                try:
                    channel_url = await ctx.bot.export_chat_invite_link(clean_ch)
                except Exception as e:
                    logger.warning(f"Could not export chat invite link for {clean_ch}: {e}")
                    channel_url = None

            kb_buttons = []
            if channel_url:
                kb_buttons.append([InlineKeyboardButton("📢 Join Channel", url=channel_url)])
            kb = InlineKeyboardMarkup(kb_buttons) if kb_buttons else None
            text = (
                "🛑 <b>Must Join Channel</b>\n\n"
                "You must join our official channel to use this bot!"
            )

            if update.callback_query:
                try:
                    await update.callback_query.answer()
                except Exception:
                    pass
                if update.callback_query.message:
                    await update.callback_query.message.reply_text(
                        text, parse_mode=ParseMode.HTML, reply_markup=kb
                    )
            elif update.effective_message:
                await update.effective_message.reply_text(
                    text, parse_mode=ParseMode.HTML, reply_markup=kb
                )
            return False
        return True
    except Exception as e:
        logger.debug(f"Force-sub check pass (open fail): {e}")
        return True


# ═══ High-Performance QR Engine ═══

SCALE = 2
try:
    font_title = ImageFont.truetype("font.ttf", 16 * SCALE)
    font_amt = ImageFont.truetype("font.ttf", 52 * SCALE)
    font_sub = ImageFont.truetype("font.ttf", 15 * SCALE)
    font_lbl = ImageFont.truetype("font.ttf", 12 * SCALE)
    font_avatar = ImageFont.truetype("font.ttf", 160)
except Exception:
    font_title = font_amt = font_sub = font_lbl = font_avatar = ImageFont.load_default()

_W = 500 * SCALE
_H = 750 * SCALE
_QR_SZ = 340 * SCALE
_PAD = 40 * SCALE
_QR_Y = 230 * SCALE
_QR_X = (_W - _QR_SZ) // 2
_LOGO_SZ = int(_QR_SZ * 0.22)
_LOGO_X = _QR_X + (_QR_SZ - _LOGO_SZ) // 2
_LOGO_Y = _QR_Y + (_QR_SZ - _LOGO_SZ) // 2

# Pre-cache circle mask and white background
_circle_mask = Image.new("L", (_LOGO_SZ, _LOGO_SZ), 0)
ImageDraw.Draw(_circle_mask).ellipse((0, 0, _LOGO_SZ, _LOGO_SZ), fill=255)
_white_bg = Image.new("RGBA", (_LOGO_SZ, _LOGO_SZ), "#FFFFFF")


def generate_qr(
    upi_id: str,
    amount: float,
    name: str = "",
    note: str = "",
    bot_username: str = "",
    pfp_path: str = "",
) -> BytesIO:
    """Generate high-contrast, loss-free UPI QR code with standard URI encoding."""
    clean_upi = upi_id.strip()
    clean_name = re.sub(r"[\r\n\t]+", " ", str(name)).strip()[:30] if name else ""
    clean_note = re.sub(r"[\r\n\t]+", " ", str(note)).strip()[:50] if note else ""

    upi_url = f"upi://pay?pa={quote_plus(clean_upi)}&pn={quote_plus(clean_name)}&am={amount:.2f}&cu=INR"
    if clean_note:
        upi_url += f"&tn={quote_plus(clean_note)}"

    canvas = Image.new("RGB", (_W, _H), "#0A0A0C")
    draw = ImageDraw.Draw(canvas)

    # Top accent line
    draw.rectangle([0, 0, _W, 6 * SCALE], fill="#00E5FF")

    # Amount block
    draw.text((_PAD, 50 * SCALE), "PAY TO", fill="#6B6B80", font=font_lbl)
    disp_name = (clean_name[:28] + "..") if len(clean_name) > 28 else clean_name
    draw.text(
        (_PAD, 70 * SCALE),
        disp_name.upper() if disp_name else "MERCHANT",
        fill="#FFFFFF",
        font=font_title,
    )
    draw.text(
        (_PAD, 110 * SCALE), f"₹{amount:,.2f}", fill="#00E5FF", font=font_amt
    )
    disp_upi = (clean_upi[:34] + "..") if len(clean_upi) > 34 else clean_upi
    draw.text(
        (_PAD, 175 * SCALE), f"UPI ID: {disp_upi}", fill="#8A8A99", font=font_sub
    )

    # QR Box background
    draw.rounded_rectangle(
        [
            _QR_X - (15 * SCALE),
            _QR_Y - (15 * SCALE),
            _QR_X + _QR_SZ + (15 * SCALE),
            _QR_Y + _QR_SZ + (15 * SCALE),
        ],
        radius=24 * SCALE,
        fill="#FFFFFF",
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10 * SCALE,
        border=0,
    )
    qr.add_data(upi_url)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert("RGB")
    qr_img = qr_img.resize((_QR_SZ, _QR_SZ), Image.Resampling.NEAREST)
    canvas.paste(qr_img, (_QR_X, _QR_Y))

    # Center Logo / Profile Picture
    if pfp_path and os.path.exists(pfp_path):
        try:
            with Image.open(pfp_path) as raw_dp:
                user_dp = raw_dp.convert("RGBA").resize(
                    (_LOGO_SZ, _LOGO_SZ), Image.Resampling.LANCZOS
                )
                canvas.paste(_white_bg, (_LOGO_X, _LOGO_Y), mask=_circle_mask)
                canvas.paste(user_dp, (_LOGO_X, _LOGO_Y), mask=_circle_mask)
        except Exception as e:
            logger.debug(f"PFP paste skipped: {e}")

    # Bottom block
    draw.text(
        (_W // 2, _QR_Y + _QR_SZ + (50 * SCALE)),
        "SCAN TO PAY",
        fill="#FFFFFF",
        font=font_title,
        anchor="mm",
    )
    draw.text(
        (_W // 2, _QR_Y + _QR_SZ + (75 * SCALE)),
        "Amount is pre-filled. Powered by UPI.",
        fill="#6B6B80",
        font=font_lbl,
        anchor="mm",
    )

    # Watermark
    clean_bot_user = bot_username.lstrip("@").upper() if bot_username else "GENPAY"
    draw.text(
        (_W // 2, _H - (30 * SCALE)),
        clean_bot_user,
        fill="#333344",
        font=font_lbl,
        anchor="mm",
    )

    bio = BytesIO()
    bio.name = "qr.png"
    canvas.save(bio, "PNG")
    bio.seek(0)
    return bio


def fmt_card(
    upi_id: str, amount: float, user_name: str, bot_username: str
) -> str:
    escaped_name = html.escape(str(user_name or "Merchant"))
    escaped_upi = html.escape(str(upi_id))
    escaped_bot = html.escape(str(bot_username or BOT_NAME))
    return (
        f"{ce('card', '💳')} <b>PAYMENT QR READY</b>\n\n"
        f"  {ce('diamond', '💎')} ₹ <b>{amount:,.2f}</b>\n"
        f"  {ce('crown', '👑')} <code>{escaped_upi}</code>\n"
        f"  {ce('user', '👤')} {escaped_name}\n\n"
        f"<i>{ce('sparkle', '✨')} Open any UPI app → Scan → Pay</i>\n"
        f"{ce('shield', '🛡️')} <i>Secured by {escaped_bot}</i>"
    )


async def log_qr_generation(bot, user, uid_str: str, amount: float, upi_id: str):
    """Log QR generation event to admin log channel asynchronously."""
    if not LOG_CHANNEL_ID:
        return
    try:
        user_name = getattr(user, "first_name", None) or "User"
        escaped_first = html.escape(str(user_name))
        escaped_upi_log = html.escape(str(upi_id))
        log_text = (
            f"📝 <b>New QR Generated</b>\n"
            f"👤 <b>User:</b> <a href='tg://user?id={uid_str}'>"
            f"{escaped_first}</a> "
            f"(<code>{uid_str}</code>)\n"
            f"💰 <b>Amount:</b> ₹{amount:,.2f}\n"
            f"🔗 <b>UPI:</b> <code>{escaped_upi_log}</code>"
        )
        await bot.send_message(
            chat_id=LOG_CHANNEL_ID,
            text=log_text,
            parse_mode=ParseMode.HTML,
        )
    except Exception as e:
        logger.debug(f"Log notice: {e}")


def generate_initials_avatar(name: str, uid: int) -> str:
    """Generate a circular avatar with user initials when they have no PFP."""
    avatar_path = os.path.join(CACHE_DIR, f"avatar_{abs(uid)}.png")
    if os.path.exists(avatar_path):
        return avatar_path

    PALETTE = [
        ("#6C5CE7", "#A29BFE"),
        ("#00B894", "#55EFC4"),
        ("#E17055", "#FAB1A0"),
        ("#0984E3", "#74B9FF"),
        ("#E84393", "#FD79A8"),
        ("#00CEC9", "#81ECEC"),
        ("#FDCB6E", "#FFEAA7"),
        ("#D63031", "#FF7675"),
    ]
    color1, color2 = PALETTE[abs(uid) % len(PALETTE)]

    parts = name.strip().split() if name and name.strip() else []
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1 and len(parts[0]) > 0:
        initials = parts[0][0].upper()
    else:
        initials = "?"

    sz = 400
    base = Image.new("RGB", (1, sz))
    c1_r, c1_g, c1_b = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
    c2_r, c2_g, c2_b = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
    for y in range(sz):
        t = y / sz
        r = int(c1_r * (1 - t) + c2_r * t)
        g = int(c1_g * (1 - t) + c2_g * t)
        b = int(c1_b * (1 - t) + c2_b * t)
        base.putpixel((0, y), (r, g, b))

    gradient = base.resize((sz, sz), Image.Resampling.BILINEAR)

    mask = Image.new("L", (sz, sz), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, sz, sz), fill=255)

    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    img.paste(gradient, (0, 0), mask=mask)
    draw = ImageDraw.Draw(img)

    draw.text(
        (sz // 2, sz // 2),
        initials,
        fill="#FFFFFF",
        font=font_avatar,
        anchor="mm",
    )

    img.save(avatar_path, "PNG")
    return avatar_path


async def get_user_pfp(bot, user) -> str:
    """Fetch user profile photo with local caching or fallback to initials avatar."""
    uid = user.id
    uid_str = str(uid)
    pfp_path = os.path.join(CACHE_DIR, f"pfp_{uid_str}.jpg")

    now = time.time()
    if os.path.exists(pfp_path) and (now - os.path.getmtime(pfp_path) < 3600):
        return pfp_path

    try:
        photos = await bot.get_user_profile_photos(user_id=uid, offset=0, limit=1)
        if photos.total_count > 0:
            photo = photos.photos[0][-1]
            file = await photo.get_file()
            await file.download_to_drive(pfp_path)
            return pfp_path
    except Exception as e:
        logger.debug(f"PFP fetch notice for {uid_str}: {e}")
        if os.path.exists(pfp_path):
            return pfp_path

    user_name = user.first_name or ""
    return generate_initials_avatar(user_name, uid)


_last_cache_cleanup = 0.0


def cleanup_cache_dir():
    """Remove cache files older than 24 hours (runs at most once an hour)."""
    global _last_cache_cleanup
    now = time.time()
    if now - _last_cache_cleanup < 3600:
        return
    _last_cache_cleanup = now
    try:
        if not os.path.exists(CACHE_DIR):
            return
        for fname in os.listdir(CACHE_DIR):
            fpath = os.path.join(CACHE_DIR, fname)
            if os.path.isfile(fpath):
                if now - os.path.getmtime(fpath) > 86400:
                    try:
                        os.remove(fpath)
                    except OSError:
                        pass
    except Exception as e:
        logger.debug(f"Cache cleanup notice: {e}")


# ═══ Zero-Delay Real-Time Crypto Engine ═══

_HTTP_CLIENT: httpx.AsyncClient | None = None
_TICKER_CACHE: dict[str, tuple[float, dict]] = {}
_TICKER_CACHE_TTL = 15.0

_LIVE_USDT_DATA = {
    "price_inr": 88.0,
    "change_pct": 0.0,
    "high": 88.0,
    "low": 88.0,
    "volume": 0.0,
    "last_updated": 0.0,
}


def get_http_client() -> httpx.AsyncClient:
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(4.0, connect=2.0),
            limits=httpx.Limits(max_keepalive_connections=25, max_connections=50),
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
    return _HTTP_CLIENT


async def update_usdt_rate_task():
    """Background task updating live USDT-INR rate every 20 seconds so conversions have 0ms latency."""
    while True:
        try:
            client = get_http_client()
            resp = await client.get(
                "https://api.wazirx.com/sapi/v1/ticker/24hr?symbol=usdtinr",
                timeout=3.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                last_p = float(data.get("lastPrice", 0))
                open_p = float(data.get("openPrice", 0))
                if last_p > 0:
                    _LIVE_USDT_DATA["price_inr"] = last_p
                    _LIVE_USDT_DATA["high"] = float(data.get("highPrice", last_p))
                    _LIVE_USDT_DATA["low"] = float(data.get("lowPrice", last_p))
                    _LIVE_USDT_DATA["volume"] = float(data.get("volume", 0))
                    if open_p > 0:
                        _LIVE_USDT_DATA["change_pct"] = (
                            (last_p - open_p) / open_p
                        ) * 100
                    _LIVE_USDT_DATA["last_updated"] = time.time()
        except Exception as e:
            logger.debug(f"USDT background update note: {e}")
        await asyncio.sleep(20)


async def fetch_crypto_ticker(symbol: str) -> dict | None:
    """Fetch live ticker data instantly via persistent warm connections with 15s in-memory TTL caching."""
    sym = symbol.upper().strip()
    now = time.time()
    if sym in _TICKER_CACHE:
        ts, cached_data = _TICKER_CACHE[sym]
        if now - ts < _TICKER_CACHE_TTL:
            return cached_data

    pair = f"{sym}USDT"
    client = get_http_client()

    # 1. Binance (typically 120-220ms via warm connection)
    try:
        resp = await client.get(
            f"https://api.binance.com/api/v3/ticker/24hr?symbol={pair}",
            timeout=2.0,
        )
        if resp.status_code == 200:
            b_data = resp.json()
            res = {
                "source": "Binance",
                "price_usdt": float(b_data["lastPrice"]),
                "change_pct": float(b_data["priceChangePercent"]),
                "high": float(b_data["highPrice"]),
                "low": float(b_data["lowPrice"]),
                "volume": float(b_data["volume"]),
            }
            _TICKER_CACHE[sym] = (now, res)
            return res
    except Exception as e:
        logger.debug(f"Binance fetch for {pair}: {e}")

    # 2. MEXC fallback
    try:
        resp = await client.get(
            f"https://api.mexc.com/api/v3/ticker/24hr?symbol={pair}",
            timeout=2.0,
        )
        if resp.status_code == 200:
            m_data = resp.json()
            res = {
                "source": "MEXC",
                "price_usdt": float(m_data["lastPrice"]),
                "change_pct": float(m_data["priceChangePercent"]) * 100,
                "high": float(m_data["highPrice"]),
                "low": float(m_data["lowPrice"]),
                "volume": float(m_data["volume"]),
            }
            _TICKER_CACHE[sym] = (now, res)
            return res
    except Exception as e:
        logger.debug(f"MEXC fetch for {pair}: {e}")

    return None


async def send_crypto_rate(update: Update, ctx: ContextTypes.DEFAULT_TYPE, currency: str):
    """Format and send zero-delay crypto price card."""
    currency = currency.lower().strip()
    is_private = update.message.chat.type == "private" if update.message else True

    # If USDT is requested, deliver instantly from memory cache with 0ms delay
    if currency == "usdt":
        usdt_inr = _LIVE_USDT_DATA["price_inr"]
        change_pct = _LIVE_USDT_DATA["change_pct"]
        high = _LIVE_USDT_DATA["high"]
        low = _LIVE_USDT_DATA["low"]
        vol = _LIVE_USDT_DATA["volume"]
        trend = "📈" if change_pct >= 0 else "📉"
        sign = "+" if change_pct > 0 else ""

        text = (
            f"{ce('coin', '🪙')} <b>USDT / INR Live Rate</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"• <b>Price (INR):</b> <code>₹{usdt_inr:,.2f}</code>\n"
            f"• <b>Price (USD):</b> <code>$1.0000</code>\n\n"
            f"• <b>24h Change:</b> <code>{sign}{change_pct:.2f}%</code> {trend}\n"
            f"• <b>24h High:</b> <code>₹{high:,.2f}</code>\n"
            f"• <b>24h Low:</b> <code>₹{low:,.2f}</code>\n"
            f"• <b>24h Volume:</b> <code>{vol:,.2f} USDT</code>\n\n"
            f"<i>⚡ Live rate • Instant zero-delay</i>"
        )
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🗑 Close",
                        callback_data=f"cb_delete_msg:{update.effective_user.id}",
                    )
                ]
            ]
        )
        if update.effective_message:
            await update.effective_message.reply_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
        return

    # Indicate typing without spamming message edit events
    if update.effective_chat:
        asyncio.create_task(
            ctx.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.TYPING
            )
        )

    ticker = await fetch_crypto_ticker(currency)
    if not ticker:
        if is_private and update.effective_message:
            await update.effective_message.reply_text(
                f"❌ <b>Could not find live market data for {html.escape(currency.upper())}</b>\n"
                f"<i>Please verify the coin symbol (e.g. BTC, ETH, SOL, DOGE).</i>",
                parse_mode=ParseMode.HTML,
            )
        return

    price_usdt = ticker["price_usdt"]
    usdt_inr = _LIVE_USDT_DATA["price_inr"]
    price_inr = price_usdt * usdt_inr
    change_pct = ticker["change_pct"]
    high = ticker["high"]
    low = ticker["low"]
    vol = ticker["volume"]
    source = ticker["source"]
    trend = "📈" if change_pct >= 0 else "📉"
    sign = "+" if change_pct > 0 else ""

    text = (
        f"{ce('coin', '🪙')} <b>{currency.upper()} Live Market Rate</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"• <b>Price (USDT):</b> <code>${price_usdt:,.4f}</code>\n"
        f"• <b>Price (INR):</b> <code>₹{price_inr:,.2f}</code>\n\n"
        f"• <b>24h Change:</b> <code>{sign}{change_pct:.2f}%</code> {trend}\n"
        f"• <b>24h High:</b> <code>${high:,.4f}</code>\n"
        f"• <b>24h Low:</b> <code>${low:,.4f}</code>\n"
        f"• <b>24h Volume:</b> <code>{vol:,.2f} {currency.upper()}</code>\n\n"
        f"<i>⚡ Live rate from {source} • Instant zero-delay</i>"
    )

    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🗑 Close",
                    callback_data=f"cb_delete_msg:{update.effective_user.id}",
                )
            ]
        ]
    )
    if update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )


async def crypto_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Explicit /crypto <symbol> or /price <symbol> command handler."""
    if not await enforce_sub(update, ctx):
        return
    if not ctx.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ <b>Usage:</b> <code>/price btc</code> or <code>/crypto eth</code>",
                parse_mode=ParseMode.HTML,
            )
        return
    currency = ctx.args[0]
    await send_crypto_rate(update, ctx, currency)


async def handle_crypto_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Dynamic ticker handler for commands like /btc, /eth, /sol."""
    if not update.message or not update.message.text:
        return

    command = update.message.text.split()[0].lower()
    if "@" in command:
        command = command.split("@")[0]
    if not command.startswith("/"):
        return

    currency = command[1:]

    STANDARD_COMMANDS = {
        "start", "help", "pay", "admin", "device", "ping", "searchuser",
        "searchupi", "resetstats", "wipeuser", "ban", "unban", "dm",
        "restart", "setupi", "setup", "cancel", "crypto", "price", "calc",
        "calculate", "c", "stats", "profile", "settings", "qr", "menu",
        "broadcast", "export", "logs", "calculator", "support",
    }
    if currency in STANDARD_COMMANDS:
        return

    # Strictly match valid 2 to 10 letter currency tickers (e.g. btc, eth, sol, pepe)
    if not re.match(r"^[a-zA-Z]{2,10}$", currency):
        return

    if not await enforce_sub(update, ctx):
        return

    await send_crypto_rate(update, ctx, currency)


# ─── High-Performance Safe Math Calculator ───

MAX_MATH_EXPR_LEN = 100
MAX_MATH_EXPONENT = 500
MAX_MATH_BASE = 1e12

SAFE_MATH_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

SAFE_MATH_FUNCS = {
    "sqrt": math.sqrt,
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "pow": pow,
}

MATH_DATE_REGEX = re.compile(
    r"^\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\s*$"
)
MATH_PHONE_REGEX = re.compile(r"^\s*\+?\d{1,4}[- ]?\d{3,5}[- ]?\d{4,6}\s*$")
MATH_ALLOWED_CHARS = re.compile(r"^[0-9\s\+\-\*\/\(\)\.\,\%\^\×\÷xX\=]+$")
MATH_HAS_OP = re.compile(
    r"[\+\*\/\×\÷\^%]|(?<=\d)\s*-\s*(?=\d)|(?<=\))\s*-\s*|(?<=\d)\s*[xX]\s*(?=\d)"
)
MATH_PERCENT_ARITH_REGEX = re.compile(
    r"(\((?:[^()]|\([^()]*\))*\)|\d+(?:\.\d+)?)\s*([\+\-])\s*(\d+(?:\.\d+)?)%"
)
MATH_PERCENT_SINGLE_REGEX = re.compile(r"(\d+(?:\.\d+)?)%")
MATH_NORM_X_REGEX = re.compile(r"(?<=\d|\))\s*[xX]\s*(?=[(\d])")
MATH_NORM_COMMA_REGEX = re.compile(r"(?<=\d),(?=\d)")


def _safe_eval_ast(node):
    """Recursively evaluates AST node ensuring strictly whitelisted operators."""
    if isinstance(node, ast.Expression):
        return _safe_eval_ast(node.body)
    elif isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError("Invalid constant type")
    elif isinstance(node, ast.Call):
        if isinstance(node.func, ast.Name):
            fname = node.func.id.lower()
            if fname in SAFE_MATH_FUNCS:
                args = [_safe_eval_ast(arg) for arg in node.args]
                if fname == "sqrt" and args and args[0] < 0:
                    raise ValueError("Cannot calculate square root of negative number")
                return SAFE_MATH_FUNCS[fname](*args)
        raise ValueError("Unsupported function call")
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type in SAFE_MATH_OPERATORS:
            return SAFE_MATH_OPERATORS[op_type](_safe_eval_ast(node.operand))
        raise ValueError("Unsupported unary operator")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type in SAFE_MATH_OPERATORS:
            left = _safe_eval_ast(node.left)
            right = _safe_eval_ast(node.right)
            if op_type is ast.Pow:
                if abs(right) > MAX_MATH_EXPONENT or abs(left) > MAX_MATH_BASE:
                    raise ValueError("Exponent or base exceeds safe bounds")
            if op_type in (ast.Div, ast.FloorDiv, ast.Mod):
                if right == 0:
                    raise ZeroDivisionError("Division by zero")
            res = SAFE_MATH_OPERATORS[op_type](left, right)
            if isinstance(res, (int, float)):
                if isinstance(res, float) and (math.isinf(res) or math.isnan(res)):
                    raise ValueError("Result overflowed floating-point bounds")
                return res
            raise ValueError("Invalid arithmetic result")
        raise ValueError("Unsupported binary operator")
    raise ValueError(f"Unsupported syntax: {type(node).__name__}")


def evaluate_math_expression(raw_expr: str) -> tuple[str | None, str | None]:
    """Safely parse and evaluate mathematical expression, returning (formatted_result, error_str)."""
    raw = raw_expr.strip().rstrip("=").lstrip("=").strip()
    if not (1 <= len(raw) <= MAX_MATH_EXPR_LEN):
        return None, "Expression length out of bounds"

    if MATH_DATE_REGEX.match(raw) or MATH_PHONE_REGEX.match(raw):
        return None, "Input appears to be a date or phone number"

    norm = raw.replace("×", "*").replace("÷", "/").replace("^", "**")
    norm = MATH_NORM_X_REGEX.sub(" * ", norm)
    norm = MATH_NORM_COMMA_REGEX.sub("", norm)

    # Handle percentage arithmetic: A + B% or A - B% -> (A +/- (A * B / 100))
    loop_count = 0
    while loop_count < 10:
        m = MATH_PERCENT_ARITH_REGEX.search(norm)
        if not m:
            break
        a, op, b = m.groups()
        norm = norm[: m.start()] + f"({a} {op} ({a} * {b} / 100))" + norm[m.end() :]
        loop_count += 1

    # Handle isolated percentages e.g. 500 * 20% -> 500 * (20 / 100)
    norm = MATH_PERCENT_SINGLE_REGEX.sub(r"(\1 / 100)", norm)

    try:
        tree = ast.parse(norm, mode="eval")
        val = _safe_eval_ast(tree)
        if isinstance(val, (int, float)):
            val = round(val, 10)
            if isinstance(val, float) and val.is_integer():
                val = int(val)
            if isinstance(val, int):
                return str(val), None
            formatted = f"{val:.8f}".rstrip("0").rstrip(".")
            return formatted, None
        return None, "Invalid result"
    except ZeroDivisionError:
        return None, "Error: Division by zero"
    except (ValueError, OverflowError, SyntaxError) as e:
        return None, str(e)
    except Exception:
        return None, "Calculation error"


_MATH_CHARS_SET = set("0123456789 +-/*()^%.,xX×÷=")


def is_math_query(text: str) -> bool:
    """Ultra-fast detection (< 3 microseconds) whether an incoming message is a pure mathematical calculation."""
    if not text:
        return False
    t_len = len(text)
    if t_len < 3 or t_len > MAX_MATH_EXPR_LEN:
        return False
    if text[0] in ("/", "@", "#", "!", "$", "~", "`"):
        return False
    if not _MATH_CHARS_SET.issuperset(text):
        return False
    cleaned = text.strip().rstrip("=").lstrip("=").strip()
    if len(cleaned) < 3:
        return False
    if not any(
        op in cleaned
        for op in ("+", "*", "/", "×", "÷", "^", "%", "x", "X", "-")
    ):
        return False
    if MATH_DATE_REGEX.match(cleaned) or MATH_PHONE_REGEX.match(cleaned):
        return False
    numbers = re.findall(r"\d+(?:\.\d+)?", cleaned)
    return len(numbers) >= 2


async def handle_text_calculator(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Auto-detect math expressions in chat messages and reply with expression = result."""
    if not update.effective_message or not update.effective_message.text:
        return

    text = update.effective_message.text
    if not bot_config.get("calculator_enabled", True):
        return

    if not is_math_query(text):
        return

    uid = update.effective_user.id if update.effective_user else None
    if uid and is_blacklisted(uid):
        return

    if update.effective_chat and update.effective_chat.type == "channel":
        return

    raw_display = text.strip().rstrip("=").strip()
    res, err = evaluate_math_expression(raw_display)
    if res is not None:
        try:
            await update.effective_message.reply_text(
                f"{raw_display} = {res}", quote=True
            )
        except Exception as e:
            logger.debug(f"Calculator reply error: {e}")
    elif err == "Error: Division by zero":
        try:
            await update.effective_message.reply_text(
                f"{raw_display} = Error: Division by zero", quote=True
            )
        except Exception as e:
            logger.debug(f"Calculator reply error: {e}")


async def calc_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Explicit /calc, /calculate, or /c command handler."""
    if not update.effective_message:
        return
    uid = update.effective_user.id if update.effective_user else None
    if uid and is_blacklisted(uid):
        return
    if not await enforce_sub(update, ctx):
        return

    raw_text = update.effective_message.text or ""
    parts = raw_text.split(None, 1)
    if len(parts) < 2 or not parts[1].strip():
        help_text = (
            "🔢 <b>Calculator</b>\n"
            "───────────────────\n"
            "Send any math expression directly in chat or use <code>/calc &lt;expr&gt;</code>\n\n"
            "<b>Examples:</b>\n"
            "• <code>300+340+85</code>\n"
            "• <code>380+330</code>\n"
            "• <code>50 * 20</code> (or <code>50 x 20</code>)\n"
            "• <code>1000 + 18%</code>\n"
            "• <code>500 - 10%</code>\n"
            "• <code>(25 + 75) / 4</code>\n"
            "• <code>2^10</code>\n"
            "• <code>sqrt(144) + 10</code>"
        )
        await update.effective_message.reply_text(help_text, parse_mode=ParseMode.HTML)
        return

    expr = parts[1].strip()
    raw_display = expr.rstrip("=").strip()
    res, err = evaluate_math_expression(raw_display)
    if res is not None:
        await update.effective_message.reply_text(f"{raw_display} = {res}")
    elif err == "Error: Division by zero":
        await update.effective_message.reply_text(
            f"{raw_display} = Error: Division by zero"
        )
    else:
        await update.effective_message.reply_text(
            f"❌ <b>Calculation error:</b> {html.escape(str(err))}\n"
            "<i>Example: <code>/calc 300+340+85</code></i>",
            parse_mode=ParseMode.HTML,
        )


# ─── Dashboard & User Interface ───


def get_dashboard_kb(uid_str):
    kb = []
    if uid_str in user_data:
        kb.append(
            [
                InlineKeyboardButton("⬡ New QR", callback_data="cb_gen_prompt"),
                InlineKeyboardButton("⚡ Instant", callback_data="cb_quick_qr"),
            ]
        )
        kb.append(
            [
                InlineKeyboardButton("◉ Profile", callback_data="cb_profile"),
                InlineKeyboardButton("↗ Share", callback_data="cb_share_profile"),
            ]
        )
        kb.append(
            [
                InlineKeyboardButton("▤ Stats", callback_data="cb_user_stats"),
                InlineKeyboardButton("⚙ Settings", callback_data="cb_user_manage"),
            ]
        )
    else:
        kb.append(
            [
                InlineKeyboardButton(
                    "→ Connect UPI to Begin", callback_data="cb_setup_start"
                )
            ]
        )

    kb.append([InlineKeyboardButton("? Help", callback_data="cb_help")])

    if is_admin(uid_str):
        kb.append(
            [InlineKeyboardButton("⊞ Admin", callback_data="cb_admin_panel")]
        )

    return InlineKeyboardMarkup(kb)


async def dashboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await enforce_sub(update, ctx):
        return ConversationHandler.END

    uid_str = str(update.effective_user.id)
    if bot_config.get("maintenance") and not is_admin(uid_str):
        maint_text = "◈ <b>SYSTEM OFFLINE</b>\n\n<i>We're performing scheduled upgrades.\nBack online shortly.</i>"
        if update.callback_query:
            try:
                await update.callback_query.answer(
                    "Bot is under maintenance.", show_alert=True
                )
            except Exception:
                pass
        elif update.effective_message:
            await update.effective_message.reply_text(
                maint_text, parse_mode=ParseMode.HTML
            )
        return ConversationHandler.END

    # Handle deep links
    if (
        ctx.args
        and ctx.args[0] == "setup"
        and update.effective_chat
        and update.effective_chat.type == "private"
    ):
        return await setup_start(update, ctx)

    first_name = html.escape(str(update.effective_user.first_name or "Friend"))
    escaped_bot_name = html.escape(BOT_NAME)
    text = (
        f"{ce('crown', '👑')} <b>{first_name}</b>, welcome back.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{ce('diamond', '💎')} <b>{escaped_bot_name} PREMIUM</b>\n"
        f"<i>{ce('sparkle', '✨')} Instant UPI QR · {ce('shield', '🛡️')} Secure · {ce('gem', '💠')} Private</i>\n\n"
        f"Select an action below ↓"
    )

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        if update.callback_query.message:
            await update.callback_query.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=get_dashboard_kb(uid_str),
            )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_dashboard_kb(uid_str),
        )

    return ConversationHandler.END


async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Render help and commands information card."""
    if not await enforce_sub(update, ctx):
        return
    support_txt = (
        f"\n\nSupport: {html.escape(SUPPORT_USERNAME)}"
        if SUPPORT_USERNAME
        else ""
    )
    text = (
        f"▸ <b>HELP & COMMANDS</b>\n"
        "───────────────────\n\n"
        "<b>Commands:</b>\n"
        "  <code>/pay 299</code> → create QR\n"
        "  <code>/pay 500 Lunch</code> → with memo\n"
        "  <code>/price btc</code> → real-time crypto rate\n"
        "  <code>/calc 300+340+85</code> → instant calculator\n"
        "  <code>/start</code> → dashboard\n"
        "  <code>/help</code> → this help menu\n\n"
        "<b>Tips:</b>\n"
        "  • <b>Calculator:</b> Send <code>300+340+85</code> directly in chat!\n"
        "  • Use <b>⚡ Instant</b> for preset amounts\n"
        "  • Set a <b>default note</b> in Settings\n"
        "  • <b>↗ Share</b> to send payment links"
        f"{support_txt}"
    )
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Dashboard", callback_data="cb_dashboard")]]
    )
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        if update.callback_query.message:
            await update.callback_query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )


# ─── Interactive Setup (Conversation) ───


async def setup_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await enforce_sub(update, ctx):
        return ConversationHandler.END

    if update.effective_chat and update.effective_chat.type != "private":
        if update.effective_message:
            await update.effective_message.reply_text(
                "🔒 Please link your UPI ID in private chat with the bot for your privacy.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔗 Link in DM",
                                url=f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=setup",
                            )
                        ]
                    ]
                ),
            )
        return ConversationHandler.END

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    text = (
        "▸ <b>LINK YOUR UPI</b>\n"
        "───────────────────\n\n"
        "Send your UPI address below\n"
        "Format: <code>name@bank</code>\n"
    )
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        if update.callback_query.message:
            await update.callback_query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    return WAITING_UPI


async def setup_receive_upi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return WAITING_UPI
    upi_id = update.message.text.strip()
    if not re.match(r"^[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+$", upi_id):
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
        )
        await update.message.reply_text(
            "✕ <b>Invalid format</b>\n\nExpected: <code>name@bank</code>\nTry again ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return WAITING_UPI

    ctx.user_data["temp_upi"] = upi_id
    kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("» Skip", callback_data="cb_skip_name")],
            [InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")],
        ]
    )
    await update.message.reply_text(
        f"✓ <b>UPI linked</b>\n\n"
        f"  <code>{html.escape(upi_id)}</code>\n\n"
        "Now send your <b>display name</b>\n"
        "<i>or skip to finish</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_NAME


async def setup_receive_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = (update.message.text.strip() if update.message and update.message.text else "")[:40]
    return await finalize_setup(update, ctx, name)


async def setup_skip_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
    return await finalize_setup(update, ctx, "")


async def finalize_setup(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE, name: str
):
    uid_str = str(update.effective_user.id)
    upi_id = ctx.user_data.get("temp_upi", "")
    existing = user_data.get(uid_str, {})

    user_data[uid_str] = {
        "upi": upi_id,
        "name": name,
        "default_note": existing.get("default_note", ""),
        "qr_generated": existing.get("qr_generated", 0),
        "joined_at": existing.get("joined_at", datetime.now().isoformat()),
    }
    save_db()

    text = (
        "✓ <b>SETUP COMPLETE</b>\n"
        "───────────────────\n\n"
        f"  UPI: <code>{html.escape(upi_id)}</code>\n"
        f"  Name: <code>{html.escape(name or 'Not set')}</code>\n\n"
        "Use <code>/pay amount</code> to create QR codes"
    )
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Dashboard", callback_data="cb_dashboard")]]
    )

    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    return ConversationHandler.END


async def user_edit_name_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
        )
        if query.message:
            await query.message.edit_text(
                "▸ <b>EDIT NAME</b>\n───────────────────\n\nSend your new display name ↓",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
    return WAITING_EDIT_NAME


async def user_edit_name_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return WAITING_EDIT_NAME
    name = update.message.text.strip()[:40]
    uid_str = str(update.effective_user.id)
    if uid_str in user_data:
        user_data[uid_str]["name"] = name
        save_db()

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Dashboard", callback_data="cb_dashboard")]]
    )
    await update.message.reply_text(
        f"✓ <b>Name updated</b>\n\n  → <code>{html.escape(name)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cancel_conversation(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid_str = str(update.effective_user.id)
    is_adm = is_admin(uid_str)

    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        if is_adm and ctx.user_data.get("in_admin_conv"):
            ctx.user_data.pop("in_admin_conv", None)
            await render_admin_config(update.callback_query)
            return ConversationHandler.END
        await dashboard(update, ctx)
    else:
        if update.effective_message:
            await update.effective_message.reply_text("✕ Cancelled.")
        await dashboard(update, ctx)
    return ConversationHandler.END


# ─── QR Generation ───


async def gen_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await enforce_sub(update, ctx):
        return

    uid = update.effective_user.id
    uid_str = str(uid)

    if bot_config.get("maintenance") and not is_admin(uid_str):
        if update.effective_message:
            await update.effective_message.reply_text(
                "🚧 <b>Maintenance Mode Active</b>", parse_mode=ParseMode.HTML
            )
        return

    data = user_data.get(uid_str)
    if not data:
        if update.effective_chat and update.effective_chat.type != "private":
            kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔗 Link UPI in DM",
                            url=f"https://t.me/{BOT_USERNAME.lstrip('@')}?start=setup",
                        )
                    ]
                ]
            )
        else:
            kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔗 Link UPI", callback_data="cb_setup_start"
                        )
                    ]
                ]
            )
        if update.effective_message:
            await update.effective_message.reply_text(
                "❌ No UPI ID linked!\n\nPlease configure your profile first.",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
        return

    if not ctx.args:
        if update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ <b>Usage:</b> <code>/pay amount [note]</code>\nExample: <code>/pay 299</code>",
                parse_mode=ParseMode.HTML,
            )
        return

    try:
        raw_amt = float(ctx.args[0])
        if math.isnan(raw_amt) or math.isinf(raw_amt) or raw_amt <= 0 or raw_amt > 99999:
            raise ValueError
        amount = round(raw_amt, 2)
    except ValueError:
        if update.effective_message:
            await update.effective_message.reply_text(
                "❌ Invalid amount. Must be a valid number between ₹1 and ₹99,999.",
                parse_mode=ParseMode.HTML,
            )
        return

    raw_note = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else data.get("default_note", "")
    note = re.sub(r"[\r\n\t]+", " ", str(raw_note)).strip()[:50]
    upi_id = data["upi"]
    name = data.get("name", "")
    bot_username = BOT_USERNAME

    try:
        if update.effective_chat:
            asyncio.create_task(
                ctx.bot.send_chat_action(
                    chat_id=update.effective_chat.id,
                    action=ChatAction.UPLOAD_PHOTO,
                )
            )
        pfp_path = await get_user_pfp(ctx.bot, update.effective_user)
        img_bio = await asyncio.to_thread(
            generate_qr, upi_id, amount, name, note, bot_username, pfp_path
        )
        caption = fmt_card(
            upi_id, amount, name or update.effective_user.first_name, bot_username
        )

        data["qr_generated"] = data.get("qr_generated", 0) + 1
        bot_config["total_generated"] = (
            bot_config.get("total_generated", 0) + 1
        )
        save_db()

        # Channel logger
        if LOG_CHANNEL_ID:
            asyncio.create_task(
                log_qr_generation(
                    ctx.bot, update.effective_user, uid_str, amount, upi_id
                )
            )

        kb_rows = []
        btn_row = []
        try:
            from telegram import CopyTextButton
            btn_row.append(
                InlineKeyboardButton(
                    "📋 Copy UPI", copy_text=CopyTextButton(text=upi_id)
                )
            )
        except Exception:
            pass
        btn_row.append(
            InlineKeyboardButton(
                "⊗ Remove", callback_data=f"cb_delete_msg:{uid_str}"
            )
        )
        kb_rows.append(btn_row)
        kb = InlineKeyboardMarkup(kb_rows)

        for attempt in range(2):
            try:
                await update.message.reply_photo(
                    photo=img_bio,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=kb,
                    reply_to_message_id=update.message.message_id,
                )
                break
            except Exception as send_err:
                if attempt == 0 and "timed out" in str(send_err).lower():
                    img_bio.seek(0)
                    await asyncio.sleep(1)
                    continue
                raise
    except Exception as e:
        logger.error(f"QR Error: {e}", exc_info=True)
        if update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ <b>Failed to generate QR. Please try again.</b>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass


# ─── Admin Helpers ───


async def render_admin_users(query):
    kb = [
        [
            InlineKeyboardButton("Top 10", callback_data="cb_admin_top_users"),
            InlineKeyboardButton(
                "Search ID", callback_data="cb_admin_search_user_start"
            ),
        ],
        [
            InlineKeyboardButton(
                "Search UPI", callback_data="cb_admin_search_upi_start"
            ),
            InlineKeyboardButton(
                "Wipe", callback_data="cb_admin_wipe_user_start"
            ),
        ],
        [
            InlineKeyboardButton(
                "Reset Stats", callback_data="cb_admin_reset_stats_start"
            ),
            InlineKeyboardButton(
                "Purge", callback_data="cb_admin_purge_inactive"
            ),
        ],
        [
            InlineKeyboardButton("CSV", callback_data="cb_admin_export_csv"),
            InlineKeyboardButton("Backup", callback_data="cb_admin_backup"),
        ],
        [InlineKeyboardButton("← Back", callback_data="cb_admin_panel")],
    ]
    await query.message.edit_text(
        "▸ <b>USER OPS</b>\n───────────────────\n\nSelect a tool ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def render_admin_system(query):
    m_status = (
        "🟢 Online" if not bot_config.get("maintenance") else "🔴 Maintenance"
    )
    uptime_sec = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    kb = [
        [
            InlineKeyboardButton(
                f"Toggle Maint. ({m_status})",
                callback_data="cb_admin_toggle_m",
            )
        ],
        [
            InlineKeyboardButton("Health", callback_data="cb_admin_health"),
            InlineKeyboardButton("Reboot", callback_data="cb_admin_reboot"),
        ],
        [
            InlineKeyboardButton(
                "📄 Get Logs", callback_data="cb_admin_get_logs"
            )
        ],
        [InlineKeyboardButton("← Back", callback_data="cb_admin_panel")],
    ]
    await query.message.edit_text(
        f"▸ <b>SYSTEM</b>\n───────────────────\n\n"
        f"Uptime: <code>{uptime_str}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(kb),
    )


async def render_admin_config(query):
    text = (
        "▸ <b>CONFIG</b>\n"
        "───────────────────\n\n"
        f"  Bot Name  →  <code>{html.escape(BOT_NAME)}</code>\n"
        f"  Username  →  <code>{html.escape(BOT_USERNAME)}</code>\n"
        f"  Support  →  <code>{html.escape(SUPPORT_USERNAME or 'Not set')}</code>\n"
        f"  Log Ch.  →  <code>{html.escape(LOG_CHANNEL_ID or 'Not set')}</code>\n"
        f"  Force Sub  →  <code>{html.escape(FORCE_SUB_CHANNEL or 'Not set')}</code>\n"
        f"  Rate Limit  →  <code>{bot_config.get('rate_limit_seconds', 0.5)}s</code>\n"
        f"  Delay  →  <code>{bot_config.get('artificial_delay_seconds', 0.0)}s</code>"
    )
    kb = [
        [
            InlineKeyboardButton("Bot Name", callback_data="cb_cfg_botname"),
            InlineKeyboardButton("Username", callback_data="cb_cfg_botuser"),
        ],
        [
            InlineKeyboardButton("Support", callback_data="cb_cfg_support"),
            InlineKeyboardButton("Log Ch.", callback_data="cb_cfg_logch"),
        ],
        [
            InlineKeyboardButton("Force Sub", callback_data="cb_cfg_forcesub"),
        ],
        [
            InlineKeyboardButton(
                "Rate Limit", callback_data="cb_cfg_ratelimit"
            ),
            InlineKeyboardButton("Delay", callback_data="cb_cfg_delay"),
        ],
        [InlineKeyboardButton("← Back", callback_data="cb_admin_panel")],
    ]
    await query.message.edit_text(
        text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb)
    )


def get_health_text():
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            lines = f.readlines()
            os_name = next(
                (
                    line.split("=")[1].strip().strip('"')
                    for line in lines
                    if line.startswith("PRETTY_NAME=")
                ),
                platform.system(),
            )
    except Exception:
        os_name = f"{platform.system()} {platform.release()}"

    py_ver = f"v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    uptime_sec = int(time.time() - psutil.boot_time())
    days, remainder = divmod(uptime_sec, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    uptime_str = f"{days}d {hours}h {minutes}m"

    def make_bar(percent, length=10):
        filled = int(round(length * percent / 100))
        return "█" * filled + "░" * (length - filled)

    def get_color(percent):
        if percent < 60:
            return "🟢"
        elif percent < 85:
            return "🟡"
        else:
            return "🔴"

    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_cores = psutil.cpu_count(logical=True)
    cpu_bar = (
        f"{get_color(cpu_percent)} [{make_bar(cpu_percent)}] {cpu_percent}%"
    )

    ram = psutil.virtual_memory()
    ram_gb = ram.total / (1024**3)
    ram_used_gb = (ram.total - ram.available) / (1024**3)
    ram_percent = ram.percent
    ram_used_str = (
        f"{ram_used_gb * 1024:.1f}MB"
        if ram_used_gb < 1
        else f"{ram_used_gb:.1f}GB"
    )
    ram_bar = (
        f"{get_color(ram_percent)} [{make_bar(ram_percent)}] {ram_percent}%"
    )

    swap = psutil.swap_memory()
    swap_gb = swap.total / (1024**3)
    swap_used_gb = swap.used / (1024**3)
    swap_percent = swap.percent
    swap_used_str = (
        f"{swap_used_gb * 1024:.1f}MB"
        if swap_used_gb < 1
        else f"{swap_used_gb:.1f}GB"
    )
    swap_bar = (
        f"{get_color(swap_percent)} [{make_bar(swap_percent)}] {swap_percent}%"
    )

    disk = psutil.disk_usage("/")
    disk_total = disk.total / (1024**3)
    disk_used = disk.used / (1024**3)
    disk_free = disk.free / (1024**3)
    disk_percent = disk.percent

    app_dir = os.path.dirname(os.path.abspath(__file__))
    total_size = 0
    file_count = 0
    for dirpath, _, filenames in os.walk(app_dir):
        if (
            "__pycache__" in dirpath
            or ".git" in dirpath
            or "venv" in dirpath
            or "cache" in dirpath
        ):
            continue
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except Exception:
                    pass

    size_str = (
        f"{total_size / 1024:.1f}KB"
        if total_size < 1024**2
        else f"{total_size / (1024**2):.1f}MB"
    )

    db_size = os.path.getsize(DATA_FILE) if os.path.exists(DATA_FILE) else 0
    db_size_str = (
        f"{db_size / 1024:.1f}KB"
        if db_size < 1024**2
        else f"{db_size / (1024**2):.1f}MB"
    )

    active_sessions = len(
        [u for u in user_data.values() if u.get("qr_generated", 0) > 0]
    )

    return (
        f"{ce('server', '🖥️')} <b>VPS STATUS DASHBOARD</b>\n"
        "────────────────────\n"
        f"{ce('gear', '⚙️')} <b>SYSTEM INFO</b>\n"
        f"• <b>OS:</b> <code>{os_name}</code>\n"
        f"• <b>Python:</b> <code>{py_ver}</code>\n"
        f"• <b>Uptime:</b> <code>{uptime_str}</code>\n\n"
        f"{ce('zap', '⚡')} <b>PERFORMANCE</b>\n"
        f"• <b>CPU:</b> {cpu_bar}\n"
        f"  <i>({cpu_cores} Cores)</i>\n"
        f"• <b>RAM:</b> {ram_bar}\n"
        f"  <i>({ram_used_str} / {ram_gb:.1f}GB)</i>\n"
        f"• <b>Swap:</b> {swap_bar}\n"
        f"  <i>({swap_used_str} / {swap_gb:.1f}GB)</i>\n\n"
        f"{ce('storage', '💾')} <b>STORAGE (VPS)</b>\n"
        f"• <b>Total:</b> <code>{disk_total:.1f}GB</code>\n"
        f"• <b>Used:</b> {get_color(disk_percent)} <code>{disk_used:.1f}GB ({disk_percent}%)</code>\n"
        f"• <b>Free:</b> <code>{disk_free:.1f}GB</code>\n\n"
        f"{ce('bot', '🤖')} <b>BOT APP USAGE</b>\n"
        f"• <b>Total Size:</b> <code>{size_str}</code> <i>({file_count} files)</i>\n"
        f"• <b>Database:</b> <code>{db_size_str}</code>\n"
        f"• <b>Sessions:</b> <code>{active_sessions} Active</code>\n"
        "────────────────────"
    )


async def render_admin_health(query):
    text = get_health_text()
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Back", callback_data="cb_admin_system")]]
    )
    try:
        await query.answer()
    except Exception:
        pass
    if query.message:
        await query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )


# ─── Callback Handlers ───


async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    uid_str = str(update.effective_user.id)

    if data == "cb_dashboard":
        await dashboard(update, ctx)

    elif data == "cb_profile":
        u = user_data.get(uid_str)
        if not u:
            await query.answer("❌ Profile not found.", show_alert=True)
            return
        joined = u.get("joined_at", "Unknown")[:10]
        text = (
            "▸ <b>YOUR PROFILE</b>\n"
            "───────────────────\n\n"
            f"  UPI  →  <code>{html.escape(u['upi'])}</code>\n"
            f"  Name  →  <code>{html.escape(u.get('name') or 'Not set')}</code>\n"
            f"  QRs  →  <code>{u.get('qr_generated', 0)}</code>\n"
            f"  Since  →  <code>{html.escape(joined)}</code>"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_dashboard")]]
        )
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )

    elif data == "cb_user_manage":
        if uid_str not in user_data:
            await query.answer("Profile not linked yet.", show_alert=True)
            return
        u = user_data[uid_str]
        default_note = u.get("default_note", "Not set")
        kb = [
            [
                InlineKeyboardButton(
                    "✎ Name", callback_data="cb_user_edit_name"
                ),
                InlineKeyboardButton(
                    "⇄ UPI", callback_data="cb_user_edit_upi"
                ),
            ],
            [
                InlineKeyboardButton(
                    f"≡ Note: {html.escape(default_note[:15])}",
                    callback_data="cb_user_set_note",
                )
            ],
            [
                InlineKeyboardButton(
                    "⊗ Delete Account", callback_data="cb_delupi_confirm"
                )
            ],
            [InlineKeyboardButton("← Back", callback_data="cb_dashboard")],
        ]
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                "▸ <b>SETTINGS</b>\n"
                "───────────────────\n\n"
                "Modify your account below ↓",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb),
            )

    elif data == "cb_delupi_confirm":
        try:
            await query.answer()
        except Exception:
            pass
        kb = [
            [
                InlineKeyboardButton(
                    "⚠️ Yes, Delete My Account",
                    callback_data="cb_delupi_execute",
                )
            ],
            [InlineKeyboardButton("✕ Cancel", callback_data="cb_user_manage")],
        ]
        if query.message:
            await query.message.edit_text(
                "⚠️ <b>WARNING: DELETE ACCOUNT</b>\n"
                "───────────────────\n\n"
                "Are you sure you want to delete your UPI profile?\n"
                "You will need to link it again to generate new QRs.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb),
            )

    elif data == "cb_delupi_execute":
        if uid_str in user_data:
            del user_data[uid_str]
            save_db()
            # Clean up cached avatar files
            pfp_f = os.path.join(CACHE_DIR, f"pfp_{uid_str}.jpg")
            av_f = os.path.join(CACHE_DIR, f"avatar_{uid_str}.png")
            for f in (pfp_f, av_f):
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass
            await query.answer("Account deleted permanently.", show_alert=True)
        else:
            await query.answer("No profile found.", show_alert=True)
        await dashboard(update, ctx)

    elif data == "cb_gen_prompt":
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.reply_text(
                "▸ <b>CREATE QR</b>\n"
                "───────────────────\n\n"
                "Type in chat:\n\n"
                "  <code>/pay 500</code>\n"
                "  <code>/pay 299 Lunch</code>\n\n"
                "<i>Or tap Instant for presets</i>",
                parse_mode=ParseMode.HTML,
            )

    elif data == "cb_help":
        await help_command(update, ctx)

    elif data == "cb_quick_qr":
        if not await enforce_sub(update, ctx):
            return
        if uid_str not in user_data:
            await query.answer("❌ Setup your UPI first!", show_alert=True)
            return
        kb = [
            [
                InlineKeyboardButton("₹50", callback_data="cb_qr_50"),
                InlineKeyboardButton("₹100", callback_data="cb_qr_100"),
                InlineKeyboardButton("₹200", callback_data="cb_qr_200"),
            ],
            [
                InlineKeyboardButton("₹500", callback_data="cb_qr_500"),
                InlineKeyboardButton("₹1K", callback_data="cb_qr_1000"),
                InlineKeyboardButton("₹2K", callback_data="cb_qr_2000"),
            ],
            [
                InlineKeyboardButton("₹5K", callback_data="cb_qr_5000"),
                InlineKeyboardButton("₹10K", callback_data="cb_qr_10000"),
            ],
            [InlineKeyboardButton("← Back", callback_data="cb_dashboard")],
        ]
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                "⚡ <b>INSTANT QR</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "💎 Pick an amount ↓",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb),
            )

    elif data.startswith("cb_qr_"):
        if not await enforce_sub(update, ctx):
            return
        if uid_str not in user_data:
            await query.answer("Please link your UPI profile first.", show_alert=True)
            return
        try:
            amount = float(data.split("_")[2])
        except (IndexError, ValueError):
            return

        u = user_data[uid_str]
        upi_id = u["upi"]
        name = u.get("name", "")
        note = u.get("default_note", "")
        bot_username = BOT_USERNAME

        try:
            await query.answer("Generating...")
        except Exception:
            pass

        try:
            pfp_path = await get_user_pfp(ctx.bot, update.effective_user)
            img_bio = await asyncio.to_thread(
                generate_qr, upi_id, amount, name, note, bot_username, pfp_path
            )
            caption = fmt_card(
                upi_id, amount, name or update.effective_user.first_name, bot_username
            )
            u["qr_generated"] = u.get("qr_generated", 0) + 1
            bot_config["total_generated"] = (
                bot_config.get("total_generated", 0) + 1
            )
            save_db()

            if LOG_CHANNEL_ID:
                asyncio.create_task(
                    log_qr_generation(
                        ctx.bot, update.effective_user, uid_str, amount, upi_id
                    )
                )

            del_rows = []
            qr_btn_row = []
            try:
                from telegram import CopyTextButton
                qr_btn_row.append(
                    InlineKeyboardButton(
                        "📋 Copy UPI", copy_text=CopyTextButton(text=upi_id)
                    )
                )
            except Exception:
                pass
            qr_btn_row.append(
                InlineKeyboardButton(
                    "⊗ Remove",
                    callback_data=f"cb_delete_msg:{uid_str}",
                )
            )
            del_rows.append(qr_btn_row)
            del_kb = InlineKeyboardMarkup(del_rows)

            if query.message:
                await query.message.reply_photo(
                    photo=img_bio,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=del_kb,
                )
        except Exception as e:
            logger.error(f"Quick QR Error: {e}", exc_info=True)
            if query.message:
                try:
                    await query.message.reply_text(
                        "❌ <b>Failed to generate QR. Please try again.</b>",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass

    elif data == "cb_user_stats":
        u = user_data.get(uid_str)
        if not u:
            await query.answer("❌ Profile not found.", show_alert=True)
            return
        qr_count = u.get("qr_generated", 0)
        joined = u.get("joined_at", "Unknown")[:10]
        user_rank = (
            sum(
                1
                for u_entry in user_data.values()
                if u_entry.get("qr_generated", 0) > qr_count
            )
            + 1
        )
        escaped_note = html.escape(str(u.get("default_note") or "None"))
        text = (
            f"📊 <b>YOUR STATS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  👑 <b>Rank</b>  →  #{user_rank}/{len(user_data)}\n"
            f"  💎 <b>QRs</b>   →  {qr_count}\n"
            f"  Joined  →  {html.escape(joined)}\n"
            f"  Note  →  {escaped_note}"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_dashboard")]]
        )
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )

    elif data == "cb_share_profile":
        u = user_data.get(uid_str)
        if not u:
            return
        bot_un = BOT_USERNAME.lstrip("@")
        share_text = (
            f"Pay me via UPI\n\n"
            f"UPI: {u['upi']}\n"
            f"Name: {u.get('name', 'N/A')}\n\n"
            f"Generate QR: https://t.me/{bot_un}?start=pay"
        )
        text = (
            "📤 <b>SHARE PROFILE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "<i>✨ Forward or copy:</i>\n\n"
            f"<code>{html.escape(share_text)}</code>"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_dashboard")]]
        )
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )

    elif data == "cb_clear_note":
        if uid_str in user_data:
            user_data[uid_str].pop("default_note", None)
            save_db()
            await query.answer("Default note cleared!", show_alert=True)
        await dashboard(update, ctx)

    elif data.startswith("cb_delete_msg"):
        if ":" in data:
            owner_id = data.split(":")[1]
            if owner_id != uid_str and not is_admin(uid_str):
                await query.answer(
                    "Only the user who generated this QR can delete it.",
                    show_alert=True,
                )
                return
        else:
            if not is_admin(uid_str):
                await query.answer("Access denied.", show_alert=True)
                return

        try:
            await query.message.delete()
            await query.answer("Message deleted.")
        except Exception:
            await query.answer(
                "Cannot delete message (Too old or missing permissions).",
                show_alert=True,
            )

    # Admin Callbacks
    elif data == "cb_admin_panel":
        if not is_admin(uid_str):
            await query.answer("❌ Access Denied", show_alert=True)
            return

        kb = [
            [
                InlineKeyboardButton("👥 Users", callback_data="cb_admin_users"),
                InlineKeyboardButton("💻 System", callback_data="cb_admin_system"),
            ],
            [
                InlineKeyboardButton("📢 Broadcast", callback_data="cb_admin_comm"),
                InlineKeyboardButton("📈 Analytics", callback_data="cb_admin_stats"),
            ],
            [
                InlineKeyboardButton("🔐 Security", callback_data="cb_admin_security"),
                InlineKeyboardButton("⚙️ Config", callback_data="cb_admin_config"),
            ],
            [InlineKeyboardButton("← Exit", callback_data="cb_dashboard")],
        ]
        text = "👑 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSelect a module ↓"
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                text,
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb),
            )

    elif data == "cb_admin_users":
        if not is_admin(uid_str):
            return
        await render_admin_users(query)

    elif data == "cb_admin_system":
        if not is_admin(uid_str):
            return
        await render_admin_system(query)

    elif data == "cb_admin_health":
        if not is_admin(uid_str):
            return
        await render_admin_health(query)

    elif data == "cb_admin_reboot":
        if not is_admin(uid_str):
            return
        await query.answer("Rebooting system...")
        if query.message:
            await query.message.edit_text(
                "🔄 <b>System is rebooting...</b>\n\nPlease wait 5 seconds.",
                parse_mode=ParseMode.HTML,
            )
        atomic_save_json(DATA_FILE, dict(user_data))
        atomic_save_json(CONFIG_FILE, dict(bot_config))
        logger.info(f"Bot reboot triggered by admin {uid_str}")
        global _restart_requested
        _restart_requested = True
        asyncio.create_task(_graceful_restart(ctx.application))

    elif data == "cb_admin_get_logs":
        if not is_admin(uid_str):
            return
        if os.path.exists("bot.log"):
            await query.answer("Uploading logs...")
            with open("bot.log", "rb") as f:
                await ctx.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=f,
                    filename="bot.log",
                )
        else:
            await query.answer("Log file not found!", show_alert=True)

    elif data == "cb_admin_comm":
        if not is_admin(uid_str):
            return
        kb = [
            [
                InlineKeyboardButton(
                    "Broadcast", callback_data="cb_admin_broadcast_start"
                ),
                InlineKeyboardButton("DM", callback_data="cb_admin_dm_start"),
            ],
            [InlineKeyboardButton("← Back", callback_data="cb_admin_panel")],
        ]
        if query.message:
            await query.message.edit_text(
                "▸ <b>BROADCAST</b>\n───────────────────\n\nSelect a tool ↓",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb),
            )

    elif data == "cb_admin_top_users":
        if not is_admin(uid_str):
            return
        sorted_users = sorted(
            list(user_data.items()),
            key=lambda x: x[1].get("qr_generated", 0),
            reverse=True,
        )[:10]
        text = "▸ <b>TOP USERS</b>\n───────────────────\n\n"
        for i, (u_id, u_info) in enumerate(sorted_users, 1):
            text += f"  {i}. <code>{html.escape(u_id)}</code> → {u_info.get('qr_generated', 0)} QRs\n"
        if not sorted_users:
            text += "<i>No users yet.</i>\n"
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_admin_users")]]
        )
        if query.message:
            await query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )

    elif data == "cb_admin_search_user_start":
        if not is_admin(uid_str):
            return
        if query.message:
            await query.message.edit_text(
                "▸ <b>SEARCH USER</b>\n───────────────────\n\nType <code>/searchuser ID</code> in chat",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "← Back", callback_data="cb_admin_users"
                            )
                        ]
                    ]
                ),
            )

    elif data == "cb_admin_wipe_user_start":
        if not is_admin(uid_str):
            return
        if query.message:
            await query.message.edit_text(
                "▸ <b>WIPE USER</b>\n───────────────────\n\nType <code>/wipeuser ID</code> to delete",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "← Back", callback_data="cb_admin_users"
                            )
                        ]
                    ]
                ),
            )

    elif data == "cb_admin_ban_user_start":
        if not is_admin(uid_str):
            return
        if query.message:
            await query.message.edit_text(
                "▸ <b>BAN USER</b>\n───────────────────\n\nType <code>/ban ID</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "← Back", callback_data="cb_admin_security"
                            )
                        ]
                    ]
                ),
            )

    elif data == "cb_admin_unban_user_start":
        if not is_admin(uid_str):
            return
        if query.message:
            await query.message.edit_text(
                "▸ <b>UNBAN USER</b>\n───────────────────\n\nType <code>/unban ID</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "← Back", callback_data="cb_admin_security"
                            )
                        ]
                    ]
                ),
            )

    elif data == "cb_admin_dm_start":
        if not is_admin(uid_str):
            return
        if query.message:
            await query.message.edit_text(
                "▸ <b>SEND DM</b>\n───────────────────\n\nType <code>/dm ID message</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "← Back", callback_data="cb_admin_comm"
                            )
                        ]
                    ]
                ),
            )

    elif data == "cb_admin_stats":
        if not is_admin(uid_str):
            return
        total_users = len(user_data)
        total_gen = bot_config.get("total_generated", 0)
        avg_qr = round(total_gen / total_users, 1) if total_users > 0 else 0
        active_today = sum(
            1
            for u in user_data.values()
            if u.get("joined_at", "")[:10] == datetime.now().strftime("%Y-%m-%d")
        )
        uptime_sec = int(time.time() - BOT_START_TIME)
        hours, remainder = divmod(uptime_sec, 3600)
        minutes, _ = divmod(remainder, 60)
        text = (
            f"▸ <b>ANALYTICS</b>\n"
            "───────────────────\n\n"
            f"  Users  →  <code>{total_users}</code>\n"
            f"  Today  →  <code>{active_today}</code>\n"
            f"  QRs  →  <code>{total_gen}</code>\n"
            f"  Avg  →  <code>{avg_qr}</code>\n"
            f"  Banned  →  <code>{len(bot_config.get('blacklist', []))}</code>\n\n"
            "───────────────────\n"
            f"  Uptime  →  <code>{hours}h {minutes}m</code>\n"
            f"  Maint.  →  {'On' if bot_config.get('maintenance') else 'Off'}\n"
            f"  ForceSub  →  {'On' if FORCE_SUB_CHANNEL else 'Off'}\n"
            f"  Logging  →  {'On' if LOG_CHANNEL_ID else 'Off'}"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_admin_panel")]]
        )
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )

    elif data == "cb_admin_toggle_m":
        if not is_admin(uid_str):
            return
        bot_config["maintenance"] = not bot_config.get("maintenance", False)
        save_db()
        await query.answer("Maintenance mode toggled!", show_alert=True)
        await render_admin_system(query)

    elif data == "cb_admin_backup":
        if not is_admin(uid_str):
            return
        await query.answer("Sending backup...")
        atomic_save_json(DATA_FILE, dict(user_data))
        backup_name = f"users_backup_{datetime.now().strftime('%Y%m%d')}.json"
        with open(DATA_FILE, "rb") as f:
            await ctx.bot.send_document(
                chat_id=query.message.chat_id,
                document=f,
                filename=backup_name,
            )

    elif data == "cb_admin_export_csv":
        if not is_admin(uid_str):
            return
        await query.answer("Generating CSV...")

        def _sanitize_csv_cell(val) -> str:
            s = str(val).replace(",", " ").replace("\n", " ").replace("\r", " ").strip()
            if s and s[0] in ("=", "+", "-", "@", "\t"):
                return "'" + s
            return s

        csv_data = "user_id,upi,name,qr_generated,joined_at\n"
        for k, v in list(user_data.items()):
            upi = _sanitize_csv_cell(v.get("upi", ""))
            name = _sanitize_csv_cell(v.get("name", ""))
            qr_gen = v.get("qr_generated", 0)
            joined = _sanitize_csv_cell(v.get("joined_at", ""))
            csv_data += f"{k},{upi},{name},{qr_gen},{joined}\n"
        bio = BytesIO(csv_data.encode("utf-8"))
        bio.name = f"users_export_{datetime.now().strftime('%Y%m%d')}.csv"
        await ctx.bot.send_document(
            chat_id=query.message.chat_id, document=bio
        )

    elif data == "cb_admin_security":
        if not is_admin(uid_str):
            return
        kb = [
            [
                InlineKeyboardButton(
                    "Ban", callback_data="cb_admin_ban_user_start"
                ),
                InlineKeyboardButton(
                    "Unban", callback_data="cb_admin_unban_user_start"
                ),
            ],
            [
                InlineKeyboardButton(
                    "Banlist", callback_data="cb_admin_banlist"
                )
            ],
            [InlineKeyboardButton("← Back", callback_data="cb_admin_panel")],
        ]
        if query.message:
            await query.message.edit_text(
                "▸ <b>SECURITY</b>\n───────────────────\n\nManage access control ↓",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(kb),
            )

    elif data == "cb_admin_banlist":
        if not is_admin(uid_str):
            return
        bl = bot_config.get("blacklist", [])
        if bl:
            text = "▸ <b>BANLIST</b>\n───────────────────\n\n"
            for i, b_id in enumerate(bl, 1):
                text += f"  {i}. <code>{html.escape(str(b_id))}</code>\n"
            text += f"\n<i>Total: {len(bl)}</i>"
        else:
            text = "▸ <b>BANLIST</b>\n───────────────────\n\n<i>Empty</i>"
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "← Back", callback_data="cb_admin_security"
                    )
                ]
            ]
        )
        try:
            await query.answer()
        except Exception:
            pass
        if query.message:
            await query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )

    elif data == "cb_admin_purge_inactive":
        if not is_admin(uid_str):
            return
        inactive = [
            uid_k
            for uid_k, u in list(user_data.items())
            if u.get("qr_generated", 0) == 0
        ]
        if inactive:
            for uid_k in inactive:
                user_data.pop(uid_k, None)
            save_db()
            await query.answer(
                f"Purged {len(inactive)} inactive users!", show_alert=True
            )
        else:
            await query.answer("No inactive users found!", show_alert=True)
        await render_admin_users(query)

    elif data == "cb_admin_search_upi_start":
        if not is_admin(uid_str):
            return
        if query.message:
            await query.message.edit_text(
                "🔎 <b>Search by UPI ID</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "💬 Type <code>/searchupi upi@bank</code> to find user by UPI ID.",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🔙 User Ops", callback_data="cb_admin_users"
                            )
                        ]
                    ]
                ),
            )

    elif data == "cb_admin_reset_stats_start":
        if not is_admin(uid_str):
            return
        if query.message:
            await query.message.edit_text(
                "▸ <b>RESET STATS</b>\n───────────────────\n\nType <code>/resetstats ID</code>",
                parse_mode=ParseMode.HTML,
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "← Back", callback_data="cb_admin_users"
                            )
                        ]
                    ]
                ),
            )

    elif data == "cb_admin_config":
        if not is_admin(uid_str):
            return
        try:
            await query.answer()
        except Exception:
            pass
        await render_admin_config(query)

    else:
        try:
            await query.answer()
        except Exception:
            pass


# ─── Config Conversation Handlers (With Clean Termination) ───


async def cfg_botname_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        return ConversationHandler.END
    ctx.user_data["in_admin_conv"] = True
    try:
        await query.answer()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    if query.message:
        await query.message.edit_text(
            f"▸ <b>EDIT BOT NAME</b>\n───────────────────\n\nCurrent: <code>{html.escape(BOT_NAME)}</code>\n\nSend new name ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_CFG_BOT_NAME


async def cfg_botname_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global BOT_NAME
    if not update.message or not update.message.text:
        return WAITING_CFG_BOT_NAME
    BOT_NAME = update.message.text.strip()[:50]
    update_env("BOT_NAME", BOT_NAME)
    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Bot name → <code>{html.escape(BOT_NAME)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_botuser_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        return ConversationHandler.END
    ctx.user_data["in_admin_conv"] = True
    try:
        await query.answer()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    if query.message:
        await query.message.edit_text(
            f"▸ <b>EDIT USERNAME</b>\n───────────────────\n\nCurrent: <code>{html.escape(BOT_USERNAME)}</code>\n\nSend new @username ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_CFG_BOT_USERNAME


async def cfg_botuser_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global BOT_USERNAME
    if not update.message or not update.message.text:
        return WAITING_CFG_BOT_USERNAME
    val = update.message.text.strip()
    if not val.startswith("@"):
        val = "@" + val
    BOT_USERNAME = val[:35]
    update_env("BOT_USERNAME", BOT_USERNAME)
    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Username → <code>{html.escape(BOT_USERNAME)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_support_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        return ConversationHandler.END
    ctx.user_data["in_admin_conv"] = True
    try:
        await query.answer()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Clear", callback_data="cb_cfg_clear_support"
                )
            ],
            [InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")],
        ]
    )
    if query.message:
        await query.message.edit_text(
            f"▸ <b>EDIT SUPPORT</b>\n───────────────────\n\n"
            f"Current: <code>{html.escape(SUPPORT_USERNAME or 'Not set')}</code>\n\n"
            f"Send @username ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_CFG_SUPPORT


async def cfg_support_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global SUPPORT_USERNAME
    if not update.message or not update.message.text:
        return WAITING_CFG_SUPPORT
    SUPPORT_USERNAME = update.message.text.strip()[:35]
    update_env("SUPPORT_USERNAME", SUPPORT_USERNAME)
    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Support → <code>{html.escape(SUPPORT_USERNAME)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_clear_support(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global SUPPORT_USERNAME
    SUPPORT_USERNAME = ""
    update_env("SUPPORT_USERNAME", "")
    ctx.user_data.pop("in_admin_conv", None)
    if update.callback_query:
        await update.callback_query.answer("Support username cleared!", show_alert=True)
        await render_admin_config(update.callback_query)
    return ConversationHandler.END


async def cfg_logch_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        return ConversationHandler.END
    ctx.user_data["in_admin_conv"] = True
    try:
        await query.answer()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Clear", callback_data="cb_cfg_clear_logch"
                )
            ],
            [InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")],
        ]
    )
    if query.message:
        await query.message.edit_text(
            f"▸ <b>EDIT LOG CHANNEL</b>\n───────────────────\n\n"
            f"Current: <code>{html.escape(LOG_CHANNEL_ID or 'Not set')}</code>\n\n"
            f"Send channel ID or @channel ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_CFG_LOG_CHANNEL


async def cfg_logch_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global LOG_CHANNEL_ID
    if not update.message or not update.message.text:
        return WAITING_CFG_LOG_CHANNEL
    LOG_CHANNEL_ID = update.message.text.strip()[:40]
    update_env("LOG_CHANNEL_ID", LOG_CHANNEL_ID)
    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Log channel → <code>{html.escape(LOG_CHANNEL_ID)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_clear_logch(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = ""
    update_env("LOG_CHANNEL_ID", "")
    ctx.user_data.pop("in_admin_conv", None)
    if update.callback_query:
        await update.callback_query.answer("Log channel cleared!", show_alert=True)
        await render_admin_config(update.callback_query)
    return ConversationHandler.END


async def cfg_forcesub_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        return ConversationHandler.END
    ctx.user_data["in_admin_conv"] = True
    try:
        await query.answer()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Clear", callback_data="cb_cfg_clear_forcesub"
                )
            ],
            [InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")],
        ]
    )
    if query.message:
        await query.message.edit_text(
            f"▸ <b>EDIT FORCE SUB</b>\n───────────────────\n\n"
            f"Current: <code>{html.escape(FORCE_SUB_CHANNEL or 'Not set')}</code>\n\n"
            f"Send @channel ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_CFG_FORCE_SUB


async def cfg_forcesub_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global FORCE_SUB_CHANNEL
    if not update.message or not update.message.text:
        return WAITING_CFG_FORCE_SUB
    FORCE_SUB_CHANNEL = update.message.text.strip()[:40]
    update_env("FORCE_SUB_CHANNEL", FORCE_SUB_CHANNEL)
    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Force sub → <code>{html.escape(FORCE_SUB_CHANNEL)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_clear_forcesub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global FORCE_SUB_CHANNEL
    FORCE_SUB_CHANNEL = ""
    update_env("FORCE_SUB_CHANNEL", "")
    ctx.user_data.pop("in_admin_conv", None)
    if update.callback_query:
        await update.callback_query.answer("Force sub cleared!", show_alert=True)
        await render_admin_config(update.callback_query)
    return ConversationHandler.END


async def cfg_ratelimit_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        return ConversationHandler.END
    ctx.user_data["in_admin_conv"] = True
    try:
        await query.answer()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    current = bot_config.get("rate_limit_seconds", 0.5)
    if query.message:
        await query.message.edit_text(
            f"▸ <b>EDIT RATE LIMIT</b>\n───────────────────\n\n"
            f"Current: <code>{current}s</code>\n\n"
            f"Send new rate limit in seconds (0.0 to 300.0) ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_CFG_RATELIMIT


async def cfg_ratelimit_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return WAITING_CFG_RATELIMIT
    try:
        val = float(update.message.text.strip())
        if math.isnan(val) or math.isinf(val) or val < 0 or val > 300:
            raise ValueError
    except ValueError:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
        )
        await update.message.reply_text(
            "❌ <b>Invalid rate limit</b>\n"
            "Must be a number between 0 and 300.\nTry again ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return WAITING_CFG_RATELIMIT

    bot_config["rate_limit_seconds"] = round(val, 2)
    save_db()
    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Rate Limit → <code>{val}s</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_delay_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        return ConversationHandler.END
    ctx.user_data["in_admin_conv"] = True
    try:
        await query.answer()
    except Exception:
        pass
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    current = bot_config.get("artificial_delay_seconds", 0.0)
    if query.message:
        await query.message.edit_text(
            f"▸ <b>EDIT ARTIFICIAL DELAY</b>\n───────────────────\n\n"
            f"Current: <code>{current}s</code>\n\n"
            f"Send new delay in seconds (0.0 to 60.0) ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_CFG_DELAY


async def cfg_delay_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return WAITING_CFG_DELAY
    try:
        val = float(update.message.text.strip())
        if math.isnan(val) or math.isinf(val) or val < 0 or val > 60:
            raise ValueError
    except ValueError:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
        )
        await update.message.reply_text(
            "❌ <b>Invalid delay</b>\n"
            "Must be a number between 0 and 60.\nTry again ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return WAITING_CFG_DELAY

    bot_config["artificial_delay_seconds"] = round(val, 2)
    save_db()
    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Delay → <code>{val}s</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


# ─── Admin Broadcast Conversation (With Flood-Wait & Throttle) ───


async def admin_broadcast_start(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if not query or not is_admin(query.from_user.id):
        if query:
            await query.answer("Access Denied", show_alert=True)
        return ConversationHandler.END

    ctx.user_data["in_admin_conv"] = True
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    try:
        await query.answer()
    except Exception:
        pass
    if query.message:
        await query.message.edit_text(
            "▸ <b>BROADCAST</b>\n"
            "───────────────────\n\n"
            "Send the message to broadcast.\n"
            "<i>HTML supported</i>",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
    return WAITING_BROADCAST_MSG


async def admin_broadcast_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    from telegram.error import Forbidden, RetryAfter

    if not update.message or not update.message.text:
        return WAITING_BROADCAST_MSG
    message = update.message.text
    sent_count = 0
    fail_count = 0
    wait_msg = await update.message.reply_text(
        "⏳ Broadcasting message...",
        reply_to_message_id=update.message.message_id,
    )

    # Snapshot target users
    target_users = list(user_data.keys())
    total_users = len(target_users)

    for i, user_id_str in enumerate(target_users):
        for _ in range(3):
            try:
                await ctx.bot.send_message(
                    chat_id=int(user_id_str),
                    text=f"📢 <b>Announcement from {html.escape(BOT_NAME)}</b>\n\n{message}",
                    parse_mode=ParseMode.HTML,
                )
                sent_count += 1
                break
            except RetryAfter as e:
                logger.warning(f"Broadcast flood limit hit, sleeping {e.retry_after}s")
                await asyncio.sleep(e.retry_after + 0.5)
            except Forbidden:
                fail_count += 1
                break
            except Exception as e:
                logger.debug(f"Broadcast to {user_id_str} failed: {e}")
                fail_count += 1
                break

        await asyncio.sleep(0.04)  # ~25 msg/s throttle

        if (i + 1) % 50 == 0:
            try:
                await wait_msg.edit_text(
                    f"⏳ Broadcasting: {i + 1}/{total_users} processed..."
                )
            except Exception:
                pass

    ctx.user_data.pop("in_admin_conv", None)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Back", callback_data="cb_admin_panel")]]
    )
    await wait_msg.edit_text(
        f"✓ <b>BROADCAST DONE</b>\n"
        "───────────────────\n\n"
        f"  Total  →  <code>{total_users}</code>\n"
        f"  Sent   →  <code>{sent_count}</code>\n"
        f"  Failed →  <code>{fail_count}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


# ─── Advanced Admin Commands ───


async def search_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/searchuser UserID</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    u_id = ctx.args[0].strip()
    u = user_data.get(u_id)
    if u:
        await update.message.reply_text(
            f"🔍 <b>User Found:</b>\n━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{html.escape(u_id)}</code>\n"
            f"🔗 <b>UPI:</b> <code>{html.escape(u.get('upi', ''))}</code>\n"
            f"🏷 <b>Name:</b> {html.escape(u.get('name') or 'N/A')}\n"
            f"📈 <b>QRs Gen:</b> {u.get('qr_generated', 0)}\n"
            f"📅 <b>Joined:</b> {html.escape(u.get('joined_at', 'Unknown')[:10])}",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("❌ User not found in database.")


async def wipe_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/wipeuser UserID</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    u_id = ctx.args[0].strip()
    if u_id in user_data:
        del user_data[u_id]
        save_db()
        pfp_f = os.path.join(CACHE_DIR, f"pfp_{u_id}.jpg")
        av_f = os.path.join(CACHE_DIR, f"avatar_{u_id}.png")
        for f in (pfp_f, av_f):
            if os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass
        await update.message.reply_text(
            f"✅ User <code>{html.escape(u_id)}</code> successfully wiped from database.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("❌ User not found.")


async def ban_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/ban UserID</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        u_id = int(ctx.args[0].strip())
    except ValueError:
        await update.message.reply_text("❌ UserID must be a numeric ID.")
        return

    bl = bot_config.setdefault("blacklist", [])
    if u_id not in _blacklist_set:
        bl.append(u_id)
        update_blacklist_cache()
        save_db()
        await update.message.reply_text(
            f"✅ User <code>{u_id}</code> permanently banned.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("⚠️ User is already banned.")


async def unban_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/unban UserID</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        u_id = int(ctx.args[0].strip())
    except ValueError:
        await update.message.reply_text("❌ UserID must be a numeric ID.")
        return

    bl = bot_config.get("blacklist", [])
    removed = False
    if u_id in bl:
        bl.remove(u_id)
        removed = True
    elif str(u_id) in bl:
        bl.remove(str(u_id))
        removed = True

    if removed:
        update_blacklist_cache()
        save_db()
        await update.message.reply_text(
            f"✅ User <code>{u_id}</code> unbanned.", parse_mode=ParseMode.HTML
        )
    else:
        await update.message.reply_text("❌ User is not in blacklist.")


async def dm_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(ctx.args) < 2:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/dm UserID Hello there!</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    try:
        u_id = int(ctx.args[0].strip())
    except ValueError:
        await update.message.reply_text("❌ UserID must be a numeric ID.")
        return
    msg = " ".join(ctx.args[1:])
    try:
        await ctx.bot.send_message(
            chat_id=u_id,
            text=f"📩 <b>Admin Message:</b>\n\n{html.escape(msg)}",
            parse_mode=ParseMode.HTML,
        )
        await update.message.reply_text("✅ Direct Message sent successfully!")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to send DM (User might have blocked the bot). Error: {html.escape(str(e))}"
        )


async def search_upi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/searchupi upi@bank</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    query_upi = ctx.args[0].lower().strip()
    results = [
        (uid_k, u)
        for uid_k, u in list(user_data.items())
        if query_upi in u.get("upi", "").lower()
    ]
    if results:
        text = f"🔎 <b>UPI Search Results for:</b> <code>{html.escape(query_upi)}</code>\n───────────────\n"
        for uid_k, u in results[:10]:
            text += f"🆔 <code>{html.escape(uid_k)}</code> → <code>{html.escape(u['upi'])}</code> ({html.escape(u.get('name', 'N/A'))})\n"
        if len(results) > 10:
            text += f"\n<i>... and {len(results) - 10} more</i>"
    else:
        text = "❌ No users found with that UPI ID."
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def reset_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not ctx.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/resetstats UserID</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    u_id = ctx.args[0].strip()
    if u_id in user_data:
        user_data[u_id]["qr_generated"] = 0
        save_db()
        await update.message.reply_text(
            f"✅ Stats reset for user <code>{html.escape(u_id)}</code>.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("❌ User not found.")


# ─── User Conversation Handlers (Edit UPI / Default Note) ───


async def user_edit_upi_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Cancel", callback_data="cb_cancel")]]
        )
        if query.message:
            await query.message.edit_text(
                "🔄 <b>Change UPI ID</b>\n\nSend your new UPI ID in the chat (e.g., <code>name@bank</code>):",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
    return WAITING_EDIT_UPI


async def user_edit_upi_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return WAITING_EDIT_UPI
    upi_id = update.message.text.strip()
    if not re.match(r"^[a-zA-Z0-9.\-_]+@[a-zA-Z0-9.\-_]+$", upi_id):
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Cancel", callback_data="cb_cancel")]]
        )
        await update.message.reply_text(
            "❌ <b>Invalid format.</b> Please ensure it looks like <code>name@bank</code> and try again:",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return WAITING_EDIT_UPI
    uid_str = str(update.effective_user.id)
    if uid_str in user_data:
        user_data[uid_str]["upi"] = upi_id
        save_db()
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Dashboard", callback_data="cb_dashboard")]]
    )
    await update.message.reply_text(
        f"✅ <b>UPI Updated Successfully!</b>\n\n🏦 Your new UPI ID is: <code>{html.escape(upi_id)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def user_set_note_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🗑 Clear Note", callback_data="cb_clear_note"
                    )
                ],
                [InlineKeyboardButton("🔙 Cancel", callback_data="cb_cancel")],
            ]
        )
        if query.message:
            await query.message.edit_text(
                "📝 <b>Set Default Note</b>\n\n"
                "Send your default payment note in the chat "
                "(e.g., <code>Payment for services</code>):\n\n"
                "<i>This will auto-fill in every QR you generate.</i>",
                parse_mode=ParseMode.HTML,
                reply_markup=kb,
            )
    return WAITING_DEFAULT_NOTE


async def user_set_note_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    if not update.message or not update.message.text:
        return WAITING_DEFAULT_NOTE
    note = re.sub(r"[\r\n\t]+", " ", update.message.text).strip()[:50]
    uid_str = str(update.effective_user.id)
    if uid_str in user_data:
        user_data[uid_str]["default_note"] = note
        save_db()
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Dashboard", callback_data="cb_dashboard")]]
    )
    await update.message.reply_text(
        f"✅ <b>Default Note Saved!</b>\n\n📌 Your default note: <code>{html.escape(note)}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


# ─── Global Error Handler ───


async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from telegram.error import Conflict, Forbidden, NetworkError, TimedOut

    # Filter transient network drops and blocks to prevent admin spam
    if isinstance(context.error, (NetworkError, Conflict, TimedOut, Forbidden)):
        logger.warning(f"Ignored transient telegram network event: {context.error}")
        return

    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(
        None, context.error, getattr(context.error, "__traceback__", None)
    )
    tb_string = "".join(tb_list)

    if update and isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ <b>An unexpected internal error occurred.</b> The admins have been notified.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass

    if ADMIN_ID:
        error_msg = (
            f"🔴 <b>SYSTEM EXCEPTION ({html.escape(BOT_NAME)})</b> 🔴\n\n"
            f"<pre>{html.escape(tb_string[-3000:])}</pre>"
        )
        admin_ids = [a.strip() for a in str(ADMIN_ID).split(",") if a.strip()]
        for adm in admin_ids:
            try:
                await context.bot.send_message(
                    chat_id=int(adm),
                    text=error_msg,
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass


async def ping_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    await ctx.bot.get_me()
    ping_ms = max(5, round((time.time() - start_time) * 1000))

    uptime_sec = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    text = (
        f"{ce('zap', '⚡')} <b>PONG!</b>\n"
        f"───────────────────\n\n"
        f"• <b>API Latency:</b> <code>{ping_ms}ms</code>\n"
        f"• <b>Bot Uptime:</b> <code>{uptime_str}</code>"
    )
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only: Direct access to admin panel."""
    uid = update.effective_user.id
    if not is_admin(uid):
        if update.effective_message:
            await update.effective_message.reply_text(
                "⛔️ <b>Admin only command.</b>", parse_mode=ParseMode.HTML
            )
        return

    kb = [
        [
            InlineKeyboardButton("👥 Users", callback_data="cb_admin_users"),
            InlineKeyboardButton("💻 System", callback_data="cb_admin_system"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="cb_admin_comm"),
            InlineKeyboardButton("📈 Analytics", callback_data="cb_admin_stats"),
        ],
        [
            InlineKeyboardButton("🔐 Security", callback_data="cb_admin_security"),
            InlineKeyboardButton("⚙️ Config", callback_data="cb_admin_config"),
        ],
        [InlineKeyboardButton("← Exit", callback_data="cb_dashboard")],
    ]
    text = "👑 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSelect a module ↓"
    if update.effective_message:
        await update.effective_message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb)
        )


async def device_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only: Show VPS status dashboard directly."""
    uid = update.effective_user.id
    if not is_admin(uid):
        if update.effective_message:
            await update.effective_message.reply_text(
                "⛔️ <b>Admin only command.</b>", parse_mode=ParseMode.HTML
            )
        return

    text = get_health_text()
    if update.effective_message:
        await update.effective_message.reply_text(text, parse_mode=ParseMode.HTML)


_restart_requested = False


async def restart_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only: Graceful bot restart."""
    global _restart_requested
    uid = update.effective_user.id
    if not is_admin(uid):
        if update.effective_message:
            await update.effective_message.reply_text(
                "⛔️ <b>Admin only command.</b>", parse_mode=ParseMode.HTML
            )
        return

    if update.effective_message:
        await update.effective_message.reply_text(
            "🔄 <b>Restarting bot...</b>\n\n"
            "<i>Saving data & shutting down gracefully.\nBot will be back online in a few seconds.</i>",
            parse_mode=ParseMode.HTML,
        )

    atomic_save_json(DATA_FILE, dict(user_data))
    atomic_save_json(CONFIG_FILE, dict(bot_config))
    logger.info(f"Bot restart requested by admin {uid}")

    _restart_requested = True
    asyncio.create_task(_graceful_restart(ctx.application))


async def _graceful_restart(app):
    """Save data, wait for pending replies, then stop polling."""
    await asyncio.sleep(1.5)
    atomic_save_json(DATA_FILE, dict(user_data))
    atomic_save_json(CONFIG_FILE, dict(bot_config))
    app.stop_running()


# ─── Main Application Builder ───


def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ Set BOT_TOKEN in .env file!")
        return

    # Wrap handlers with rate limiting
    global dashboard, gen_command, ping_command, handle_crypto_price, crypto_command, button_handler
    global setup_start, setup_receive_upi, setup_receive_name, setup_skip_name
    global user_edit_name_start, user_edit_name_receive
    global user_edit_upi_start, user_edit_upi_receive
    global user_set_note_start, user_set_note_receive
    global calc_command

    dashboard = slow_and_rate_limited(dashboard)
    gen_command = slow_and_rate_limited(gen_command)
    ping_command = slow_and_rate_limited(ping_command)
    handle_crypto_price = slow_and_rate_limited(handle_crypto_price)
    crypto_command = slow_and_rate_limited(crypto_command)
    calc_command = slow_and_rate_limited(calc_command)
    button_handler = slow_and_rate_limited(button_handler)
    setup_start = slow_and_rate_limited(setup_start)
    setup_receive_upi = slow_and_rate_limited(setup_receive_upi)
    setup_receive_name = slow_and_rate_limited(setup_receive_name)
    setup_skip_name = slow_and_rate_limited(setup_skip_name)
    user_edit_name_start = slow_and_rate_limited(user_edit_name_start)
    user_edit_name_receive = slow_and_rate_limited(user_edit_name_receive)
    user_edit_upi_start = slow_and_rate_limited(user_edit_upi_start)
    user_edit_upi_receive = slow_and_rate_limited(user_edit_upi_receive)
    user_set_note_start = slow_and_rate_limited(user_set_note_start)
    user_set_note_receive = slow_and_rate_limited(user_set_note_receive)

    print(f"🚀 {BOT_NAME} starting in Enterprise Mode...")

    async def post_init(application: Application):
        asyncio.create_task(db_writer_loop())
        asyncio.create_task(update_usdt_rate_task())
        try:
            if ADMIN_ID:
                admin_ids = [a.strip() for a in str(ADMIN_ID).split(",") if a.strip()]
                for adm in admin_ids:
                    try:
                        await application.bot.send_message(
                            chat_id=int(adm),
                            text=(
                                f"🟢 <b>{html.escape(BOT_NAME)} System Online</b>\n\n"
                                f"All services operational. Zero-delay live crypto engine active."
                            ),
                            parse_mode=ParseMode.HTML,
                        )
                    except Exception:
                        pass
        except Exception as e:
            logger.debug(f"Startup notify error: {e}")

    req = HTTPXRequest(
        connection_pool_size=64,
        read_timeout=20.0,
        write_timeout=20.0,
        connect_timeout=10.0,
        pool_timeout=10.0,
    )
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(req)
        .post_init(post_init)
        .concurrent_updates(True)
        .build()
    )

    async def cancel_to_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        ctx.user_data.pop("in_admin_conv", None)
        await admin_command(update, ctx)
        return ConversationHandler.END

    conv_fallbacks = [
        CallbackQueryHandler(cancel_conversation, pattern="^cb_cancel$"),
        CommandHandler("cancel", cancel_conversation),
        CommandHandler("start", cancel_conversation),
        CommandHandler("admin", cancel_to_admin),
    ]

    # Setup Conversation
    setup_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(setup_start, pattern="^cb_setup_start$"),
            CommandHandler("setupi", setup_start),
            CommandHandler("setup", setup_start),
            CommandHandler(
                "start", setup_start, filters=filters.Regex(r"^/start\s+setup")
            ),
            CallbackQueryHandler(
                user_edit_name_start, pattern="^cb_user_edit_name$"
            ),
        ],
        states={
            WAITING_UPI: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, setup_receive_upi
                )
            ],
            WAITING_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, setup_receive_name
                ),
                CallbackQueryHandler(
                    setup_skip_name, pattern="^cb_skip_name$"
                ),
            ],
            WAITING_EDIT_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, user_edit_name_receive
                )
            ],
        },
        fallbacks=conv_fallbacks,
    )

    # Edit UPI Conversation
    edit_upi_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                user_edit_upi_start, pattern="^cb_user_edit_upi$"
            )
        ],
        states={
            WAITING_EDIT_UPI: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, user_edit_upi_receive
                )
            ]
        },
        fallbacks=conv_fallbacks,
    )

    # Set Default Note Conversation
    set_note_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                user_set_note_start, pattern="^cb_user_set_note$"
            )
        ],
        states={
            WAITING_DEFAULT_NOTE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, user_set_note_receive
                )
            ]
        },
        fallbacks=conv_fallbacks,
    )

    # Broadcast Conversation
    broadcast_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                admin_broadcast_start, pattern="^cb_admin_broadcast_start$"
            )
        ],
        states={
            WAITING_BROADCAST_MSG: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, admin_broadcast_receive
                )
            ]
        },
        fallbacks=conv_fallbacks,
    )

    # Admin Config Conversation
    cfg_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(
                cfg_botname_start, pattern="^cb_cfg_botname$"
            ),
            CallbackQueryHandler(
                cfg_botuser_start, pattern="^cb_cfg_botuser$"
            ),
            CallbackQueryHandler(
                cfg_support_start, pattern="^cb_cfg_support$"
            ),
            CallbackQueryHandler(cfg_logch_start, pattern="^cb_cfg_logch$"),
            CallbackQueryHandler(
                cfg_forcesub_start, pattern="^cb_cfg_forcesub$"
            ),
            CallbackQueryHandler(
                cfg_ratelimit_start, pattern="^cb_cfg_ratelimit$"
            ),
            CallbackQueryHandler(cfg_delay_start, pattern="^cb_cfg_delay$"),
        ],
        states={
            WAITING_CFG_BOT_NAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_botname_receive
                )
            ],
            WAITING_CFG_BOT_USERNAME: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_botuser_receive
                )
            ],
            WAITING_CFG_SUPPORT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_support_receive
                ),
                CallbackQueryHandler(
                    cfg_clear_support, pattern="^cb_cfg_clear_support$"
                ),
            ],
            WAITING_CFG_LOG_CHANNEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_logch_receive
                ),
                CallbackQueryHandler(
                    cfg_clear_logch, pattern="^cb_cfg_clear_logch$"
                ),
            ],
            WAITING_CFG_FORCE_SUB: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_forcesub_receive
                ),
                CallbackQueryHandler(
                    cfg_clear_forcesub, pattern="^cb_cfg_clear_forcesub$"
                ),
            ],
            WAITING_CFG_RATELIMIT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_ratelimit_receive
                )
            ],
            WAITING_CFG_DELAY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_delay_receive
                )
            ],
        },
        fallbacks=conv_fallbacks,
    )

    app.add_handler(setup_conv)
    app.add_handler(edit_upi_conv)
    app.add_handler(set_note_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(cfg_conv)

    app.add_handler(CommandHandler("start", dashboard))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("device", device_command))
    app.add_handler(CommandHandler("pay", gen_command))
    app.add_handler(CommandHandler("ping", ping_command))
    app.add_handler(CommandHandler("crypto", crypto_command))
    app.add_handler(CommandHandler("price", crypto_command))
    app.add_handler(CommandHandler(["calc", "calculate", "c"], calc_command))

    # Admin Commands
    app.add_handler(CommandHandler("searchuser", search_user))
    app.add_handler(CommandHandler("searchupi", search_upi))
    app.add_handler(CommandHandler("resetstats", reset_stats))
    app.add_handler(CommandHandler("wipeuser", wipe_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("dm", dm_user))
    app.add_handler(CommandHandler("restart", restart_command))

    # Dynamic crypto ticker commands (/btc, /eth, /sol, etc.)
    app.add_handler(MessageHandler(filters.COMMAND, handle_crypto_price))

    # Auto-detect math expressions in chat (e.g. 300+340+85 -> 300+340+85 = 725)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_calculator)
    )

    # Buttons callback dispatcher
    app.add_handler(CallbackQueryHandler(button_handler))

    # Error logging
    app.add_error_handler(error_handler)

    print("✅ Advanced Bot Architecture is running! Press Ctrl+C to stop.")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app.run_polling(drop_pending_updates=True)

    if _restart_requested:
        logger.info("Polling stopped cleanly. Relaunching process in 3 seconds...")
        time.sleep(3)
        os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    keep_alive.keep_alive()
    main()
