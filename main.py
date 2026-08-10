import keep_alive
import os
import json
import re
import logging
import traceback
import html
from datetime import datetime
import time
import asyncio
import sys
import httpx
import warnings
import platform
import psutil
from io import BytesIO

import qrcode
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from telegram.request import HTTPXRequest
from telegram.constants import ParseMode
from telegram.warnings import PTBUserWarning

warnings.filterwarnings("ignore", category=PTBUserWarning)

BOT_START_TIME = time.time()
load_dotenv(override=True)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
BOT_NAME = os.getenv("BOT_NAME", "GenPay QR Bot")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@GenvQRbot")
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME")
LOG_CHANNEL_ID = os.getenv("LOG_CHANNEL_ID")
FORCE_SUB_CHANNEL = os.getenv("FORCE_SUB_CHANNEL")

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


class NetworkErrorFilter(logging.Filter):
    def filter(self, record):
        if record.exc_info:
            exc_type = record.exc_info[0]
            if exc_type and exc_type.__name__ in ("NetworkError", "Conflict"):
                return False
        return True


logging.getLogger("telegram.ext.Updater").addFilter(NetworkErrorFilter())

DATA_FILE = "users.json"
CONFIG_FILE = "bot_config.json"


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default


def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


user_data = load_json(DATA_FILE, {})
bot_config = load_json(
    CONFIG_FILE, {"maintenance": False, "total_generated": 0, "blacklist": []}
)
if "rate_limit_seconds" not in bot_config:
    bot_config["rate_limit_seconds"] = 5.0
if "artificial_delay_seconds" not in bot_config:
    bot_config["artificial_delay_seconds"] = 1.5

db_dirty = False


def save_db():
    global db_dirty
    db_dirty = True


async def db_writer_loop():
    global db_dirty
    while True:
        await asyncio.sleep(5)
        if db_dirty:
            db_dirty = False
            await asyncio.to_thread(save_json, DATA_FILE, user_data)
            await asyncio.to_thread(save_json, CONFIG_FILE, bot_config)


def is_admin(uid: int) -> bool:
    return str(uid) == str(ADMIN_ID)


# Conversation States
WAITING_UPI, WAITING_NAME = range(2)
WAITING_BROADCAST_MSG = 10
WAITING_EDIT_NAME = 40
WAITING_EDIT_UPI = 41
WAITING_DEFAULT_NOTE = 42
WAITING_RESET_STATS_ID = 43
WAITING_SEARCH_UPI = 44
WAITING_CFG_BOT_NAME = 50
WAITING_CFG_BOT_USERNAME = 51
WAITING_CFG_SUPPORT = 52
WAITING_CFG_LOG_CHANNEL = 53
WAITING_CFG_FORCE_SUB = 54
WAITING_CFG_RATELIMIT = 55
WAITING_CFG_DELAY = 56


def update_env(key: str, value: str):
    """Update a key in the .env file."""
    env_path = ".env"
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{key}="):
            lines[i] = f"{key}={value}\n"
            found = True
            break
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(lines)


# Rate limiter: {user_id: last_command_time}
_rate_limit = {}


def check_rate_limit(uid: int) -> bool:
    """Returns True if user is allowed, False if rate-limited."""
    now = time.time()
    last = _rate_limit.get(uid, 0)
    limit = bot_config.get("rate_limit_seconds", 5.0)
    if now - last < limit:
        return False
    _rate_limit[uid] = now
    return True


def slow_and_rate_limited(func):
    """Enforces global rate limiting and artificial delays to slow down the bot."""

    async def wrapper(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        if not update or not update.effective_user:
            return await func(update, context, *args, **kwargs)

        uid = update.effective_user.id

        # Admins are exempt from rate limit and delays
        if is_admin(uid):
            return await func(update, context, *args, **kwargs)

        # 1. Rate limiting check
        now = time.time()
        last = _rate_limit.get(uid, 0)
        limit = bot_config.get("rate_limit_seconds", 5.0)
        if now - last < limit:
            remaining = int(limit - (now - last)) + 1
            if update.callback_query:
                try:
                    await update.callback_query.answer(
                        f"⚠️ Slow down! Please wait {remaining}s.",
                        show_alert=True,
                    )
                except Exception:
                    pass
            elif update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        f"⚠️ <b>Slow down!</b> Please wait {remaining}s "
                        f"between commands.",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass
            return

        # 2. Artificial delay
        delay = bot_config.get("artificial_delay_seconds", 1.5)
        if delay > 0:
            await asyncio.sleep(delay)

        # Update rate limit timestamp
        _rate_limit[uid] = time.time()

        return await func(update, context, *args, **kwargs)

    return wrapper


async def enforce_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> bool:
    if not FORCE_SUB_CHANNEL:
        return True

    uid = update.effective_user.id
    if is_admin(uid):
        return True

    if uid in bot_config.get("blacklist", []) or str(uid) in [
        str(x) for x in bot_config.get("blacklist", [])
    ]:
        if update.callback_query:
            await update.callback_query.answer(
                "You are permanently banned.", show_alert=True
            )
        else:
            await update.message.reply_text(
                "⛔️ <b>You are permanently banned from using this bot.</b>",
                parse_mode=ParseMode.HTML,
            )
        return False

    try:
        member = await ctx.bot.get_chat_member(
            chat_id=FORCE_SUB_CHANNEL, user_id=uid
        )
        if member.status in ["left", "kicked", "restricted"]:
            channel_url = f"https://t.me/{FORCE_SUB_CHANNEL.replace('@', '')}"
            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📢 Join Channel", url=channel_url)]]
            )
            text = (
                "🛑 <b>Must Join Channel</b>\n\n"
                "You must join our official channel to use this bot!"
            )

            if update.callback_query:
                await update.callback_query.message.reply_text(
                    text, parse_mode=ParseMode.HTML, reply_markup=kb
                )
            else:
                await update.message.reply_text(
                    text, parse_mode=ParseMode.HTML, reply_markup=kb
                )
            return False
        return True
    except Exception:
        # If bot is not admin in channel, fail safely open
        return True


# ═══ QR Engine ═══

# Global Cached Fonts
SCALE = 2
try:
    font_title = ImageFont.truetype("font.ttf", 16 * SCALE)
    font_amt = ImageFont.truetype("font.ttf", 52 * SCALE)
    font_sub = ImageFont.truetype("font.ttf", 15 * SCALE)
    font_lbl = ImageFont.truetype("font.ttf", 12 * SCALE)
except Exception:
    font_title = font_amt = font_sub = font_lbl = ImageFont.load_default()

# Pre-computed constants
_W = 500 * SCALE
_H = 750 * SCALE
_QR_SZ = 340 * SCALE
_PAD = 40 * SCALE
_QR_Y = 230 * SCALE
_QR_X = (_W - _QR_SZ) // 2
_LOGO_SZ = int(_QR_SZ * 0.22)
_LOGO_X = _QR_X + (_QR_SZ - _LOGO_SZ) // 2
_LOGO_Y = _QR_Y + (_QR_SZ - _LOGO_SZ) // 2

