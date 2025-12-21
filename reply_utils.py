from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import re

def clean_markdown(text):
    """Clean text for Markdown parsing"""
    if not text:
        return text
    
    # Remove problematic characters for Markdown
    text = re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)
    
    # Ensure proper line breaks
    text = text.replace('\n\n', '\n').replace('\n', '\n')
    
    return text

def escape_markdown(text):
    """Escape special Markdown characters"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text

def format_operator_message(user_name, user_id, chat_id, question, request_id, pending_count):
    """Format message for operator with proper Markdown"""
    safe_question = escape_markdown(question)[:1000]  # Limit length
    safe_user_name = escape_markdown(user_name)
    
    message = (
        f"🔔 *ՆՈՐ ՀԱՐՑ օգտատիրոջից*\n\n"
        f"👤 *Օգտատեր:* {safe_user_name}\n"
        f"🆔 User ID: {user_id}\n"
        f"💬 Chat ID: {chat_id}\n"
        f"📅 Ժամանակ: HH:MM:SS\n\n"
        f"❓ *ՀԱՐՃ:*\n"
        f"{safe_question}\n\n"
        f"📋 *ՊԱՏԱՍԽԱՆԵԼՈՒ ՀԱՄԱՐ:*\n"
        f"`/reply {chat_id} {request_id} Ձեր պատասխանը`\n\n"
        f"📊 *ՍՊԱՍՈՂ ՀԱՐՑԵՐ:* {pending_count}"
    )
    
    return clean_markdown(message)

def format_user_confirmation(question, request_id, pending_count):
    """Format confirmation message for user"""
    safe_question = escape_markdown(question)[:500]
    
    message = (
        f"✅ *ՀԱՐՑԸ ՈՒՂԱՐԿՎԵՑ*\n\n"
        f"📝 *Ձեր հարցը:*\n"
        f"{safe_question}\n\n"
        f"🆔 *Հարցի ID:* {request_id[-6:]}\n"
        f"⏰ *Պատասխանի սպասվող ժամանակ:* 5-15 րոպե\n"
        f"📊 *Հերթական համար:* {pending_count}\n\n"
        f"👨‍💼 *Օպերատորը կպատասխանի հնարավորինս շուտ:*\n\n"
        f"💡 *Մինչ պատասխանը կարող եք:*\n"
        f"• Սեղմել «📋 Թեմաներ»\n"
        f"• Կամ սպասել այստեղ"
    )
    
    return clean_markdown(message)

def format_operator_reply(message, request_id):
    """Format operator's reply to user"""
    safe_message = escape_markdown(message)[:2000]
    short_id = request_id[-6:] if request_id and len(request_id) > 6 else request_id
    
    reply_text = (
        f"👨‍💼 *ՕՊԵՐԱՏՈՐԻՑ ՊԱՏԱՍԽԱՆ*\n\n"
        f"💬 *Պատասխան:*\n"
        f"{safe_message}\n\n"
        f"🆔 *Հարցի ID:* {short_id}\n"
        f"⏰ *Պատասխանի ժամանակ:* HH:MM:SS\n\n"
        f"📞 *Հետագա հարցերի համար:*\n"
        f"Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    return clean_markdown(reply_text)

def get_simple_keyboard():
    """Get simplified keyboard"""
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    
    buttons = [
        [KeyboardButton("🏠 Գլխավոր մենյու"), KeyboardButton("💬 Հարց տալ օպերատորին")],
        [KeyboardButton("📊 Իմ հարցերը"), KeyboardButton("❓ Օգնություն")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_main_keyboard():
    """Get main keyboard"""
    from telegram import KeyboardButton, ReplyKeyboardMarkup
    
    buttons = [
        [KeyboardButton("📋 Թեմաներ"), KeyboardButton("❓ Օգնություն")],
        [KeyboardButton("💰 Ֆինանսներ"), KeyboardButton("📞 Կապ")],
        [KeyboardButton("👨‍💼 Կապ օպերատորի հետ"), KeyboardButton("💬 Հարց տալ օպերատորին")],
        [KeyboardButton("📊 Իմ հարցերը"), KeyboardButton("ℹ️ Օգնություն")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)
