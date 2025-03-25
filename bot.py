import os
import requests
import bcrypt
import random
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import init_db
from dotenv import load_dotenv
from telegram.error import BadRequest
import mysql.connector
import re
from fastapi import FastAPI, Request
import asyncio
import uvicorn



# Load environment variables
load_dotenv()

# Initialize the database
def connect_db():
    return mysql.connector.connect(
        host= DATABASE_HOST,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        database=DATABASE_NAME
    )

# Temporary storage for user account creation process
user_data = {}

# Secure credentials & API endpoints
AGENT_USERNAME = os.getenv("AGENT_USERNAME")
AGENT_PASSWORD = os.getenv("AGENT_PASSWORD")
PAYEER_ACCOUNT =os.getenv("PAYEER_ACCOUNT")
SYREATEL_ACCOUNT=os.getenv("SYREATEL_ACCOUNT")
BEMO_ACCOUNT=os.getenv("BEMO_ACCOUNT")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_PASSWORD= os.getenv("DATABASE_PASSWORD")
DATABASE_USER=os.getenv("DATABASE_USER")
DATABASE_NAME=os.getenv("DATABASE_NAME")
DATABASE_HOST=os.getenv("DATABASE_HOST")
LOGIN_URL = "https://agents.wayxbet.com/global/api/User/signIn"
REGISTER_USER_URL = "https://agents.wayxbet.com/global/api/Player/registerPlayer"
FIXED_PARENT_ID = "2301209"
FETCH_PLAYER_DETAILS="https://agents.wayxbet.com/global/api/Statistics/getPlayersStatisticsPro"
FETCH_PLAYER_BALANCE="https://agents.wayxbet.com/global/api/Player/getPlayerBalanceById"
DEPOSIT_URL = "https://agents.wayxbet.com/global/api/Player/depositToPlayer"
WITHDRAW_WEBSITE_URL = "https://agents.wayxbet.com/global/api/Player/withdrawFromPlayer"
exchange_rate = 10000
WEBHOOK_URL = "https://2bc4-169-150-196-153.ngrok-free.app/webhook" 



app = FastAPI()
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# ✅ Set up logging for debugging
logging.basicConfig(level=logging.INFO) 

async def start_bot():
    """Initialize and start the Telegram bot."""
        
    await telegram_app.initialize()
    await telegram_app.start()
    print("✅ Telegram bot initialized!")

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive updates from Telegram and process them."""
    try:
        update_data = await request.json()
        if not update_data:
            raise ValueError("Received empty JSON from Telegram")
        
        logging.info(f"📩 Received update: {update_data}")
        update = Update.de_json(update_data, telegram_app.bot)
        await telegram_app.process_update(update)

        return {"status": "ok"}

    except Exception as e:
        logging.error(f"❌ Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

async def set_webhook():
    """Set Telegram webhook to FastAPI server."""
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={"url": WEBHOOK_URL},
    )
    if response.status_code == 200:
        print("✅ Webhook set successfully!")
    else:
        print(f"❌ Failed to set webhook: {response.text}")


@app.on_event("startup")
async def on_startup():
    """Run on FastAPI startup: Set webhook & start the bot."""
    await set_webhook()
    asyncio.create_task(start_bot())  # ✅ Initialize the bot
    

logging.basicConfig(level=logging.DEBUG)  # ✅ Enable debug logging
from fastapi import FastAPI, Request
import logging
import re
from datetime import datetime
import sys



@app.post("/sms")
async def receive_sms(request: Request):
    """Receive SMS from SMS Forwarder and process the transaction."""
    try:
        # ✅ Get raw request body and headers
        raw_body = await request.body()
        headers = request.headers

        print(f"📩 Raw request body: {raw_body.decode('utf-8')}")
        print(f"📩 Headers: {headers}")  # ✅ Check Content-Type
        
        # ✅ Safely parse JSON
        try:
            sms_data = await request.json()
        except Exception as json_error:
            sys.stderr.write(f"❌ JSON Parsing Error: {json_error}\n")
            return {"status": "error", "message": "Invalid JSON format"}

        # ✅ Extract SMS text and timestamp
        raw_text = sms_data.get("key", "").strip()
        raw_time = sms_data.get("time", "").strip()

        # ✅ Convert time to `YYYY-MM-DD HH:MM:SS` format
        try:
            formatted_time = datetime.strptime(raw_time, "%d/%m, %I:%M %p").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            formatted_time = "Unknown"

        print(f"📩 Received SMS: {raw_text} at {formatted_time}")

        # ✅ Process the cleaned SMS content
        result = await process_sms(raw_text, update=None, context=None)
        
        

        return {"status": "ok", "message": result}

    except Exception as e:
        sys.stderr.write(f"❌ Error processing SMS: {e}\n")  # ✅ Force print errors
        logging.error(f"❌ Error processing SMS: {e}")
        return {"status": "error", "message": str(e)}

    



# Global session for agent authentication
agent_session = None

def generate_fake_email(username):
    """Generate a fake email based on the username."""
    return f"{username}{random.randint(1000, 9999)}@fakeemail.com"

def hash_password(password):
    """Securely hash passwords."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def login_as_agent():
    """Log in as an agent and store the session globally."""
    global agent_session
    session = requests.Session()
     # Set proxy (Replace with actual Syrian proxy)
   
    
    try:
        response = session.post(LOGIN_URL, json={"username": AGENT_USERNAME, "password": AGENT_PASSWORD}, headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://agents.wayxbet.com",
            "Referer": "https://agents.wayxbet.com"
        })

        response.raise_for_status()  # Raise an error for bad responses

        if response.status_code == 200 and response.json().get("result", {}).get("message") == "dashboard":
            logging.info("✅ Agent login successful!")
            agent_session = session
            return True
        else:
            logging.error(f"❌ Agent login failed: {response.text}")

    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Login request failed: {str(e)}")
    
    return False

def fetch_player_details(username):
    """Fetch player details using the search API after account creation."""
    global agent_session
    if not agent_session and not login_as_agent():
        return None

    payload = {
        "start": 0,
        "limit": 10,
        "filter": {},
        "searchBy": {"players": username}
    }

    response = agent_session.post(FETCH_PLAYER_DETAILS, json=payload)

    if response.status_code == 200:
        data = response.json()
        if data.get("status") and data["result"]["records"]:
            player_data = data["result"]["records"][0]  # Get the first matching record
            return {
                "playerId": player_data["playerId"],
                "username": player_data["username"]
            }

    return None 

def fetch_player_balance(user_id):
    """Fetch player balance using player_id and update the database."""
    global agent_session

    # Ensure the agent session is active
    if not agent_session and not login_as_agent():
        return {"error": "Failed to log in as agent"}

    conn = None
    cursor = None

    try:
        conn = connect_db()
        cursor = conn.cursor()

        # Fetch player_id from the database
        cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            return {"error": "User ID not found in accounts table"}

        player_id = result[0]  # Extract player_id

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        return {"error": "Database error occurred"}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    # API Call to Fetch Player Balance
    payload = {"playerId": str(player_id)}

    try:
        response = agent_session.post(FETCH_PLAYER_BALANCE, json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        data = response.json()  # Parse JSON response

        if data.get("status") and "result" in data:
            balance_info = data["result"]

            # Handle if balance_info is a list instead of a dictionary
            if isinstance(balance_info, list) and balance_info:
                balance_info = balance_info[0]  # Extract first item if it's a list

            website_balance = balance_info.get("balance", 0)
            currency = balance_info.get("currencyCode", "Unknown")

            # Update the database with the new website balance
            try:
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute("UPDATE wallets SET website_balance = %s WHERE user_id = %s", 
                               (website_balance, user_id))
                conn.commit()

            except mysql.connector.Error as err:
                print(f"❌ MySQL Error (Updating balance): {err}")

            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()

            return {
                "balance": website_balance,
                "currency": currency
            }

        else:
            return {"error": "Invalid response structure or player not found"}

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}



#------------------------------------create user on the website funcion ------------------------


