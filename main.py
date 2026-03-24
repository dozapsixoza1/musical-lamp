"""
╔══════════════════════════════════════════════════════════════════════╗
║                  🛡 GROUPHELP BOT — MULTI-GROUP                     ║
║              Полный клон GroupHelp для всех групп                    ║
╚══════════════════════════════════════════════════════════════════════╝

УСТАНОВКА:
    pip install python-telegram-bot==20.7 aiosqlite flask

ЗАПУСК БОТА:
    python bot.py

ЗАПУСК ВЕБ-ПАНЕЛИ (отдельный терминал):
    python admin_panel.py
"""

import logging
import asyncio
import time
import re
import hashlib
import os
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ChatPermissions, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters, ChatMemberHandler
)
from telegram.constants import ParseMode, ChatMemberStatus

import db  # наш модуль базы данных

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                        🔧 КОНФИГ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BOT_TOKEN   = "8602508429:AAEsjeV-66FKYvCuQpuJ7qxyUTINI2YJcC0"     # @BotFather
BOT_OWNER_IDS = [
    7950038145,    # 👑 Супер-овнер 1
    7780853114,    # 👑 Супер-овнер 2
]

SPAM_MSG_LIMIT    = 5
SPAM_TIME_WINDOW  = 10
SPAM_BAN_AFTER    = 3
DEFAULT_MUTE_MINS = 30

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(name)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# RAM-кеш для антиспама (не нужно в БД)
spam_tracker: dict = defaultdict(list)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                        🛠 УТИЛИТЫ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_bot_owner(uid: int) -> bool:
    return uid in BOT_OWNER_IDS

def mention(user) -> str:
    name = (user.full_name if hasattr(user, "full_name") and user.full_name else None) or str(user.id)
    return f'<a href="tg://user?id={user.id}">{name}</a>'

async def is_admin(chat_id, user_id, bot) -> bool:
    if is_bot_owner(user_id):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False

async def get_target(msg, ctx, args):
    """Возвращает целевого пользователя из ответа или аргумента"""
    if msg.reply_to_message:
        return msg.reply_to_message.from_user, " ".join(args) if args else "Не указана"
    if args:
        try:
            t = await ctx.bot.get_chat(int(args[0]))
            return t, " ".join(args[1:]) if len(args) > 1 else "Не указана"
        except Exception:
            pass
    return None, None

def ts() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#              🤖 СТАРТ / ПОМОЩЬ (работает везде)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Регистрируем пользователя
    await db.register_user(user.id, user.username or "", user.full_name or "")
    await db.log_event("bot", None, user.id, "start", f"chat:{chat.id}")

    if chat.type != "private":
        await db.register_group(chat.id, chat.title or "", chat.username or "")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📩 Написать в личку", url=f"https://t.me/{(await ctx.bot.get_me()).username}")
        ]])
        await update.message.reply_text(
            "👋 Привет! Для управления ботом напиши мне в <b>личные сообщения</b>.",
            reply_markup=kb, parse_mode=ParseMode.HTML
        )
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Добавить в группу", url=f"https://t.me/{(await ctx.bot.get_me()).username}?startgroup=true")],
        [InlineKeyboardButton("📋 Команды",    callback_data="help_main"),
         InlineKeyboardButton("⚙️ Мои группы", callback_data="my_groups")],
        [InlineKeyboardButton("📊 Статистика", callback_data="bot_stats"),
         InlineKeyboardButton("ℹ️ О боте",     callback_data="about_bot")],
    ])
    bot_info = await ctx.bot.get_me()
    await update.message.reply_text(
        f"👋 Привет, {mention(user)}!\n\n"
        f"🛡 <b>{bot_info.first_name}</b> — мощный менеджер групп!\n\n"
        "🔥 <b>Возможности:</b>\n"
        "• Управление участниками (бан, мьют, варн, кик)\n"
        "• Антиспам и антифлуд система\n"
        "• Фильтры слов и ссылок\n"
        "• Приветствия и прощания\n"
        "• Заметки и правила\n"
        "• Система предупреждений\n"
        "• Анти-спам заявки\n"
        "• Статистика чата\n\n"
        "📌 Добавь меня в группу как <b>администратора</b>!\n"
        "Бот работает в <b>любых группах</b> бесплатно 🎉",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ Модерация",   callback_data="help_mod"),
         InlineKeyboardButton("⚙️ Настройки",   callback_data="help_settings")],
        [InlineKeyboardButton("🔒 Фильтры",      callback_data="help_filters"),
         InlineKeyboardButton("📝 Заметки",      callback_data="help_notes")],
        [InlineKeyboardButton("👋 Приветствие",  callback_data="help_welcome"),
         InlineKeyboardButton("📊 Инфо",         callback_data="help_info")],
        [InlineKeyboardButton("🚨 Анти-Спам",    callback_data="help_antispam"),
         InlineKeyboardButton("❌ Закрыть",       callback_data="close")],
    ])
    await update.message.reply_text(
        "📖 <b>ПОМОЩЬ — выбери категорию:</b>",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                    ⚔️ МОДЕРАЦИЯ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 <b>Только для администраторов!</b>", parse_mode=ParseMode.HTML)

    target, reason = await get_target(msg, ctx, ctx.args)
    if not target:
        return await msg.reply_text("❌ Укажи пользователя (ответ или ID).", parse_mode=ParseMode.HTML)
    if is_bot_owner(target.id):
        return await msg.reply_text("👑 Нельзя забанить владельца бота!", parse_mode=ParseMode.HTML)

    try:
        await ctx.bot.ban_chat_member(chat.id, target.id)
        await db.add_action(chat.id, user.id, target.id, "ban", reason)
        await db.log_event(chat.id, chat.title, user.id, "ban", f"target:{target.id} reason:{reason}")
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔓 Разбанить", callback_data=f"unban_{target.id}_{chat.id}"),
            InlineKeyboardButton("📋 Инфо",      callback_data=f"uinfo_{target.id}_{chat.id}"),
        ]])
        await msg.reply_text(
            f"🔨 <b>БАН</b>\n\n"
            f"👤 Пользователь: {mention(target)}\n"
            f"🆔 ID: <code>{target.id}</code>\n"
            f"👮 Модератор: {mention(user)}\n"
            f"📝 Причина: <i>{reason}</i>\n"
            f"🕐 {ts()}",
            reply_markup=kb, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)


async def cmd_unban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text("❌ /unban <user_id>", parse_mode=ParseMode.HTML)
    try:
        uid = int(ctx.args[0])
        await ctx.bot.unban_chat_member(chat.id, uid)
        await db.log_event(chat.id, chat.title, user.id, "unban", f"target:{uid}")
        await msg.reply_text(f"✅ <b>Разбан</b>\n🆔 <code>{uid}</code> разбанен.\n👮 {mention(user)}", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)