# Pre-cache circle mask and white background at startup (reused for every QR)
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
    upi_url = f"upi://pay?pa={upi_id}&pn={name}&am={amount}&cu=INR"
    if note:
        upi_url += f"&tn={note}"

    canvas = Image.new("RGB", (_W, _H), "#0A0A0C")
    draw = ImageDraw.Draw(canvas)

    # Top accent line
    draw.rectangle([0, 0, _W, 6 * SCALE], fill="#00E5FF")

    # Amount block
    draw.text((_PAD, 50 * SCALE), "PAY TO", fill="#6B6B80", font=font_lbl)
    draw.text(
        (_PAD, 70 * SCALE),
        name.upper() if name else "MERCHANT",
        fill="#FFFFFF",
        font=font_title,
    )
    draw.text(
        (_PAD, 110 * SCALE), f"₹{amount:,.2f}", fill="#00E5FF", font=font_amt
    )
    draw.text(
        (_PAD, 175 * SCALE), f"UPI ID: {upi_id}", fill="#8A8A99", font=font_sub
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
    qr_img = qr.make_image(fill_color="#000000", back_color="#FFFFFF").convert(
        "RGB"
    )
    qr_img = qr_img.resize((_QR_SZ, _QR_SZ), Image.Resampling.NEAREST)
    canvas.paste(qr_img, (_QR_X, _QR_Y))

    # Paste user's profile picture (DP) in the center of the QR code
    if pfp_path and os.path.exists(pfp_path):
        try:
            user_dp = Image.open(pfp_path).convert("RGBA")
            user_dp = user_dp.resize(
                (_LOGO_SZ, _LOGO_SZ), Image.Resampling.LANCZOS
            )
            canvas.paste(_white_bg, (_LOGO_X, _LOGO_Y), mask=_circle_mask)
            canvas.paste(user_dp, (_LOGO_X, _LOGO_Y), mask=_circle_mask)
        except Exception:
            pass  # If PFP loading fails, QR works fine without it

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
    draw.text(
        (_W // 2, _H - (30 * SCALE)),
        bot_username.upper() if bot_username else "GENPAY",
        fill="#333344",
        font=font_lbl,
        anchor="mm",
    )

    bio = BytesIO()
    bio.name = "qr.jpg"
    canvas.save(bio, "JPEG", quality=92, optimize=False)
    bio.seek(0)
    return bio


def fmt_card(
    upi_id: str, amount: float, user_name: str, bot_username: str
) -> str:
    return (
        f"💳 <b>PAYMENT QR READY</b>\n"
        f"\n"
        f"  💎 ₹ <b>{amount:,.2f}</b>\n"
        f"  👑 <code>{upi_id}</code>\n"
        f"  👤 {html.escape(user_name)}\n"
        f"\n"
        f"<i>✨ Open any UPI app → Scan → Pay</i>\n"
        f"🛡️ <i>Secured by {bot_username}</i>"
    )


# ─── User Dashboard ───


def get_dashboard_kb(uid_str):
    kb = []
    if uid_str in user_data:
        kb.append(
            [
                InlineKeyboardButton(
                    "⬡ New QR", callback_data="cb_gen_prompt"
                ),
                InlineKeyboardButton(
                    "⚡ Instant", callback_data="cb_quick_qr"
                ),
            ]
        )
        kb.append(
            [
                InlineKeyboardButton("◉ Profile", callback_data="cb_profile"),
                InlineKeyboardButton(
                    "↗ Share", callback_data="cb_share_profile"
                ),
            ]
        )
        kb.append(
            [
                InlineKeyboardButton("▤ Stats", callback_data="cb_user_stats"),
                InlineKeyboardButton(
                    "⚙ Settings", callback_data="cb_user_manage"
                ),
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
            await update.callback_query.answer(
                "Bot is under maintenance.", show_alert=True
            )
        elif update.message:
            await update.message.reply_text(
                maint_text, parse_mode=ParseMode.HTML
            )
        return ConversationHandler.END

    # Handle deep link from groups
    if (
        ctx.args
        and ctx.args[0] == "setup"
        and update.message.chat.type == "private"
    ):
        data = user_data.get(uid_str)
        if not data:
            # Emulate setup_start
            kb = InlineKeyboardMarkup(
                [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
            )
            text = (
                "▸ <b>LINK YOUR UPI</b>\n"
                "───────────────────\n\n"
                "Send your UPI address below\n"
                "Format: <code>name@bank</code>\n"
            )
            await update.message.reply_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
            return WAITING_UPI

    first_name = update.effective_user.first_name
    text = (
        f"👑 <b>{html.escape(first_name)}</b>, welcome back.\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💎 <b>{BOT_NAME} PREMIUM</b>\n"
        f"<i>✨ Instant UPI QR · 🛡️ Secure · 💠 Private</i>\n\n"
        f"Select an action below ↓"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_dashboard_kb(uid_str),
        )
    else:
        await update.message.reply_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=get_dashboard_kb(uid_str),
        )

    return ConversationHandler.END


# ─── Interactive Setup (Conversation) ───


async def setup_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await enforce_sub(update, ctx):
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
        await update.callback_query.answer()
        await update.callback_query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    return WAITING_UPI


async def setup_receive_upi(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    upi_id = update.message.text.strip()
    if not re.match(r"^[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+$", upi_id):
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
        f"  <code>{upi_id}</code>\n\n"
        "Now send your <b>display name</b>\n"
        "<i>or skip to finish</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_NAME


async def setup_receive_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    return await finalize_setup(update, ctx, name)


async def setup_skip_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    return await finalize_setup(update, ctx, "")


async def finalize_setup(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE, name: str
):
    uid_str = str(update.effective_user.id)
    upi_id = ctx.user_data.get("temp_upi", "")

    user_data[uid_str] = {
        "upi": upi_id,
        "name": name,
        "qr_generated": user_data.get(uid_str, {}).get("qr_generated", 0),
        "joined_at": user_data.get(uid_str, {}).get(
            "joined_at", datetime.now().isoformat()
        ),
    }
    save_db()

    text = (
        "✓ <b>SETUP COMPLETE</b>\n"
        "───────────────────\n\n"
        f"  UPI: <code>{upi_id}</code>\n"
        f"  Name: <code>{name or 'Not set'}</code>\n\n"
        "Use <code>/pay amount</code> to create QR codes"
    )
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Dashboard", callback_data="cb_dashboard")]]
    )

    if update.callback_query:
        await update.callback_query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    else:
        await update.message.reply_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )
    return ConversationHandler.END


async def user_edit_name_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    asyncio.create_task(query.answer())
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    await query.message.edit_text(
        "▸ <b>EDIT NAME</b>\n───────────────────\n\nSend your new display name ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_EDIT_NAME


async def user_edit_name_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    name = update.message.text.strip()
    uid_str = str(update.effective_user.id)
    if uid_str in user_data:
        user_data[uid_str]["name"] = name
        save_db()

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Dashboard", callback_data="cb_dashboard")]]
    )
    await update.message.reply_text(
        f"✓ <b>Name updated</b>\n\n  → <code>{name}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cancel_conversation(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await dashboard(update, ctx)
    else:
        await update.message.reply_text("✕ Cancelled.")
        await dashboard(update, ctx)
    return ConversationHandler.END


# ─── QR Generation ───
def generate_initials_avatar(name: str, uid: int) -> str:
    """Generate a circular avatar with the user's initials when they have no PFP."""
    avatar_path = f"avatar_{uid}.png"

    # Deterministic gradient color based on user ID
    PALETTE = [
        ("#6C5CE7", "#A29BFE"),  # Purple
        ("#00B894", "#55EFC4"),  # Green
        ("#E17055", "#FAB1A0"),  # Coral
        ("#0984E3", "#74B9FF"),  # Blue
        ("#E84393", "#FD79A8"),  # Pink
        ("#00CEC9", "#81ECEC"),  # Teal
        ("#FDCB6E", "#FFEAA7"),  # Yellow
        ("#D63031", "#FF7675"),  # Red
    ]
    color1, color2 = PALETTE[uid % len(PALETTE)]

    # Extract initials (max 2 chars)
    parts = name.strip().split() if name.strip() else []
    if len(parts) >= 2:
        initials = (parts[0][0] + parts[1][0]).upper()
    elif len(parts) == 1 and len(parts[0]) > 0:
        initials = parts[0][0].upper()
    else:
        initials = "?"

    sz = 400
    # Fast gradient generation: 1D to 2D
    base = Image.new("RGB", (1, sz))
    for y in range(sz):
        t = y / sz
        r = int(int(color1[1:3], 16) * (1 - t) + int(color2[1:3], 16) * t)
        g = int(int(color1[3:5], 16) * (1 - t) + int(color2[3:5], 16) * t)
        b = int(int(color1[5:7], 16) * (1 - t) + int(color2[5:7], 16) * t)
        base.putpixel((0, y), (r, g, b))

    gradient = base.resize((sz, sz))

    # Circle mask
    mask = Image.new("L", (sz, sz), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, sz, sz), fill=255)

    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    img.paste(gradient, (0, 0), mask=mask)
    draw = ImageDraw.Draw(img)

    # Draw initials
    try:
        init_font = ImageFont.truetype("font.ttf", 160)
    except Exception:
        init_font = ImageFont.load_default()

    draw.text(
        (sz // 2, sz // 2),
        initials,
        fill="#FFFFFF",
        font=init_font,
        anchor="mm",
    )

    img.save(avatar_path, "PNG")
    return avatar_path


async def get_user_pfp(bot, user) -> str:
    """Always fetch the user's currently applied profile photo fresh from Telegram."""
    uid = user.id
    uid_str = str(uid)
    pfp_path = f"pfp_{uid_str}.jpg"

    # 1-hour cache: PFPs rarely change, and fetching costs 3 API calls (~2-5
    # seconds)
    if os.path.exists(pfp_path):
        if time.time() - os.path.getmtime(pfp_path) < 3600:
            return pfp_path

    try:
        # offset=0, limit=1 = the currently applied/visible profile photo
        photos = await bot.get_user_profile_photos(
            user_id=uid, offset=0, limit=1
        )
        logger.info(
            f"PFP fetch for {uid_str}: total_count={photos.total_count}"
        )
        if photos.total_count > 0:
            photo = photos.photos[0][-1]  # Highest resolution of current PFP
            file = await photo.get_file()
            await file.download_to_drive(pfp_path)
            logger.info(f"Current PFP downloaded for {uid_str}")
            return pfp_path
        else:
            logger.info(f"User {uid_str} has no profile photos")
    except Exception as e:
        logger.error(f"Failed to fetch PFP for {uid_str}: {e}")
        # If fetch failed but we have a previous download, use it
        if os.path.exists(pfp_path):
            return pfp_path

    # No PFP at all — generate initials avatar
    user_name = user.first_name or ""
    return generate_initials_avatar(user_name, uid)


async def gen_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await enforce_sub(update, ctx):
        return

    uid = update.effective_user.id
    uid_str = str(uid)

    if bot_config.get("maintenance") and not is_admin(uid_str):
        await update.message.reply_text(
            "🚧 <b>Maintenance Mode Active</b>", parse_mode=ParseMode.HTML
        )
        return

    data = user_data.get(uid_str)
    if not data:
        if update.message.chat.type != "private":
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
        await update.message.reply_text(
            "❌ No UPI ID linked!\n\nPlease configure your profile first.",
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
        )
        return

    if not ctx.args:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b> <code>/pay amount [note]</code>\nExample: <code>/pay 299</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        amount = float(ctx.args[0])
        if amount <= 0 or amount > 99999:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid amount. Must be between ₹1 and ₹99,999.",
            parse_mode=ParseMode.HTML,
        )
        return

    note = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else ""
    upi_id = data["upi"]
    name = data.get("name", "")
    bot_username = BOT_USERNAME

    try:
        msg = await update.message.reply_text(
            "⏳ <b>Generating QR...</b>", parse_mode=ParseMode.HTML
        )
        pfp_path = await get_user_pfp(ctx.bot, update.effective_user)
        img_bio = await asyncio.to_thread(
            generate_qr, upi_id, amount, name, note, bot_username, pfp_path
        )
        caption = fmt_card(
            upi_id, amount, update.effective_user.first_name, bot_username
        )

        # Track stats
        data["qr_generated"] = data.get("qr_generated", 0) + 1
        bot_config["total_generated"] = (
            bot_config.get("total_generated", 0) + 1
        )
        save_db()

        # Fire-and-forget log to channel (don't block QR delivery)
        if LOG_CHANNEL_ID:

            async def _log():
                try:
                    log_text = (
                        f"📝 <b>New QR Generated</b>\n"
                        f"👤 <b>User:</b> <a href='tg://user?id={uid_str}'>"
                        f"{update.effective_user.first_name}</a> "
                        f"(<code>{uid_str}</code>)\n"
                        f"💰 <b>Amount:</b> ₹{amount}\n"
                        f"🔗 <b>UPI:</b> <code>{upi_id}</code>"
                    )
                    await ctx.bot.send_message(
                        chat_id=LOG_CHANNEL_ID,
                        text=log_text,
                        parse_mode=ParseMode.HTML,
                    )
                except Exception as e:
                    logger.error(f"Failed to send log to channel: {e}")

            asyncio.create_task(_log())

        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⊗ Remove", callback_data=f"cb_delete_msg:{uid_str}"
                    )
                ]
            ]
        )

        try:
            await msg.delete()
        except Exception:
            pass

        # Retry once on timeout
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
                    img_bio.seek(0)  # Reset buffer for retry
                    await asyncio.sleep(1)
                    continue
                raise
    except Exception as e:
        logger.error(f"QR Error: {e}", exc_info=True)
        try:
            await update.message.reply_text(
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
        f"  Bot Name  →  <code>{BOT_NAME}</code>\n"
        f"  Username  →  <code>{BOT_USERNAME}</code>\n"
        f"  Support  →  <code>{SUPPORT_USERNAME or 'Not set'}</code>\n"
        f"  Log Ch.  →  <code>{LOG_CHANNEL_ID or 'Not set'}</code>\n"
        f"  Force Sub  →  <code>{FORCE_SUB_CHANNEL or 'Not set'}</code>\n"
        f"  Rate Limit  →  <code>{bot_config.get('rate_limit_seconds', 5.0)}s</code>\n"
        f"  Delay  →  <code>{bot_config.get('artificial_delay_seconds', 1.5)}s</code>"
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
    if swap_used_gb < 1:
        swap_used_str = (
            "0.0B" if swap.used == 0 else f"{swap_used_gb * 1024:.1f}MB"
        )
    else:
        swap_used_str = f"{swap_used_gb:.1f}GB"
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
        if "__pycache__" in dirpath or ".git" in dirpath:
            continue
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
                file_count += 1

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
        "🖥️ <b>VPS STATUS DASHBOARD</b>\n"
        "────────────────────\n"
        "⚙️ <b>SYSTEM INFO</b>\n"
        f"💻 OS: <code>{os_name}</code>\n"
        f"🐍 Python: <code>{py_ver}</code>\n"
        f"⏳ Uptime: <code>{uptime_str}</code>\n\n"
        "🏎️ <b>PERFORMANCE</b>\n"
        f"⚡ CPU : {cpu_bar}\n"
        f"🔗 <i>({cpu_cores} Cores)</i>\n"
        f"🧠 RAM : {ram_bar}\n"
        f"🔋 <i>({ram_used_str} / {ram_gb:.1f}GB)</i>\n"
        f"🔄 Swap: {swap_bar}\n"
        f"⚖️ <i>({swap_used_str} / {swap_gb:.1f}GB)</i>\n\n"
        "💾 <b>STORAGE (VPS)</b>\n"
        f"📦 Total : <code>{disk_total:.1f}GB</code>\n"
        f"💿 Used  : {get_color(disk_percent)} <code>{disk_used:.1f}GB ({disk_percent}%)</code>\n"
        f"📀 Free  : <code>{disk_free:.1f}GB</code>\n\n"
        "🤖 <b>BOT APP USAGE</b>\n"
        f"🗂️ Total Size : <code>{size_str}</code> <i>({file_count} files)</i>\n"
        f"🗄️ Database   : <code>{db_size_str}</code>\n"
        f"👤 Sessions   : <code>{active_sessions} Active</code>\n"
        "────────────────────"
    )