def create_user_on_website(username, password):
    """Create a user account on the website and return account details."""
    global agent_session
    if not agent_session and not login_as_agent():
        return None
    
    payload = {
        "player": {
            "email": generate_fake_email(username),
            "password": password,
            "parentId": FIXED_PARENT_ID,
            "login": username
        }
    }
    response = agent_session.post(REGISTER_USER_URL, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status"):  # Check if account creation was successful
            player_details = fetch_player_details(username)  # Fetch player details
            
            if player_details:
                return {
                    "username": player_details["username"],
                    "password": password,
                    "playerId": player_details["playerId"]
                    
                }

    return None  # Return None if creation or fetching fails


#--------------------------start command ------------------------------------------


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command and display terms for first-time users."""
    
    context.user_data["state"] = "expecting_no_input"
    user_id = update.message.from_user.id 

    user = update.effective_user  # Get the user object
    first_name = user.first_name  # Get the user's first name
    
    user_exists = None  # Initialize variable
    welcome_sticker_id = "CAACAgIAAxkBAeLeCmfdgKwm3XwP2yxX-l0gOsdn2xSbAAIxNAAC6BugStKvp8RmJqK8NgQ"  # Replace with your sticker ID
    try:
        conn = connect_db()
        cursor = conn.cursor()
        
        # Check if the user exists in the database
        cursor.execute("SELECT user_id FROM accounts WHERE user_id = %s", (user_id,))
        user_exists = cursor.fetchone()

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء الاتصال بقاعدة البيانات. يرجى المحاولة لاحقًا!")
        return  # Stop execution in case of an error

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    terms_text = ""
    if not user_exists:
        # If the user is new, send the Terms and Conditions first
        terms_text = (
            "📜 شروط وأحكام استخدام البوت:\n\n"
            "🟥 أنت المسؤول الوحيد عن أموالك، دورنا يقتصر على الوساطة بينك وبين الموقع، مع ضمان إيداع وسحب أموالك بكفاءة وموثوقية.\n\n"
            "🟥 لا يجوز للاعب إيداع وسحب الأرصدة بهدف التبديل بين وسائل الدفع. تحتفظ إدارة البوت بالحق في سحب أي رصيد والاحتفاظ به إذا تم اكتشاف عملية تبديل أو أي انتهاك لقوانين البوت.\n\n"
            "🟥 إنشاء أكثر من حساب يؤدي إلى حظر جميع الحسابات وتجميد الأرصدة الموجودة فيها، وذلك وفقاً لشروط وأحكام الموقع للحد من الأنشطة الاحتيالية، وامتثالاً لسياسة اللعب النظيف.\n\n"
            "📌 يُعدّ انضمامك للبوت واستخدامه موافقة على هذه الشروط، وتحمل المسؤولية الكاملة عن أي انتهاك لها.\n\n"
        )

    # Define the main menu keyboard
    keyboard = [[
        InlineKeyboardButton("🆕 انشاء حساب وتعبئته ", callback_data='create_account'),
        InlineKeyboardButton("💳 محفطة البوت وشحنها ", callback_data='charge')
    ], [
        InlineKeyboardButton("💸 الرصيد", callback_data='cash'),
        InlineKeyboardButton("📊 عرض آخر 5 معاملات", callback_data="show_transactions")
    ], 
    [InlineKeyboardButton("🎰 Slot Machine", callback_data="slot_machine")],
    [
        InlineKeyboardButton("📜 الشروط و الأحكام", callback_data='terms')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = f"مرحباً👋 `{first_name}` الرجاء اختيار الخدمة من القائمة."
    await update.message.reply_sticker(sticker=welcome_sticker_id)

    # If the user is new, send terms first, then send the main menu
    if terms_text:
        await update.message.reply_text(terms_text, parse_mode="Markdown")

    # Send the main menu
    await update.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

#--------------------------------Terms command --------------------------------------------

    
#--------------------------------help command ----------------------------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [
        [InlineKeyboardButton("📖 حسابي", callback_data='help_account')],
        [InlineKeyboardButton("💰 الإيداع", callback_data='help_deposit')],
        [InlineKeyboardButton("💸 السحب", callback_data='help_withdraw')],
        [InlineKeyboardButton("📞 الدعم", callback_data='help_support')],
       
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    help_text = (
        "🆘 قسم المساعدة\n\n"
        "اختر أحد المواضيع التالية لمعرفة المزيد:\n"
        "📖 حسابي - كيفية إنشاء حساب وإدارته.\n"
        "💰 الإيداع - كيفية شحن حسابك.\n"
        "💸 السحب - كيفية سحب الأموال.\n"
        "📞 الدعم - كيفية التواصل معنا لحل مشاكلك."
    )

    await update.message.reply_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")
    
    
    
#================================Button commands============================================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle button clicks and navigation."""
    
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # Initialize user navigation history if not exists
    if "history" not in context.user_data:
        context.user_data["history"] = []

#--------------------------------Create account Button commands--------------------------------------------
    if query.data == 'create_account':
        context.user_data["state"] = "expecting_Create_accout_input"

        try:
            conn = connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT username, player_id FROM accounts WHERE user_id = %s", (user_id,))
            account = cursor.fetchone()  # Fetch before closing cursor
            
            
             # Fetch bot balance from wallets
            cursor.execute("SELECT bot_balance FROM wallets WHERE user_id = %s", (user_id,))
            bot_result = cursor.fetchone()

            bot_balance = bot_result[0] if bot_result else 0  # Handle None case safely
            
            
        except mysql.connector.Error as err:
            print(f"❌ MySQL Error: {err}")
            await query.edit_message_text("❌ حدث خطأ في قاعدة البيانات. حاول مرة أخرى لاحقًا.")
            return
        
        finally:
            cursor.close()
            conn.close()
            
           
         # Fetch website balance from API
         

         
         
            print("done")
        

        if account:
            username, player_id = account
            keyboard = [
                [InlineKeyboardButton("🌐 WayXbet الانتقال الى موقع ", url="https://m.wayxbet.com/en/")],
                [InlineKeyboardButton("💰 شحن الحساب", callback_data='charge_website_account'), 
                 InlineKeyboardButton("💸 سحب رصيد الحساب", callback_data='withdraw_website')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            balance_details = fetch_player_balance(user_id)
            if "error" in balance_details:
                balance_text = f"⚠️ Error: {balance_details['error']}"
                
            else:
             balance_text = (
                f"💰 الرصيد:\n"
                f"💵 رصيدك على الموقع: `{balance_details.get('balance', 0)}` {balance_details.get('currency', 'SYP')}\n"
                f"🤖 رصيد البوت: `{bot_balance}` {balance_details.get('currency', 'SYP')}\n"
            )
             
             
            
            message =( f"حساب WayXbet الخاص بك:\n👤  اسم حسابك على الموقع : {username}\n ⚽️ معرف اللاعب:  {player_id}\n"
                      f"{balance_text}")
            await query.edit_message_text(message, reply_markup=reply_markup)
            
        else:
            user_data[user_id] = {"step": "username"}  # Store state properly
            await query.edit_message_text("أدخل اسم المستخدم الخاص بك  ")

#--------------------------------💳 محفظة البوت وشحنها Button commands--------------------------------------------
    elif query.data == 'charge':
        context.user_data["state"] = "expecting_no_input"

        try:
            conn = connect_db()
            cursor = conn.cursor()
            
            # Fetch user player_id
            cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
            player_data = cursor.fetchone()

            # Fetch bot balance
            cursor.execute("SELECT bot_balance FROM wallets WHERE user_id = %s", (user_id,))
            bot_result = cursor.fetchone()

            bot_balance = bot_result[0] if bot_result else 0  # Handle None case

        except mysql.connector.Error as err:
            print(f"❌ MySQL Error: {err}")
            await query.edit_message_text("❌ حدث خطأ أثناء استرداد البيانات.")
            return

        finally:
            cursor.close()
            conn.close()

        if player_data:
            # Fetch website balance from external API
            balance_details = fetch_player_balance(user_id)

            if "error" in balance_details:
                balance_text = f"⚠️ Error: {balance_details['error']}"
            else:
                balance_text = (
                    f"💰 الرصيد:\n"
                    f"💵  رصيدك على الموقع :  `{balance_details.get('balance', 0)}` {balance_details.get('currency', 'SYP')}\n"
                    f"💵🤖 رصيد البوت : `{bot_balance}` {balance_details.get('currency', 'SYP')}\n"
                )
        else:
            balance_text = "❌ لم يتم العثور على حساب. يرجى إنشاء حساب أولا."
            erorr_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"

         
            await update.message.reply_sticker(sticker=erorr_sticker_id)
            await query.edit_message_text(balance_text, parse_mode="Markdown")
            return

        keyboard = [
            [InlineKeyboardButton("💰 (فوري) شحن محفظة البوت", callback_data='charge_bot'),
             InlineKeyboardButton("💸 سحب من محفظة البوت", callback_data="withdraw_from_bot")],
            
            [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.user_data["history"].append((balance_text, keyboard))

        await query.edit_message_text(balance_text, reply_markup=reply_markup, parse_mode="Markdown")

#-------------------------game functions -------------------------------------------------------------------------------


    elif query.data == 'slot_machine':
        # ✅ Connect to the database
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute("select player_id from accounts where user_id = %s" ,(user_id,))
        player_id = cursor.fetchone()
        if player_id:
        
            await start_slot_machine(update, context)
        else:
            await query.edit_message_text("❌ لم يتم العثور على حساب. يرجى إنشاء حساب أولا.")
            return
        conn.close()

    
    
    elif query.data == 'charge_bot':
        context.user_data["state"] = "expecting_no_input"
        keyboard = [
            [InlineKeyboardButton("🏦  بيمو", callback_data='charge_bemo')],
            [InlineKeyboardButton("💳  بايير", callback_data='charge_payeer')],
            [InlineKeyboardButton("📱  سيرياتل كاش", callback_data='charge_syriatel')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Save the current menu before changing
        context.user_data["history"].append(("💰 اختر طريقة الدفع:", keyboard))
        

        await query.edit_message_text("💰 اختر طريقة الدفع:", reply_markup=reply_markup, parse_mode="Markdown")
        
        
#--------------------------------charge payeer Button commands--------------------------------------------

        
    elif query.data == 'charge_payeer':
     context.user_data["state"] = "expecting_payeer_transaction_id"
    
    # Send the payment instructions
     payeer_wallet = PAYEER_ACCOUNT
     
     image_path = "imges/payeeer_instructions.jpg"

     payment_text = (
        f"💰 إرسال المبلغ إلى حساب Payeer التالي:\n\n"
        f"🏦 عنوان محفظة البوت: `{payeer_wallet}`\n\n"
        f"💵 سعر الصرف:  Payeer 1 USD = {exchange_rate} بالعملة المحلية\n\n"
        f"📌 بعد الدفع، قم بإرسال رقم العملية المكون من 10 أرقام\n"
        f"📍 (مثال: `210573xxxx`)\n\n"
        f"⚠️ لا تقبل عمليات الشحن بدون رقم العملية (Operation ID)!"
     )

     keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
     reply_markup = InlineKeyboardMarkup(keyboard)

     with open(image_path, "rb") as photo:
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo,
            caption=payment_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
     print("User is now expected to send transaction ID")  # Debugging



#--------------------------------charge syriatel Button commands--------------------------------------------
        
    elif query.data == "charge_syriatel":
        context.user_data["state"] = "expecting_syriatel_transaction_id"
        syriatel_cash_code = SYREATEL_ACCOUNT
        image_path = "imges/syreatel_cash_charge_instructions.jpg"  # Ensure this image exists in your bot's directory
        payment_text = (
        "📲 إرسال المبلغ إلى كود التاجر التالي وبطريقة التحويل اليدوي حصراً كما موضح بالصورة 👆:\n\n"
        f"🏦 كود Syriatel Cash الخاص بالبوت: `{syriatel_cash_code}`\n\n"
        "📌 بعد دفع المبلغ، قم بإرسال رقم العملية المكون من:\n"
        "🔹  12رقم ,(مثال: `600000xxxxxx`)\n"
        "🔹 أو 15 رقم (مثال: `80000000xxxxxxx`)\n\n"
        "⚠️ لا تقبل عمليات الشحن من دون رقم العملية!"
    )

        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send the image and message together
        with open(image_path, "rb") as photo:
         await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo,
            caption=payment_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        context.user_data["history"].append((photo, keyboard))
        
        
        

#--------------------------------charge Beom Button commands--------------------------------------------


    elif query.data == "charge_bemo":
     context.user_data["state"] = "expecting_bemo_transaction_id"
     bemo_account = BEMO_ACCOUNT
     image_path = "imges/bemo_instructions.jpg"  # Ensure this image exists in your bot's directory
    
     payment_text = (
        "📲 أرسل المبلغ المراد شحنه إلى الحساب التالي:\n\n"
        f"🏦 رقم حساب البيمو الخاص بالبوت: `{bemo_account}`\n\n"
        "📌 وبعد دفع المبلغ ...\n"
        "🔹 قم بإرسال رقم العملية المكون من 9 أرقام\n"
        "🔹 كما موضح في الأعلى 👆\n\n"
        "🔹 (مثال: 25951xxxx)\n\n"
        "⚠️ لا تقبل عمليات الشحن من دون رقم العملية!"
     )

     keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
     reply_markup = InlineKeyboardMarkup(keyboard) 

    # Send the image and message together
     with open(image_path, "rb") as photo:
        await context.bot.send_photo(
            chat_id=query.message.chat_id,
            photo=photo,
            caption=payment_text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
    
    # Save history for back navigation
     context.user_data["history"].append((payment_text, keyboard))
     

   
   
   #--------------------------------الرصيد Button commands--------------------------------------------
   
    elif query.data == 'cash':
        context.user_data["state"] = "expecting_no_input"

        try:
         conn = connect_db()
         cursor = conn.cursor()

         # Fetch player_id from accounts
         cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
         player_data = cursor.fetchone()

         # Fetch bot balance from wallets
         cursor.execute("SELECT bot_balance FROM wallets WHERE user_id = %s", (user_id,))
         bot_result = cursor.fetchone()

         bot_balance = bot_result[0] if bot_result else 0  # Handle None case safely

        except mysql.connector.Error as err:
         print(f"❌ MySQL Error: {err}")
         await query.edit_message_text("❌ حدث خطأ أثناء جلب البيانات من قاعدة البيانات.")
         return  # Exit to prevent further execution

        finally:
         cursor.close()
         conn.close()

        if player_data:
         # Fetch website balance from API
         balance_details = fetch_player_balance(user_id)

         if "error" in balance_details:
            balance_text = f"⚠️ Error: {balance_details['error']}"
         else:
            balance_text = (
                f"💰 الرصيد:\n"
                f"💵 رصيدك على الموقع: `{balance_details.get('balance', 0)}` {balance_details.get('currency', 'SYP')}\n"
                f"🤖 رصيد البوت: `{bot_balance}` {balance_details.get('currency', 'SYP')}\n"
            )
            print("done")
        else:
         balance_text = "❌ لم يتم العثور على حساب. يرجى إنشاء حساب أولا."

        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(balance_text, reply_markup=reply_markup, parse_mode="Markdown")
         

        
#--------------------------------💸 سحب من محفظة البوت" Button commands--------------------------------------------

    elif query.data == 'withdraw_from_bot':
        context.user_data["state"] = "expecting_no_input"
        keyboard = [
            [InlineKeyboardButton("🏦 بيمو", callback_data='withdrawl_bemo')],
            [InlineKeyboardButton("💳 بايير", callback_data='withdrawl_payeer')],
            [InlineKeyboardButton("📱 سيرياتل كاش", callback_data='withdrawl_syriatel')],
            [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Save the current menu before changing
        context.user_data["history"].append(("💰 اختر طريقة السحب:", keyboard))
        

        await query.edit_message_text("💰 اختر طريقة السحب:", reply_markup=reply_markup, parse_mode="Markdown")
        
        
    elif query.data.startswith("withdrawl_"):
     method = query.data.split("_")[1]  # Extracts 'bemo', 'payeer', or 'syriatel'
     # Store method and set state
     context.user_data["withdraw_method"] = method
     context.user_data["state"] = "expecting_withdraw_amount"
     keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
     reply_markup = InlineKeyboardMarkup(keyboard) 
     if method == "payeer":
         await query.edit_message_text(
        f"💰 أدخل المبلغ  الذي تريد سحبه بعملة USD  عبر {method.upper()}:"
        ,
        reply_markup=reply_markup, parse_mode="Markdown"
    )
        
      
     else:
         
      await query.edit_message_text(
        f"💰 أدخل المبلغ الذي تريد سحبه عبر {method.upper()}:",
        reply_markup=reply_markup, parse_mode="Markdown"
    )    
     



#-------------------------------- 💰 شحن الحساب" Button commands--------------------------------------------

    elif query.data == 'charge_website_account':
        context.user_data["state"] = "expecting_website_charge_amount_From_Bot"

        await query.message.reply_text(
        "💰 الحد الادنى للتعبئة هو 10.000 أدخل المبلغ الذي تريد تحويله إلى حسابك على الموقع:",
        parse_mode="Markdown"
    )
        

#-------------------------------- 💰 سحب رصيد الحساب" Button commands--------------------------------------------

    elif query.data == 'withdraw_website':
     context.user_data["state"] = "expecting_website_withdraw_amount_To_Bot"
     
     await query.message.reply_text("💵 أدخل المبلغ المراد سحبه من حسابك على الموقع:", parse_mode="Markdown")
    
#--------------------------------رجوع  Button commands--------------------------------------------


    elif query.data == 'back':
     context.user_data["state"] = "expecting_no_input"
     if context.user_data.get("history") and len(context.user_data["history"]) > 1:
        # Get the previous menu before popping the current one
        previous_menu_text, previous_keyboard = context.user_data["history"][-2]

        # Now safely remove the current menu from history
        context.user_data["history"].pop()
        
        

        reply_markup = InlineKeyboardMarkup(previous_keyboard)

        try:
            if query.message.text:
                # If it's a text message, edit it normally
                await query.edit_message_text(previous_menu_text, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                # If the last message was a photo, delete it and send a new message
                await query.message.delete()
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=previous_menu_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except BadRequest as e:
            if "Message is not modified" in str(e):
                pass  # Ignore the error
            else:
                raise  # Re-raise other errors

     else:
        # If no history, go back to the main menu
        main_text = "مرحباً😇 الرجاء اختيار الخدمة من القائمة."
        main_markup = InlineKeyboardMarkup(main_menu_keyboard())

        if query.message.text != main_text:
            try:
                await query.edit_message_text(main_text, reply_markup=main_markup, parse_mode='Markdown')
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    pass  # Ignore the error
                else:
                    raise  # Re-raise other errors

#-------------------------------------help button -------------------------------------------------

    elif query.data == "help":
     context.user_data["state"] = "expecting_no_input"
     keyboard = [
        [InlineKeyboardButton("📖 حسابي", callback_data='help_account')],
        [InlineKeyboardButton("💰 الإيداع", callback_data='help_deposit')],
        [InlineKeyboardButton("💸 السحب", callback_data='help_withdraw')],
        [InlineKeyboardButton("📞 الدعم", callback_data='help_support')],
     ]
     reply_markup = InlineKeyboardMarkup(keyboard)

     help_text = (
        "🆘 قسم المساعدة \n\n"
        "🔹 اختر الموضوع اللي بدك تعرف عنه أكتر:\n\n"
        "📖 حسابي - طريقة إنشاء وإدارة حسابك.\n"
        "💰 الإيداع - كيف تشحن رصيدك بسهولة.\n"
        "💸 السحب - طريقة سحب أرباحك.\n"
        "📞 الدعم - كيف تتواصل معنا لحل أي مشكلة."
     )

     context.user_data["history"].append((help_text, keyboard))
     await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")
     
     #---------------------------------help acount ----------------------------------------------
    elif query.data == "help_account":
     context.user_data["state"] = "expecting_no_input"
     help_text = (
         
         #TODO  add an instruction vedio 
        "👆 اكبس زر Start وبعدها إنشاء حساب وتعبئته وتابع مع البوت... 🤖💬\n\n"
        "📝 البوت رح يطلب منك تختار اسم مستخدم وكلمة سر 🔒 لحسابك، اختار اللي بناسبك، وبعدها رح يقلك تم إنشاء حسابك بنجاح ✔️🎉\n\n"
        "🔑 بعد ما تنشئ الحساب، فوت عالموقع وسجل دخول متل مو موضح بالفيديو 📹.\n\n"
        "📩 شوف الفيديو وجرب، وإذا واجهتك أي مشكلة، تواصل معنا ع حساب الدعم 📞👍."
     )
     keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='help')]]
     reply_markup = InlineKeyboardMarkup(keyboard)
     context.user_data["history"].append((help_text, keyboard))
     await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")
    
#-----------------------------------------help deposit-------------------------------------------

             #TODO  add an instruction vedio 

    elif query.data == "help_deposit":
     context.user_data["state"] = "expecting_no_input"
     help_text = (
        "💰 الإيداع\n\n"
    "🔹 فيك تشحن حسابك بأكتر من طريقة، مثل Payeer, Bemo Bank, Syriatel Cash.\n"
    "🔹 اختر طريقة الدفع وحوّل المبلغ للحساب المحدد.\n"
    "🔹 بعد التحويل، دخل رقم العملية ليتم تأكيد الدفع."
     )
     keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='help')]]
     reply_markup = InlineKeyboardMarkup(keyboard)
     context.user_data["history"].append((help_text, keyboard))
     await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")



#-------------------------------------help_withdraw-----------------------------------------------
         #TODO  add an instruction vedio 

    elif query.data == "help_withdraw":
     context.user_data["state"] = "expecting_no_input"
     help_text = (
        "💸 السحب\n\n"
        "🔹 فيك تسحب مصاري لحساب بيمو ، Payeer، أو Syriatel Cash.\n"
        
        f"💰 نظام الرسوم على عمليات السحب: \n"
        
        f"🔹 5٪ - على كل عملية سحب\n\n"
        f"🔹 قدم طلب السحب وحنعالجه خلال 24 ساعة."
     )
     keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='help')]]
     reply_markup = InlineKeyboardMarkup(keyboard)
     context.user_data["history"].append((help_text, keyboard))
     await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")


#--------------------------------------help_support------------------------------------------------


    elif query.data == "help_support":
     context.user_data["state"] = "expecting_no_input"
     help_text = (
        "📞 الدعم\n\n"
        "🔹 إذا واجهت أي مشكلة،  تواصل معنا عبر:\n"
        
        "☎️ رقم الهاتف: -0991 685 557\n"
        
     )
     keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='help')]]
     reply_markup = InlineKeyboardMarkup(keyboard)
     context.user_data["history"].append((help_text, keyboard))
     await query.edit_message_text(help_text, reply_markup=reply_markup, parse_mode="Markdown")


    
