# TotoGamingSupport-Bot
A Telegram bot providing 24/7 customer support for TotoGaming users.

🌟 Features
For Users
📋 Topic Navigation - Browse 15+ categories

🤖 Instant Answers - AI-powered responses

👨‍💼 Operator Connect - Direct chat with support agents

📊 Question History - Track all your questions

💰 Financial Info - Payment & withdrawal details

📞 Contact Info - Addresses, phones, emails

For Admins/Operators
🔔 Request Queue - Manage unanswered questions

⚡ Quick Reply - /reply command for fast responses

📈 Statistics - User activity and bot performance

📢 Broadcast - Send announcements to all users

📝 Logging - Full conversation history

🚀 Quick Start  


---------------------------------------------------------
Installation 

    bash (In terminal)
            |
            |
          \ | /
           \|/
            
bash
# 1. Clone repository
git clone <your-repo-url>

# 2. Install dependencies
pip install python-telegram-bot

# 3. Configure bot
cp config.example.py config.py
# Edit config.py with your tokens
Configuration


---------------------------------------------------------
---------------------------------------------------------
python  
 
            |
            |
          \ | /
           \|/
            

# config.py
TELEGRAM_TOKEN = "your_bot_token_here"
OPERATOR_CHAT_ID = "operator_group_chat_id_here"

------------------------------------------------------------


------------------------------------------------------------
Run the Bot | (In terminal)
            |
          \ | /
           \|/
            

python bot.py

------------------------------------------------------------



⚙️ Admin Management
Operator Commands
text
/reply <chat_id> <request_id> <message>  # Reply to user
/requests                               # View pending questions
/status                                 # Check bot status
/broadcast <message>                    # Send to all users
Managing Bot Answers
Edit rules_data.py to add/update responses:



------------------------------------------------------------
python code 

            |
            |
          \ | /
           \|/
            

RULES = {
    "topic_id": {
        "keywords": ["keyword1", "keyword2"],
        "answer": {
            "hy": "Պատասխան հայերեն",
            "en": "Answer in English"
        }
    }
}
Adding New Topics
Add to RULES in rules_data.py

Add to TOPICS_LIST in bot.py

Restart bot
------------------------------------------------------------



------------------------------------------------------------
TO get operator's ID - USE get_my_id.py 

in Terminal 

            |
            |
          \ | /
           \|/


python get_my_id.py 
------------------------------------------------------------

📁 Project Structure
text
bot.py              # Main bot application
config.py           # Configuration (tokens, IDs)
rules_data.py       # Q&A database
matcher.py          # AI matching engine
logger.py           # Logging system

data/
├── user_requests.json      # Active user questions
├── user_conversations.json # Chat history
└── user_stats.json         # User statistics

🔧 Troubleshooting
Common Issues
Bot not responding: Check token in config.py

Operator commands not working: Verify OPERATOR_CHAT_ID

Markdown errors: Escape special characters (*, _, `, etc.)

Slow performance: Check JSON file sizes

Logs & Monitoring
Check bot.log for errors

Monitor JSON files in data/ folder

Use /status command for bot health

📞 Support
User Support: Use "💬 Հարց տալ օպերատորին" in bot

Technical Issues: Contact dev team

Emergency: Restart bot with python bot.py

📈 Stats & Analytics
The bot automatically tracks:

Total users and questions

Response times

Popular topics

Operator performance

🔮 Future Plans
Database migration (PostgreSQL)

Multi-language support

Web dashboard

Advanced analytics

Mobile app integration