async def render_admin_health(query):
    text = get_health_text()
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Back", callback_data="cb_admin_system")]]
    )
    asyncio.create_task(query.answer())
    await query.message.edit_text(
        text, parse_mode=ParseMode.HTML, reply_markup=kb
    )


# ─── Callback Handlers ───


async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global SUPPORT_USERNAME, LOG_CHANNEL_ID, FORCE_SUB_CHANNEL
    query = update.callback_query
    data = query.data
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
            f"  UPI  →  <code>{u['upi']}</code>\n"
            f"  Name  →  <code>{u.get('name') or 'Not set'}</code>\n"
            f"  QRs  →  <code>{u.get('qr_generated', 0)}</code>\n"
            f"  Since  →  <code>{joined}</code>"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_dashboard")]]
        )
        asyncio.create_task(query.answer())
        await query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )

    elif data == "cb_user_manage":
        if uid_str not in user_data:
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
                    f"≡ Note: {default_note[:15]}",
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
        await query.message.edit_text(
            "▸ <b>SETTINGS</b>\n"
            "───────────────────\n\n"
            "Modify your account below ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "cb_delupi_confirm":
        asyncio.create_task(query.answer())
        kb = [
            [
                InlineKeyboardButton(
                    "⚠️ Yes, Delete My Account",
                    callback_data="cb_delupi_execute",
                )
            ],
            [InlineKeyboardButton("✕ Cancel", callback_data="cb_user_manage")],
        ]
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
            await query.answer("Account deleted permanently.", show_alert=True)
        else:
            await query.answer("No profile found.", show_alert=True)
        await dashboard(update, ctx)

    elif data == "cb_gen_prompt":
        asyncio.create_task(query.answer())
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
        support_txt = (
            f"\n\nSupport: {SUPPORT_USERNAME}" if SUPPORT_USERNAME else ""
        )
        text = (
            f"▸ <b>HELP</b>\n"
            "───────────────────\n\n"
            "<b>Commands:</b>\n"
            "  <code>/pay 299</code> → create QR\n"
            "  <code>/pay 500 Note</code> → with memo\n"
            "  <code>/start</code> → dashboard\n\n"
            "<b>Tips:</b>\n"
            "  • Use <b>Instant</b> for preset amounts\n"
            "  • Set a <b>default note</b> in Settings\n"
            "  • <b>Share</b> to send payment links"
            f"{support_txt}"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_dashboard")]]
        )
        asyncio.create_task(query.answer())
        await query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )

    elif data == "cb_quick_qr":
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
        asyncio.create_task(query.answer())
        await query.message.edit_text(
            "⚡ <b>INSTANT QR</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "💎 Pick an amount ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data.startswith("cb_qr_"):
        if uid_str not in user_data:
            return
        amount = float(data.split("_")[2])
        u = user_data[uid_str]
        upi_id = u["upi"]
        name = u.get("name", "")
        note = u.get("default_note", "")
        bot_username = BOT_USERNAME

        asyncio.create_task(query.answer())
        try:
            msg = await query.message.reply_text(
                "⏳ <b>Generating QR...</b>", parse_mode=ParseMode.HTML
            )
            pfp_path = await get_user_pfp(ctx.bot, update.effective_user)
            img_bio = await asyncio.to_thread(
                generate_qr, upi_id, amount, name, note, bot_username, pfp_path
            )
            caption = fmt_card(
                upi_id, amount, update.effective_user.first_name, bot_username
            )
            u["qr_generated"] = u.get("qr_generated", 0) + 1
            bot_config["total_generated"] = (
                bot_config.get("total_generated", 0) + 1
            )
            save_db()
            del_kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⊗ Remove",
                            callback_data=f"cb_delete_msg:{uid_str}",
                        )
                    ]
                ]
            )

            try:
                await msg.delete()
            except Exception:
                pass

            # Retry once on timeout
            for attempt in range(2):
                try:
                    await query.message.reply_photo(
                        photo=img_bio,
                        caption=caption,
                        parse_mode=ParseMode.HTML,
                        reply_markup=del_kb,
                    )
                    break
                except Exception as send_err:
                    if attempt == 0 and "timed out" in str(send_err).lower():
                        img_bio.seek(0)
                        await asyncio.sleep(1)
                        continue
                    raise
        except Exception as e:
            logger.error(f"Quick QR Error: {e}", exc_info=True)
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
        rank = sorted(
            user_data.items(),
            key=lambda x: x[1].get("qr_generated", 0),
            reverse=True,
        )
        user_rank = next(
            (i + 1 for i, (uid, _) in enumerate(rank) if uid == uid_str), "?"
        )
        text = (
            f"📊 <b>YOUR STATS</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            f"  👑 <b>Rank</b>  →  #{user_rank}/{len(user_data)}\n"
            f"  💎 <b>QRs</b>   →  {qr_count}\n"
            f"  Joined  →  {joined}\n"
            f"  Note  →  {u.get('default_note', 'None')}"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_dashboard")]]
        )
        asyncio.create_task(query.answer())
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
            f"<code>{share_text}</code>"
        )
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_dashboard")]]
        )
        asyncio.create_task(query.answer())
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
        try:
            await query.message.delete()
        except Exception:
            await query.answer(
                "Cannot delete message (Too old).", show_alert=True
            )

    # Admin Callbacks
    elif data == "cb_admin_panel":
        if not is_admin(uid_str):
            await query.answer("❌ Access Denied", show_alert=True)
            return

        kb = [
            [
                InlineKeyboardButton(
                    "👥 Users", callback_data="cb_admin_users"
                ),
                InlineKeyboardButton(
                    "💻 System", callback_data="cb_admin_system"
                ),
            ],
            [
                InlineKeyboardButton(
                    "📢 Broadcast", callback_data="cb_admin_comm"
                ),
                InlineKeyboardButton(
                    "📈 Analytics", callback_data="cb_admin_stats"
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔐 Security", callback_data="cb_admin_security"
                ),
                InlineKeyboardButton(
                    "⚙️ Config", callback_data="cb_admin_config"
                ),
            ],
            [InlineKeyboardButton("← Exit", callback_data="cb_dashboard")],
        ]
        text = (
            "👑 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSelect a module ↓"
        )
        asyncio.create_task(query.answer())
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
        await query.message.edit_text(
            "🔄 <b>System is rebooting...</b>\n\nPlease wait 5 seconds.",
            parse_mode=ParseMode.HTML,
        )
        save_json(DATA_FILE, user_data)
        save_json(CONFIG_FILE, bot_config)
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
        await query.message.edit_text(
            "▸ <b>BROADCAST</b>\n───────────────────\n\nSelect a tool ↓",
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(kb),
        )

    elif data == "cb_admin_top_users":
        if not is_admin(uid_str):
            return
        sorted_users = sorted(
            user_data.items(),
            key=lambda x: x[1].get("qr_generated", 0),
            reverse=True,
        )[:10]
        text = "▸ <b>TOP USERS</b>\n───────────────────\n\n"
        for i, (u_id, u_info) in enumerate(sorted_users, 1):
            text += f"  {i}. <code>{u_id}</code> → {u_info.get('qr_generated', 0)} QRs\n"
        if not sorted_users:
            text += "<i>No users yet.</i>\n"
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("← Back", callback_data="cb_admin_users")]]
        )
        await query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )

    elif data == "cb_admin_search_user_start":
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
            if u.get("joined_at", "")[:10]
            == datetime.now().strftime("%Y-%m-%d")
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
        asyncio.create_task(query.answer())
        await query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )

    elif data == "cb_admin_toggle_m":
        if not is_admin(uid_str):
            return
        bot_config["maintenance"] = not bot_config.get("maintenance", False)
        save_db()
        await query.answer("Maintenance mode toggled!", show_alert=True)
        # Reload panel
        await render_admin_system(query)

    elif data == "cb_admin_backup":
        if not is_admin(uid_str):
            return
        await query.answer("Sending backup...")
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
        csv_data = "user_id,upi,name,qr_generated,joined_at\n"
        for k, v in user_data.items():
            upi = v.get("upi", "")
            name = v.get("name", "").replace(",", "")
            qr_gen = v.get("qr_generated", 0)
            joined = v.get("joined_at", "")
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
                text += f"  {i}. <code>{b_id}</code>\n"
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
        asyncio.create_task(query.answer())
        await query.message.edit_text(
            text, parse_mode=ParseMode.HTML, reply_markup=kb
        )

    elif data == "cb_admin_purge_inactive":
        if not is_admin(uid_str):
            return
        inactive = [
            uid
            for uid, u in user_data.items()
            if u.get("qr_generated", 0) == 0
        ]
        if inactive:
            for uid in inactive:
                del user_data[uid]
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
        asyncio.create_task(query.answer())
        await render_admin_config(query)

    elif data == "cb_cfg_clear_support":
        if not is_admin(uid_str):
            return
        SUPPORT_USERNAME = ""
        update_env("SUPPORT_USERNAME", "")
        await query.answer("Support cleared!", show_alert=True)
        await render_admin_config(query)

    elif data == "cb_cfg_clear_logch":
        if not is_admin(uid_str):
            return
        LOG_CHANNEL_ID = ""
        update_env("LOG_CHANNEL_ID", "")
        await query.answer("Log channel cleared!", show_alert=True)
        await render_admin_config(query)

    elif data == "cb_cfg_clear_forcesub":
        if not is_admin(uid_str):
            return
        FORCE_SUB_CHANNEL = ""
        update_env("FORCE_SUB_CHANNEL", "")
        await query.answer("Force sub cleared!", show_alert=True)
        await render_admin_config(query)