async def cmd_mute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)

    target, reason = await get_target(msg, ctx, ctx.args)
    if not target:
        return await msg.reply_text("❌ Укажи пользователя.", parse_mode=ParseMode.HTML)
    if is_bot_owner(target.id):
        return await msg.reply_text("👑 Нельзя замьютить владельца!", parse_mode=ParseMode.HTML)

    # Парсим длительность
    duration = DEFAULT_MUTE_MINS
    if ctx.args:
        for arg in ctx.args:
            if arg.endswith("m") and arg[:-1].isdigit():
                duration = int(arg[:-1]); break
            elif arg.endswith("h") and arg[:-1].isdigit():
                duration = int(arg[:-1]) * 60; break
            elif arg.endswith("d") and arg[:-1].isdigit():
                duration = int(arg[:-1]) * 1440; break
            elif arg.isdigit():
                duration = int(arg); break

    until = datetime.now() + timedelta(minutes=duration)
    try:
        await ctx.bot.restrict_chat_member(chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=until)
        await db.add_action(chat.id, user.id, target.id, "mute", f"{duration}мин: {reason}")
        await db.log_event(chat.id, chat.title, user.id, "mute", f"target:{target.id} dur:{duration}m")
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔊 Размьютить", callback_data=f"unmute_{target.id}_{chat.id}")]])
        # Форматируем длительность
        if duration >= 1440:
            dur_str = f"{duration//1440}д"
        elif duration >= 60:
            dur_str = f"{duration//60}ч {duration%60}м"
        else:
            dur_str = f"{duration}м"
        await msg.reply_text(
            f"🔇 <b>МЬЮТf</b>\n\n"
            f"👤 {mention(target)}\n"
            f"⏱ На: <b>{dur_str}</b>\n"
            f"👮 {mention(user)}\n"
            f"📝 <i>{reason}</i>",
            reply_markup=kb, parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)


async def cmd_unmute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target and ctx.args:
        try:
            target = await ctx.bot.get_chat(int(ctx.args[0]))
        except Exception:
            pass
    if not target:
        return await msg.reply_text("❌ Укажи пользователя.", parse_mode=ParseMode.HTML)
    try:
        await ctx.bot.restrict_chat_member(
            chat.id, target.id,
            ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                            can_send_other_messages=True, can_add_web_page_previews=True)
        )
        await db.log_event(chat.id, chat.title, user.id, "unmute", f"target:{target.id}")
        await msg.reply_text(f"🔊 <b>Размьют</b>\n👤 {mention(target)}\n👮 {mention(user)}", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)


async def cmd_warn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)

    target, reason = await get_target(msg, ctx, ctx.args)
    if not target:
        return await msg.reply_text("❌ Укажи пользователя.", parse_mode=ParseMode.HTML)
    if is_bot_owner(target.id):
        return await msg.reply_text("👑 Нельзя варнить владельца!", parse_mode=ParseMode.HTML)

    settings = await db.get_group_settings(chat.id)
    max_warns = settings.get("max_warns", SPAM_BAN_AFTER)

    count = await db.add_warn(chat.id, target.id, user.id, reason)
    await db.log_event(chat.id, chat.title, user.id, "warn", f"target:{target.id} count:{count} reason:{reason}")

    if count >= max_warns:
        action = settings.get("warn_action", "ban")
        await db.clear_warns(chat.id, target.id)
        if action == "ban":
            await ctx.bot.ban_chat_member(chat.id, target.id)
            result_text = f"🔨 <b>Автобан</b> — {count} предупреждений!"
        elif action == "mute":
            until = datetime.now() + timedelta(minutes=DEFAULT_MUTE_MINS * 2)
            await ctx.bot.restrict_chat_member(chat.id, target.id, ChatPermissions(can_send_messages=False), until_date=until)
            result_text = f"🔇 <b>Автомьют</b> — {count} предупреждений!"
        else:
            await ctx.bot.ban_chat_member(chat.id, target.id)
            result_text = f"🔨 <b>Автобан</b> — {count} предупреждений!"

        await msg.reply_text(
            f"{result_text}\n👤 {mention(target)}\n📝 Последняя причина: <i>{reason}</i>\n"
            "💬 Забаненный может написать боту /antispam",
            parse_mode=ParseMode.HTML
        )
        return

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Снять варн", callback_data=f"unwarn_{target.id}_{chat.id}"),
        InlineKeyboardButton("📊 Все варны",  callback_data=f"warnlist_{target.id}_{chat.id}"),
    ]])
    await msg.reply_text(
        f"⚠️ <b>ПРЕДУПРЕЖДЕНИЕ</b>\n\n"
        f"👤 {mention(target)}\n"
        f"📊 Варнов: <b>{count}/{max_warns}</b>\n"
        f"👮 {mention(user)}\n"
        f"📝 <i>{reason}</i>\n"
        f"⚡ До наказания: <b>{max_warns - count}</b>",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )


async def cmd_unwarn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target and ctx.args:
        try:
            target = await ctx.bot.get_chat(int(ctx.args[0]))
        except Exception:
            pass
    if not target:
        return await msg.reply_text("❌ Укажи пользователя.", parse_mode=ParseMode.HTML)
    count = await db.remove_warn(chat.id, target.id)
    await msg.reply_text(
        f"✅ Один варн снят с {mention(target)}\n📊 Осталось: <b>{count}</b>",
        parse_mode=ParseMode.HTML
    )


