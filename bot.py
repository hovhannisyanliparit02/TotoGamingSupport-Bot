from config import TELEGRAM_TOKEN, OPERATOR_CHAT_ID
from rules_data import RULES
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    CallbackContext  
)
from matcher import normalize
from matcher import find_answer
from logger import setup_logger
import logging
import json
import os
from datetime import datetime, timedelta
import random

# ------------------------------
# Setup Logger
# ------------------------------
setup_logger()
logger = logging.getLogger(__name__)

# Files for data management
USER_REQUESTS_FILE = "user_requests.json"
USER_CONVERSATIONS_FILE = "user_conversations.json"
USER_STATS_FILE = "user_stats.json"

# ------------------------------
# Data Management Functions
# ------------------------------

def load_json_file(filename, default={}):
    """Load JSON file"""
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return default
    return default

def save_json_file(filename, data):
    """Save JSON file"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")
        return False

def load_user_requests():
    """Load user requests from file"""
    return load_json_file(USER_REQUESTS_FILE)

def save_user_requests(requests):
    """Save user requests to file"""
    return save_json_file(USER_REQUESTS_FILE, requests)

def load_user_conversations():
    """Load user conversations from file"""
    return load_json_file(USER_CONVERSATIONS_FILE)

def save_user_conversations(conversations):
    """Save user conversations to file"""
    return save_json_file(USER_CONVERSATIONS_FILE, conversations)

def load_user_stats():
    """Load user statistics"""
    return load_json_file(USER_STATS_FILE)

def save_user_stats(stats):
    """Save user statistics"""
    return save_json_file(USER_STATS_FILE, stats)

def update_user_stats(user_chat_id, action):
    """Update user statistics"""
    stats = load_user_stats()
    user_id = str(user_chat_id)
    
    if user_id not in stats:
        stats[user_id] = {
            "questions_sent": 0,
            "questions_answered": 0,
            "first_seen": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topics_asked": []
        }
    
    stats[user_id]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if action == "question_sent":
        stats[user_id]["questions_sent"] = stats[user_id].get("questions_sent", 0) + 1
    elif action == "question_answered":
        stats[user_id]["questions_answered"] = stats[user_id].get("questions_answered", 0) + 1
    
    save_user_stats(stats)
    return stats[user_id]

def add_user_request(user_chat_id, user_name, user_message=""):
    """Add user to active requests"""
    requests = load_user_requests()
    request_id = f"{user_chat_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    requests[request_id] = {
        "user_id": user_chat_id,
        "user_name": user_name,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "pending",
        "message": user_message,
        "answered_by": None,
        "answer_time": None,
        "message_id": None
    }
    
    save_user_requests(requests)
    update_user_stats(user_chat_id, "question_sent")
    return request_id

def update_user_request(request_id, **kwargs):
    """Update user request"""
    requests = load_user_requests()
    
    if request_id in requests:
        requests[request_id].update(kwargs)
        if kwargs.get("status") == "answered":
            update_user_stats(requests[request_id]["user_id"], "question_answered")
        save_user_requests(requests)
        return True
    return False

def get_user_requests(user_chat_id=None, status=None):
    """Get user requests with filters"""
    requests = load_user_requests()
    
    if user_chat_id:
        requests = {k: v for k, v in requests.items() if v["user_id"] == user_chat_id}
    
    if status:
        requests = {k: v for k, v in requests.items() if v["status"] == status}
    
    return requests

def get_pending_requests_count():
    """Count pending requests"""
    requests = load_user_requests()
    return sum(1 for r in requests.values() if r["status"] == "pending")

def add_to_conversation(user_chat_id, role, message, request_id=None):
    """Add message to conversation history"""
    conversations = load_user_conversations()
    user_id = str(user_chat_id)
    
    if user_id not in conversations:
        conversations[user_id] = []
    
    conversations[user_id].append({
        "role": role,  # "user" or "operator"
        "message": message,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "request_id": request_id
    })
    
    # Keep only last 50 messages
    if len(conversations[user_id]) > 50:
        conversations[user_id] = conversations[user_id][-50:]
    
    save_user_conversations(conversations)
    return True

def get_conversation_history(user_chat_id, limit=10):
    """Get conversation history for a user"""
    conversations = load_user_conversations()
    user_conversations = conversations.get(str(user_chat_id), [])
    return user_conversations[-limit:] if limit else user_conversations

# ------------------------------
# Helper Functions
# ------------------------------

def escape_markdown(text: str) -> str:
    """Escape Markdown special characters"""
    escape_chars = r'\_*[]()~`>#+-=|{}.!'
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


def get_random_wait_message():
    """Get random waiting message"""
    messages = [
        "⏳ Պատրաստվում է...",
        "📡 Ուղարկվում է օպերատորին...",
        "🤔 Վերլուծվում է ձեր հարցը...",
        "💭 Մշակվում է...",
        "🚀 Ուղարկվում է..."
    ]
    return random.choice(messages)

def get_random_confirmation_message():
    """Get random confirmation message"""
    messages = [
        "✅ Հիանալի է! Ձեր հարցը ուղարկվել է օպերատորին։",
        "📬 Շնորհակալություն! Ձեր հարցն ընդունվել է։",
        "👍 Հարցը հաջողությամբ ուղարկված է։",
        "🎯 Ձեր հարցը հասել է օպերատորին։",
        "💫 Հիանալի հարց! Մենք այն ուղարկել ենք օպերատորին։"
    ]
    return random.choice(messages)

def get_random_wait_time_estimate():
    """Get random wait time estimate"""
    times = [
        "Մոտավոր պատասխանի սպասվող ժամանակ՝ 5-10 րոպե",
        "Օպերատորը կպատասխանի 15 րոպեի ընթացքում",
        "Սպասեք պատասխանի՝ մինչև 20 րոպե",
        "Պատասխան կստանաք հաջորդ 10 րոպեի ընթացքում",
        "Օպերատորը պատասխանելու է 5-15 րոպեում"
    ]
    return random.choice(times)

def get_suggestion_for_question(question):
    """Get suggestions to improve the question"""
    suggestions = []
    
    question_lower = question.lower()
    
    if len(question) < 10:
        suggestions.append("Խնդրում եմ գրեք ավելի մանրամասն հարց։")
    
    if "?" not in question:
        suggestions.append("Խնդրում եմ հարցում ավելացրեք հարցական նշան (?)։")
    
    if len(question.split()) < 3:
        suggestions.append("Փորձեք ձեր հարցն ավելի հստակ ձևակերպել։")
    
    # Common topics suggestions
    if any(word in question_lower for word in ["գումար", "դրամ", "փող", "դեպոզիտ", "հանել"]):
        suggestions.append("Ֆինանսական հարցերի համար կարող եք նաև սեղմել «💰 Ֆինանսներ» կոճակը։")
    
    if any(word in question_lower for word in ["կանոն", "կանոններ", "պայման", "պայմաններ"]):
        suggestions.append("Կանոնների մասին կարող եք սեղմել «📋 Թեմաներ» կոճակը։")
    
    if any(word in question_lower for word in ["հասցե", "հեռախոս", "էլեկտրոնային"]):
        suggestions.append("Կապի տվյալների համար կարող եք սեղմել «📞 Կապ» կոճակը։")
    
    return suggestions

# ------------------------------
# Keyboard Functions
# ------------------------------

def get_main_keyboard():
    """Get main keyboard"""
    MAIN_MENU_BUTTONS = [
        [KeyboardButton("📋 Թեմաներ"), KeyboardButton("❓ Օգնություն")],
        [KeyboardButton("💰 Ֆինանսներ"), KeyboardButton("📞 Կապ")],
        [KeyboardButton("💬 Հարց տալ օպերատորին")],
        [KeyboardButton("📊 Իմ հարցերը"), KeyboardButton("ℹ️ Օգնություն")]
    ]
    return ReplyKeyboardMarkup(MAIN_MENU_BUTTONS, resize_keyboard=True)

def get_simple_keyboard():
    """Get simplified keyboard"""
    buttons = [
        [KeyboardButton("🏠 Գլխավոր մենյու"), KeyboardButton("💬 Հարց տալ օպերատորին")],
        [KeyboardButton("📊 Իմ հարցերը"), KeyboardButton("❓ Օգնություն")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

TOPICS_LIST = [
        ("Ընկերության մասին", "companyinfo"),
        ("Տարիքի սահմանափակում", "agerequirement"),
        ("Խաղադրույքի տեսակներ", "bettypes"),
        ("Խաղ․ սահմանափակումներ", "betlimits"),
        ("Վճարային մեթոդներ", "paymentmethods"),
        ("Խաղ․ ընդունման կարգ", "betacceptance"),
        ("Ավտոմատ խաղադրույք", "autobet"),
        ("Բեթ Բիլդեր", "betbuilder"),
        ("Արագ խաղադրույք", "quickbet"),
        ("Արդյունքների աղբյուրներ", "resultsources"),
        ("Առավելագույն շահում", "maxwin"),
        ("Տոմսի փոփոխություն", "chequeredact"),
        ("Համակարգային խաղադրույք", "systembet"),
        ("Էքսպրեսի գեներացիա", "expressgeneration"),
        ("Քեշաութ", "cashout"),
    ]

def get_topics_keyboard():
    """Get inline keyboard for topics"""
    
    
    keyboard = []
    for i in range(0, len(TOPICS_LIST), 2):
        row = []
        for j in range(2):
            if i + j < len(TOPICS_LIST):
                topic_name, topic_id = TOPICS_LIST[i + j]
                row.append(InlineKeyboardButton(topic_name, callback_data=f"topic_{topic_id}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🔙 Գլխավոր մենյու", callback_data="main_menu")])
    return InlineKeyboardMarkup(keyboard)

def get_help_keyboard():
    """Get inline keyboard for help"""
    keyboard = [
        [InlineKeyboardButton("📋 Թեմաներ", callback_data="topics"),
         InlineKeyboardButton("💰 Ֆինանսներ", callback_data="help_finance")],
        [InlineKeyboardButton("📞 Կապ", callback_data="help_contact"),
         InlineKeyboardButton("👨‍💼 Օպերատոր", callback_data="help_operator")],
        [InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_help_back_keyboard():
    """Get keyboard for returning from help sections"""
    keyboard = [
        [InlineKeyboardButton("🔙 Օգնություն", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_topic_back_keyboard():
    """Get keyboard for returning from topic view"""
    keyboard = [
        [InlineKeyboardButton("🔙 Թեմաներ", callback_data="topics")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_operator_keyboard():
    """Get keyboard for operator contact"""
    keyboard = [
        [InlineKeyboardButton("✅ Ուղարկել հարցը օպերատորին", callback_data="operator_confirm")],
        [InlineKeyboardButton("✏️ Նորից գրել հարցը", callback_data="rewrite_question")],
        [InlineKeyboardButton("🔙 Օգնություն", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_question_confirmation_keyboard():
    """Get keyboard for question confirmation"""
    keyboard = [
        [InlineKeyboardButton("✅ Այո, ուղարկել", callback_data="send_question")],
        [InlineKeyboardButton("✏️ Փոփոխել հարցը", callback_data="change_question")],
        [InlineKeyboardButton("❌ Չեղարկել", callback_data="cancel_question")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_main_keyboard():
    """Get keyboard to go back to main menu"""
    keyboard = [
        [InlineKeyboardButton("🏠 Գլխավոր մենյու", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_finance_keyboard():
    """Get keyboard for finance section"""
    keyboard = [
        [InlineKeyboardButton("💰 Դեպոզիտ", callback_data="finance_deposit"),
         InlineKeyboardButton("💳 Քարտեր", callback_data="finance_cards")],
        [InlineKeyboardButton("🏦 Դուրսբերում", callback_data="finance_withdraw"),
         InlineKeyboardButton("🔙 Օգնություն", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_contact_keyboard():
    """Get keyboard for contact section"""
    keyboard = [
        [InlineKeyboardButton("📍 Հասցե", callback_data="contact_address"),
         InlineKeyboardButton("🌐 Կայք", callback_data="contact_website")],
        [InlineKeyboardButton("📧 Էլ․ փոստ", callback_data="contact_email"),
         InlineKeyboardButton("👨‍💼 Օպերատոր", callback_data="help_operator")],
        [InlineKeyboardButton("🔙 Օգնություն", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ------------------------------
# Command Handlers
# ------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Update user stats
    update_user_stats(chat.id, "question_sent")
    
    welcome_text = (
        f"🎉 *Բարի գալուստ, {user.first_name}!*\n\n"
        f"Ես TotoGaming-ի օգնող բոտն եմ 🤖\n\n"
        
        "✨ *Ինչ կարող եմ անել.*\n"
        "• Պատասխանել կանոնների մասին հարցերին\n"
        "• Կապ հաստատել օպերատորի հետ\n"
        "• Օգնել ֆինանսական հարցերում\n"
        "• Ցույց տալ կապի տվյալները\n\n"
        
        "🚀 *Արագ հրամաններ.*\n"
        "`/help` - Օգնություն\n"
        "`/ask` - Հարց տալ օպերատորին\n"
        "`/myquestions` - Իմ հարցերը\n"
        "`/topics` - Թեմաների ցանկ\n\n"
        
        "Սեղմեք կոճակները կամ գրեք ձեր հարցը 👇"
    )
    
    if update.message:
        await update.message.reply_text(welcome_text, parse_mode='Markdown', reply_markup=get_main_keyboard())
        
        # Send helpful tip after 2 seconds
        async def send_tip():
            await context.bot.send_message(
                chat_id=chat.id,
                text="💡 *Հուշում.* Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը արագ օգնության համար։",
                parse_mode='Markdown'
            )
        
        # Schedule tip
        import asyncio
        asyncio.create_task(send_tip())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    help_text = (
        "🆘 *Օգնության կենտրոն*\n\n"
        
        "📋 *Ինչպես օգտվել բոտից.*\n"
        "1. Սեղմեք կոճակները ստորև\n"
        "2. Գրեք ձեր հարցը հայերեն\n"
        "3. Օգտագործեք հրամանները\n\n"
        
        "🚀 *Արագ հրամաններ.*\n"
        "• `/ask` - Հարց տալ օպերատորին\n"
        "• `/myquestions` - Իմ հարցերը\n"
        "• `/topics` - Թեմաների ցանկ\n"
        "• `/finance` - Ֆինանսական հարցեր\n"
        "• `/contact` - Կապի տվյալներ\n\n"
        
        "⏱️ *Աշխատանքային ժամեր.*\n"
        "• Օպերատոր՝ 09:00-20:00\n"
        "• Բոտ՝ 24/7\n\n"
        
        "Ընտրեք հետաքրքրող թեման 👇"
    )
    
    if update.message:
        await update.message.reply_text(help_text, 
                                       parse_mode='Markdown',
                                       reply_markup=get_help_keyboard())

async def topics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /topics command."""
    topics_text = (
        "📚 *Թեմաների ցանկ*\n\n"
        "Ընտրեք թեման՝ տեղեկություն ստանալու համար։\n\n"
        "*Հուշում.* Եթե չեք գտնում ձեր թեման, օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    await update.message.reply_text(topics_text, parse_mode='Markdown', reply_markup=get_topics_keyboard())

async def finance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /finance command."""
    finance_text = (
        "💰 *Ֆինանսական գործարքներ*\n\n"
        "✅ **Ինչպես դեպոզիտ անել գումար**\n"
        "• ՏոտոԳեյմինգ քարտեր\n"
        "• Բանկային քարտեր\n"
        "• Էլեկտրոնային դրամապանակներ\n\n"
        "✅ **Ինչպես դուրս հանել գումար**\n"
        "• Բանկային փոխանցում\n"
        "• Էլեկտրոնային համակարգեր\n\n"
        "📞 *Ավելի մանրամասն տեղեկության համար.*\n"
        "Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    if update.message:
        await update.message.reply_text(finance_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /contact command."""
    contact_text = (
        "📞 *Կապի տվյալներ*\n\n"
        "📍 **Հասցե**\n"
        "Երևան, Ծովակալ Իսակովի պողոտա 15/3\n\n"
        "🌐 **Կայք**\n"
        "sport.totogaming.am\n\n"
        "⏰ **Աշխատանքային ժամեր**\n"
        "• Երկուշաբթի-Ուրբաթ՝ 09:00-18:00\n"
        "• Շաբաթ՝ 10:00-16:00\n\n"
        "💬 *Անհետաձգելի հարցերի համար.*\n"
        "Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    if update.message:
        await update.message.reply_text(contact_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def ask_operator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle direct question to operator."""
    user = update.effective_user
    
    if context.args:
        # If user sends /ask <question>
        question = " ".join(context.args)
        await send_direct_question(update, context, user, question)
    else:
        # Show instructions for asking questions
        ask_text = (
            "💬 *Հարց տալ օպերատորին*\n\n"
            "Գրեք ձեր հարցը ստորև, և ես այն կուղարկեմ մեր օպերատորին։\n\n"
            "🎯 *Օրինակներ լավ հարցերի.*\n"
            "• «Ինչպե՞ս կարող եմ փոխել իմ գաղտնաբառը»\n"
            "• «Ինչու չի աշխատում դեպոզիտի համակարգը»\n"
            "• «Ինչպե՞ս կարող եմ ստանալ բոնուս»\n\n"
            "📝 *Հուշում.* Որքան մանրամասն գրեք, այնքան արագ կստանաք պատասխան։\n\n"
            "Գրեք ձեր հարցը հիմա 👇"
        )
        
        # Set state for awaiting question
        context.user_data['awaiting_question'] = True
        
        if update.message:
            await update.message.reply_text(
                ask_text,
                parse_mode='Markdown',
                reply_markup=ReplyKeyboardMarkup(
                    [[KeyboardButton("Չեղարկել")]],
                    resize_keyboard=True
                )
            )

async def send_direct_question(update: Update, context: ContextTypes.DEFAULT_TYPE, user, question):
    """Send direct question to operator"""
    chat = update.effective_chat
    
    # First, send a waiting message
    waiting_msg = await update.message.reply_text(
        f"{get_random_wait_message()}\n\n"
        f"*Ձեր հարցը.* {question[:50]}...",
        parse_mode='Markdown'
    )
    
    if not OPERATOR_CHAT_ID:
        await waiting_msg.edit_text(
            "⚠️ *Օպերատորը այժմ անհասանելի է*\n\n"
            "Կարող եք փորձել ավելի ուշ կամ օգտագործել բոտի այլ հնարավորությունները։",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        return
    
    try:
        # Generate request ID
        request_id = add_user_request(chat.id, user.full_name, question)
        pending_count = get_pending_requests_count()
        
        # Send notification to operator
        escaped_question = escape_markdown(question)
        operator_message = (
            f"🔔 *ՆՈՐ ՀԱՐՑ օգտատիրոջից*\n\n"
            f"👤 *Օգտատեր.* {escape_markdown(user.full_name)}\n"
            f"🆔 User ID: `{user.id}`\n"
            f"💬 Chat ID: `{chat.id}`\n"
            f"📅 Ժամանակ: `{datetime.now().strftime('%H:%M:%S')}`\n\n"
            f"❓ *ՀԱՐՑ.*\n"
            f"{escaped_question}\n\n"
            f"📋 *ՊԱՏԱՍԽԱՆԵԼՈՒ ՀԱՄԱՐ.*\n"
            f"`/reply {chat.id} {request_id} Ձեր պատասխանը`\n\n"
            f"📊 *ՍՊԱՍՈՂ ՀԱՐՑԵՐ.* {pending_count}\n"
            f"⏰ *ՇՏԱՊ ՊԱՏԱՍԽԱՆԵԼ ՄԻՆՉԵՎ.* 15 րոպե"
        )
        
        await context.bot.send_message(
            chat_id=OPERATOR_CHAT_ID,
            text=operator_message,
            parse_mode='Markdown'
        )
        
        # Add to conversation history
        add_to_conversation(chat.id, "user", question, request_id)
        
        # Update waiting message with confirmation
        confirmation_text = (
            f"{get_random_confirmation_message()}\n\n"
            f"📝 *Ձեր հարցը.*\n"
            f"{question}\n\n"
            f"🆔 *Հարցի ID.* {request_id[-6:]}\n"
            f"⏰ *Պատասխանի սպասվող ժամանակ.* 5-15 րոպե\n"
            f"📊 *Ձեր հարցի հերթական համարը.* {pending_count}\n\n"
            f"👨‍💼 *Օպերատորը կպատասխանի հնարավորինս շուտ։*\n\n"
            f"📋 *Հարցիդ կարգավիճակը կարող ես տեսնել.*\n"
            f"«📊 Իմ հարցերը» կոճակով կամ `/myquestions` հրամանով։"
        )
        
        await waiting_msg.edit_text(
            confirmation_text,
            parse_mode='Markdown',
            reply_markup=get_simple_keyboard()
        )
        
        logger.info(f"✅ Direct question sent from user {user.id}: {question[:50]}...")
        
        # Send follow-up message after 30 seconds
        async def send_follow_up():
            await asyncio.sleep(30)
            try:
                await context.bot.send_message(
                    chat_id=chat.id,
                    text="💡 *Հուշում.* Մինչ օպերատորը պատասխանում է, կարող եք սեղմել «📋 Թեմաներ»՝ տեղեկություն ստանալու համար։",
                    parse_mode='Markdown',
                    reply_markup=get_simple_keyboard()
                )
            except Exception as e:
                logger.error(f"Error sending follow-up: {e}")
        
        import asyncio
        asyncio.create_task(send_follow_up())
        
    except Exception as e:
        logger.error(f"❌ Failed to send direct question: {e}")
        
        error_text = (
            "❌ *Ու՞՛փս, տեխնիկական խնդիր*\n\n"
            "Չհաջողվեց ուղարկել հարցը օպերատորին։\n\n"
            "🔧 *Ինչ անել.*\n"
            "1. Սպասեք 1 րոպե և կրկին փորձեք\n"
            "2. Գրեք ավելի կարճ հարց\n"
            "3. Օգտագործեք այլ կապի միջոցներ\n\n"
            "Ներողություն անհարմարության համար 🙏"
        )
        
        await waiting_msg.edit_text(
            error_text,
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

async def my_questions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's recent questions and answers."""
    user_chat_id = update.effective_chat.id
    user_requests = get_user_requests(user_chat_id)
    
    if not user_requests:
        await update.message.reply_text(
            "📭 *Դեռ հարցեր չունեք*\n\n"
            "Դեռ չեք ուղարկել հարցեր օպերատորին։\n\n"
            "🎯 *Որտեղից սկսել.*\n"
            "• Սեղմեք «💬 Հարց տալ օպերատորին»\n"
            "• Կամ օգտագործեք `/ask ձեր հարցը`\n\n"
            "Օպերատորը պատրաստ է օգնել ձեզ 💪",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        return
    
    # Sort requests by time (newest first)
    sorted_requests = sorted(
        user_requests.values(),
        key=lambda x: x["time"],
        reverse=True
    )[:10]  # Show last 10
    
    messages_text = "📊 *Ձեր հարցերը*\n\n"
    
    for i, req in enumerate(sorted_requests, 1):
        status_icon = "✅" if req["status"] == "answered" else "⏳"
        status_text = "Պատասխանված" if req["status"] == "answered" else "Սպասվում է"
        short_id = req["time"].split()[1] if "time" in req else "N/A"
        
        messages_text += f"{i}. {status_icon} *{status_text}*\n"
        messages_text += f"   🕒 {req.get('time', 'N/A')}\n"
        messages_text += f"   📝 {req['message'][:80]}{'...' if len(req['message']) > 80 else ''}\n"
        
        if req["status"] == "answered" and req.get("answered_by"):
            messages_text += f"   👨‍💼 Պատասխանել է՝ {req['answered_by']}\n"
            messages_text += f"   ⏰ {req.get('answer_time', '')}\n"
        
        messages_text += "\n"
    
    # Add statistics
    total = len(user_requests)
    answered = sum(1 for r in user_requests.values() if r["status"] == "answered")
    pending = total - answered
    
    messages_text += f"📈 *Վիճակագրություն.*\n"
    messages_text += f"• Ընդհանուր հարցեր՝ {total}\n"
    messages_text += f"• Պատասխանված՝ {answered}\n"
    messages_text += f"• Սպասվող՝ {pending}\n\n"
    
    if pending > 0:
        avg_wait_time = "10-15 րոպե"
        messages_text += f"⏰ *Միջին սպասման ժամանակ.* {avg_wait_time}\n\n"
    
    messages_text += "💡 *Հուշում.* Օպերատորը պատասխանում է ըստ հերթականության։"
    
    await update.message.reply_text(
        messages_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

async def commands_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands command."""
    commands_text = (
        "📋 *Բոտի հրամանների ցանկ*\n\n"
        
        "🚀 *ԱՐԱԳ ՀՐԱՄԱՆՆԵՐ.*\n"
        "`/start` - Բոտի մեկնարկ\n"
        "`/ask` - Հարց տալ օպերատորին\n"
        "`/myquestions` - Իմ հարցերը\n"
        "`/help` - Օգնություն\n\n"
        
        "📚 *ԹԵՄԱՆԵՐ.*\n"
        "`/topics` - Թեմաների ցանկ\n"
        "`/finance` - Ֆինանսներ\n"
        "`/contact` - Կապ\n\n"
        
        "👨‍💼 *ՕՊԵՐԱՏՈՐ.*\n"
        "`/operator` - 💬 Հարց տալ օպերատորին\n"
        
        "ℹ️ *ԻՄ ՏՎՅԱԼՆԵՐ.*\n"
        "`/stats` - Իմ վիճակագրությունը\n"
        "`/commands` - Այս ցանկը"
    )
    
    if update.message:
        await update.message.reply_text(commands_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def user_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics."""
    user_chat_id = update.effective_chat.id
    user = update.effective_user
    
    stats = load_user_stats().get(str(user_chat_id), {})
    
    if not stats:
        stats_text = (
            f"📊 *Ողջույն, {user.first_name}!*\n\n"
            f"Դուք դեռ չեք օգտվել մեր ծառայություններից։\n\n"
            f"🎯 *Սկսելու համար.*\n"
            f"• Սեղմեք «💬 Հարց տալ օպերատորին»\n"
            f"• Կամ սեղմեք «📋 Թեմաներ»\n\n"
            f"Մենք այստեղ ենք՝ օգնելու ձեզ 💪"
        )
    else:
        questions_sent = stats.get("questions_sent", 0)
        questions_answered = stats.get("questions_answered", 0)
        first_seen = stats.get("first_seen", "N/A")
        
        stats_text = (
            f"📊 *Ձեր վիճակագրությունը, {user.first_name}*\n\n"
            
            f"📈 *Ընդհանուր.*\n"
            f"• Ուղարկված հարցեր՝ {questions_sent}\n"
            f"• Պատասխանված հարցեր՝ {questions_answered}\n"
            f"• Պատասխանման տոկոս՝ {int((questions_answered/questions_sent)*100) if questions_sent > 0 else 0}%\n\n"
            
            f"⏰ *Պատմություն.*\n"
            f"• Առաջին այց՝ {first_seen}\n"
            f"• Վերջին ակտիվություն՝ {stats.get('last_active', 'N/A')}\n\n"
            
            f"🏆 *Ձեր ակտիվությունը.*\n"
        )
        
        if questions_sent >= 10:
            stats_text += "🔝 Դուք ակտիվ օգտատեր եք!\n"
        elif questions_sent >= 5:
            stats_text += "👍 Լավ ակտիվություն!\n"
        elif questions_sent > 0:
            stats_text += "👋 Շնորհակալություն մեզ հետ լինելու համար!\n"
        
        stats_text += "\n💡 *Հուշում.* Որքան շատ հարցաքննեք, այնքան արագ կստանաք պատասխաններ։"
    
    await update.message.reply_text(
        stats_text,
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

async def about(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /about command."""
    total_users = len(load_user_stats())
    total_questions = sum(stats.get("questions_sent", 0) for stats in load_user_stats().values())
    
    about_text = (
        "🤖 *TotoGaming Օգնող Բոտ*\n\n"
        
        "📊 *Ընդհանուր վիճակագրություն.*\n"
        f"• Օգտատերեր՝ {total_users}\n"
        f"• Հարցեր՝ {total_questions}\n"
        f"• Պատասխանված՝ {sum(stats.get('questions_answered', 0) for stats in load_user_stats().values())}\n\n"
        
        "⚙️ *Տեխնիկական տվյալներ.*\n"
        "• Վերսիա 3.0\n"
        "• Հայերեն լեզու\n"
        "• 24/7 աշխատանք\n"
        "• AI-օգնությամբ\n\n"
        
        "🎯 *Մեր նպատակը.*\n"
        "Օգնել ամեն օգտատիրոջ արագ և որակյալ պատասխան ստանալ։\n\n"
        
        "© TotoGaming 2024"
    )
    
    if update.message:
        await update.message.reply_text(about_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

# ------------------------------
# Callback Query Handler
# ------------------------------

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    logger.info(f"📱 Button pressed: {callback_data}")
    
    # Map callbacks to handlers
    handlers = {
        "help": help_callback,
        "help_contact": contact_callback,
        "help_finance": finance_callback,
        "help_operator": operator_help_callback,
        "topics": topics_callback,
        "operator_confirm": operator_confirm_callback,
        "send_question": send_question_callback,
        "change_question": change_question_callback,
        "cancel_question": cancel_question_callback,
        "rewrite_question": rewrite_question_callback,
        "main_menu": main_menu_callback,
        "finance_deposit": finance_deposit_callback,
        "finance_cards": finance_cards_callback,
        "finance_withdraw": finance_withdraw_callback,
        "contact_address": contact_address_callback,
        "contact_website": contact_website_callback,
        "contact_email": contact_email_callback,
    }
    
    if callback_data.startswith("topic_"):
        await handle_topic_callback(update, context, callback_data)
    elif callback_data in handlers:
        await handlers[callback_data](update, context)
    else:
        await query.message.reply_text("⚠️ Այս կոճակը դեռ չի աշխատում:", reply_markup=get_main_keyboard())

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle help callback from inline button."""
    query = update.callback_query
    help_text = (
        "🆘 *Օգնության կենտրոն*\n\n"
        "Ընտրեք հետաքրքրող թեման.\n"
        "Կամ գրեք ձեր հարցը հայերեն։"
    )
    await query.message.edit_text(help_text, parse_mode='Markdown', reply_markup=get_help_keyboard())

async def contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact callback."""
    query = update.callback_query
    await query.answer()
    
    contact_text = (
        "📞 *Կապի տվյալներ*\n\n"
        "Ընտրեք հետաքրքրող թեման.\n\n"
        "💡 *Հուշում.* Անհետաձգելի հարցերի համար օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    await query.message.edit_text(
        contact_text, 
        parse_mode='Markdown',
        reply_markup=get_contact_keyboard()
    )

async def finance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle finance callback."""
    query = update.callback_query
    await query.answer()
    
    finance_text = (
        "💰 *Ֆինանսական գործարքներ*\n\n"
        "Ընտրեք հետաքրքրող թեման.\n\n"
        "💡 *Հուշում.* Եթե ֆինանսական խնդիր ունեք, կարող եք ուղղակի օպերատորին հարց տալ «💬 Հարց տալ օպերատորին» կոճակով։"
    )
    
    await query.message.edit_text(
        finance_text, 
        parse_mode='Markdown',
        reply_markup=get_finance_keyboard()
    )

async def operator_help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle operator help callback."""
    query = update.callback_query
    await query.answer()
    
    operator_text = (
        "👨‍💼 *💬 Հարց տալ օպերատորին*\n\n"
        "Օպերատորը կարող է օգնել.\n"
        "• Անձնական հաշվի խնդիրներ\n"
        "• Տեխնիկական աջակցություն\n"
        "• Հատուկ հարցումներ\n"
        "• Այլ հարցեր\n\n"
        "⏰ *Պատասխանի սպասվող ժամանակ.*\n"
        "5-15 րոպե\n\n"
        "Կապի համար սեղմեք ստորև նշված կոճակը 👇"
    )
    
    await query.message.edit_text(operator_text, parse_mode='Markdown', reply_markup=get_operator_keyboard())

async def operator_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle operator contact confirmation."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    chat = update.effective_chat
    
    if not OPERATOR_CHAT_ID:
        error_text = "⚠️ *Օպերատորը այժմ անհասանելի է*\n\nՕպերատորի համակարգը կարգավորման փուլում է։"
        await query.message.edit_text(error_text, parse_mode='Markdown', reply_markup=get_help_back_keyboard())
        return
    
    # Ask for the question
    await query.message.edit_text(
        "💬 *Գրեք ձեր հարցը*\n\n"
        "Խնդրում եմ գրեք, թե ինչ հարց ունեք օպերատորից։\n\n"
        "*Օրինակ.*\n"
        "«Ինչպե՞ս կարող եմ փոխել իմ գաղտնաբառը»\n"
        "«Ինչու չի աշխատում դեպոզիտի համակարգը»\n\n"
        "Սպասում եմ ձեր հարցին...",
        parse_mode='Markdown'
    )
    
    # Store state
    context.user_data['awaiting_operator_question'] = True
    context.user_data['awaiting_chat_id'] = chat.id

async def send_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle send question confirmation."""
    query = update.callback_query
    await query.answer()
    
    if 'last_question' not in context.user_data:
        await query.message.edit_text(
            "❌ *Հարցը չի գտնվել*\n\nԽնդրում եմ նորից գրեք ձեր հարցը։",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        return
    
    question = context.user_data['last_question']
    user = update.effective_user
    
    # Send the question
    await send_direct_question_callback(query, context, user, question)

async def send_direct_question_callback(query, context, user, question):
    """Send direct question from callback"""
    chat = query.message.chat
    
    if not OPERATOR_CHAT_ID:
        await query.message.edit_text(
            "⚠️ *Օպերատորը այժմ անհասանելի է*\n\nՕպերատորի համակարգը կարգավորման փուլում է։",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )
        return
    
    # Show sending animation
    await query.message.edit_text(
        f"⏳ *Ուղարկվում է...*\n\n"
        f"Ձեր հարցը ուղարկվում է օպերատորին։",
        parse_mode='Markdown'
    )
    
    try:
        request_id = add_user_request(chat.id, user.full_name, question)
        pending_count = get_pending_requests_count()
        
        operator_message = (
            f"🔔 *ՆՈՐ ՀԱՐՑ օգտատիրոջից*\n\n"
            f"👤 *Օգտատեր.* {user.full_name}\n"
            f"🆔 User ID: {user.id}\n"
            f"💬 Chat ID: {chat.id}\n"
            f"📅 Ժամանակ: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"❓ *ՀԱՐՑ.*\n"
            f"{question}\n\n"
            f"📋 *ՊԱՏԱՍԽԱՆԵԼՈՒ ՀԱՄԱՐ.*\n"
            f"`/reply {chat.id} {request_id} Ձեր պատասխանը`\n\n"
            f"📊 *ՍՊԱՍՈՂ ՀԱՐՑԵՐ.* {pending_count}"
        )
        
        await context.bot.send_message(chat_id=OPERATOR_CHAT_ID, text=operator_message, parse_mode='Markdown')
        
        add_to_conversation(chat.id, "user", question, request_id)
        
        # Send success message
        success_text = (
            f"✅ *ՀԱՐՑԸ ՈՒՂԱՐԿՎԵՑ*\n\n"
            f"📝 *Ձեր հարցը.*\n"
            f"{question}\n\n"
            f"🆔 *Հարցի ID.* {request_id[-6:]}\n"
            f"⏰ *Պատասխանի սպասվող ժամանակ.* 5-15 րոպե\n"
            f"📊 *Հերթական համար.* {pending_count}\n\n"
            f"👨‍💼 *Օպերատորը կպատասխանի հնարավորինս շուտ։*\n\n"
            f"💡 *Մինչ պատասխանը կարող եք.*\n"
            f"• Սեղմել «📋 Թեմաներ»\n"
            f"• Կամ սպասել այստեղ"
        )
        
        await query.message.edit_text(success_text, parse_mode='Markdown', reply_markup=get_simple_keyboard())
        
        logger.info(f"✅ Direct question sent from user {user.id}: {question[:50]}...")
        
    except Exception as e:
        logger.error(f"❌ Failed to send direct question: {e}")
        error_text = "❌ *Տեղի ունեցավ սխալ*\n\nՉհաջողվեց ուղարկել հարցը օպերատորին։"
        await query.message.edit_text(error_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

async def change_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle change question request."""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "✏️ *Փոփոխել հարցը*\n\n"
        "Խնդրում եմ գրեք ձեր նոր հարցը ստորև։\n\n"
        "🎯 *Օրինակ.*\n"
        "«Ինչպե՞ս կարող եմ փոխել իմ գաղտնաբառը»\n"
        "«Ինչու չի աշխատում դեպոզիտի համակարգը»",
        parse_mode='Markdown'
    )
    
    # Store state
    context.user_data['awaiting_question_change'] = True

async def cancel_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel question request."""
    query = update.callback_query
    await query.answer()
    
    # Clear stored question
    context.user_data.pop('last_question', None)
    
    await query.message.edit_text(
        "❌ *Հարցումը չեղարկված է*\n\n"
        "Դուք չեղարկեցիք հարցի ուղարկումը։\n\n"
        "🎯 *Ինչ կարող եք անել հիմա.*\n"
        "• Նորից փորձել «💬 Հարց տալ օպերատորին»\n"
        "• Սեղմել «📋 Թեմաներ»\n"
        "• Օգտագործել այլ հնարավորություններ",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

async def rewrite_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rewrite question request."""
    query = update.callback_query
    await query.answer()
    
    await query.message.edit_text(
        "✏️ *Նորից գրել հարցը*\n\n"
        "Խնդրում եմ գրեք ձեր հարցը նորից։\n\n"
        "💡 *Հուշում.* Փորձեք հարցը գրել ավելի մանրամասն։\n\n"
        "Սպասում եմ ձեր հարցին...",
        parse_mode='Markdown'
    )
    
    # Store state
    context.user_data['awaiting_question_rewrite'] = True

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle main menu callback."""
    query = update.callback_query
    await query.answer()
    
    welcome_back_text = (
        "🏠 *Գլխավոր մենյու*\n\n"
        "Ընտրեք հետաքրքրող հնարավորությունը.\n\n"
        "💡 *Արագ հուշում.*\n"
        "Օգտագործեք «💬 Հարց տալ օպերատորին» ամենաարագ օգնության համար։"
    )
    
    await query.message.edit_text(
        welcome_back_text,
        parse_mode='Markdown',
        reply_markup=get_help_keyboard()
    )

async def topics_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle topics callback."""
    query = update.callback_query
    await query.answer()
    topics_text = "📚 *Թեմաների ցանկ*\n\nԸնտրեք հետաքրքրող թեման։"
    await query.message.edit_text(topics_text, parse_mode='Markdown', reply_markup=get_topics_keyboard())

async def handle_topic_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, callback_data: str):
    """Handle topic callback."""
    query = update.callback_query
    await query.answer()
    topic_id = callback_data.split("_")[1]
    
    if topic_id in RULES:
        rule = RULES[topic_id]
        lang = "hy"
        if "answer" in rule and lang in rule["answer"]:
            response = rule["answer"][lang]
            
            # Add helpful footer
            response += "\n\n💡 *Ավելի մանրամասն տեղեկության համար.*\n"
            response += "Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
            
            await query.message.edit_text(response, parse_mode='Markdown', reply_markup=get_back_to_main_keyboard())
        else:
            response = f"📌 *Թեմա՝ {topic_id}*\n\nՏեղեկության կառուցվածքը սխալ է։"
            await query.message.edit_text(response, parse_mode='Markdown', reply_markup=get_back_to_main_keyboard())
    else:
        topic_name = "Անհայտ թեմա"
        for name, tid in TOPICS_LIST:
            if tid == topic_id:
                topic_name = name
                break
        response = f"📌 *Թեմա՝ {topic_name}*\n\nՏեղեկությունը դեռ հասանելի չէ կամ պատրաստվում է։"
        await query.message.edit_text(response, parse_mode='Markdown', reply_markup=get_back_to_main_keyboard())

async def finance_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle deposit callback."""
    query = update.callback_query
    await query.answer()
    
    deposit_text = (
        "💰 *Դեպոզիտի մեթոդներ*\n\n"
        "✅ **ՏոտոԳեյմինգ քարտեր**\n"
        "• Գնեք անվանական արժեքով քարտ\n"
        "• Մուտք գործեք sport.totogaming.am\n"
        "• Մուտքագրեք PIN կոդը\n"
        "• Գումարը կտեղափոխվի ձեր հաշվին\n\n"
        "✅ **Բանկային քարտեր**\n"
        "• Visa/MasterCard\n"
        "• Անմիջապես փոխանցում\n"
        "• Պահպանված քարտեր արագ մուտքի համար\n\n"
        "✅ **Էլեկտրոնային համակարգեր**\n"
        "• Տարբեր էլեկտրոնային դրամապանակներ\n"
        "• Արագ և անվտանգ գործարքներ\n\n"
        "💡 *Խնդիրների դեպքում.* Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Ֆինանսներ", callback_data="help_finance"),
         InlineKeyboardButton("💬 Հարց տալ", callback_data="help_operator")]
    ]
    
    await query.message.edit_text(
        deposit_text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def finance_cards_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cards callback."""
    query = update.callback_query
    await query.answer()
    
    cards_text = (
        "💳 *Քարտերի տեսակներ*\n\n"
        "✅ **ՏոտոԳեյմինգ քարտեր**\n"
        "• Տարբեր անվանական արժեքներով\n"
        "• Հասանելի են բուքմեյքերական կետերում\n"
        "• Անվտանգ և անանուն\n\n"
        "✅ **Բոնուսային քարտեր**\n"
        "• Լրացուցիչ բոնուսներով\n"
        "• Հատուկ ակցիաների համար\n"
        "• Խաղային հաշվին ավելացված գումար\n\n"
        "💡 *Հարցերի դեպքում.* Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Ֆինանսներ", callback_data="help_finance"),
         InlineKeyboardButton("💬 Հարց տալ", callback_data="help_operator")]
    ]
    
    await query.message.edit_text(
        cards_text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def finance_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdraw callback."""
    query = update.callback_query
    await query.answer()
    
    withdraw_text = (
        "🏦 *Դուրսբերման մեթոդներ*\n\n"
        "✅ **Բանկային փոխանցում**\n"
        "• Ուղիղ բանկային հաշվին\n"
        "• 1-3 աշխատանքային օրվա ընթացքում\n"
        "• Նվազագույն գումար՝ 1000 ՀՀ դրամ\n\n"
        "✅ **Էլեկտրոնային համակարգեր**\n"
        "• Նույն համակարգով, որով ավանդել եք\n"
        "• Արագ մշակում\n"
        "• Փոքր միջնորդավճարներ\n\n"
        "✅ **Նվազագույն գումարներ**\n"
        "• Դուրսբերման նվազագույն՝ 1000 ՀՀ դրամ\n"
        "• Մեկ օրվա առավելագույն՝ 500,000 ՀՀ դրամ\n\n"
        "💡 *Խնդիրների դեպքում.* Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Ֆինանսներ", callback_data="help_finance"),
         InlineKeyboardButton("💬 Հարց տալ", callback_data="help_operator")]
    ]
    
    await query.message.edit_text(
        withdraw_text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def contact_address_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle address callback."""
    query = update.callback_query
    await query.answer()
    
    address_text = (
        "📍 *Հասցեներ*\n\n"
        "**Գլխավոր գրասենյակ**\n"
        "Երևան, Կենտրոն, 0082\n"
        "Ծովակալ Իսակովի պողոտա 15/3\n\n"
        "**Բուքմեյքերական կետեր**\n"
        "1. Երևան, Արաբկիր, Կոմիտասի պողոտա 59/6\n"
        "2. Երևան, Մալաթիա-Սեբաստիա, Ա.Բաբաջանյան 91/6\n"
        "3. Երևան, Նոր Նորք, Գայի պողոտա 28/5\n"
        "4. Երևան, Աջափնյակ, Շինարարների փողոց 25\n"
        "5. Գյումրի, Բագրատունյաց հրապարակ 8\n"
        "6. Արմավիր, Չարենցի 4\n\n"
        "💡 *Ճանապարհային հարցերի դեպքում.* Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Կապ", callback_data="help_contact"),
         InlineKeyboardButton("💬 Հարց տալ", callback_data="help_operator")]
    ]
    
    await query.message.edit_text(
        address_text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def contact_website_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle website callback."""
    query = update.callback_query
    await query.answer()
    
    website_text = (
        "🌐 *Կայքեր և հարթակներ*\n\n"
        "**Հիմնական կայքեր**\n"
        "• sport.totogaming.am - սպորտային խաղադրույքներ\n"
        "• totogaming.am - գլխավոր կայք\n"
        "• blog.totogaming.am - բլոգ և նորություններ\n\n"
        "**Մոբայլ հավելվածներ**\n"
        "• iOS App Store-ում\n"
        "• Android Google Play-ում\n"
        "• Մոբայլ բրաուզերում\n\n"
        "**Աջակցություն**\n"
        "• Online chat աջակցություն\n"
        "• Հեռախոսով աջակցություն\n"
        "• FAQ բաժին\n\n"
        "💡 *Կայքի հետ կապված հարցերի դեպքում.* Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Կապ", callback_data="help_contact"),
         InlineKeyboardButton("💬 Հարց տալ", callback_data="help_operator")]
    ]
    
    await query.message.edit_text(
        website_text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def contact_email_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle email callback."""
    query = update.callback_query
    await query.answer()
    
    email_text = (
        "📧 *Կապի միջոցներ*\n\n"
        "**Էլեկտրոնային փոստ**\n"
        "• support@totogaming.am - տեխնիկական աջակցություն\n"
        "• info@totogaming.am - ընդհանուր տեղեկատվություն\n"
        "• partnership@totogaming.am - գործընկերային հարցեր\n\n"
        "**Հեռախոսահամարներ**\n"
        "• Տեխնիկական աջակցություն՝ +374 XX XXX XXX\n"
        "• Գործընկերային հարցեր՝ +374 XX XXX XXX\n"
        "• Ընդհանուր հարցեր՝ +374 XX XXX XXX\n\n"
        "**Աշխատանքային ժամեր**\n"
        "• Երկուշաբթի-Ուրբաթ՝ 09:00-18:00\n"
        "• Շաբաթ-Կիրակի՝ 10:00-16:00\n"
        "• Online աջակցություն՝ 24/7\n\n"
        "💡 *Ավելի արագ պատասխանի համար.* Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 Կապ", callback_data="help_contact"),
         InlineKeyboardButton("💬 Հարց տալ", callback_data="help_operator")]
    ]
    
    await query.message.edit_text(
        email_text, 
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ------------------------------
# Message Handler with Keyboard Support
# ------------------------------
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle normal text messages and keyboard buttons."""
    text = update.message.text
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    logger.info(f"User message: {text}")
    
    # Check for keyboard button presses
    button_handlers = {
        "📋 Թեմաներ": topics,
        "❓ Օգնություն": help_command,
        "💰 Ֆինանսներ": finance,
        "📞 Կապ": contact,
        "💬 Հարց տալ օպերատորին": lambda u, c: ask_operator(u, c),
        
        "📊 Իմ հարցերը": my_questions,
        "ℹ️ Օգնություն": help_command,
        "🏠 Գլխավոր մենյու": start,
        "Չեղարկել": cancel_action
    }
    
    if text in button_handlers:
        await button_handlers[text](update, context)
        return
    
    # Handle different states
    if context.user_data.get('awaiting_question', False):
        await handle_awaiting_question(update, context, text)
        return
    
    if context.user_data.get('awaiting_operator_question', False):
        await handle_operator_question(update, context, text)
        return
    
    if context.user_data.get('awaiting_question_change', False):
        await handle_question_change(update, context, text)
        return
    
    if context.user_data.get('awaiting_question_rewrite', False):
        await handle_question_rewrite(update, context, text)
        return
    
    # Process regular messages
    answer = find_answer(text)
    
    if answer:
        logger.info(f"Found answer: {answer[:50]}...")
        
        # Add helpful footer to answer
        answer += "\n\n💡 *Ավելի մանրամասն տեղեկության համար.*\n"
        answer += "Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։"
        
        await update.message.reply_text(answer, parse_mode='Markdown', reply_markup=get_main_keyboard())
    else:
        # No answer found - suggest options
        await handle_no_answer(update, context, text)

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cancel action."""
    # Clear all states
    for key in ['awaiting_question', 'awaiting_operator_question', 
                'awaiting_question_change', 'awaiting_question_rewrite']:
        context.user_data.pop(key, None)
    
    await update.message.reply_text(
        "❌ *Գործողությունը չեղարկված է*\n\n"
        "Վերադարձ դեպի գլխավոր մենյու։",
        parse_mode='Markdown',
        reply_markup=get_main_keyboard()
    )

async def handle_awaiting_question(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Handle when user is awaiting to ask a question."""
    context.user_data['awaiting_question'] = False
    context.user_data['last_question'] = text
    
    # Get suggestions for the question
    suggestions = get_suggestion_for_question(text)
    
    confirmation_text = (
        f"❓ *Հաստատեք ձեր հարցը*\n\n"
        f"📝 *Ձեր հարցը.*\n"
        f"{text}\n\n"
    )
    
    if suggestions:
        confirmation_text += "💡 *Հուշումներ.*\n"
        for suggestion in suggestions[:2]:  # Show max 2 suggestions
            confirmation_text += f"• {suggestion}\n"
        confirmation_text += "\n"
    
    confirmation_text += "Այս հարցը ուղարկե՞լ օպերատորին։"
    
    await update.message.reply_text(
        confirmation_text,
        parse_mode='Markdown',
        reply_markup=get_question_confirmation_keyboard()
    )

async def handle_operator_question(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Handle operator question."""
    context.user_data['awaiting_operator_question'] = False
    context.user_data['last_question'] = text
    
    # Get suggestions
    suggestions = get_suggestion_for_question(text)
    
    confirmation_text = (
        f"👨‍💼 *Հարց օպերատորին*\n\n"
        f"📝 *Ձեր հարցը.*\n"
        f"{text}\n\n"
    )
    
    if suggestions:
        confirmation_text += "💡 *Հուշումներ.*\n"
        for suggestion in suggestions[:2]:
            confirmation_text += f"• {suggestion}\n"
        confirmation_text += "\n"
    
    confirmation_text += (
        f"⏰ *Պատասխանի սպասվող ժամանակ.*\n"
        f"5-15 րոպե\n\n"
        f"Ուղարկե՞լ հարցը օպերատորին։"
    )
    
    await update.message.reply_text(
        confirmation_text,
        parse_mode='Markdown',
        reply_markup=get_question_confirmation_keyboard()
    )

async def handle_question_change(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Handle question change."""
    context.user_data['awaiting_question_change'] = False
    context.user_data['last_question'] = text
    
    confirmation_text = (
        f"✏️ *Փոփոխված հարցը*\n\n"
        f"📝 *Ձեր նոր հարցը.*\n"
        f"{text}\n\n"
        f"Ուղարկե՞լ այս հարցը օպերատորին։"
    )
    
    await update.message.reply_text(
        confirmation_text,
        parse_mode='Markdown',
        reply_markup=get_question_confirmation_keyboard()
    )

async def handle_question_rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Handle question rewrite."""
    context.user_data['awaiting_question_rewrite'] = False
    context.user_data['last_question'] = text
    
    confirmation_text = (
        f"✏️ *Վերագրված հարցը*\n\n"
        f"📝 *Ձեր նոր հարցը.*\n"
        f"{text}\n\n"
        f"Ուղարկե՞լ այս հարցը օպերատորին։"
    )
    
    await update.message.reply_text(
        confirmation_text,
        parse_mode='Markdown',
        reply_markup=get_question_confirmation_keyboard()
    )

async def handle_no_answer(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Handle when no answer is found."""
    # Analyze the question
    suggestions = get_suggestion_for_question(text)
    
    response = (
        "🤔 *Չգտա պատասխան ձեր հարցին*\n\n"
        f"📝 *Ձեր հարցը.* {text[:100]}...\n\n"
    )
    
    if suggestions:
        response += "💡 *Ինչ կարող եք անել.*\n"
        for suggestion in suggestions[:3]:  # Show max 3 suggestions
            response += f"• {suggestion}\n"
        response += "\n"
    
    response += (
        "🚀 *Արագ լուծում.*\n"
        "1. Սեղմեք «💬 Հարց տալ օպերատորին»\n"
        "2. Գրեք ձեր հարցը\n"
        "3. Ստացեք անձնական պատասխան\n\n"
        
        "📚 *Կամ փորձեք.*\n"
        "• Սեղմել «📋 Թեմաներ»\n"
        "• Գրել հարցը այլ կերպ\n"
        "• Օգտագործել հրամանները\n\n"
        
        "Օպերատորը պատրաստ է օգնել ձեզ 👍"
    )
    
    await update.message.reply_text(response, parse_mode='Markdown', reply_markup=get_main_keyboard())

# ------------------------------
# Operator Command Handlers
# ------------------------------

async def operator_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Operator replies to user - /reply <chat_id> <request_id> <message>"""
    from datetime import datetime
    
    user = update.effective_user
    chat = update.effective_chat
    
    # Check if the message is from the operator
    if str(chat.id) != str(OPERATOR_CHAT_ID):
        await update.message.reply_text("❌ Այս հրամանը միայն օպերատորների համար է։")
        return
    
    # Check if command has enough arguments
    if len(context.args) < 3:
        await update.message.reply_text(
            "📋 *Օգտագործում.*\n"
            "`/reply <chat_id> <request_id> <հաղորդագրություն>`\n\n"
            "*Օրինակ.*\n"
            "`/reply 123456789 req_123456 Բարև, ես օպերատորն եմ`\n\n"
            "*Տվյալները կարող եք գտնել օպերատորին ուղարկված ծանուցման մեջ։*",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_chat_id = int(context.args[0])
        request_id = context.args[1]
        message = " ".join(context.args[2:])
        
        # Escape Markdown characters in the message
        import re
        def escape_markdown(text):
            """Escape Markdown special characters"""
            escape_chars = r'\_*[]()~`>#+-=|{}.!'
            for char in escape_chars:
                text = text.replace(char, f'\\{char}')
            return text
        
        # Escape the operator's message
        escaped_message = escape_markdown(message)
        
        # Send message to user with proper escaping
        await context.bot.send_message(
            chat_id=user_chat_id,
            text=f"👨‍💼 *ՕՊԵՐԱՏՈՐԻՑ ՊԱՏԱՍԽԱՆ*\n\n"
                 f"💬 *Պատասխան.*\n"
                 f"{escaped_message}\n\n"
                 f"🆔 *Հարցի ID.* `{request_id[-6:] if '_' in request_id else request_id}`\n"
                 f"⏰ *Պատասխանի ժամանակ.* `{datetime.now().strftime('%H:%M:%S')}`\n\n"
                 f"📞 *Հետագա հարցերի համար.*\n"
                 f"Օգտագործեք «💬 Հարց տալ օպերատորին» կոճակը։",
            parse_mode='Markdown'
        )
        
        # Update request status
        update_user_request(request_id, 
                          status="answered",
                          answered_by=user.full_name,
                          answer_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        # Add to conversation history
        add_to_conversation(user_chat_id, "operator", message, request_id)
        
        # Notify operator - Escape message here too
        escaped_message_preview = escape_markdown(message[:100])
        await update.message.reply_text(
            f"✅ *ՊԱՏԱՍԽԱՆԸ ՈՒՂԱՐԿՎԵՑ*\n\n"
            f"👤 *Օգտատեր.* `{user_chat_id}`\n"
            f"🆔 *Հարցի ID.* `{request_id}`\n"
            f"📝 *Պատասխան.* {escaped_message_preview}{'...' if len(message) > 100 else ''}\n\n"
            f"📊 *Մնացած սպասող հարցեր.* {get_pending_requests_count()}",
            parse_mode='Markdown'
        )
        
        logger.info(f"Operator {user.id} replied to user {user_chat_id}")
        
    except ValueError:
        await update.message.reply_text("❌ Chat ID-ն պետք է լինի թիվ։")
    except Exception as e:
        logger.error(f"Failed to send reply: {e}")
        error_message = str(e)
        # Extract the problematic part if available
        if "byte offset" in error_message:
            # Try to find the problematic character
            import re
            match = re.search(r'byte offset (\d+)', error_message)
            if match:
                offset = int(match.group(1))
                problematic_char = message[offset-1:offset+2] if len(message) >= offset else "end of message"
                await update.message.reply_text(
                    f"❌ *Մարկդաունի սխալ*\n\n"
                    f"Պրոբլեմային սիմվոլներ՝ `{problematic_char}`\n\n"
                    f"Փորձեք՝\n"
                    f"1. Չօգտագործել *, _, `, [, ] սիմվոլներ\n"
                    f"2. Օգտագործել պարզ տեքստ\n"
                    f"3. Կրկին փորձել",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"❌ Սխալ: {str(e)[:100]}")
        else:
            await update.message.reply_text(f"❌ Սխալ: {str(e)[:100]}")

async def operator_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active user requests - /requests"""
    chat = update.effective_chat
    
    # Check if the message is from the operator
    if str(chat.id) != str(OPERATOR_CHAT_ID):
        await update.message.reply_text("❌ Այս հրամանը միայն օպերատորների համար է։")
        return
    
    active_requests = {k: v for k, v in get_user_requests().items() if v["status"] == "pending"}
    
    if not active_requests:
        await update.message.reply_text("🎉 *Բոլոր հարցերը պատասխանված են!*\n\nՍպասող հարցեր չկան։")
        return
    
    text = f"📋 *ՍՊԱՍՈՂ ՀԱՐՑԵՐ: {len(active_requests)}*\n\n"
    
    for idx, (request_id, req) in enumerate(active_requests.items(), 1):
        time_ago = datetime.now() - datetime.strptime(req["time"], "%Y-%m-%d %H:%M:%S")
        minutes_ago = int(time_ago.total_seconds() / 60)
        
        text += f"{idx}. *Հարց ID:* {request_id[-6:]}\n"
        text += f"   👤 *Օգտատեր.* {req['user_name']}\n"
        text += f"   🆔 *Chat ID:* {req['user_id']}\n"
        text += f"   ⏰ *Սպասում է:* {minutes_ago} րոպե\n"
        text += f"   📝 *Հարց.* {req['message'][:100]}...\n"
        text += f"   📋 *Պատասխանելու համար.*\n"
        text += f"   `/reply {req['user_id']} {request_id} Ձեր պատասխանը`\n\n"
    
    text += f"⏰ *Միջին սպասման ժամանակ.* {sum(1 for _ in active_requests) * 10} րոպե\n"
    text += f"🚀 *Շտապ պատասխանեք հերթականությամբ։*"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def operator_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot status - /status"""
    chat = update.effective_chat
    
    # Check if the message is from the operator
    if str(chat.id) != str(OPERATOR_CHAT_ID):
        await update.message.reply_text("❌ Այս հրամանը միայն օպերատորների համար է։")
        return
    
    active_requests = get_user_requests()
    conversations = load_user_conversations()
    total_conversations = sum(len(conv) for conv in conversations.values())
    
    status_text = (
        "🤖 *Բոտի վիճակ*\n\n"
        "✅ Բոտը գործում է\n"
        f"👥 Ակտիվ հարցումներ: {len(active_requests)}\n"
        f"💬 Ընդհանուր հաղորդագրություններ: {total_conversations}\n"
        f"👨‍💼 Օպերատոր Chat ID: {OPERATOR_CHAT_ID}\n"
        f"⏰ Ժամանակ: {update.message.date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"📋 *Հրամաններ.*\n"
        f"`/reply <chat_id> <հաղորդագրություն>` - Պատասխանել օգտատիրոջը\n"
        f"`/requests` - Ցուցադրել ակտիվ հարցումները\n"
        f"`/status` - Բոտի վիճակը\n"
        f"`/broadcast <հաղորդագրություն>` - Մասսայական հաղորդագրություն"
    )
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast message to all users - /broadcast <message>"""
    chat = update.effective_chat
    
    # Check if the message is from the operator
    if str(chat.id) != str(OPERATOR_CHAT_ID):
        await update.message.reply_text("❌ Այս հրամանը միայն օպերատորների համար է։")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 *Մասսայական հաղորդագրություն*\n\n"
            "`/broadcast <հաղորդագրություն>`\n\n"
            "*Ուշադրություն:* Այս հրամանը կուղարկի հաղորդագրությունը բոլոր օգտատերերին։",
            parse_mode='Markdown'
        )
        return
    
    message = " ".join(context.args)
    
    # Get all user chat IDs from active requests
    active_requests = get_user_requests()
    user_chat_ids = list(active_requests.keys())
    
    if not user_chat_ids:
        await update.message.reply_text("❌ Օգտատերերի ցանկը դատարկ է։")
        return
    
    success_count = 0
    fail_count = 0
    
    # Send to each user
    for chat_id in user_chat_ids:
        try:
            await context.bot.send_message(
                chat_id=int(chat_id),
                text=f"📢 *Կարևոր ծանուցում TotoGaming-ից*\n\n{message}",
                parse_mode='Markdown'
            )
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {chat_id}: {e}")
            fail_count += 1
    
    await update.message.reply_text(
        f"📊 *Մասսայական հաղորդագրության արդյունքներ*\n\n"
        f"✅ Հաջողված: {success_count}\n"
        f"❌ Չհաջողված: {fail_count}\n"
        f"📈 Ընդհանուր փորձ: {success_count + fail_count}",
        parse_mode='Markdown'
    )

# ------------------------------
# Error Handler
# ------------------------------

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Error occurred: {context.error}")
    
    if update and update.message:
        await update.message.reply_text(
            "😕 *Տեխնիկական խնդիր*\n\n"
            "Սխալ է տեղի ունեցել։ Խնդրում եմ փորձել մի փոքր ուշ։\n\n"
            "🔧 *Ինչ կարող եք անել.*\n"
            "• Սպասել 1 րոպե և կրկին փորձել\n"
            "• Օգտագործել `/start` հրամանը\n"
            "• Կապ հաստատել այլ եղանակով\n\n"
            "Ներողություն անհարմարության համար 🙏",
            parse_mode='Markdown',
            reply_markup=get_main_keyboard()
        )

# ------------------------------
# Main Function
# ------------------------------

def main():
    """Start the bot."""
    # Create the bot application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("topics", topics))
    app.add_handler(CommandHandler("finance", finance))
    app.add_handler(CommandHandler("contact", contact))
    app.add_handler(CommandHandler("operator", ask_operator))
    app.add_handler(CommandHandler("ask", ask_operator))
    app.add_handler(CommandHandler("myquestions", my_questions))
    app.add_handler(CommandHandler("stats", user_stats))
    app.add_handler(CommandHandler("commands", commands_list))
    app.add_handler(CommandHandler("about", about))
    
    # Register operator command handlers
    app.add_handler(CommandHandler("reply", operator_reply))
    app.add_handler(CommandHandler("requests", operator_requests))
    app.add_handler(CommandHandler("status", operator_status))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # Register callback query handler
    app.add_handler(CallbackQueryHandler(button_callback))

    # Register message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register error handler
    app.add_error_handler(error_handler)

    # Log bot start
    logger.info("🤖 User-friendly bot started")
    
    # Create data files if they don't exist
    if not os.path.exists(USER_REQUESTS_FILE):
        save_json_file(USER_REQUESTS_FILE, {})
    
    if not os.path.exists(USER_CONVERSATIONS_FILE):
        save_json_file(USER_CONVERSATIONS_FILE, {})
    
    if not os.path.exists(USER_STATS_FILE):
        save_json_file(USER_STATS_FILE, {})

    # Start polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)

# ------------------------------
# Entry Point
# ------------------------------

if __name__ == "__main__":
    main()