# ─── Config Conversation Handlers ───


async def cfg_botname_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    asyncio.create_task(query.answer())
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    await query.message.edit_text(
        f"▸ <b>EDIT BOT NAME</b>\n───────────────────\n\nCurrent: <code>{BOT_NAME}</code>\n\nSend new name ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_CFG_BOT_NAME


async def cfg_botname_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global BOT_NAME
    BOT_NAME = update.message.text.strip()
    update_env("BOT_NAME", BOT_NAME)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Bot name → <code>{BOT_NAME}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_botuser_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    asyncio.create_task(query.answer())
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    await query.message.edit_text(
        f"▸ <b>EDIT USERNAME</b>\n───────────────────\n\nCurrent: <code>{BOT_USERNAME}</code>\n\nSend new @username ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_CFG_BOT_USERNAME


async def cfg_botuser_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global BOT_USERNAME
    val = update.message.text.strip()
    if not val.startswith("@"):
        val = "@" + val
    BOT_USERNAME = val
    update_env("BOT_USERNAME", BOT_USERNAME)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Username → <code>{BOT_USERNAME}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_support_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    asyncio.create_task(query.answer())
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
    await query.message.edit_text(
        f"▸ <b>EDIT SUPPORT</b>\n───────────────────\n\n"
        f"Current: <code>{SUPPORT_USERNAME or 'Not set'}</code>\n\n"
        f"Send @username ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_CFG_SUPPORT


async def cfg_support_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global SUPPORT_USERNAME
    SUPPORT_USERNAME = update.message.text.strip()
    update_env("SUPPORT_USERNAME", SUPPORT_USERNAME)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Support → <code>{SUPPORT_USERNAME}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_logch_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    asyncio.create_task(query.answer())
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
    await query.message.edit_text(
        f"▸ <b>EDIT LOG CHANNEL</b>\n───────────────────\n\n"
        f"Current: <code>{LOG_CHANNEL_ID or 'Not set'}</code>\n\n"
        f"Send channel ID ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_CFG_LOG_CHANNEL


async def cfg_logch_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global LOG_CHANNEL_ID
    LOG_CHANNEL_ID = update.message.text.strip()
    update_env("LOG_CHANNEL_ID", LOG_CHANNEL_ID)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Log channel → <code>{LOG_CHANNEL_ID}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_forcesub_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    asyncio.create_task(query.answer())
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
    await query.message.edit_text(
        f"▸ <b>EDIT FORCE SUB</b>\n───────────────────\n\n"
        f"Current: <code>{FORCE_SUB_CHANNEL or 'Not set'}</code>\n\n"
        f"Send @channel ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_CFG_FORCE_SUB


async def cfg_forcesub_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global FORCE_SUB_CHANNEL
    FORCE_SUB_CHANNEL = update.message.text.strip()
    update_env("FORCE_SUB_CHANNEL", FORCE_SUB_CHANNEL)
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Force sub → <code>{FORCE_SUB_CHANNEL}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def cfg_ratelimit_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    asyncio.create_task(query.answer())
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    current = bot_config.get("rate_limit_seconds", 5.0)
    await query.message.edit_text(
        f"▸ <b>EDIT RATE LIMIT</b>\n───────────────────\n\n"
        f"Current: <code>{current}s</code>\n\n"
        f"Send new rate limit in seconds (float or int) ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_CFG_RATELIMIT


async def cfg_ratelimit_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    try:
        val = float(update.message.text.strip())
        if val < 0 or val > 300:
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

    bot_config["rate_limit_seconds"] = val
    save_db()
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
    if not is_admin(query.from_user.id):
        return ConversationHandler.END
    asyncio.create_task(query.answer())
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    current = bot_config.get("artificial_delay_seconds", 1.5)
    await query.message.edit_text(
        f"▸ <b>EDIT ARTIFICIAL DELAY</b>\n───────────────────\n\n"
        f"Current: <code>{current}s</code>\n\n"
        f"Send new artificial delay in seconds (float or int) ↓",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_CFG_DELAY


async def cfg_delay_receive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.strip())
        if val < 0 or val > 60:
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

    bot_config["artificial_delay_seconds"] = val
    save_db()
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Config", callback_data="cb_admin_config")]]
    )
    await update.message.reply_text(
        f"✓ Delay → <code>{val}s</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


# ─── Admin Broadcast Conversation ───


async def admin_broadcast_start(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("Access Denied", show_alert=True)
        return ConversationHandler.END

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✕ Cancel", callback_data="cb_cancel")]]
    )
    asyncio.create_task(query.answer())
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
    message = update.message.text
    sent_count = 0
    fail_count = 0
    wait_msg = await update.message.reply_text(
        "⏳ Broadcasting message...",
        reply_to_message_id=update.message.message_id,
    )

    for user_id_str in user_data.keys():
        try:
            await ctx.bot.send_message(
                chat_id=int(user_id_str),
                text=f"📢 <b>Announcement from {BOT_NAME}</b>\n\n{message}",
                parse_mode=ParseMode.HTML,
            )
            sent_count += 1
        except Exception:
            fail_count += 1

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("← Back", callback_data="cb_admin_panel")]]
    )
    await wait_msg.edit_text(
        f"✓ <b>BROADCAST DONE</b>\n"
        "───────────────────\n\n"
        f"  Sent  →  <code>{sent_count}</code>\n"
        f"  Failed  →  <code>{fail_count}</code>",
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
    u_id = ctx.args[0]
    u = user_data.get(u_id)
    if u:
        await update.message.reply_text(
            f"🔍 <b>User Found:</b>\n━━━━━━━━━━\n"
            f"🆔 <b>ID:</b> <code>{u_id}</code>\n"
            f"🔗 <b>UPI:</b> <code>{u['upi']}</code>\n"
            f"🏷 <b>Name:</b> {u.get('name') or 'N/A'}\n"
            f"📈 <b>QRs Gen:</b> {u.get('qr_generated', 0)}\n"
            f"📅 <b>Joined:</b> {u.get('joined_at', 'Unknown')[:10]}",
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
    u_id = ctx.args[0]
    if u_id in user_data:
        del user_data[u_id]
        save_db()
        await update.message.reply_text(
            f"✅ User <code>{u_id}</code> successfully wiped from database.",
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
    u_id = int(ctx.args[0])
    if u_id not in bot_config.setdefault("blacklist", []):
        bot_config["blacklist"].append(u_id)
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
    u_id = int(ctx.args[0])
    if u_id in bot_config.get("blacklist", []):
        bot_config["blacklist"].remove(u_id)
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
    u_id = ctx.args[0]
    msg = " ".join(ctx.args[1:])
    try:
        await ctx.bot.send_message(
            chat_id=int(u_id),
            text=f"📩 <b>Admin Message:</b>\n\n{msg}",
            parse_mode=ParseMode.HTML,
        )
        await update.message.reply_text("✅ Direct Message sent successfully!")
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to send DM (User might have blocked the bot). Error: {e}"
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
    query_upi = ctx.args[0].lower()
    results = [
        (uid, u)
        for uid, u in user_data.items()
        if query_upi in u.get("upi", "").lower()
    ]
    if results:
        text = f"🔎 <b>UPI Search Results for:</b> <code>{query_upi}</code>\n───────────────\n"
        for uid, u in results[:10]:
            text += f"🆔 <code>{uid}</code> → <code>{u['upi']}</code> ({u.get('name', 'N/A')})\n"
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
    u_id = ctx.args[0]
    if u_id in user_data:
        user_data[u_id]["qr_generated"] = 0
        save_db()
        await update.message.reply_text(
            f"✅ Stats reset for user <code>{u_id}</code>.",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text("❌ User not found.")


# ─── User Conversation Handlers (Edit UPI / Default Note) ───


async def user_edit_upi_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    asyncio.create_task(query.answer())
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔙 Cancel", callback_data="cb_cancel")]]
    )
    await query.message.edit_text(
        "🔄 <b>Change UPI ID</b>\n\nSend your new UPI ID in the chat (e.g., <code>name@bank</code>):",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return WAITING_EDIT_UPI


async def user_edit_upi_receive(
    update: Update, ctx: ContextTypes.DEFAULT_TYPE
):
    upi_id = update.message.text.strip()
    if not re.match(r"^[a-zA-Z0-9.\-_]+@[a-zA-Z0-9]+$", upi_id):
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
        f"✅ <b>UPI Updated Successfully!</b>\n\n🏦 Your new UPI ID is: <code>{upi_id}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


async def user_set_note_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    asyncio.create_task(query.answer())
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
    note = update.message.text.strip()[:100]
    uid_str = str(update.effective_user.id)
    if uid_str in user_data:
        user_data[uid_str]["default_note"] = note
        save_db()
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Dashboard", callback_data="cb_dashboard")]]
    )
    await update.message.reply_text(
        f"✅ <b>Default Note Saved!</b>\n\n📌 Your default note: <code>{note}</code>",
        parse_mode=ParseMode.HTML,
        reply_markup=kb,
    )
    return ConversationHandler.END


# ─── Error Handler ───


async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    from telegram.error import NetworkError, Conflict

    # Ignore transient network errors to prevent admin spam
    if isinstance(context.error, (NetworkError, Conflict)):
        logger.warning(f"Transient network error: {context.error}")
        return

    logger.error("Exception while handling an update:", exc_info=context.error)
    tb_list = traceback.format_exception(
        None, context.error, context.error.__traceback__
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
        error_msg = f"🔴 <b>SYSTEM EXCEPTION ({BOT_NAME})</b> 🔴\n\n<pre>{html.escape(tb_string[-3000:])}</pre>"
        try:
            await context.bot.send_message(
                chat_id=int(ADMIN_ID),
                text=error_msg,
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def ping_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Measure raw API latency without message processing overhead
    start_time = time.time()
    await ctx.bot.get_me()
    ping_ms = max(5, round((time.time() - start_time) * 1000))

    # Send the response
    msg = await ctx.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🏓 <b>Pong!</b>",
        parse_mode=ParseMode.HTML,
    )

    uptime_sec = int(time.time() - BOT_START_TIME)
    hours, remainder = divmod(uptime_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"

    text = (
        f"🏓 <b>Pong!</b>\n"
        f"───────────────────\n\n"
        f"⚡ <b>Latency:</b> <code>{ping_ms}ms</code>\n"
        f"⏱ <b>Uptime:</b> <code>{uptime_str}</code>"
    )
    await msg.edit_text(text, parse_mode=ParseMode.HTML)


async def handle_crypto_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    command = update.message.text.split()[0].lower()
    # Strip @botusername suffix from commands in groups
    if "@" in command:
        command = command.split("@")[0]
    if not command.startswith("/"):
        return

    currency = command[1:]

    # Exclude standard bot commands
    if currency in [
        "start",
        "help",
        "pay",
        "admin",
        "device",
        "ping",
        "searchuser",
        "searchupi",
        "resetstats",
        "wipeuser",
        "ban",
        "unban",
        "dm",
        "restart",
        "setupi",
        "cancel",
    ]:
        return

    if len(currency) > 10 or len(currency) < 2:
        return

    is_private = update.message.chat.type == "private"

    wait_msg = None
    if is_private:
        wait_msg = await update.message.reply_text(
            f"⏳ <b>Fetching market rate for {currency.upper()}...</b>",
            parse_mode=ParseMode.HTML,
        )

    try:
        # Force IPv4 to prevent ConnectionError on VPS with broken IPv6
        transport = httpx.AsyncHTTPTransport(local_address="0.0.0.0")
        async with httpx.AsyncClient(
            timeout=10.0, transport=transport
        ) as client:
            # Get USDT to INR
            try:
                wazirx_resp = await client.get(
                    "https://api.wazirx.com/sapi/v1/tickers/24hr"
                )
                wazirx_status = wazirx_resp.status_code
            except Exception:
                wazirx_status = 500
                wazirx_resp = None

            usdt_inr = 88.0
            change_pct = high = low = vol = 0.0
            price_usdt = 1.0
            price_inr = usdt_inr
            item = None

            if wazirx_status == 200 and wazirx_resp:
                wazirx_data = wazirx_resp.json()
                item = next(
                    (i for i in wazirx_data if i["symbol"] == "usdtinr"), None
                )
                if item:
                    usdt_inr = float(item["lastPrice"])

            if currency == "usdt":
                price_usdt = 1.0
                price_inr = usdt_inr
                if item:
                    open_p = float(item["openPrice"])
                    change_pct = (
                        ((usdt_inr - open_p) / open_p * 100) if open_p else 0.0
                    )
                    high = float(item["highPrice"])
                    low = float(item["lowPrice"])
                    vol = float(item["volume"])
            else:
                success = False

                # Try Binance First
                try:
                    binance_resp = await client.get(
                        f"https://api.binance.com/api/v3/ticker/24hr?symbol={currency.upper()}USDT",
                        timeout=5.0,
                    )
                    if binance_resp.status_code == 200:
                        b_data = binance_resp.json()
                        price_usdt = float(b_data["lastPrice"])
                        price_inr = price_usdt * usdt_inr
                        change_pct = float(b_data["priceChangePercent"])
                        high = float(b_data["highPrice"])
                        low = float(b_data["lowPrice"])
                        vol = float(b_data["volume"])
                        success = True
                except Exception as e:
                    logger.warning(f"Binance fetch failed for {currency}: {e}")

                # Fallback to MEXC
                if not success:
                    try:
                        mexc_resp = await client.get(
                            f"https://api.mexc.com/api/v3/ticker/24hr?symbol={currency.upper()}USDT",
                            timeout=5.0,
                        )
                        if mexc_resp.status_code == 200:
                            b_data = mexc_resp.json()
                            price_usdt = float(b_data["lastPrice"])
                            price_inr = price_usdt * usdt_inr
                            change_pct = (
                                float(b_data["priceChangePercent"]) * 100
                            )
                            high = float(b_data["highPrice"])
                            low = float(b_data["lowPrice"])
                            vol = float(b_data["volume"])
                            success = True
                    except Exception as e:
                        logger.warning(
                            f"MEXC fetch failed for {currency}: {e}"
                        )

                if not success:
                    if is_private and wait_msg:
                        await wait_msg.edit_text(
                            f"❌ <b>Could not find market data for "
                            f"{currency.upper()}</b>\n"
                            f"<i>Please verify the coin symbol or try again.</i>",
                            parse_mode=ParseMode.HTML,
                        )
                    return

            trend = "📈" if change_pct >= 0 else "📉"
            sign = "+" if change_pct > 0 else ""

            text = (
                f"🪙 <b>{currency.upper()} Market Rate</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"💵 <b>Price (USDT):</b> <code>${price_usdt:,.4f}</code>\n"
                f"🇮🇳 <b>Price (INR):</b> <code>₹{price_inr:,.2f}</code>\n\n"
                f"{trend} <b>24h Change:</b> <code>{sign}{change_pct:.2f}%</code>\n"
                f"🔼 <b>24h High:</b> <code>{'₹' if currency == 'usdt' else '$'}{high:,.4f}</code>\n"
                f"🔽 <b>24h Low:</b> <code>{'₹' if currency == 'usdt' else '$'}{low:,.4f}</code>\n"
                f"📊 <b>24h Volume:</b> <code>{vol:,.2f} {currency.upper()}</code>\n\n"
                f"<i>⏱ Auto-fetched • Live Rate</i>"
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
            if wait_msg:
                await wait_msg.edit_text(
                    text, parse_mode=ParseMode.HTML, reply_markup=kb
                )
            else:
                await update.message.reply_text(
                    text, parse_mode=ParseMode.HTML, reply_markup=kb
                )

    except Exception as e:
        logger.error(f"Crypto fetch error for {currency}: {e}")
        if is_private and wait_msg:
            await wait_msg.edit_text(
                f"❌ <b>Error fetching price for {currency.upper()}</b>\n<i>Please try again later.</i>",
                parse_mode=ParseMode.HTML,
            )


_restart_requested = False


async def admin_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only: Direct access to the admin panel."""
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(
            "⛔️ <b>Admin only command.</b>", parse_mode=ParseMode.HTML
        )
        return

    kb = [
        [
            InlineKeyboardButton("👥 Users", callback_data="cb_admin_users"),
            InlineKeyboardButton("💻 System", callback_data="cb_admin_system"),
        ],
        [
            InlineKeyboardButton(
                "📢 Broadcast", callback_data="cb_admin_comm"
            ),
            InlineKeyboardButton(
                "📈 Analytics", callback_data="cb_admin_stats"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔐 Security", callback_data="cb_admin_security"
            ),
            InlineKeyboardButton("⚙️ Config", callback_data="cb_admin_config"),
        ],
        [InlineKeyboardButton("← Exit", callback_data="cb_dashboard")],
    ]
    text = "👑 <b>ADMIN PANEL</b>\n━━━━━━━━━━━━━━━━━━━━\n\nSelect a module ↓"
    await update.message.reply_text(
        text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb)
    )


async def device_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only: Show VPS status dashboard directly."""
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(
            "⛔️ <b>Admin only command.</b>", parse_mode=ParseMode.HTML
        )
        return

    text = get_health_text()
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def restart_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Admin-only: Restart the bot process."""
    global _restart_requested
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text(
            "⛔️ <b>Admin only command.</b>", parse_mode=ParseMode.HTML
        )
        return

    await update.message.reply_text(
        "🔄 <b>Restarting bot...</b>\n\n"
        "<i>Saving data & shutting down gracefully.\nBot will be back online in a few seconds.</i>",
        parse_mode=ParseMode.HTML,
    )

    # Force save all data before restart
    save_json(DATA_FILE, user_data)
    save_json(CONFIG_FILE, bot_config)
    logger.info(f"Bot restart triggered by admin {uid}")

    _restart_requested = True
    # Gracefully stop polling so the connection closes cleanly
    asyncio.create_task(_graceful_restart(ctx.application))


async def _graceful_restart(app):
    """Wait briefly for the reply to send, then stop the application."""
    await asyncio.sleep(1.5)
    app.stop_running()


# ─── Main ───


def main():
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("❌ Set BOT_TOKEN in .env file!")
        return

    # Decorate user handlers with slowdown / rate limit controls
    global dashboard, gen_command, ping_command, handle_crypto_price, button_handler
    global setup_start, setup_receive_upi, setup_receive_name, setup_skip_name
    global user_edit_name_start, user_edit_name_receive
    global user_edit_upi_start, user_edit_upi_receive
    global user_set_note_start, user_set_note_receive

    dashboard = slow_and_rate_limited(dashboard)
    gen_command = slow_and_rate_limited(gen_command)
    ping_command = slow_and_rate_limited(ping_command)
    handle_crypto_price = slow_and_rate_limited(handle_crypto_price)
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
        try:
            if ADMIN_ID:
                await application.bot.send_message(
                    chat_id=ADMIN_ID,
                    text=(
                        f"🟢 <b>{BOT_NAME} System Online</b>\n\n"
                        f"All services operational. "
                        f"Version 2.0 deployed successfully."
                    ),
                    parse_mode=ParseMode.HTML,
                )
        except Exception as e:
            print(f"Failed to send startup notification: {e}")

    req = HTTPXRequest(
        connection_pool_size=8,
        read_timeout=30.0,
        write_timeout=30.0,
        connect_timeout=30.0,
        pool_timeout=30.0,
    )
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .request(req)
        .post_init(post_init)
        .build()
    )

    # Advanced Conversational Setup
    setup_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(setup_start, pattern="^cb_setup_start$"),
            CommandHandler("setupi", setup_start),
            CommandHandler("start", dashboard),
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
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^cb_cancel$"),
            CommandHandler("cancel", cancel_conversation),
        ],
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
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^cb_cancel$"),
            CommandHandler("cancel", cancel_conversation),
        ],
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
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^cb_cancel$"),
            CommandHandler("cancel", cancel_conversation),
        ],
    )

    # Advanced Conversational Broadcast
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
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^cb_cancel$"),
            CommandHandler("cancel", cancel_conversation),
        ],
    )

    # Config Conversation
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
                )
            ],
            WAITING_CFG_LOG_CHANNEL: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_logch_receive
                )
            ],
            WAITING_CFG_FORCE_SUB: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, cfg_forcesub_receive
                )
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
        fallbacks=[
            CallbackQueryHandler(cancel_conversation, pattern="^cb_cancel$"),
            CommandHandler("cancel", cancel_conversation),
        ],
    )

    app.add_handler(setup_conv)
    app.add_handler(edit_upi_conv)
    app.add_handler(set_note_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(cfg_conv)

    app.add_handler(CommandHandler("start", dashboard))
    app.add_handler(CommandHandler("help", dashboard))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("device", device_command))
    app.add_handler(CommandHandler("pay", gen_command))
    app.add_handler(CommandHandler("ping", ping_command))

    # Advanced Admin Commands
    app.add_handler(CommandHandler("searchuser", search_user))
    app.add_handler(CommandHandler("searchupi", search_upi))
    app.add_handler(CommandHandler("resetstats", reset_stats))
    app.add_handler(CommandHandler("wipeuser", wipe_user))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("dm", dm_user))
    app.add_handler(CommandHandler("restart", restart_command))

    # Catch-all for dynamic crypto commands
    app.add_handler(MessageHandler(filters.COMMAND, handle_crypto_price))

    # Catch-all for basic callbacks
    app.add_handler(CallbackQueryHandler(button_handler))

    # Enterprise Error Logging
    app.add_error_handler(error_handler)

    print("✅ Advanced Bot Architecture is running! Press Ctrl+C to stop.")

    # Fix for Python 3.14+
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app.run_polling(drop_pending_updates=True)

    # If restart was requested, relaunch the process after clean shutdown
    if _restart_requested:
        logger.info(
            "Polling stopped cleanly. Waiting 3 seconds before relaunching..."
        )
        time.sleep(3)  # Give Telegram API time to drop the old connection
        os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    keep_alive.keep_alive()
    main()