async def cmd_resetwarns(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    target = msg.reply_to_message.from_user if msg.reply_to_message else None
    if not target and ctx.args:
        try:
            target = await ctx.bot.get_chat(int(ctx.args[0]))
        except Exception:
            pass
    if not target:
        return await msg.reply_text("❌ Укажи пользователя.", parse_mode=ParseMode.HTML)
    await db.clear_warns(chat.id, target.id)
    await msg.reply_text(f"🗑 Все варны сброшены для {mention(target)}", parse_mode=ParseMode.HTML)


async def cmd_kick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not msg.reply_to_message:
        return await msg.reply_text("❌ Ответь на сообщение!", parse_mode=ParseMode.HTML)
    target = msg.reply_to_message.from_user
    if is_bot_owner(target.id):
        return await msg.reply_text("👑 Нельзя кикнуть владельца!", parse_mode=ParseMode.HTML)
    reason = " ".join(ctx.args) if ctx.args else "Не указана"
    try:
        await ctx.bot.ban_chat_member(chat.id, target.id)
        await ctx.bot.unban_chat_member(chat.id, target.id)
        await db.log_event(chat.id, chat.title, user.id, "kick", f"target:{target.id}")
        await msg.reply_text(
            f"👢 <b>КИК</b>\n👤 {mention(target)}\n👮 {mention(user)}\n📝 <i>{reason}</i>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)


async def cmd_ro(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Только чтение"""
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not msg.reply_to_message:
        return await msg.reply_text("❌ Ответь на сообщение!", parse_mode=ParseMode.HTML)
    target = msg.reply_to_message.from_user
    duration = int(ctx.args[0]) if ctx.args and ctx.args[0].isdigit() else 60
    until = datetime.now() + timedelta(minutes=duration)
    try:
        await ctx.bot.restrict_chat_member(
            chat.id, target.id,
            ChatPermissions(can_send_messages=False, can_send_media_messages=False,
                            can_send_other_messages=False),
            until_date=until
        )
        await msg.reply_text(
            f"👁 <b>Только чтение</b>\n👤 {mention(target)}\n⏱ На <b>{duration} мин.</b>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)


async def cmd_purge(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not msg.reply_to_message:
        return await msg.reply_text("❌ Ответь на первое сообщение для удаления!", parse_mode=ParseMode.HTML)
    start, end, deleted = msg.reply_to_message.message_id, msg.message_id, 0
    for mid in range(start, end + 1):
        try:
            await ctx.bot.delete_message(chat.id, mid)
            deleted += 1
        except Exception:
            pass
    n = await ctx.bot.send_message(chat.id, f"🗑 Удалено <b>{deleted}</b> сообщений", parse_mode=ParseMode.HTML)
    await asyncio.sleep(5)
    try:
        await n.delete()
    except Exception:
        pass


async def cmd_del(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Удалить одно сообщение"""
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return
    if msg.reply_to_message:
        try:
            await msg.reply_to_message.delete()
        except Exception:
            pass
    try:
        await msg.delete()
    except Exception:
        pass


async def cmd_tban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Временный бан: /tban <время> <причина>"""
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not msg.reply_to_message:
        return await msg.reply_text("❌ /tban <время(1d/2h/30m)> [причина]", parse_mode=ParseMode.HTML)
    target = msg.reply_to_message.from_user
    duration = DEFAULT_MUTE_MINS
    reason = "Не указана"
    if ctx.args:
        arg = ctx.args[0]
        if arg.endswith("d") and arg[:-1].isdigit():
            duration = int(arg[:-1]) * 1440
        elif arg.endswith("h") and arg[:-1].isdigit():
            duration = int(arg[:-1]) * 60
        elif arg.endswith("m") and arg[:-1].isdigit():
            duration = int(arg[:-1])
        reason = " ".join(ctx.args[1:]) if len(ctx.args) > 1 else reason
    until = datetime.now() + timedelta(minutes=duration)
    try:
        await ctx.bot.ban_chat_member(chat.id, target.id, until_date=until)
        if duration >= 1440:
            dur_str = f"{duration//1440}д"
        elif duration >= 60:
            dur_str = f"{duration//60}ч"
        else:
            dur_str = f"{duration}м"
        await msg.reply_text(
            f"⏳ <b>ВРЕМЕННЫЙ БАН</b>\n👤 {mention(target)}\n⏱ На <b>{dur_str}</b>\n📝 <i>{reason}</i>",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: <code>{e}</code>", parse_mode=ParseMode.HTML)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                   📝 ЗАМЕТКИ (Notes)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if len(ctx.args) < 2:
        return await msg.reply_text("❌ /save <название> <текст>", parse_mode=ParseMode.HTML)
    name = ctx.args[0].lower()
    text = " ".join(ctx.args[1:])
    await db.save_note(chat.id, name, text, user.id)
    await msg.reply_text(f"📝 Заметка <b>#{name}</b> сохранена!", parse_mode=ParseMode.HTML)


async def cmd_get(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if not ctx.args:
        return await update.message.reply_text("❌ /get <название>", parse_mode=ParseMode.HTML)
    name = ctx.args[0].lower()
    note = await db.get_note(chat.id, name)
    if not note:
        return await update.message.reply_text(f"❌ Заметка <b>#{name}</b> не найдена.", parse_mode=ParseMode.HTML)
    await update.message.reply_text(
        f"📝 <b>#{name}</b>\n\n{note['text']}",
        parse_mode=ParseMode.HTML
    )


async def cmd_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    notes = await db.get_all_notes(chat.id)
    if not notes:
        return await update.message.reply_text("📭 Заметок нет.", parse_mode=ParseMode.HTML)
    text = "📝 <b>ЗАМЕТКИ ЧАТА</b>\n\n"
    for n in notes:
        text += f"• <code>#{n['name']}</code> — {n['text'][:40]}{'...' if len(n['text'])>40 else ''}\n"
    text += "\n💡 Получить: <code>/get название</code>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_clear_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text("❌ /clearnote <название>", parse_mode=ParseMode.HTML)
    name = ctx.args[0].lower()
    deleted = await db.delete_note(chat.id, name)
    if deleted:
        await msg.reply_text(f"🗑 Заметка <b>#{name}</b> удалена.", parse_mode=ParseMode.HTML)
    else:
        await msg.reply_text(f"❌ Заметка <b>#{name}</b> не найдена.", parse_mode=ParseMode.HTML)


async def handle_hashtag_notes(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Получение заметки через #название"""
    msg  = update.message
    chat = update.effective_chat
    if not msg or not msg.text:
        return
    match = re.search(r"#(\w+)", msg.text)
    if match:
        name = match.group(1).lower()
        note = await db.get_note(chat.id, name)
        if note:
            await msg.reply_text(f"📝 <b>#{name}</b>\n\n{note['text']}", parse_mode=ParseMode.HTML)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#               📜 ПРАВИЛА
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_rules(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    settings = await db.get_group_settings(chat.id)
    rules_text = settings.get("rules", "")
    if not rules_text:
        rules_text = (
            "1️⃣ Уважай участников\n"
            "2️⃣ Без флуда и спама\n"
            "3️⃣ Без оскорблений\n"
            "4️⃣ Без рекламы\n"
            "5️⃣ Только по теме\n"
            "6️⃣ Без 18+ контента"
        )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Принимаю", callback_data="accept_rules")]])
    await update.message.reply_text(
        f"📜 <b>ПРАВИЛА — {chat.title}</b>\n\n{rules_text}",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )


async def cmd_setrules(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text("❌ /setrules <текст правил>", parse_mode=ParseMode.HTML)
    rules = " ".join(ctx.args)
    await db.update_group_setting(chat.id, "rules", rules)
    await msg.reply_text("✅ <b>Правила обновлены!</b>", parse_mode=ParseMode.HTML)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#               👋 ПРИВЕТСТВИЕ / ПРОЩАНИЕ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_setwelcome(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text(
            "❌ /setwelcome <текст>\n\n"
            "Переменные:\n{name} — имя\n{username} — @username\n{chat} — название чата\n{id} — ID",
            parse_mode=ParseMode.HTML
        )
    text = " ".join(ctx.args)
    await db.update_group_setting(chat.id, "welcome_text", text)
    await msg.reply_text(f"✅ <b>Приветствие установлено:</b>\n\n{text}", parse_mode=ParseMode.HTML)


async def cmd_setgoodbye(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text("❌ /setgoodbye <текст>", parse_mode=ParseMode.HTML)
    text = " ".join(ctx.args)
    await db.update_group_setting(chat.id, "goodbye_text", text)
    await msg.reply_text(f"✅ <b>Прощание установлено!</b>", parse_mode=ParseMode.HTML)


async def on_member_join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    settings = await db.get_group_settings(chat.id)
    if not settings.get("welcome_enabled", True):
        return

    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        await db.register_user(member.id, member.username or "", member.full_name or "")
        await db.log_event(chat.id, chat.title, member.id, "join", "")

        welcome = settings.get("welcome_text", "👋 Добро пожаловать в {chat}, {name}!")
        welcome = welcome.replace("{name}", member.full_name or "Пользователь")
        welcome = welcome.replace("{username}", f"@{member.username}" if member.username else member.full_name or "")
        welcome = welcome.replace("{chat}", chat.title or "")
        welcome = welcome.replace("{id}", str(member.id))

        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("📜 Правила",   callback_data="show_rules_join"),
            InlineKeyboardButton("👤 Профиль",   callback_data=f"uinfo_{member.id}_{chat.id}"),
        ]])
        await update.message.reply_text(
            f"{welcome}\n\n🆔 ID: <code>{member.id}</code>",
            reply_markup=kb, parse_mode=ParseMode.HTML
        )


async def on_member_left(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    member = update.message.left_chat_member
    if not member or member.is_bot:
        return
    settings = await db.get_group_settings(chat.id)
    if not settings.get("goodbye_enabled", True):
        return
    await db.log_event(chat.id, chat.title, member.id, "leave", "")
    goodbye = settings.get("goodbye_text", "👋 {name} покинул(а) чат.")
    goodbye = goodbye.replace("{name}", member.full_name or "Пользователь")
    goodbye = goodbye.replace("{username}", f"@{member.username}" if member.username else "")
    await update.message.reply_text(goodbye, parse_mode=ParseMode.HTML)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#               🔒 ФИЛЬТРЫ И НАСТРОЙКИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if chat.type == "private":
        return await msg.reply_text("⚙️ Используй в группе!", parse_mode=ParseMode.HTML)
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    settings = await db.get_group_settings(chat.id)
    await msg.reply_text(
        f"⚙️ <b>НАСТРОЙКИ — {chat.title}</b>",
        reply_markup=await build_settings_kb(chat.id, settings),
        parse_mode=ParseMode.HTML
    )


async def build_settings_kb(chat_id, settings) -> InlineKeyboardMarkup:
    def tog(key, default=True): return "✅" if settings.get(key, default) else "❌"
    kb = [
        [InlineKeyboardButton(f"{tog('welcome_enabled')} Приветствие",    callback_data=f"stog_welcome_enabled_{chat_id}"),
         InlineKeyboardButton(f"{tog('goodbye_enabled')} Прощание",       callback_data=f"stog_goodbye_enabled_{chat_id}")],
        [InlineKeyboardButton(f"{tog('antiflood')} Антифлуд",             callback_data=f"stog_antiflood_{chat_id}"),
         InlineKeyboardButton(f"{tog('antilinks')} Антиссылки",           callback_data=f"stog_antilinks_{chat_id}")],
        [InlineKeyboardButton(f"{tog('badwords')} Фильтр слов",           callback_data=f"stog_badwords_{chat_id}"),
         InlineKeyboardButton(f"{tog('antispam_enabled')} Анти-спам",     callback_data=f"stog_antispam_enabled_{chat_id}")],
        [InlineKeyboardButton(f"{tog('log_actions')} Лог действий",       callback_data=f"stog_log_actions_{chat_id}"),
         InlineKeyboardButton(f"{tog('antibot', False)} Антибот",         callback_data=f"stog_antibot_{chat_id}")],
        [InlineKeyboardButton("📝 Макс. варнов",                           callback_data=f"set_maxwarns_{chat_id}"),
         InlineKeyboardButton("🔄 Обновить",                               callback_data=f"refresh_settings_{chat_id}")],
        [InlineKeyboardButton("❌ Закрыть",                                callback_data="close")],
    ]
    return InlineKeyboardMarkup(kb)


async def cmd_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Добавить фильтр слова/фразы"""
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if len(ctx.args) < 2:
        return await msg.reply_text("❌ /filter <слово> <ответ>", parse_mode=ParseMode.HTML)
    keyword = ctx.args[0].lower()
    response = " ".join(ctx.args[1:])
    await db.add_filter(chat.id, keyword, response, user.id)
    await msg.reply_text(f"✅ Фильтр <b>«{keyword}»</b> добавлен!", parse_mode=ParseMode.HTML)


async def cmd_filters(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    fltrs = await db.get_filters(chat.id)
    if not fltrs:
        return await update.message.reply_text("🔒 Фильтров нет.", parse_mode=ParseMode.HTML)
    text = "🔒 <b>ФИЛЬТРЫ ЧАТА</b>\n\n"
    for f in fltrs:
        text += f"• <code>{f['keyword']}</code> → {f['response'][:30]}...\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_stop_filter(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text("❌ /stopfilter <слово>", parse_mode=ParseMode.HTML)
    keyword = ctx.args[0].lower()
    deleted = await db.delete_filter(chat.id, keyword)
    if deleted:
        await msg.reply_text(f"🗑 Фильтр <b>«{keyword}»</b> удалён.", parse_mode=ParseMode.HTML)
    else:
        await msg.reply_text(f"❌ Фильтр <b>«{keyword}»</b> не найден.", parse_mode=ParseMode.HTML)


async def cmd_addword(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Добавить запрещённое слово"""
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text("❌ /addword <слово>", parse_mode=ParseMode.HTML)
    word = ctx.args[0].lower()
    await db.add_bad_word(chat.id, word, user.id)
    await msg.reply_text(f"✅ Слово <b>«{word}»</b> добавлено в чёрный список.", parse_mode=ParseMode.HTML)


async def cmd_rmword(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not ctx.args:
        return await msg.reply_text("❌ /rmword <слово>", parse_mode=ParseMode.HTML)
    word = ctx.args[0].lower()
    await db.remove_bad_word(chat.id, word)
    await msg.reply_text(f"✅ Слово <b>«{word}»</b> удалено из чёрного списка.", parse_mode=ParseMode.HTML)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#               📊 ИНФОРМАЦИЯ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_info_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    chat = update.effective_chat
    target = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user
    warns = await db.get_warn_count(chat.id, target.id)
    actions = await db.get_user_actions(chat.id, target.id, limit=5)

    try:
        member = await ctx.bot.get_chat_member(chat.id, target.id)
        status_map = {
            "creator": "👑 Создатель", "administrator": "⚙️ Администратор",
            "member": "👤 Участник",    "restricted": "🔒 Ограничен",
            "left": "🚪 Покинул",       "kicked": "🔨 Забанен",
        }
        status = status_map.get(member.status, member.status)
    except Exception:
        status = "❓ Неизвестно"

    settings = await db.get_group_settings(chat.id)
    max_warns = settings.get("max_warns", SPAM_BAN_AFTER)

    recent = ""
    if actions:
        recent = "\n\n📋 <b>Последние действия:</b>\n"
        for a in actions[:3]:
            recent += f"• {a['action_type']} — {a['created_at'][:16]}\n"

    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚠️ Варн",         callback_data=f"quick_warn_{target.id}_{chat.id}"),
        InlineKeyboardButton("🔇 Мьют",          callback_data=f"quick_mute_{target.id}_{chat.id}"),
        InlineKeyboardButton("🔨 Бан",           callback_data=f"quick_ban_{target.id}_{chat.id}"),
    ]])
    await msg.reply_text(
        f"👤 <b>ИНФОРМАЦИЯ</b>\n\n"
        f"🆔 ID: <code>{target.id}</code>\n"
        f"📛 Имя: {mention(target)}\n"
        f"🔖 @{target.username or '—'}\n"
        f"📊 Статус: {status}\n"
        f"⚠️ Варнов: <b>{warns}/{max_warns}</b>\n"
        f"👑 Владелец бота: {'✅' if is_bot_owner(target.id) else '❌'}"
        f"{recent}",
        reply_markup=kb, parse_mode=ParseMode.HTML
    )


async def cmd_warns_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    chat = update.effective_chat
    target = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user
    warns = await db.get_warns_list(chat.id, target.id)
    settings = await db.get_group_settings(chat.id)
    max_warns = settings.get("max_warns", SPAM_BAN_AFTER)

    if not warns:
        return await msg.reply_text(f"✅ У {mention(target)} нет предупреждений.", parse_mode=ParseMode.HTML)

    text = f"⚠️ <b>ВАРНЫ</b> — {mention(target)} ({len(warns)}/{max_warns})\n\n"
    for i, w in enumerate(warns, 1):
        text += f"{i}. <i>{w['reason']}</i> — {w['created_at'][:16]}\n"
    await msg.reply_text(text, parse_mode=ParseMode.HTML)


async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    global_stats = await db.get_global_stats()
    await update.message.reply_text(
        "📊 <b>СТАТИСТИКА БОТА</b>\n\n"
        f"👥 Групп: <b>{global_stats.get('groups',0)}</b>\n"
        f"👤 Пользователей: <b>{global_stats.get('users',0)}</b>\n"
        f"🔨 Банов: <b>{global_stats.get('bans',0)}</b>\n"
        f"🔇 Мьютов: <b>{global_stats.get('mutes',0)}</b>\n"
        f"⚠️ Варнов: <b>{global_stats.get('warns',0)}</b>\n"
        f"🚫 Спама: <b>{global_stats.get('spam',0)}</b>\n\n"
        f"🕐 {ts()}",
        parse_mode=ParseMode.HTML
    )


async def cmd_chatinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        return await update.message.reply_text("❌ Только для групп!", parse_mode=ParseMode.HTML)
    try:
        count = await ctx.bot.get_chat_member_count(chat.id)
    except Exception:
        count = "?"
    await update.message.reply_text(
        f"💬 <b>ЧАТ</b>\n\n"
        f"📛 {chat.title}\n"
        f"🆔 <code>{chat.id}</code>\n"
        f"👥 Участников: <b>{count}</b>\n"
        f"🔗 @{chat.username or '—'}\n"
        f"📋 Тип: <b>{chat.type}</b>",
        parse_mode=ParseMode.HTML
    )


async def cmd_admins(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type == "private":
        return await update.message.reply_text("❌ Только для групп!", parse_mode=ParseMode.HTML)
    try:
        admins = await ctx.bot.get_chat_administrators(chat.id)
        lines = [f"👮 <b>АДМИНИСТРАТОРЫ — {chat.title}</b>\n"]
        for a in admins:
            u = a.user
            role = "🤖" if u.is_bot else ("👑" if a.status == "creator" else "⚙️")
            lines.append(f"{role} {mention(u)}")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}", parse_mode=ParseMode.HTML)


async def cmd_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    chat = update.effective_chat
    target = msg.reply_to_message.from_user if msg.reply_to_message else update.effective_user
    await msg.reply_text(
        f"🆔 Пользователь: <code>{target.id}</code>\n💬 Чат: <code>{chat.id}</code>",
        parse_mode=ParseMode.HTML
    )


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = time.time()
    m = await update.message.reply_text("🏓 Пинг...")
    await m.edit_text(f"🏓 Понг! <b>{int((time.time()-t)*1000)}ms</b>", parse_mode=ParseMode.HTML)


async def cmd_pin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    if not msg.reply_to_message:
        return await msg.reply_text("❌ Ответь на сообщение!", parse_mode=ParseMode.HTML)
    try:
        await ctx.bot.pin_chat_message(chat.id, msg.reply_to_message.message_id, disable_notification=False)
        await msg.reply_text(f"📌 Закреплено — {mention(user)}", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: {e}", parse_mode=ParseMode.HTML)


async def cmd_unpin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    try:
        await ctx.bot.unpin_all_chat_messages(chat.id)
        await msg.reply_text("📌 Все закреплённые сняты.", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: {e}", parse_mode=ParseMode.HTML)


async def cmd_invitelink(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat, user, msg = update.effective_chat, update.effective_user, update.message
    if not await is_admin(chat.id, user.id, ctx.bot):
        return await msg.reply_text("🚫 Только для администраторов!", parse_mode=ParseMode.HTML)
    try:
        link = await ctx.bot.export_chat_invite_link(chat.id)
        await msg.reply_text(f"🔗 <b>Ссылка:</b>\n{link}", parse_mode=ParseMode.HTML)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: {e}", parse_mode=ParseMode.HTML)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                 🚨 АНТИ-СПАМ ЗАЯВКИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def cmd_antispam(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user, msg = update.effective_user, update.message
    if update.effective_chat.type != "private":
        return await msg.reply_text(
            "🚨 Команда работает только в <b>личных сообщениях</b> с ботом!",
            parse_mode=ParseMode.HTML
        )
    reason = " ".join(ctx.args) if ctx.args else "Причина не указана"
    req_id = await db.create_antispam_request(user.id, user.username or "", user.full_name or "", reason)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Одобрить",      callback_data=f"as_approve_{req_id}"),
         InlineKeyboardButton("❌ Отказать",       callback_data=f"as_deny_{req_id}")],
        [InlineKeyboardButton("📋 Детали",         callback_data=f"as_info_{req_id}")],
    ])
    notif = (
        f"🚨 <b>АНТИ-СПАМ ЗАЯВКА #{req_id}</b>\n\n"
        f"👤 {mention(user)}\n"
        f"🆔 <code>{user.id}</code>\n"
        f"📝 <i>{reason}</i>\n"
        f"🕐 {ts()}"
    )
    for oid in BOT_OWNER_IDS:
        try:
            await ctx.bot.send_message(oid, notif, reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            pass
    await msg.reply_text(
        "📨 <b>Заявка #{} отправлена!</b>\n\nОжидай ответа администраторов.\n⏳ Обычно до 24 часов.".format(req_id),
        parse_mode=ParseMode.HTML
    )


async def cmd_antispam_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_bot_owner(update.effective_user.id):
        return await update.message.reply_text("🚫 Только для владельцев бота!", parse_mode=ParseMode.HTML)
    reqs = await db.get_antispam_requests()
    if not reqs:
        return await update.message.reply_text("📭 Заявок нет.", parse_mode=ParseMode.HTML)
    text = "📋 <b>АНТИ-СПАМ ЗАЯВКИ</b>\n\n"
    for r in reqs[:10]:
        status_icon = {"pending": "⏳", "approved": "✅", "denied": "❌"}.get(r["status"], "❓")
        text += f"{status_icon} <b>#{r['id']}</b> — {r['full_name']} (@{r['username'] or '—'})\n"
        text += f"   📝 {r['reason'][:50]}\n"
        text += f"   🕐 {r['created_at'][:16]}\n\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#               🛡 АВТО-МОДЕРАЦИЯ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def auto_moderate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg  = update.message
    if not msg or not msg.text:
        return
    chat, user = update.effective_chat, update.effective_user
    if not user or chat.type == "private":
        return
    if await is_admin(chat.id, user.id, ctx.bot):
        return

    settings = await db.get_group_settings(chat.id)
    text = msg.text

    await db.inc_global_stat("messages")

    # Проверка фильтров (ответы на ключевые слова)
    filters_list = await db.get_filters(chat.id)
    for f in filters_list:
        if f["keyword"].lower() in text.lower():
            await msg.reply_text(f["response"], parse_mode=ParseMode.HTML)
            break

    # Антифлуд
    if settings.get("antiflood", True):
        now   = time.time()
        times = spam_tracker[user.id]
        times = [t for t in times if now - t < SPAM_TIME_WINDOW]
        times.append(now)
        spam_tracker[user.id] = times
        if len(times) >= SPAM_MSG_LIMIT:
            try:
                await msg.delete()
            except Exception:
                pass
            spam_tracker[user.id] = []
            await db.inc_global_stat("spam")
            await _auto_action(chat, user, ctx, "Флуд", settings)
            return

    # Антиссылки
    if settings.get("antilinks", True):
        url_pat = re.compile(r"(https?://|www\.|t\.me/+\S)", re.IGNORECASE)
        if url_pat.search(text):
            allowed = ["t.me/joinchat", "t.me/+"]
            if not any(a in text for a in allowed):
                try:
                    await msg.delete()
                except Exception:
                    pass
                await db.inc_global_stat("spam")
                await _auto_action(chat, user, ctx, "Запрещённая ссылка", settings)
                return

    # Фильтр плохих слов
    if settings.get("badwords", True):
        bad_words = await db.get_bad_words(chat.id)
        lower = text.lower()
        for bw in bad_words:
            if bw in lower:
                try:
                    await msg.delete()
                except Exception:
                    pass
                await db.inc_global_stat("spam")
                await _auto_action(chat, user, ctx, "Запрещённое слово", settings)
                return


async def _auto_action(chat, user, ctx, reason: str, settings: dict):
    """Автоматическое наказание"""
    max_warns = settings.get("max_warns", SPAM_BAN_AFTER)
    count = await db.add_warn(chat.id, user.id, 0, f"[АВТО] {reason}")
    await db.log_event(chat.id, chat.title, user.id, "auto_warn", reason)

    if count >= max_warns:
        action = settings.get("warn_action", "ban")
        await db.clear_warns(chat.id, user.id)
        if action == "mute":
            until = datetime.now() + timedelta(minutes=DEFAULT_MUTE_MINS)
            try:
                await ctx.bot.restrict_chat_member(chat.id, user.id, ChatPermissions(can_send_messages=False), until_date=until)
            except Exception:
                pass
            result = f"🔇 Автомьют на {DEFAULT_MUTE_MINS} мин."
            await db.inc_global_stat("mutes")
        else:
            try:
                await ctx.bot.ban_chat_member(chat.id, user.id)
            except Exception:
                pass
            result = "🔨 Автобан"
            await db.inc_global_stat("bans")

        sent = await ctx.bot.send_message(
            chat.id,
            f"{result}\n👤 {mention(user)}\n📝 {reason}\n\n"
            "💬 Ошибка? Напиши боту в личку: /antispam",
            parse_mode=ParseMode.HTML
        )
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔓 Разбанить", callback_data=f"unban_{user.id}_{chat.id}")]])
        for oid in BOT_OWNER_IDS:
            try:
                await ctx.bot.send_message(
                    oid,
                    f"🤖 <b>Авто-наказание</b>\n👤 {mention(user)}\n💬 {chat.title}\n📝 {reason}",
                    reply_markup=kb, parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
    else:
        remaining = max_warns - count
        w = await ctx.bot.send_message(
            chat.id,
            f"⚠️ {mention(user)} — авто-варн ({count}/{max_warns})\n📝 {reason}\n⚡ До наказания: {remaining}",
            parse_mode=ParseMode.HTML
        )
        await db.inc_global_stat("warns")
        await asyncio.sleep(8)
        try:
            await w.delete()
        except Exception:
            pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                   🎛 CALLBACK КНОПКИ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

HELP_TEXTS = {
    "help_mod": (
        "⚔️ <b>МОДЕРАЦИЯ</b>\n\n"
        "/ban — Бан (ответ/ID)\n"
        "/unban <id> — Разбан\n"
        "/tban <время> — Временный бан (1d/2h/30m)\n"
        "/mute [время] — Мьют\n"
        "/unmute — Размьют\n"
        "/warn [причина] — Предупреждение\n"
        "/unwarn — Снять варн\n"
        "/resetwarns — Сбросить все варны\n"
        "/kick — Кикнуть\n"
        "/ro [мин] — Только чтение\n"
        "/del — Удалить сообщение\n"
        "/purge — Очистить с ответа"
    ),
    "help_settings": (
        "⚙️ <b>НАСТРОЙКИ</b>\n\n"
        "/settings — Открыть настройки чата\n"
        "/setrules <текст> — Установить правила\n"
        "/setwelcome <текст> — Приветствие\n"
        "/setgoodbye <текст> — Прощание\n"
        "/addword <слово> — Добавить в чёрный список\n"
        "/rmword <слово> — Убрать из чёрного списка\n\n"
        "Переменные: {name} {username} {chat} {id}"
    ),
    "help_filters": (
        "🔒 <b>ФИЛЬТРЫ</b>\n\n"
        "/filter <слово> <ответ> — Добавить фильтр\n"
        "/filters — Список фильтров\n"
        "/stopfilter <слово> — Удалить фильтр\n\n"
        "Фильтр срабатывает когда слово встречается в сообщении."
    ),
    "help_notes": (
        "📝 <b>ЗАМЕТКИ</b>\n\n"
        "/save <название> <текст> — Сохранить заметку\n"
        "/get <название> — Получить заметку\n"
        "/notes — Список всех заметок\n"
        "/clearnote <название> — Удалить заметку\n\n"
        "Также работает через <code>#название</code>"
    ),
    "help_welcome": (
        "👋 <b>ПРИВЕТСТВИЕ / ПРОЩАНИЕ</b>\n\n"
        "/setwelcome <текст> — Задать приветствие\n"
        "/setgoodbye <текст> — Задать прощание\n\n"
        "Переменные:\n"
        "{name} — Имя\n{username} — @username\n{chat} — Чат\n{id} — ID\n\n"
        "В /settings можно вкл/выкл"
    ),
    "help_info": (
        "📊 <b>ИНФОРМАЦИЯ</b>\n\n"
        "/info — Инфо о пользователе (ответ)\n"
        "/warns — Список варнов\n"
        "/stats — Глобальная статистика\n"
        "/chatinfo — Информация о чате\n"
        "/admins — Список администраторов\n"
        "/id — ID пользователя/чата\n"
        "/ping — Проверить бота\n"
        "/invitelink — Ссылка приглашения\n"
        "/rules — Правила чата"
    ),
    "help_antispam": (
        "🚨 <b>АНТИ-СПАМ</b>\n\n"
        "<b>Система работает так:</b>\n"
        "1️⃣ Бот авто-банит за спам/флуд\n"
        "2️⃣ Юзер пишет боту в <b>личку</b>\n"
        "3️⃣ Команда: <code>/antispam причина</code>\n"
        "4️⃣ Владельцы получают заявку с кнопками\n"
        "5️⃣ ✅ Разбанить или ❌ Отказать\n\n"
        "/antispam_list — Список заявок\n"
        "/stats — Статистика бота"
    ),
}


async def callback_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data  = query.data
    user  = query.from_user
    await query.answer()

    # ЗАКРЫТЬ
    if data == "close":
        try:
            await query.message.delete()
        except Exception:
            pass
        return

    # ПРАВИЛА (из приветствия)
    if data in ("show_rules_join", "accept_rules"):
        await query.answer("✅ Добро пожаловать!", show_alert=True)
        return

    # ПОМОЩЬ
    if data in HELP_TEXTS:
        back_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("◀️ Назад", callback_data="help_main"),
            InlineKeyboardButton("❌ Закрыть", callback_data="close"),
        ]])
        try:
            await query.message.edit_text(HELP_TEXTS[data], reply_markup=back_kb, parse_mode=ParseMode.HTML)
        except Exception:
            await ctx.bot.send_message(user.id, HELP_TEXTS[data], reply_markup=back_kb, parse_mode=ParseMode.HTML)
        return

    if data == "help_main":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Модерация",    callback_data="help_mod"),
             InlineKeyboardButton("⚙️ Настройки",    callback_data="help_settings")],
            [InlineKeyboardButton("🔒 Фильтры",       callback_data="help_filters"),
             InlineKeyboardButton("📝 Заметки",       callback_data="help_notes")],
            [InlineKeyboardButton("👋 Приветствие",   callback_data="help_welcome"),
             InlineKeyboardButton("📊 Инфо",          callback_data="help_info")],
            [InlineKeyboardButton("🚨 Анти-Спам",     callback_data="help_antispam"),
             InlineKeyboardButton("❌ Закрыть",        callback_data="close")],
        ])
        try:
            await query.message.edit_text("📖 <b>ПОМОЩЬ — выбери категорию:</b>", reply_markup=kb, parse_mode=ParseMode.HTML)
        except Exception:
            pass
        return

    # МОИ ГРУППЫ
    if data == "my_groups":
        # Показываем группы где юзер является создателем
        await query.answer("🔄 Загружаю...", show_alert=False)
        try:
            await query.message.edit_text(
                "💬 <b>МОИ ГРУППЫ</b>\n\nДобавь бота в группу и он появится здесь.\n"
                "Управляй настройками через /settings в группе.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_start")]]),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        return

    if data == "bot_stats":
        s = await db.get_global_stats()
        try:
            await query.message.edit_text(
                "📊 <b>СТАТИСТИКА</b>\n\n"
                f"👥 Групп: <b>{s.get('groups',0)}</b>\n"
                f"👤 Пользователей: <b>{s.get('users',0)}</b>\n"
                f"🔨 Банов: <b>{s.get('bans',0)}</b>\n"
                f"⚠️ Варнов: <b>{s.get('warns',0)}</b>\n"
                f"🚫 Спама: <b>{s.get('spam',0)}</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_start")]]),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        return

    if data == "about_bot":
        bot_info = await ctx.bot.get_me()
        try:
            await query.message.edit_text(
                f"ℹ️ <b>О БОТЕ</b>\n\n"
                f"🤖 Имя: <b>{bot_info.first_name}</b>\n"
                f"🔖 @{bot_info.username}\n"
                f"🆔 <code>{bot_info.id}</code>\n\n"
                "🛡 Полный менеджер групп\n"
                "✅ Бесплатный для всех групп\n"
                "🔥 Работает 24/7",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="back_start")]]),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        return

    if data == "back_start":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Добавить в группу", url=f"https://t.me/{(await ctx.bot.get_me()).username}?startgroup=true")],
            [InlineKeyboardButton("📋 Команды",    callback_data="help_main"),
             InlineKeyboardButton("⚙️ Мои группы", callback_data="my_groups")],
            [InlineKeyboardButton("📊 Статистика", callback_data="bot_stats"),
             InlineKeyboardButton("ℹ️ О боте",     callback_data="about_bot")],
        ])
        try:
            await query.message.edit_text(
                f"👋 Привет!\n\n🛡 <b>GroupHelp Bot</b> — мощный менеджер групп!\n\nВыбери раздел:",
                reply_markup=kb, parse_mode=ParseMode.HTML
            )
        except Exception:
            pass
        return

    # НАСТРОЙКИ ЧАТА — ПЕРЕКЛЮЧАТЕЛИ
    if data.startswith("stog_"):
        parts   = data.split("_")
        # stog_<key>_<chat_id> — key может содержать _
        chat_id = int(parts[-1])
        setting = "_".join(parts[1:-1])
        if not await is_admin(chat_id, user.id, ctx.bot) and not is_bot_owner(user.id):
            await query.answer("🚫 Только администраторы!", show_alert=True)
            return
        settings = await db.get_group_settings(chat_id)
        current  = settings.get(setting, True)
        await db.update_group_setting(chat_id, setting, not current)
        settings = await db.get_group_settings(chat_id)
        try:
            await query.message.edit_reply_markup(reply_markup=await build_settings_kb(chat_id, settings))
        except Exception:
            pass
        await query.answer(f"{'✅ Включено' if not current else '❌ Выключено'}", show_alert=False)
        return

    if data.startswith("refresh_settings_"):
        chat_id = int(data.split("_")[-1])
        settings = await db.get_group_settings(chat_id)
        try:
            await query.message.edit_reply_markup(reply_markup=await build_settings_kb(chat_id, settings))
        except Exception:
            pass
        return

    if data.startswith("set_maxwarns_"):
        chat_id = int(data.split("_")[-1])
        if not await is_admin(chat_id, user.id, ctx.bot) and not is_bot_owner(user.id):
            await query.answer("🚫 Только администраторы!", show_alert=True)
            return
        settings = await db.get_group_settings(chat_id)
        current  = settings.get("max_warns", SPAM_BAN_AFTER)
        options  = [2, 3, 4, 5, 10]
        nxt = options[(options.index(current) + 1) % len(options)] if current in options else 3
        await db.update_group_setting(chat_id, "max_warns", nxt)
        await query.answer(f"⚠️ Макс. варнов: {nxt}", show_alert=True)
        settings = await db.get_group_settings(chat_id)
        try:
            await query.message.edit_reply_markup(reply_markup=await build_settings_kb(chat_id, settings))
        except Exception:
            pass
        return

    # БЫСТРЫЕ ДЕЙСТВИЯ
    if data.startswith("quick_"):
        parts  = data.split("_")
        action = parts[1]
        tid    = int(parts[2])
        cid    = int(parts[3])
        if not await is_admin(cid, user.id, ctx.bot) and not is_bot_owner(user.id):
            await query.answer("🚫 Только администраторы!", show_alert=True)
            return
        if action == "ban":
            await ctx.bot.ban_chat_member(cid, tid)
            await db.inc_global_stat("bans")
            await query.answer("🔨 Забанен!", show_alert=True)
        elif action == "mute":
            until = datetime.now() + timedelta(minutes=DEFAULT_MUTE_MINS)
            await ctx.bot.restrict_chat_member(cid, tid, ChatPermissions(can_send_messages=False), until_date=until)
            await db.inc_global_stat("mutes")
            await query.answer(f"🔇 Замьючен на {DEFAULT_MUTE_MINS} мин!", show_alert=True)
        elif action == "warn":
            settings = await db.get_group_settings(cid)
            max_warns = settings.get("max_warns", SPAM_BAN_AFTER)
            count = await db.add_warn(cid, tid, user.id, "Быстрое действие")
            await db.inc_global_stat("warns")
            await query.answer(f"⚠️ Варн! {count}/{max_warns}", show_alert=True)
        return

    # РАЗБАН
    if data.startswith("unban_"):
        parts = data.split("_")
        tid, cid = int(parts[1]), int(parts[2])
        if not is_bot_owner(user.id) and not await is_admin(cid, user.id, ctx.bot):
            await query.answer("🚫 Только администраторы!", show_alert=True)
            return
        try:
            await ctx.bot.unban_chat_member(cid, tid)
            await query.message.edit_text(
                query.message.text_html + f"\n\n✅ <b>Разбанен</b> — {mention(user)}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await query.answer(f"❌ {e}", show_alert=True)
        return

    # РАЗМЬЮТ
    if data.startswith("unmute_"):
        parts = data.split("_")
        tid, cid = int(parts[1]), int(parts[2])
        try:
            await ctx.bot.restrict_chat_member(
                cid, tid,
                ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                can_send_other_messages=True, can_add_web_page_previews=True)
            )
            await query.message.edit_text(
                query.message.text_html + f"\n\n✅ <b>Размьючен</b> — {mention(user)}",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            await query.answer(f"❌ {e}", show_alert=True)
        return

    # СНЯТЬ ВАРН
    if data.startswith("unwarn_"):
        parts = data.split("_")
        tid, cid = int(parts[1]), int(parts[2])
        if not await is_admin(cid, user.id, ctx.bot) and not is_bot_owner(user.id):
            await query.answer("🚫 Только администраторы!", show_alert=True)
            return
        count = await db.remove_warn(cid, tid)
        await query.answer(f"✅ Варн снят! Осталось: {count}", show_alert=True)
        return

    # СПИСОК ВАРНОВ
    if data.startswith("warnlist_"):
        parts = data.split("_")
        tid, cid = int(parts[1]), int(parts[2])
        warns = await db.get_warns_list(cid, tid)
        if not warns:
            await query.answer("✅ Варнов нет!", show_alert=True)
        else:
            text = f"⚠️ Варны (ID {tid}):\n" + "\n".join(f"{i+1}. {w['reason']}" for i, w in enumerate(warns[:5]))
            await query.answer(text[:200], show_alert=True)
        return

    # ИНФО О ПОЛЬЗОВАТЕЛЕ
    if data.startswith("uinfo_"):
        parts = data.split("_")
        tid, cid = int(parts[1]), int(parts[2])
        warns = await db.get_warn_count(cid, tid)
        settings = await db.get_group_settings(cid)
        max_warns = settings.get("max_warns", SPAM_BAN_AFTER)
        try:
            member = await ctx.bot.get_chat_member(cid, tid)
            status = member.status
        except Exception:
            status = "unknown"
        await query.answer(
            f"🆔 ID: {tid}\n📊 Статус: {status}\n⚠️ Варны: {warns}/{max_warns}",
            show_alert=True
        )
        return

    # АНТИ-СПАМ ЗАЯВКИ
    if data.startswith("as_approve_"):
        if not is_bot_owner(user.id):
            await query.answer("🚫 Только для владельцев бота!", show_alert=True)
            return
        req_id = int(data.split("_")[2])
        req = await db.get_antispam_request(req_id)
        if req:
            await db.update_antispam_status(req_id, "approved")
            await db.inc_global_stat("antispam_granted")
            try:
                await query.message.edit_text(
                    query.message.text_html + f"\n\n✅ <b>ОДОБРЕНО</b> — {mention(user)}",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
            try:
                await ctx.bot.send_message(
                    req["user_id"],
                    "🎉 <b>Заявка одобрена!</b>\nТы можешь вернуться в чат. Больше не нарушай! 🙏",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
        return

    if data.startswith("as_deny_"):
        if not is_bot_owner(user.id):
            await query.answer("🚫 Только для владельцев бота!", show_alert=True)
            return
        req_id = int(data.split("_")[2])
        req = await db.get_antispam_request(req_id)
        if req:
            await db.update_antispam_status(req_id, "denied")
            try:
                await query.message.edit_text(
                    query.message.text_html + f"\n\n❌ <b>ОТКАЗАНО</b> — {mention(user)}",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
            try:
                await ctx.bot.send_message(
                    req["user_id"],
                    "❌ <b>Заявка отклонена.</b>\nАдминистраторы отказали в разбане.",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
        return

    if data.startswith("as_info_"):
        req_id = int(data.split("_")[2])
        req    = await db.get_antispam_request(req_id)
        if req:
            await query.answer(
                f"#{req_id}\nID: {req['user_id']}\nПричина: {req['reason'][:100]}\nВремя: {req['created_at'][:16]}",
                show_alert=True
            )
        return

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#                      🚀 ЗАПУСК
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def post_init(app: Application):
    """Инициализация базы данных и команд"""
    await db.init_db()
    commands = [
        BotCommand("start",        "🏠 Главное меню"),
        BotCommand("help",         "📖 Помощь"),
        BotCommand("ban",          "🔨 Забанить"),
        BotCommand("unban",        "🔓 Разбанить"),
        BotCommand("mute",         "🔇 Замьютить"),
        BotCommand("unmute",       "🔊 Размьютить"),
        BotCommand("warn",         "⚠️ Варн"),
        BotCommand("unwarn",       "🗑 Снять варн"),
        BotCommand("kick",         "👢 Кикнуть"),
        BotCommand("info",         "👤 Инфо о пользователе"),
        BotCommand("warns",        "📊 Список варнов"),
        BotCommand("rules",        "📜 Правила"),
        BotCommand("notes",        "📝 Заметки"),
        BotCommand("settings",     "⚙️ Настройки чата"),
        BotCommand("stats",        "📊 Статистика"),
        BotCommand("admins",       "👮 Администраторы"),
        BotCommand("pin",          "📌 Закрепить"),
        BotCommand("antispam",     "🚨 Анти-спам заявка"),
    ]
    await app.bot.set_my_commands(commands)
    logger.info("✅ Бот инициализирован!")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    COMMANDS = [
        ("start",          cmd_start),
        ("help",           cmd_help),
        ("ban",            cmd_ban),
        ("unban",          cmd_unban),
        ("mute",           cmd_mute),
        ("unmute",         cmd_unmute),
        ("warn",           cmd_warn),
        ("unwarn",         cmd_unwarn),
        ("resetwarns",     cmd_resetwarns),
        ("kick",           cmd_kick),
        ("tban",           cmd_tban),
        ("ro",             cmd_ro),
        ("purge",          cmd_purge),
        ("del",            cmd_del),
        ("save",           cmd_save),
        ("get",            cmd_get),
        ("notes",          cmd_notes),
        ("clearnote",      cmd_clear_note),
        ("rules",          cmd_rules),
        ("setrules",       cmd_setrules),
        ("setwelcome",     cmd_setwelcome),
        ("setgoodbye",     cmd_setgoodbye),
        ("filter",         cmd_filter),
        ("filters",        cmd_filters),
        ("stopfilter",     cmd_stop_filter),
        ("addword",        cmd_addword),
        ("rmword",         cmd_rmword),
        ("info",           cmd_info_user),
        ("warns",          cmd_warns_list),
        ("stats",          cmd_stats),
        ("chatinfo",       cmd_chatinfo),
        ("admins",         cmd_admins),
        ("id",             cmd_id),
        ("ping",           cmd_ping),
        ("pin",            cmd_pin),
        ("unpin",          cmd_unpin),
        ("invitelink",     cmd_invitelink),
        ("antispam",       cmd_antispam),
        ("antispam_list",  cmd_antispam_list),
    ]

    for cmd, func in COMMANDS:
        app.add_handler(CommandHandler(cmd, func))

    app.add_handler(CallbackQueryHandler(callback_handler))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
        auto_moderate
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"#\w+"),
        handle_hashtag_notes
    ))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_member_join))
    app.add_handler(MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_member_left))

    logger.info("🔥 GroupHelp Bot запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