#--------------------------------terms button ----------------------------------------------------------
    elif query.data == "terms":
     context.user_data["state"] = "expecting_no_input"
     terms_text = (
        "📜 شروط وأحكام استخدام البوت:\n\n"
        "🟥 أنت المسؤول الوحيد عن أموالك، دورنا يقتصر على الوساطة بينك وبين الموقع، مع ضمان إيداع وسحب أموالك بكفاءة وموثوقية.\n\n"
        "🟥 لا يجوز للاعب إيداع وسحب الأرصدة بهدف التبديل بين وسائل الدفع. تحتفظ إدارة البوت بالحق في سحب أي رصيد والاحتفاظ به إذا تم اكتشاف عملية تبديل أو أي انتهاك لقوانين البوت.\n\n"
        "🟥 إنشاء أكثر من حساب يؤدي إلى حظر جميع الحسابات وتجميد الأرصدة الموجودة فيها، وذلك وفقاً لشروط وأحكام الموقع للحد من الأنشطة الاحتيالية، وامتثالاً لسياسة اللعب النظيف.\n\n"
        
        "📌 يُعدّ انضمامك للبوت واستخدامه موافقة على هذه الشروط، وتحمل المسؤولية الكاملة عن أي انتهاك لها.\n\n"
       
     )
     
     await query.edit_message_text(terms_text)
     
    elif query.data == "show_transactions":
        await handle_show_last_transactions(update, context)

#--------------------------------confirm_withdraw_button-----------------------------------------------
    elif query.data.startswith("confirm_withdraw"):
        data = query.data.replace("confirm_withdraw_", "", 1)  # Remove prefix
        amount, method = data.rsplit("_", 1)  
        amount = int(amount)  # Convert amount to integer
        context.user_data["withdraw_amount"] = amount
        context.user_data["state"] = "expecting_payment_account"

        await query.message.reply_text(
         f"🏦 يرجى إدخال رقم حسابك الخاص بـ {method.upper()}:",
         parse_mode="Markdown"
          )

    elif query.data == "cancel_withdraw":
        await query.edit_message_text("❌ تم إلغاء عملية السحب.")

                
        


def main_menu_keyboard():
    """Returns the main menu keyboard."""
    return [[
        InlineKeyboardButton("🆕 انشاء حساب وتعبئته ", callback_data='create_account'),
        InlineKeyboardButton("💳 محفطة البوت وشحنها ", callback_data='charge')
    ], [
        InlineKeyboardButton("💸 الرصيد", callback_data='cash'),
        InlineKeyboardButton("📊 عرض آخر 5 معاملات", callback_data="show_transactions")
    ],
    [InlineKeyboardButton("🎰 Slot Machine", callback_data="slot_machine")],
    [
        InlineKeyboardButton("📜 الشروط و الأحكام", callback_data='terms')
        
    ]]
    

    
    

#--------------------------------user inout handlers--------------------------------------------
  
async def handle_user_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user input based on their state."""
    
    user_id = update.message.from_user.id  # Get Telegram user ID
    user_input = update.message.text.strip()
    
    state = context.user_data.get("state", None)
    erorr_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"

    if state == "expecting_Create_accout_input":
        await handel_create_account(update, context, user_input)

    elif state == "expecting_syriatel_transaction_id":
        await handle_charge_syriatel_transaction_id(update, context, user_input)

    elif state == "expecting_payeer_transaction_id":
        await handle_charge_payeer_transaction_id(update, context, user_input)

    elif state == "expecting_bemo_transaction_id":
        await handle_charge_bemo_transaction_id(update, context, user_input)

    elif state == "expecting_website_charge_amount_From_Bot":
        await handle_website_charge_amount_From_Bot(update, context, user_input)

    elif state == "expecting_website_withdraw_amount_To_Bot":
        await handle_website_withdraw_amount_To_Bot(update, context, user_input)
        
    elif state == "awaiting_deposit_amount":
        await handle_deposit_amount(update, context)

    elif state == "expecting_withdraw_amount":
        method = context.user_data.get("withdraw_method")  # Get selected method

        if not method:
            await update.message.reply_text("❌ لم يتم تحديد طريقة السحب!", parse_mode="Markdown")
            return
        
        # ✅ Call `process_withdrawal_amount_from_bot_to_user` Instead of Handling It Here
        await process_withdrawal_amount_from_bot_to_user(update, context, user_input, method)

    elif state == "expecting_payment_account":
        account_number = user_input.strip()

        if len(account_number) < 5:  # Validate input
            await update.message.reply_sticker(sticker=erorr_sticker_id)
            await update.message.reply_text("❌ رقم الحساب غير صالح! الرجاء إدخال رقم صحيح.", parse_mode="Markdown")
            return

        # Store the account number
        context.user_data["account_number"] = account_number

        # ✅ Call the final withdrawal processing function
        await finalize_withdrawal(update, context)
        
    elif state == "expecting_deposit_charge_amount":
        await handle_deposit_amount(update, context, user_input)
        
    
    
    else:
        await update.message.reply_sticker(sticker=erorr_sticker_id)
        await update.message.reply_text("⚠️ إدخال غير متوقع! يرجى اختيار خيار من القائمة.", parse_mode="Markdown")

        
        
        

#--------------------------------account createion handler --------------------------------------------
  

async def handel_create_account(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """Handles user account creation in MySQL database"""

    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists

    text = update.message.text.strip()

    # ✅ Step 1: Check if the user is at the username input stage
    if user_id in user_data and user_data[user_id]["step"] == "username":
        try:
            conn = connect_db()
            cursor = conn.cursor()

            # ✅ Check if username exists in MySQL
            cursor.execute("SELECT username FROM accounts WHERE username = %s", (text,))
            existing_user = cursor.fetchone()

            if existing_user:
                await send_message("❌ اسم المستخدم موجود بالفعل. اختر اسمًا مختلفًا.")
            else:
                user_data[user_id] = {"step": "password", "username": text}
                await send_message("🔑 أدخل كلمة المرور الخاصة بك.")
            
        except mysql.connector.Error as err:
            print(f"❌ MySQL Error: {err}")
            await send_message("⚠️ خطأ في الاتصال بقاعدة البيانات.")
        
        finally:
            cursor.close()
            conn.close()

    # ✅ Step 2: Handle password input and insert into MySQL
    elif user_id in user_data and user_data[user_id]["step"] == "password":
        username = user_data[user_id]["username"]
        password = text
        hashed_password = hash_password(password)  # Hash password for security

        try:
            conn = connect_db()
            cursor = conn.cursor()

            # ✅ Create account on external website (if needed)
            account_details = create_user_on_website(username, password)

            if account_details:
                player_id = account_details.get("playerId")

                # ✅ Insert user data into MySQL
                cursor.execute(
                    "INSERT INTO accounts (player_id, username, password, user_id) VALUES (%s, %s, %s, %s)", 
                    (player_id, username, hashed_password, user_id)
                )

                # ✅ Insert default wallet balance for the new user
                cursor.execute(
                    "INSERT INTO wallets (user_id) VALUES (%s)", 
                    (user_id,)
                )

                conn.commit()  # ✅ Commit the transaction

                await send_message(
                    f"✅ تم إنشاء الحساب بنجاح!\n"
                    f"👤 Username: `{username}`\n"
                    f"🔑 Password: `{password}`\n"
                    f"🆔 Player ID: `{player_id}`\n\n"
                    "⚠️ يُرجى تغيير كلمة مرور حسابك من خلال الموقع لحمايته!"
                )

                # ✅ Reset user state after successful registration
                context.user_data["state"] = None
                user_data.pop(user_id, None)  # Remove user from temporary state tracking
            
            else:
                await send_message("❌ فشل في إنشاء الحساب.")

        except mysql.connector.Error as err:
            print(f"❌ MySQL Error: {err}")
            await send_message("⚠️ حدث خطأ أثناء إنشاء الحساب. الرجاء المحاولة لاحقًا.")

        finally:
            cursor.close()
            conn.close()

        
        
#================================payment functions===============================================



#--------------------------------Syriatel cash payment function--------------------------------------------

async def handle_charge_syriatel_transaction_id(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str ):
   
    """Handles the Syriatel Cash transaction ID input from the user."""
    print("✅ Bot is expecting a syreatel cash transaction ID, processing...")  # Debugging
    
    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text  # ✅ Use update.message
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text  # ✅ Use update.callback_query.message
    else:
        return  # Prevent crashes if neither exists
    
    processing_sticker_id = "CAACAgIAAxkBAeLe02fdg4hbX96ODk5SRx08-jtV08apAALDPQACzBMpSoUPzZoaigNGNgQ"
    erorr_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"
    warning_sticker_id ="CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
    success_sticker_id="CAACAgIAAxkBAeLfjWfdhmXMrgLfaZJoEAWhTenCC6DrAALnNQACtoxBS2JmFwWrYLwGNgQ"
    syriatel_cash_transaction_id = update.message.text.strip()
    
    if context.user_data.get("state") != "expecting_syriatel_transaction_id":
        await update.message.reply_sticker(sticker=warning_sticker_id)
        await send_message("⚠️ إدخال غير متوقع! الرجاء اختيار طريقة الدفع أولاً.")
        return

    # Validate transaction ID format (12 or 15 digits)
    if not (syriatel_cash_transaction_id.isdigit() and len(syriatel_cash_transaction_id) in [12, 15]):
        await send_message(
            "❌ رقم العملية غير صالح!\n\n"
            "🔹 يجب أن يكون رقم العملية مكوناً من 12 رقمًا (مثال: `600000xxxxxx`)\n"
            "🔹 أو 15 رقمًا (مثال: `80000000xxxxxxx`)\n\n"
            "🔄 يرجى المحاولة مرة أخرى وإرسال رقم صحيح!",
            parse_mode="Markdown"
        )
        return

     # ✅ Connect to the database
    conn = connect_db()
    cursor = conn.cursor()

    try:
        
        # ✅ Check if the transaction ID already exists
        cursor.execute("SELECT status FROM transactions WHERE external_transaction_id = %s", (syriatel_cash_transaction_id,))
        existing_transaction = cursor.fetchone()

        if existing_transaction:
          transaction_status = existing_transaction[0]  # Extract the status

          if transaction_status == "pending":
            await update.message.reply_sticker(sticker=processing_sticker_id)
            await send_message("⚠️ هذه العملية قيد المعالجة..\n\n"
                           "⏳ يرجى الانتظار حتى اكتمالها 🫡", 
                           parse_mode="Markdown")
          else:
            await update.message.reply_sticker(sticker=erorr_sticker_id)
            await send_message("❌ رقم العملية الذي أدخلته موجود بالفعل!\n\n"
                           "🔹 يرجى التحقق من رقم العملية والمحاولة مجددًا.", 
                           parse_mode="Markdown")
          return  # Stop further execution
        
        # ✅ Fetch player ID from accounts table
        cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            await send_message("❌ لم يتم العثور على حسابك. يرجى إنشاء حساب أولاً.", parse_mode="Markdown")
            return

        player_id = result[0]  # Extract player_id safely

        # ✅ Insert transaction into database
        cursor.execute(
            "INSERT INTO transactions (external_transaction_id, user_id, player_id, transaction_type, payment_method, status) "
            "VALUES (%s, %s, %s, 'deposit', 'Syriatel', 'pending')",
            (syriatel_cash_transaction_id, user_id, player_id)
        )

        conn.commit()  # ✅ Save changes

         # ✅ Store transaction ID in user context
        context.user_data["pending_transaction_id"] = syriatel_cash_transaction_id
        context.user_data["state"] = "awaiting_deposit_amount"
        
        await update.message.reply_sticker(sticker=success_sticker_id)
        await send_message(
            f"✅ تم تسجيل رقم العملية بنجاح!\n\n"
            f"💵 رقم العملية: `{syriatel_cash_transaction_id}`\n"
            
            ,parse_mode="Markdown"
        )
        
        await send_message(f"🔢 هلأ دخّل المبلغ اللي حولته بالليرة السورية. 💰",parse_mode="Markdown")
        
        
    except Exception as e:
        print(f"❌ Database Error: {e}")  # Log error
        await send_message("❌ حدث خطأ أثناء تسجيل الطلب. يرجى المحاولة لاحقاً.", parse_mode="Markdown")

    finally:
        cursor.close()
        conn.close()  # ✅ Always close the database connection

    
    
# ------>> here call the function that check if the transaction is validated(def check_syreatel_cash_transaction_validation) 
# ------>> then the function update the user's bot_balance with the amount extracted form the sms 
   
 #--------------------------------payeer payment function----------------------------------------------------------



async def handle_charge_payeer_transaction_id(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """Handle user input when they send a Payeer transaction ID."""
    

    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text  # ✅ Use update.message
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text  # ✅ Use update.callback_query.message
    else:
        return  # Prevent crashes if neither exists

    charge_payeer_transaction_id = update.message.text.strip()
    processing_sticker_id = "CAACAgIAAxkBAeLe02fdg4hbX96ODk5SRx08-jtV08apAALDPQACzBMpSoUPzZoaigNGNgQ"
    erorr_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"
    warning_sticker_id ="CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
    success_sticker_id="CAACAgIAAxkBAeLfjWfdhmXMrgLfaZJoEAWhTenCC6DrAALnNQACtoxBS2JmFwWrYLwGNgQ"
    print("📩 Received message:", charge_payeer_transaction_id)  # Debugging

    # Ensure bot is expecting a transaction ID
    if context.user_data.get("state") != "expecting_payeer_transaction_id":
        await update.message.reply_sticker(sticker=warning_sticker_id)
        await send_message("⚠️ إدخال غير متوقع! الرجاء اختيار طريقة الدفع أولاً.")
        return
    
    print("✅ Bot is expecting a transaction ID, processing...")  # Debugging

    # Validate the transaction ID (must be 10 digits)
    if not charge_payeer_transaction_id.isdigit() or len(charge_payeer_transaction_id) != 10:
        await update.message.reply_sticker(sticker=erorr_sticker_id)
        await send_message("⚠️ رقم العملية غير صحيح! يجب أن يكون 10 أرقام، مثال: 210573xxxx")
        return
    

     # ✅ Connect to the database
    conn = connect_db()
    cursor = conn.cursor()

    try:
        
        # ✅ Check if the transaction ID already exists
        cursor.execute("SELECT status FROM transactions WHERE external_transaction_id = %s", (charge_payeer_transaction_id,))
        existing_transaction = cursor.fetchone()

        if existing_transaction:
          transaction_status = existing_transaction[0]  # Extract the status

          if transaction_status == "pending":
            await update.message.reply_sticker(sticker=processing_sticker_id)
            await send_message("⚠️ هذه العملية قيد المعالجة..\n\n"
                           "⏳ يرجى الانتظار حتى اكتمالها 🫡", 
                           parse_mode="Markdown")
          else:
            await update.message.reply_sticker(sticker=erorr_sticker_id)
            await send_message("❌ رقم العملية الذي أدخلته موجود بالفعل!\n\n"
                           "🔹 يرجى التحقق من رقم العملية والمحاولة مجددًا.", 
                           parse_mode="Markdown")
          return  # Stop further execution
        
        # ✅ Fetch player ID from accounts table
        cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            await send_message("❌ لم يتم العثور على حسابك. يرجى إنشاء حساب أولاً.", parse_mode="Markdown")
            return

        player_id = result[0]  # Extract player_id safely

        # ✅ Insert transaction into database
        cursor.execute(
            "INSERT INTO transactions (external_transaction_id, user_id, player_id, transaction_type, payment_method, status) "
            "VALUES (%s, %s, %s, 'deposit', 'Payeer', 'pending')",
            (charge_payeer_transaction_id, user_id, player_id)
        )

        conn.commit()  # ✅ Save changes

         # ✅ Store transaction ID in user context
        context.user_data["pending_transaction_id"] = charge_payeer_transaction_id
        context.user_data["method"] = "Payeer"
        context.user_data["state"] = "awaiting_deposit_amount"
        
        await update.message.reply_sticker(sticker=success_sticker_id)
        await send_message(
            f"✅ تم تسجيل رقم العملية بنجاح!\n\n"
            f"💵 رقم العملية: `{charge_payeer_transaction_id}`\n"
            
            ,parse_mode="Markdown"
        )
        
        await send_message(f"🔢 اهلأ دخّل المبلغ اللي حولته  USD  💰",parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Database Error: {e}")  # Log error
        await update.message.reply_sticker(sticker=erorr_sticker_id)
        await send_message("❌ حدث خطأ أثناء تسجيل الطلب. يرجى المحاولة لاحقاً.", parse_mode="Markdown")

    finally:
        cursor.close()
        conn.close()  # ✅ Always close the database connection

    
    

    # Acknowledge the user
    

# ------>> here call the function that check if the transaction is validated(def check_payeer_transaction_validation) 
# ------>> then the function (def check_payeer_transaction_validation) update the user's bot_balance with the amount extracted form payeer API call 
    
#--------------------------------Bemo payment function--------------------------------------------

    
async def handle_charge_bemo_transaction_id(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """Handles the Bemo Cash transaction ID input from the user and stores it in the database."""

    print("✅ Bot is expecting a Bemo transaction ID, processing...")  # Debugging

    # ✅ Detect message source
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists

    bemo_transaction_id = update.message.text.strip()
    processing_sticker_id = "CAACAgIAAxkBAeLe02fdg4hbX96ODk5SRx08-jtV08apAALDPQACzBMpSoUPzZoaigNGNgQ"
    erorr_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"
    warning_sticker_id ="CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
    success_sticker_id="CAACAgIAAxkBAeLfjWfdhmXMrgLfaZJoEAWhTenCC6DrAALnNQACtoxBS2JmFwWrYLwGNgQ"
    
    # Ensure bot is expecting a transaction ID
    if context.user_data.get("state") != "expecting_bemo_transaction_id":
        await update.message.reply_sticker(sticker=warning_sticker_id)
        await send_message("⚠️ إدخال غير متوقع! الرجاء اختيار طريقة الدفع أولاً.")
        return

    # ✅ Validate transaction ID format (must be 9 digits)
    if not (bemo_transaction_id.isdigit() and len(bemo_transaction_id) == 9):
        await update.message.reply_sticker(sticker=erorr_sticker_id)
        await send_message(
            "❌ رقم العملية غير صالح!\n\n"
            "🔹 يجب أن يكون رقم العملية مكوناً من 9 أرقام (مثال: `600000123`)\n\n"
            "🔄 يرجى المحاولة مرة أخرى وإرسال رقم صحيح!",
            parse_mode="Markdown"
        )
        return

    

    # ✅ Connect to the database
    conn = connect_db()
    cursor = conn.cursor()

    try:
        
        # ✅ Check if the transaction ID already exists and get its status
        cursor.execute("SELECT status FROM transactions WHERE external_transaction_id = %s", (bemo_transaction_id,))
        existing_transaction = cursor.fetchone()

        if existing_transaction:
          transaction_status = existing_transaction[0]  # Extract the status

          if transaction_status == "pending":
            await update.message.reply_sticker(sticker=processing_sticker_id)
            await send_message("⚠️ هذه العملية قيد المعالجة..\n\n"
                           "⏳ يرجى الانتظار حتى اكتمالها 🫡", 
                           parse_mode="Markdown")
          else:
            await update.message.reply_sticker(sticker=erorr_sticker_id)
            await send_message("❌ رقم العملية الذي أدخلته موجود بالفعل!\n\n"
                           "🔹 يرجى التحقق من رقم العملية والمحاولة مجددًا.", 
                           parse_mode="Markdown")
          return  # Stop further execution

        
        
        # ✅ Fetch player ID from accounts table
        cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            await update.message.reply_sticker(sticker=erorr_sticker_id)
            await send_message("❌ لم يتم العثور على حسابك. يرجى إنشاء حساب أولاً.", parse_mode="Markdown")
            return

        player_id = result[0]  # Extract player_id safely

        # ✅ Insert transaction into database
        cursor.execute(
            "INSERT INTO transactions (external_transaction_id, user_id, player_id, transaction_type, payment_method, status) "
            "VALUES (%s, %s, %s, 'deposit', 'Bemo', 'pending')",
            (bemo_transaction_id, user_id, player_id)
        )

        conn.commit()  # ✅ Save changes

         # ✅ Store transaction ID in user context
        context.user_data["pending_transaction_id"] = bemo_transaction_id
        context.user_data["state"] = "awaiting_deposit_amount"
        
        await update.message.reply_sticker(sticker=success_sticker_id)
        await send_message(
            f"✅ تم تسجيل رقم العملية بنجاح!\n\n"
            f"💵 رقم العملية: `{bemo_transaction_id}`\n"
            
            ,parse_mode="Markdown"
        )
        
        await send_message(f"🔢 هلأ دخّل المبلغ اللي حولته بالليرة السورية. 💰",parse_mode="Markdown")

    except Exception as e:
        print(f"❌ Database Error: {e}")  # Log error
        await send_message("❌ حدث خطأ أثناء تسجيل الطلب. يرجى المحاولة لاحقاً.", parse_mode="Markdown")

    finally:
        cursor.close()
        conn.close()  # ✅ Always close the database connection

    
    
    

   
 
 
 
async def handle_deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user input for deposit amount and updates the transaction record."""
    
    # ✅ Detect message source
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  

    deposit_amount_text = update.message.text.strip()
    processing_sticker_id = "CAACAgIAAxkBAeLfTGfdhXlPLdyMr_PA2nAxtCwOq8CwAAISNQACx6ehSqkeK7OWc836NgQ"
    aproved_sticker_id = "CAACAgIAAxkBAeLfjWfdhmXMrgLfaZJoEAWhTenCC6DrAALnNQACtoxBS2JmFwWrYLwGNgQ"

    # ✅ Ensure user is in the correct state
    if context.user_data.get("state") != "awaiting_deposit_amount":
        return 
    # ✅ Validate deposit amount
    if not deposit_amount_text.replace(".", "", 1).isdigit():  # Allow decimals
        await send_message("❌ المبلغ غير صالح!\n\n"
                           "🔹 يرجى إدخال رقم صحيح يمثل المبلغ (مثل: 10000 أو 150.5)",
                           parse_mode="Markdown")
        return

    deposit_amount = float(deposit_amount_text)

    if deposit_amount <= 0:
        await send_message("❌ يجب أن يكون المبلغ أكبر من 0!", parse_mode="Markdown")
        return

    # ✅ Retrieve pending transaction ID
    transaction_id = context.user_data.get("pending_transaction_id")
    method = context.user_data.get("method")

    if not transaction_id:
        await send_message("❌ لا يوجد طلب إيداع معلق مرتبط بك! أعد إدخال رقم العملية.", parse_mode="Markdown")
        return

    # ✅ Update transaction with amount
    conn = connect_db()
    cursor = conn.cursor()

    try:
        if method == "Payeer":
            deposit_amount = exchange_rate
            cursor.execute("""
            UPDATE transactions 
            SET amount = %s
            WHERE external_transaction_id = %s AND user_id = %s
        """, (deposit_amount, transaction_id, user_id))

            conn.commit()
            await update.message.reply_sticker(sticker=processing_sticker_id)
            await send_message(
            f"✅ تم تسجيل المبلغ بنجاح!\n\n"
            f"💰 المبلغ: `{deposit_amount}` SYP\n"
            f"⏳ في انتظار الموافقة على الطلب...",
            parse_mode="Markdown"
            )
            
            
        else:
         cursor.execute("""
            UPDATE transactions 
            SET amount = %s
            WHERE external_transaction_id = %s AND user_id = %s
         """, (deposit_amount, transaction_id, user_id))

         conn.commit()
         
         await update.message.reply_sticker(sticker=processing_sticker_id)   
         await send_message(
            f"✅ تم تسجيل المبلغ بنجاح!\n\n"
            f"💰 المبلغ: `{deposit_amount}` SYP\n"
            f"⏳ في انتظار الموافقة على الطلب...",
            parse_mode="Markdown"
         )

    except Exception as e:
        print(f"❌ Database Error: {e}")  
        await send_message("❌ حدث خطأ أثناء تسجيل المبلغ. يرجى المحاولة لاحقًا!", parse_mode="Markdown")

    finally:
        cursor.close()
        conn.close()

    # ✅ Reset user state
    context.user_data["state"] = None
    context.user_data.pop("pending_transaction_id", None)
    result = verify_transaction_from_user_input(transaction_id,user_id)
    if "error" in result:
     await send_message(result["error"])
     
    else:
     keyboard = [
                [InlineKeyboardButton("🌐 WayXbet الانتقال الى موقع ", url="https://m.wayxbet.com/en/")],
                [InlineKeyboardButton("💰 شحن الحساب", callback_data='charge_website_account'), 
                 InlineKeyboardButton("💸 سحب رصيد الحساب", callback_data='withdraw_website')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
            ]
     reply_markup = InlineKeyboardMarkup(keyboard)
     await update.message.reply_sticker(sticker=aproved_sticker_id)
     await send_message(f" ✅ تم تعبئة محفطة البوت \n"
                        f"Good Luck 🔥💫"
                        ,reply_markup=reply_markup, parse_mode="Markdown")

#This function is triggered when an SMS is received via forwarding.


async def process_sms(sms_text, update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
    """Extract transaction details from SMS and verify against pending transactions."""
    bot = Bot(token= BOT_TOKEN)
    print("📩 Processing new SMS...")

    # ✅ Detect message source (Reply in Bot Chat)
    user_id = None  # Default if triggered by an SMS
    send_message = None

    if update and context:
        if update.message:
            user_id = update.message.from_user.id
            send_message = update.message.reply_text
        elif update.callback_query:
            user_id = update.callback_query.from_user.id
            send_message = update.callback_query.message.reply_text

    # ✅ Step 1: Remove "From: ..." if it exists
    sms_text = re.sub(r"^From : .+\n", "", sms_text)
    print(f"🔍 Cleaned SMS Text: {sms_text}")

    # ✅ Step 2: Check both patterns (Bemo & Syriatel Cash)
    pattern_bemo = r"استلام حوالة الكترونية (\d+)ل.س من (.+?)،رقم العملية (\d{9})"
    pattern_syriatel = r"تم استلام مبلغ (\d+) ل.س بنجاح. رقم العملية هو (\d{12})"

    match_bemo = re.search(pattern_bemo, sms_text)
    match_syriatel = re.search(pattern_syriatel, sms_text)

    if match_bemo:
        print("✅ Matched Pattern: Bemo Bank")
        sms_amount = float(match_bemo.group(1))
        sender_name = match_bemo.group(2)
        sms_transaction_id = match_bemo.group(3)
    elif match_syriatel:
        print("✅ Matched Pattern: Syriatel Cash")
        sms_amount = float(match_syriatel.group(1))
        sender_name = "Syriatel Cash"
        sms_transaction_id = match_syriatel.group(2)
    else:
        print("❌ SMS format does not match expected patterns")
        if send_message:
            await send_message("❌ رسالة غير متوافقة مع النمط المطلوب.", parse_mode="Markdown")
        return {"error": "❌ رسالة غير متوافقة مع النمط المطلوب"}

    print(f"✅ Extracted Data: Transaction ID={sms_transaction_id}, Amount={sms_amount}, Sender={sender_name}")

    # ✅ Step 3: Connect to MySQL
    try:
        conn = connect_db()
        cursor = conn.cursor()
        print("✅ Database connection established.")

        # ✅ Step 4: Check if the transaction exists in `transactions`
        cursor.execute("SELECT user_id, amount, status FROM transactions WHERE external_transaction_id = %s", (sms_transaction_id,))
        transaction = cursor.fetchone()

        if transaction:
            db_user_id, db_amount, status = transaction
            print(f"✅ Transaction found: User ID={db_user_id}, Status={status}")

            # ✅ Step 5: Verify transaction status
            if status != "pending":
                print("⚠️ Transaction is already verified or completed.")
                if db_user_id:
                    await bot.send_message(
                        chat_id=db_user_id,
                        text=
                        f"⚠️ هذه العملية تمت معالجتها بالفعل، لا يمكنك إضافتها مرة أخرى.", parse_mode="Markdown")
                return {"error": "⚠️ هذه العملية تمت معالجتها بالفعل."}

            # ✅ Step 6: Verify transaction amount
            if db_amount != sms_amount:
                print("❌ Transaction amount does not match!")
                if db_user_id:
                    await bot.send_message(
                        chat_id=db_user_id,
                        text=
                        f"❌ خطأ في المبلغ!.. تاكد من المبلغ وحاول مرة اخرى", parse_mode="Markdown")
                    cursor.execute("DELETE FROM transactions where external_transaction_id =%s",(sms_transaction_id,))
                    cursor.execute("INSERT INTO sms_logs (transaction_id, amount, sender_phone) VALUES (%s, %s, %s)", 
                        (sms_transaction_id, sms_amount, sender_name))

                    conn.commit()
                return {"error": "❌ المبلغ غير مطابق!"}

            # ✅ Step 7: Approve transaction and update user balance
            cursor.execute("""
                UPDATE transactions 
                SET status = 'approved', verification_source = 'SMS' 
                WHERE external_transaction_id = %s
            """, (sms_transaction_id,))

            cursor.execute("UPDATE wallets SET bot_balance = bot_balance + %s WHERE user_id = %s", (sms_amount, db_user_id))
            conn.commit()

            print(f"✅ Transaction {sms_transaction_id} verified and balance updated!")

            # ✅ Notify user inside the bot chat
            keyboard = [
                [InlineKeyboardButton("🌐 WayXbet الانتقال الى موقع ", url="https://m.wayxbet.com/en/")],
                [InlineKeyboardButton("💰 شحن الحساب", callback_data='charge_website_account'), 
                InlineKeyboardButton("💸 سحب رصيد الحساب", callback_data='withdraw_website')],
                [InlineKeyboardButton("🔙 رجوع", callback_data='back')]
                ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if db_user_id:
             await bot.send_message(
             chat_id=db_user_id,
             text=f"✅ تم تأكيد عمليتك بنجاح!\n\n💰 المبلغ: `{sms_amount}` ل.س\n📌 رقم العملية: `{sms_transaction_id}`",
             parse_mode="Markdown",
             reply_markup=reply_markup  # ✅ Include the inline keyboard
             )

            # ✅ Reset user state
            if context:
                context.user_data["state"] = None

            return {"success": f"✅ تم تأكيد العملية وإضافة {sms_amount} ل.س إلى رصيدك!"}

        else:
            print(f"⚠️ Transaction {sms_transaction_id} not found, saving to `sms_logs`...")
            cursor.execute("INSERT INTO sms_logs (transaction_id, amount, sender_phone) VALUES (%s, %s, %s)", 
                        (sms_transaction_id, sms_amount, sender_name))
            conn.commit()

            return {"info": "⚠️ العملية غير موجودة، تم حفظها للمراجعة لاحقًا."}

    except Exception as e:
        print(f"❌ Database Error: {e}")
        return {"error": f"❌ خطأ في النظام: {str(e)}"}

    finally:
        cursor.close()
        conn.close()
        print("✅ Database connection closed.")





def verify_transaction_from_user_input(transaction_id, user_id):
    """Verify a transaction when the user enters the transaction ID manually."""
    
    conn = connect_db()
    cursor = conn.cursor()
    
    
    
    # ✅ Check if transaction already exists in `transactions`
    cursor.execute("SELECT amount, status FROM transactions WHERE external_transaction_id = %s AND user_id = %s", 
                   (transaction_id, user_id))
    transaction = cursor.fetchone()

    if transaction:
        amount, status = transaction

        if status != "pending":
            conn.close()
            return {"error": "Transaction is already verified or completed"}

        # ✅ Check if SMS has already been received
        cursor.execute("SELECT amount FROM sms_logs WHERE transaction_id = %s", (transaction_id,))
        sms_entry = cursor.fetchone()

        if sms_entry:
            sms_amount = sms_entry[0]

            if sms_amount != amount:
                cursor.execute("DELETE FROM transactions WHERE external_transaction_id = %s",(transaction_id,))
                conn.commit()  # ✅ Commit the deletion
                conn.close()
                return {"error": "المبلغ في الرسالة النصية لا يتطابق مع المبلغ المُدخل للمعاملة ❌⚠️ يرجى التحقق والمحاولة مرة أخرى 🔄✅"}

            # ✅ Approve the transaction & credit balance
            cursor.execute("""
                UPDATE transactions 
                SET status = 'approved', verification_source = 'SMS' 
                WHERE external_transaction_id = %s
            """, (transaction_id,))
            
            cursor.execute("UPDATE wallets SET bot_balance = bot_balance + %s WHERE user_id = %s", (amount, user_id))

            # ✅ Delete from `sms_logs` since it's now verified
            cursor.execute("DELETE FROM sms_logs WHERE transaction_id = %s", (transaction_id,))
            conn.commit()
            conn.close()

            return {"success": True, "message": f"Transaction {transaction_id} verified via SMS logs and balance updated!"}

        else:
            conn.close()
            return {
                        "error": "🔄 العملية قيد المعالجة... يُرجى الانتظار حتى اكتمالها.\n"
                         "⏳ إذا لم تكتمل خلال 10 دقائق، حاول مرة أخرى.\n"
                         "❌ قد يكون رقم العملية غير صحيح.\n"
                         "📞 في حال كان الرقم صحيحًا ولم تكتمل العملية خلال 20 دقيقة ، يُرجى التواصل مع الدعم."
                    }


#==================================== website_charge_amount handler ============================

async def handle_website_charge_amount_From_Bot(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """Handles user input for charging their website account, prioritizing game winnings, and using bot balance if needed."""

    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists

    amount_text = update.message.text.strip()
    processing_sticker_id = "CAACAgIAAxkBAeLe02fdg4hbX96ODk5SRx08-jtV08apAALDPQACzBMpSoUPzZoaigNGNgQ"
    error_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"
    success_sticker_id="CAACAgIAAxkBAeLaJGfddT5-nwAB0D9SFNMeScLbCI3V1QACfz0AAi3JKUp2tyZPFVNcFzYE"
    # ✅ Step 1: Prevent duplicate requests
    if context.user_data.get("processing_transaction"):
        await update.message.reply_sticker(sticker=processing_sticker_id)
        await send_message("⏳ لديك معاملة جارية بالفعل. يرجى الانتظار حتى تكتمل.")
        return

    # ✅ Step 2: Lock the process
    context.user_data["processing_transaction"] = True

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # ✅ Validate amount
        if not amount_text.isdigit():
            await update.message.reply_sticker(sticker=error_sticker_id)
            await send_message("⚠️ المبلغ يجب أن يكون رقمًا صحيحًا!", parse_mode="Markdown")
            return

        amount = int(amount_text)

        if amount <= 0:
            await update.message.reply_sticker(sticker=error_sticker_id)
            await send_message("⚠️ المبلغ يجب أن يكون أكبر من 0 SYP", parse_mode="Markdown")
            return

        # ✅ Fetch user's balances
        cursor.execute("SELECT bot_balance, game_balance FROM wallets WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            await send_message("❌ لم يتم العثور على حساب المحفظة الخاص بك!", parse_mode="Markdown")
            return

        bot_balance, game_balance = result

        total_available_balance = bot_balance + game_balance

        if amount > total_available_balance:
            await update.message.reply_sticker(sticker=error_sticker_id)
            await send_message("⚠️ رصيدك غير كافٍ لهذا التحويل!", parse_mode="Markdown")
            return

        # ✅ Step 3: Determine how to deduct balance
        game_used = min(amount, game_balance)  # Use game_balance first
        bot_used = amount - game_used  # If more is needed, use bot_balance

        # ✅ Step 4: Deposit to player's website account FIRST
        await update.message.reply_sticker(sticker=processing_sticker_id)
        await send_message("🔄 جارٍ تنفيذ عملية الشحن... يرجى الانتظار!", parse_mode="Markdown")

        deposit_result = deposit_to_player(user_id, amount)

        if deposit_result.get("success"):
            # ✅ Step 5: Update balances in the database
            new_game_balance = game_balance - game_used
            new_bot_balance = bot_balance - bot_used

            cursor.execute("UPDATE wallets SET game_balance = %s, bot_balance = %s WHERE user_id = %s", 
                           (new_game_balance, new_bot_balance, user_id))
            conn.commit()

            # ✅ Fetch the user's current website balance
            balance_details = fetch_player_balance(user_id)

            if "error" in balance_details:
                await send_message(f"❌ خطأ في جلب الرصيد: {balance_details['error']}", parse_mode="Markdown")
                return

            new_website_balance = balance_details["balance"]

            cursor.execute("UPDATE wallets SET website_balance = %s WHERE user_id = %s", 
                           (new_website_balance, user_id))
            conn.commit()
             
            if amount >= 100000:
             cursor.execute("select game_points from wallets where user_id = %s",(user_id,))
             game_points=cursor.fetchone()[0]
             game_points += 10
             cursor.execute("update wallets set game_points = %s where user_id = %s",(game_points,user_id))
             conn.commit()

            success_message = (
                f"✅ تم تحويل المبلغ بنجاح إلى حسابك على الموقع!\n\n"
                f"💰 المبلغ المحول: `{amount}` SYP\n"
                f"🎰 رصيد أرباح اللعبة بعد الخصم: `{new_game_balance}` SYP\n"
                f"🤖 رصيدك في المحفظة بعد الخصم: `{new_bot_balance}` SYP\n"
                f"🌍 رصيدك في الموقع بعد التعبئة: `{new_website_balance}` SYP"
            )
            await update.message.reply_sticker(sticker=success_sticker_id)
            await send_message(success_message, parse_mode="Markdown")

        else:
            # ✅ Replace deposit failure message with a custom response
            error_message = f"❌ فشل في الإيداع في حساب الموقع!\n⚠️ السبب: {deposit_result['error']}"
            await send_message(error_message, parse_mode="Markdown")

    except Exception as e:
        await send_message(f"❌ حدث خطأ غير متوقع: `{str(e)}`", parse_mode="Markdown")

    finally:
        # ✅ Step 6: Unlock the process so the user can make another request
        context.user_data["processing_transaction"] = False
        cursor.close()
        conn.close()

#==================================== website_withdraw_amount handler ============================


async def handle_website_withdraw_amount_To_Bot(update: Update, context: ContextTypes.DEFAULT_TYPE, user_input: str):
    """Handles user input for website withdrawals while preventing duplicate requests."""

    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists

    amount_text = update.message.text.strip()
    processing_sticker_id = "CAACAgIAAxkBAeLe02fdg4hbX96ODk5SRx08-jtV08apAALDPQACzBMpSoUPzZoaigNGNgQ"
    error_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"
    success_sticker_id="CAACAgIAAxkBAeLaJGfddT5-nwAB0D9SFNMeScLbCI3V1QACfz0AAi3JKUp2tyZPFVNcFzYE"
    warning_sticker_id ="CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
     

    # ✅ Step 1: Prevent duplicate requests
    if context.user_data.get("processing_transaction"):
        await update.message.reply_sticker(sticker=processing_sticker_id)
        await send_message("⏳ لديك معاملة جارية بالفعل. يرجى الانتظار حتى تكتمل.", parse_mode="Markdown")
        return

    # ✅ Step 2: Lock the process
    context.user_data["processing_transaction"] = True

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # ✅ Validate amount
        if not amount_text.isdigit():
            await update.message.reply_sticker(sticker=error_sticker_id)
            await send_message("⚠️ المبلغ يجب أن يكون رقمًا صحيحًا!", parse_mode="Markdown")
            return

        withdrawal_amount = int(amount_text)

        if withdrawal_amount <= 0:
            await update.message.reply_sticker(sticker=error_sticker_id)
            await send_message("⚠️ المبلغ يجب أن يكون أكبر من 0!", parse_mode="Markdown")
            return

        # ✅ Fetch the user's current website balance
        balance_details = fetch_player_balance(user_id)

        if "error" in balance_details:
            await send_message(f"❌ خطأ في جلب الرصيد: {balance_details['error']}", parse_mode="Markdown")
            return

        website_balance = balance_details["balance"]

        # ✅ Validate withdrawal amount
        if withdrawal_amount > website_balance:
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_sticker(sticker=warning_sticker_id)
            await send_message(
                f"❌ رصيدك غير كافٍ! \n\n"
                f"💰 رصيد الموقع المتاح: `{website_balance}` {balance_details['currency']}\n"
                f"📌 يرجى إدخال مبلغ أقل أو مساوي لرصيدك.",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
            return

        # ✅ Step 3: Process the withdrawal request
        await update.message.reply_sticker(sticker=processing_sticker_id)
        await send_message("🔄 جارٍ تنفيذ عملية السحب... يرجى الانتظار!", parse_mode="Markdown")
        withdrawal_status = withdraw_from_website(user_id, withdrawal_amount)
        
        if withdrawal_status.get("success"):
            print("after the withdrawal call ")
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # ✅ Update the database: Deduct from website balance and add to bot wallet
            cursor.execute(
                "UPDATE wallets SET website_balance = website_balance - %s, bot_balance = bot_balance + %s WHERE user_id = %s",
                (withdrawal_amount, withdrawal_amount, user_id),
            )
            conn.commit()
            print("before the success message ")
            # ✅ Notify user about successful withdrawal
            await update.message.reply_sticker(sticker=success_sticker_id)
            await send_message(
                f"✅ تمت عملية السحب بنجاح!\n\n"
                f"💰 المبلغ المسحوب: `{withdrawal_amount}` SYP\n"
                f"💳 رصيد الموقع الجديد: `{website_balance - withdrawal_amount}` SYP\n"
                f"🤖 رصيدك في البوت: `{withdrawal_amount}`SYP",
                
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

        else:
            # ✅ Withdrawal failed
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data='back')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_sticker(sticker=error_sticker_id)
            await send_message(
                f"❌ فشلت عملية السحب!\n"
                f"📌 السبب: {withdrawal_status.get('error', 'خطأ غير معروف')}",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

    except Exception as e:
        await send_message(f"❌ حدث خطأ غير متوقع: `{str(e)}`", parse_mode="Markdown")

    finally:
        # ✅ Step 4: Unlock the process so the user can make another request
        context.user_data["processing_transaction"] = False
        cursor.close()
        conn.close()


#-------------------------------------handle_withdraw_amount_from_bot_to_user-------------------



   
    
#------------------------------------show last 5 transaction handler ----------------------------

async def handle_show_last_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and display the last 5 transactions when the user clicks the inline button."""
    
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # ✅ Fetch the last 5 transactions for the user
        cursor.execute("""
            SELECT amount, transaction_type, payment_method, status, timestamp 
            FROM transactions 
            WHERE user_id = %s 
            ORDER BY timestamp DESC 
            LIMIT 5
        """, (user_id,))
        transactions = cursor.fetchall()

        if not transactions:
            
            await query.edit_message_text("🔍 لا يوجد لديك أي معاملات حتى الآن.", parse_mode="Markdown")
            return

        # ✅ Format transaction history
        history = "\n\n".join([
            f"📅 التاريخ: `{t[4]}`\n"
            f"🔄 النوع: `{t[1]}`\n"
            f"💰 المبلغ: `{t[0]}` SYP\n"
            f"💳 طريقة الدفع: `{t[2] if t[2] else 'غير محددة'}`\n"
            f"📌 الحالة: `{t[3]}`"
            for t in transactions
        ])

        # ✅ Add a "Back to Menu" button
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"📜 آخر 5 معاملات لك:\n\n{history}",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    except Exception as e:
        await query.message.reply_text(f"❌ حدث خطأ غير متوقع: `{str(e)}`", parse_mode="Markdown")

    finally:
        cursor.close()
        conn.close()

    

#==================================== شحن الحساب function =======================================


def deposit_to_player(user_id, amount):
    """Deposits the specified amount to the user's website account before updating the database."""
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # ✅ Ensure agent session is active
        global agent_session
        if not agent_session and not login_as_agent():
            return {"error": "Agent login failed"}

        # ✅ Fetch player ID from the database
        cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            return {"error": "Player ID not found in database"}

        player_id = result[0]  # Extract player ID
        currency_code = "NSP"  # Ensure this is the correct currency

        # ✅ Prepare the request payload
        payload = {
            "amount": amount,
            "comment": None,
            "playerId": str(player_id),
            "currencyCode": currency_code,
            "currency": currency_code,
            "moneyStatus": 5
        }

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }

    except Exception as db_error:
        return {"error": f"Database error: {str(db_error)}"}

    finally:
        cursor.close()
        conn.close()

    # ✅ Send deposit request
    try:
        response = agent_session.post(DEPOSIT_URL, json=payload, headers=headers)
        response.raise_for_status()  # Raises an error if request fails
        data = response.json()

          # ✅ Handle success
        if data.get("status") and isinstance(data.get("result"), dict):
            return {"success": True, "message": "Deposit successful"}

        # ✅ Handle failure (extract error message properly)
        notifications = data.get("notification", [])
        if notifications and isinstance(notifications, list) and len(notifications) > 0:
            error_message = notifications[0].get("content", "Unknown error")
        else:
            error_message = "Unknown error (No notifications provided)"
        
        return {"error": error_message}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}


#==================================== withdrawal from the website  functions =======================================

def withdraw_from_website(user_id, amount):
    """Withdraw funds from the website account to the bot wallet."""
    
    conn = connect_db()
    cursor = conn.cursor()
    
    try:
        # ✅ Ensure agent session is active
        global agent_session
        if not agent_session and not login_as_agent():
            return {"error": "Failed to log in as agent"}

        # ✅ Fetch player_id from the database
        cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()

        if not result:
            return {"error": "User ID not found in accounts table"}

        player_id = result[0]  # Extract player_id

        # ✅ Fetch current website balance
        cursor.execute("SELECT website_balance FROM wallets WHERE user_id = %s", (user_id,))
        balance_result = cursor.fetchone()

        if not balance_result:
            return {"error": "Wallet not found"}
        
        website_balance = balance_result[0]

        # ✅ Validate if user has enough balance
        if amount > website_balance:
            return {"error": "Insufficient balance"}

        # ✅ Prepare withdrawal payload
        payload = {
            "amount": -amount,  # The API requires a negative amount
            "comment": None,
            "playerId": str(player_id),
            "currencyCode": "NSP",
            "currency": "NSP",
            "moneyStatus": 5
        }

        # ✅ Send the withdrawal request
        response = agent_session.post(WITHDRAW_WEBSITE_URL, json=payload)
        response.raise_for_status()  # Raise error if request fails
        data = response.json()

        # ✅ Handle API response properly
        if data.get("status") and isinstance(data.get("result"), dict):
            # ✅ Deduct from website balance and add to bot wallet
            cursor.execute(
                "UPDATE wallets SET website_balance = website_balance - %s, bot_balance = bot_balance + %s WHERE user_id = %s",
                (amount, amount, user_id)
            )

            # ✅ Log transaction
          
            return {"success": True, "message": f"Successfully withdrawn {amount} NSP from website to bot wallet!"}

        else:
            # ✅ Handle failure correctly
            notifications = data.get("notification", [])
            if notifications and isinstance(notifications, list) and len(notifications) > 0:
                error_message = notifications[0].get("content", "Unknown error")
            else:
                error_message = "Unknown error (No notifications provided)"
            
            return {"error": error_message}

    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}"}

    except Exception as db_error:
        return {"error": f"Database error: {str(db_error)}"}

    finally:
        cursor.close()
        conn.close()  # ✅ Ensure database connection is closed

#-------------------------------- withdrawal_from_bot_to_user function--------------------------------------------
async def process_withdrawal_amount_from_bot_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE, amount: str, method: str):
    """Handles withdrawals for different payment methods dynamically."""
    print("Processing withdrawal request...")
    conn = connect_db()
    cursor = conn.cursor()

    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists
    
   
    erorr_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"
    warning_sticker_id ="CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
    what_sticker_id ="CAACAgIAAxkBAeLkf2fdjvmHUYuWm-x2JOFH3xs--fgyAALUMAACmTChSgQ1fTazyf2VNgQ"
    
    # ✅ Convert amount safely
    try:
        amount = int(amount)
    except ValueError:
        await update.message.reply_sticker(sticker=erorr_sticker_id)
        await send_message("⚠️ المبلغ يجب أن يكون رقمًا صحيحًا!", parse_mode="Markdown")
        return

    # ✅ Ensure a method was selected
    if not method:
        await send_message("❌ لم يتم تحديد طريقة السحب!", parse_mode="Markdown")
        return

    # ✅ Fetch user balance
    cursor.execute("SELECT bot_balance FROM wallets WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()

    if not result:
        await send_message("❌ لم يتم العثور على حساب المحفظة الخاص بك!")
        return

    bot_balance = int(result[0])

    # ✅ Check if the user has enough balance
    if amount > bot_balance:
        await update.message.reply_sticker(sticker=warning_sticker_id)
        await send_message("⚠️ رصيدك في المحفظة غير كافٍ لهذا السحب!")
        return

    # ✅ Handle Payeer (USD to SYP conversion)
    if method == "payeer":
        print("Method is Payeer")

        # ✅ Ensure exchange rate is defined
        global exchange_rate
        if not exchange_rate:
            await send_message("❌ خطأ في سعر الصرف، يرجى المحاولة لاحقًا.")
            return

        USD_to_SYP = round(amount * exchange_rate)

        if USD_to_SYP > bot_balance:
            await update.message.reply_sticker(sticker=warning_sticker_id)
            await send_message("⚠️ رصيدك في المحفظة غير كافٍ لهذا السحب!")
            return

        # ✅ Store the converted amount before continuing
        context.user_data["withdraw_amount"] = USD_to_SYP

        # ✅ Define confirmation keyboard
        keyboard = [
            [InlineKeyboardButton("✔ تأكيد", callback_data=f"confirm_withdraw_{USD_to_SYP}_{method}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # ✅ Send confirmation message for Payeer
        withdrawal_message = (
            f"💵 سعر الصرف:  Payeer 1 USD = {exchange_rate} SYP\n\n"
            f"⚠️ هل أنت متأكد من سحب {USD_to_SYP} SYP عبر {method.upper()}؟\n\n"
            f"💰 نظام الرسوم على عمليات السحب: \n"
            f"🔹 5٪ - على كل عملية سحب\n\n"
            f"⚠️ يتم خصم الرسوم تلقائيًا عند تنفيذ الطلب."
        )
        await update.message.reply_sticker(sticker=what_sticker_id)
        await send_message(withdrawal_message, reply_markup=reply_markup, parse_mode="Markdown")

    else:
        # ✅ Store the withdrawal amount before confirmation
        context.user_data["withdraw_amount"] = amount

        # ✅ Define confirmation keyboard
        keyboard = [
            [InlineKeyboardButton("✔ تأكيد", callback_data=f"confirm_withdraw_{amount}_{method}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_withdraw")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # ✅ Send confirmation message for normal withdrawals (Bemo, Syriatel, etc.)
        withdrawal_message = (
            f"⚠️ هل أنت متأكد من سحب {amount} SYP عبر {method.upper()}؟\n\n"
            f"💰 نظام الرسوم على عمليات السحب: \n"
            f"🔹 5٪ - على كل عملية سحب\n\n"
            f"⚠️ يتم خصم الرسوم تلقائيًا عند تنفيذ الطلب."
        )
        await update.message.reply_sticker(sticker=what_sticker_id)
        await send_message(withdrawal_message, reply_markup=reply_markup, parse_mode="Markdown")

    # ✅ Set state for confirmation
    context.user_data["state"] = "confirm_withdraw"

    # ✅ Close database connection
    cursor.close()
    conn.close()




async def finalize_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Calculates fees, updates transaction status, and confirms withdrawal request."""
    conn = connect_db()
    cursor = conn.cursor(dictionary=True)  # Using dictionary=True to fetch data as dict
    query = update.callback_query
    
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text  # ✅ Use update.message
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text  # ✅ Use update.callback_query.message
    else:
        return 
    success_sticker_id="CAACAgIAAxkBAeLfjWfdhmXMrgLfaZJoEAWhTenCC6DrAALnNQACtoxBS2JmFwWrYLwGNgQ"
    erorr_sticker_id ="CAACAgIAAxkBAeLfqGfdhv5zCSIhUgJGjM6LbmkaIB9wAAJxOwACtUNZSjpcwC49bZ4dNgQ"

    # Retrieve stored withdrawal details
    amount = context.user_data.get("withdraw_amount")
    method = context.user_data.get("withdraw_method")
    account_number = context.user_data.get("account_number")

    if not amount or not method or not account_number:
        await update.message.reply_sticker(sticker=success_sticker_id)
        await send_message("❌ حدث خطأ! تأكد من إدخال جميع البيانات بشكل صحيح.", parse_mode="Markdown")
        return

    # Convert amount to integer if it's stored as a string
    try:
        amount = int(amount)
    except ValueError:
        await update.message.reply_sticker(sticker=success_sticker_id)
        await send_message("❌ المبلغ غير صالح!", parse_mode="Markdown")
        return

    # Calculate withdrawal fees
    
    fee_percentage = 0.05

    fee = round(amount * fee_percentage)
    final_amount = amount - fee

    # Prevent final_amount from being negative
    if final_amount < 0:
        await update.message.reply_sticker(sticker=success_sticker_id)
        await send_message("❌ المبلغ النهائي غير صالح، يرجى مراجعة التفاصيل!", parse_mode="Markdown")
        return

    try:
        # Deduct balance from bot wallet
        cursor.execute("SELECT bot_balance FROM wallets WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        bot_balance = result["bot_balance"] if result else 0

        if bot_balance < final_amount:
            await update.message.reply_sticker(sticker=success_sticker_id)
            await send_message("❌ رصيدك غير كافٍ للسحب!", parse_mode="Markdown")
            return

        cursor.execute("UPDATE wallets SET bot_balance = bot_balance - %s WHERE user_id = %s", (final_amount, user_id))
        # Fetch player_id correctly
        cursor.execute("SELECT player_id FROM accounts WHERE user_id = %s", (user_id,))
        player_id_result = cursor.fetchone()
        player_id = player_id_result["player_id"] if player_id_result else None

# Ensure player_id exists
        if player_id is None:
            await send_message("❌ لا يوجد Player ID مرتبط بحسابك!", parse_mode="Markdown")
            return

# Insert transaction details (with player_id properly extracted)
        cursor.execute("INSERT INTO transactions (user_id, amount, player_id, transaction_type, status, payment_method, account_number, fee, final_amount) "
            "VALUES (%s, %s, %s, 'withdrawal', 'approved', %s, %s, %s, %s)",
         (user_id, amount, player_id, method, account_number, fee, final_amount)
)


        conn.commit()

        # Notify the user
        await update.message.reply_sticker(sticker=success_sticker_id)
        await send_message(
            f"✅ طلب السحب قيد المعالجة! 🏦\n\n"
            f"💳 طريقة السحب: `{method.upper()}`\n"
            f"💰 المبلغ المطلوب: `{amount}` SYP\n"
            f"🧾 الرسوم: `{fee}` SYP\n"
            f"📉 المبلغ النهائي: `{final_amount}` SYP\n"
            f"🏦 رقم الحساب: `{account_number}`\n\n"
            f"⌛ سيتم تنفيذ الطلب خلال 24 ساعة.",
            parse_mode="Markdown"
        )

    except mysql.connector.Error as err:
        await send_message(f"❌ خطأ في قاعدة البيانات: {err}", parse_mode="Markdown")
        conn.rollback()  # Rollback on failure

    finally:
        cursor.close()
        conn.close()


async def start_slot_machine(update: Update, context: ContextTypes.DEFAULT_TYPE):
     """Start the slot machine game and send a sticker animation."""
     user_id = update.callback_query.from_user.id
     chat_id = update.callback_query.message.chat_id  # Get chat ID
 
     
 
     # ✅ Connect to the database
     conn = connect_db()
     cursor = conn.cursor()
     
     cursor.execute("update wallets set game_points = game_points - 1 where user_id = %s", (user_id,))
     conn.commit()
     
     cursor.execute("select game_points from wallets where user_id = %s",(user_id,))
     game_points = cursor.fetchone()[0]
     print (f"{game_points}")
     if game_points == 0 :
         slot_sticker_id = "CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
         await context.bot.send_sticker(chat_id=chat_id, sticker=slot_sticker_id)# if the game status = 0 that's mean that the player reached his limits 
         await update.callback_query.message.reply_text(
             "⚠️ ما معك نقاط كفاية لتلعب 🎮💔\n\n"
             "لازم تشحن حسابك بـ WayXbet مشان تجمع نقاط ✨\n\n"
             "🔹 كل عملية شحن فوق 100,000 ل.س بتعطيك 10 نقاط 🎁\n\n"
             "🔹 كل نقطة بتخليك تعمل سبين باللعبة 🎰 \n\n"
             "يلا اشحن وجمّع نقاطك! 💪🔥",
             parse_mode="Markdown"
         )
         conn.close()
         
     
     
     
     cursor.execute("SELECT SUM(total_game_balance) FROM wallets")
     updated_total_game_balance = cursor.fetchone()[0] or 0
     print(f"{updated_total_game_balance}")
     if updated_total_game_balance >= 1000000:
         slot_sticker_id = "CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
         await context.bot.send_sticker(chat_id=chat_id, sticker=slot_sticker_id)
         message = "\n\n🚫 اللعبة مقفلة الآن! وصلت جميع الجوائز إلى الحد الأقصى (1,000,000 SYP)."
         # ✅ Send result message
         keyboard = [[InlineKeyboardButton("🔄 لعب مرة أخرى", callback_data="slot_machine")]]
         reply_markup = InlineKeyboardMarkup(keyboard)
 
         await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")
         conn.close()
     
     
     
         
 
     # ✅ Check user's game balance
     cursor.execute("SELECT game_balance FROM wallets WHERE user_id = %s", (user_id,))
     game_balance = cursor.fetchone()
 
     if not game_balance:
         game_balance = (0,)  # Default to 0 if user has no record
 
     # ✅ Check if the user already hit their 50,000 SYP limit
     cursor.execute("SELECT game_status from wallets where user_id =%s",(user_id,))
     game_status = cursor.fetchone()
     if game_balance[0] >= 50000 or game_status[0] == 0:
         slot_sticker_id = "CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
         await context.bot.send_sticker(chat_id=chat_id, sticker=slot_sticker_id)# if the game status = 0 that's mean that the player reached his limits 
         await update.callback_query.message.reply_text(
             "⚠️ لقد وصلت للحد الأقصى لأرباحك (50,000 SYP).\n\n"
             "🚫 لا يمكنك اللعب مرة أخرى.",
             parse_mode="Markdown"
         )
         cursor.execute("UPDATE wallets set game_status = %s where user_id = %s" ,(0,user_id))
         conn.commit()
         conn.close()
         return
 
     # ✅ Generate slot machine result
     symbols = ["🍒", "🍋", "🍉"]
     result = [random.choice(symbols) for _ in range(3)]
 
     # ✅ Check if the player won (all symbols match)
     win_amount = 25000 if result[0] == result[1] == result[2] else 0
 
     if win_amount > 0:
         
          # ✅ Add winnings to user's game balance
         cursor.execute("UPDATE wallets SET game_balance = game_balance + %s WHERE user_id = %s", (win_amount, user_id))
    
         # ✅ Update the total game balance correctly
         cursor.execute("UPDATE wallets SET total_game_balance = total_game_balance + %s WHERE user_id = %s", (win_amount, user_id))
    
         conn.commit()
         # ✅ Send Slot Machine Sticker (Replace with your own `file_id`)
         slot_sticker_id = "CAACAgIAAxkBAeLaJGfddT5-nwAB0D9SFNMeScLbCI3V1QACfz0AAi3JKUp2tyZPFVNcFzYE"
         await context.bot.send_sticker(chat_id=chat_id, sticker=slot_sticker_id)
 
     # ✅ Get updated total balance after the spin
     
 
     
 
     # ✅ Generate game message
     message = f"🎰 نتيجة السحب: \n\n {result[0]} | {result[1]} | {result[2]} |\n\n"
 
     if win_amount > 0:
         message += (
             f"🎉 مبروك! ربحت `{win_amount}` ل.س 🎉\n"
             f"💰 رصيدك في اللعبة: `{game_balance[0] + win_amount}` ل.س\n"
             f"🚫لا يمكنك سحب رصيد اللعبة \n"
             "🔄 استخدم الأرباح لشحن حسابك في WayXbet!"
         )
     else:
         message += "😔 للأسف لم تفز هذه المرة.\n🔄 حاول مرة أخرى!"
 
     # ✅ Check if the total game balance exceeded the global limit
     if updated_total_game_balance >= 1000000:
         cursor.execute("UPDATE game_settings SET game_locked = 1")
         conn.commit()
         conn.close()
         slot_sticker_id = "CAACAgIAAxkBAeLea2fdghlNXrLzSIKqJ_kW8t43fAE1AALzQQACb7NoSV-j4NDXxKN2NgQ"
         await context.bot.send_sticker(chat_id=chat_id, sticker=slot_sticker_id)
         message += "\n\n🚫 اللعبة مقفلة الآن! وصلت جميع الجوائز إلى الحد الأقصى (1,000,000 SYP)."
 
     # ✅ Send result message
     keyboard = [[InlineKeyboardButton("🔄 لعب مرة أخرى", callback_data="slot_machine")]]
     reply_markup = InlineKeyboardMarkup(keyboard)
 
     await update.callback_query.message.reply_text(message, reply_markup=reply_markup, parse_mode="Markdown")

# ✅ Register handlers
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("help", help_command))
telegram_app.add_handler(CallbackQueryHandler(button))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))

if __name__ == "__main__":
    
    login_as_agent()
    uvicorn.run(app, host="0.0.0.0", port=8000)
