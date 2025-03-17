import os
import requests
from telegram.error import BadRequest
import bcrypt
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sqlite3
from dotenv import load_dotenv
import mysql.connector


# Load environment variables
load_dotenv()

# Initialize the database


ADMIN_BOT_TOKEN = os.getenv("ADMIN_BOT_TOKEN")
DATABASE_PASSWORD= os.getenv("DATABASE_PASSWORD")
DATABASE_USER=os.getenv("DATABASE_USER")
DATABASE_NAME=os.getenv("DATABASE_NAME")
DATABASE_HOST=os.getenv("DATABASE_HOST")

def connect_db():
    return mysql.connector.connect(
        host= DATABASE_HOST,
        user=DATABASE_USER,
        password=DATABASE_PASSWORD,
        database=DATABASE_NAME
    )

def admin_only(func):
    
    """Decorator to restrict access to logged-in admins."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # ✅ Detect whether the update is a message or callback query
        if update.message:
         user_id = update.message.from_user.id
         send_message = update.message.reply_text  # ✅ Use update.message
        elif update.callback_query:
         user_id = update.callback_query.from_user.id
         send_message = update.callback_query.message.reply_text  # ✅ Use update.callback_query.message
        else:
         return  # Prevent crashes if neither exists
        if not context.user_data.get("is_admin"):
            await send_message("🚫 *يجب تسجيل الدخول كمشرف لاستخدام هذه الميزة!*", parse_mode="Markdown")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles /start command and prompts admin for login."""
    user_id = update.message.from_user.id

    # Check if already logged in
    if context.user_data.get("is_admin"):
        await update.message.reply_text("✅ *أنت بالفعل مسجل الدخول كمشرف!*", parse_mode="Markdown")
        await admin_panel(update, context)
        return

    # Ask for username
    context.user_data["state"] = "awaiting_username"
    await update.message.reply_text("🔑 *الرجاء إدخال اسم المستخدم:*", parse_mode="Markdown")


async def handle_admin_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles username input and asks for password."""
    user_id = update.message.from_user.id
    username = update.message.text.strip()

    # Store username and ask for password
    context.user_data["admin_username"] = username
    context.user_data["state"] = "awaiting_password"

    await update.message.reply_text("🔒 *الرجاء إدخال كلمة المرور:*", parse_mode="Markdown")


async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin login by verifying password."""
    user_id = update.message.from_user.id
    password = update.message.text.strip()
    username = context.user_data.get("admin_username")

    if not username:
        await update.message.reply_text("⚠️ *حدث خطأ! يرجى محاولة تسجيل الدخول مرة أخرى.*", parse_mode="Markdown")
        return

    conn = None
    cursor = None

    try:
        # Connect to the database
        conn = connect_db()
        cursor = conn.cursor()

        # Fetch stored password from database
        cursor.execute("SELECT password FROM admins WHERE username = %s", (username,))
        result = cursor.fetchone()

        if not result:
            await update.message.reply_text("❌ *اسم المستخدم غير صحيح!*", parse_mode="Markdown")
            return

        stored_password = result[0]

        # Verify the entered password
        if bcrypt.checkpw(password.encode(), stored_password.encode()):  # Ensure proper encoding
            context.user_data["is_admin"] = True
            context.user_data["admin_username"] = username

            # ✅ Store Telegram user ID for this admin
            cursor.execute("UPDATE admins SET user_id = %s WHERE username = %s", (user_id, username))
            conn.commit()

            await update.message.reply_text("✅ *تم تسجيل الدخول بنجاح!*", parse_mode="Markdown")

            # Show admin panel
            await admin_panel(update, context)

        else:
            await update.message.reply_text("❌ *كلمة المرور غير صحيحة!*", parse_mode="Markdown")

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await update.message.reply_text("⚠️ *خطأ في قاعدة البيانات، يرجى المحاولة لاحقاً!*", parse_mode="Markdown")

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

async def handle_admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    action = query.data

    if action == "show_transactions":
        await show_approved_transactions(update, context)
    elif action == "show_summary":
        await show_financial_summary(update, context)
    elif action == "show_daily_summary":
        await show_daily_financial_summary(update, context)
    elif action == "show_monthly_summary":
        await show_monthly_financial_summary(update, context)
    elif action == "custom_broadcast":
        context.user_data["state"] = "awaiting_broadcast_message"
        await query.message.reply_text("📝 *الرجاء كتابة الرسالة التي تريد إرسالها لجميع المستخدمين:*", parse_mode="Markdown")
        
    elif action == "confirm_broadcast":
        context.user_data["state"] = None
        await confirm_broadcast(update, context)
        
    elif action == "cancel_broadcast":
        context.user_data["state"] = None
        await cancel_broadcast(update, context)
        
    elif action.startswith("complete_"):
        await complete_transaction(update, context)


async def handle_broadcast_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles admin text input dynamically."""
    user_id = update.message.from_user.id
    user_input = update.message.text.strip()

    state = context.user_data.get("state")
    

    if state == "awaiting_broadcast_message":
        context.user_data["broadcast_message"] = user_input
        context.user_data["state"] = None  # Reset state
        
        message_text = update.message.caption if update.message.caption else update.message.text
        if update.message.photo:
        # ✅ User sent a photo → store file ID & caption
         photo_file_id = update.message.photo[-1].file_id  # Get highest resolution photo
         context.user_data["broadcast_photo"] = photo_file_id
    
    if message_text:
        # ✅ User sent a text or caption → store message text
        context.user_data["broadcast_message"] = message_text.strip()

        # ✅ Confirm before sending
        keyboard = [
            [InlineKeyboardButton("✅ إرسال", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_broadcast")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"📢 *رسالتك:* \n\n{user_input}\n\n✅ *هل تريد إرسالها لجميع المستخدمين؟*",
            parse_mode="Markdown", reply_markup=reply_markup
        )


async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text  # ✅ Use update.message
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text  # ✅ Use update.callback_query.message
    else:
        return  # Prevent crashes if neither exists
    """Handles both username and password inputs dynamically."""
    user_id = update.message.from_user.id
    user_input = update.message.text.strip()
    
    state = context.user_data.get("state")  # Get current login step
    
    if state == "awaiting_username":
        context.user_data["admin_username"] = user_input  # Store username
        context.user_data["state"] = "awaiting_password"  # Move to next step
        await send_message("🔒 *الرجاء إدخال كلمة المرور:*", parse_mode="Markdown")
    
    elif state == "awaiting_password":
        context.user_data["admin_password"] = user_input  # Store password
        await handle_admin_password(update, context)  # Call password verification function
        
    elif state == "awaiting_broadcast_message":
        context.user_data["broadcast_message"] = user_input
        context.user_data["state"] = None
        keyboard = [
            [InlineKeyboardButton("✅ إرسال", callback_data="confirm_broadcast")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_broadcast")]
        ]
        await update.message.reply_text(f"📢 *رسالتك:* \n\n{user_input}\n\n✅ *هل تريد إرسالها لجميع المستخدمين؟*",
                                        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        
    else:
        await update.message.reply_text("⚠️ *يرجى استخدام /start لتسجيل الدخول.*", parse_mode="Markdown")


# ✅ Admin Panel Menu
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
     keyboard = [
        [InlineKeyboardButton("📋 عرض العمليات المعتمدة", callback_data="show_transactions")],
        [InlineKeyboardButton("📊 عرض الملخص المالي", callback_data="show_summary")],
        [InlineKeyboardButton("📅 الملخص المالي الشهري", callback_data="show_monthly_summary")],
        [InlineKeyboardButton("📆 الملخص المالي اليومي", callback_data="show_daily_summary")],  # New Button# New Button
        [InlineKeyboardButton("📢 إرسال رسالة مخصصة", callback_data="custom_broadcast")]  # New Button
        
     ]
     reply_markup = InlineKeyboardMarkup(keyboard)

     await update.message.reply_text("🔧 *لوحة تحكم المشرف:*", reply_markup=reply_markup, parse_mode="Markdown")



# ✅ Fetch & Show Approved Transactions
@admin_only
async def show_approved_transactions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and display approved transactions for admins."""
    
    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevents crashes if neither exists

    try:
        # ✅ Connect to MySQL Database
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Query to fetch transactions that need to be processed
        cursor.execute("""
            SELECT t.transaction_id, t.user_id, a.player_id, a.username, t.payment_method, 
                   t.account_number, t.timestamp, t.fee, t.final_amount, t.status 
            FROM transactions t
            JOIN accounts a ON t.user_id = a.user_id  -- Join to fetch username
            WHERE t.status = 'approved' and t.transaction_type = 'withdrawal'
            ORDER BY t.timestamp DESC
            LIMIT 10  -- Fetch only 10 transactions (Modify as needed)
        """)
        transactions = cursor.fetchall()

        if not transactions:
            await send_message("✅ *لا توجد معاملات بحاجة إلى التنفيذ حاليًا!*", parse_mode="Markdown")
            return

        # ✅ Process and Display Each Transaction
        for transaction in transactions:
            (transaction_id, user_id, player_id, username, 
             payment_method, account_number, timestamp, fee, 
             final_amount, status) = transaction

            message = (
                f"🆔 *رقم العملية:* `{transaction_id}`\n"
                f"👤 *المستخدم:* `{username}` (`{user_id}`)\n"
                f"🎮 *Player ID:* `{player_id}`\n"
                f"💳 *طريقة الدفع:* `{payment_method}`\n"
                f"🏦 *رقم الحساب:* `{account_number}`\n"
                f"📅 *التاريخ:* `{timestamp}`\n"
                f"💰 *المبلغ النهائي:* `{final_amount}` SYP\n"
                f"🧾 *الرسوم:* `{fee}` SYP\n"
                f"📌 *الحالة:* `{status}`"
            )

            # ✅ Inline Button to Complete Transaction
            keyboard = [[InlineKeyboardButton("✅ إكمال", callback_data=f"complete_{transaction_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await send_message(message, reply_markup=reply_markup, parse_mode="Markdown")

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await send_message("❌ *حدث خطأ في قاعدة البيانات!*", parse_mode="Markdown")

    finally:
        # ✅ Ensure proper closing of database connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
   
@admin_only
async def show_monthly_financial_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and display the financial summary for the current month."""
    
    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists

    try:
        # ✅ Connect to MySQL Database
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Fetch financial summary for the current month (MySQL query)
        cursor.execute("""
            SELECT 
                COALESCE(SUM(fee), 0) AS total_fees, 
                COALESCE(SUM(final_amount), 0) AS total_payments
                
            FROM transactions
            WHERE DATE_FORMAT(timestamp, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
        """)

        result = cursor.fetchone()
        
        cursor.execute("""
                       select sum(amount) from transactions where transaction_type = 'deposit' 
                       and DATE_FORMAT(timestamp, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')
                       """)
        results = cursor.fetchone()
        
        # Extract values safely
        total_fees = round(result[0]) if result else 0
        total_payments = round(result[1]) if result else 0
        total_received = round(results[0]) if results else 0
        profit = total_received - total_payments

        # ✅ Format response message
        message = (
            f"📅 *التقرير المالي لهذا الشهر:* 📊\n\n"
            f"💵 *إجمالي الرسوم:* `{total_fees}` SYP\n"
            f"💰 *إجمالي المدفوعات:* `{total_payments}` SYP\n"
            f"📥 *إجمالي المبالغ المستلمة:* `{total_received}` SYP\n"
            f"💴 *إجمالي الربح:* `{profit}` SYP"
        )

        await send_message(message, parse_mode="Markdown")

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await send_message("❌ *حدث خطأ في قاعدة البيانات!*", parse_mode="Markdown")

    finally:
        # ✅ Ensure proper closing of database connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()

   


# ✅ Handle the "Complete Transaction" Button
@admin_only
async def complete_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Marks a transaction as 'completed' and updates the message accordingly."""

    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists

    # ✅ Ensure only admins can complete transactions
    if not context.user_data.get("is_admin"):
        await send_message("🚫 *يجب تسجيل الدخول كمشرف لاستخدام هذه الميزة!*", parse_mode="Markdown")
        return

    query = update.callback_query
    transaction_id = query.data.split("_")[1]

    try:
        # ✅ Connect to MySQL Database
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Check if transaction already marked as 'completed'
        cursor.execute("SELECT status FROM transactions WHERE transaction_id = %s", (transaction_id,))
        result = cursor.fetchone()

        if not result:
            await send_message("❌ *لم يتم العثور على المعاملة!*", parse_mode="Markdown")
            return

        if result[0] == "completed":
            await query.answer("⚠️ هذه المعاملة مكتملة بالفعل!", show_alert=True)
            return

        # ✅ Update transaction status to 'completed'
        cursor.execute("UPDATE transactions SET status = 'completed' WHERE transaction_id = %s", (transaction_id,))
        conn.commit()

        # ✅ Update the message with confirmation
        await query.edit_message_text(
            text=f"{query.message.text}\n\n✅ *تمت العملية بنجاح!*",
            parse_mode="Markdown"
        )

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await send_message("❌ *حدث خطأ أثناء تحديث المعاملة!*", parse_mode="Markdown")

    finally:
        # ✅ Ensure proper database connection closure
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ✅ Show Financial Summary
@admin_only
async def show_financial_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and display the overall financial summary."""
    
    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists
    
    # ✅ Ensure only admins can access the summary
    if not context.user_data.get("is_admin"):
        await send_message("🚫 *يجب تسجيل الدخول كمشرف لاستخدام هذه الميزة!*", parse_mode="Markdown")
        return

    try:
        # ✅ Connect to MySQL Database
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Fetch financial summary
        cursor.execute("SELECT SUM(fee), SUM(final_amount), SUM(amount) FROM transactions where transaction_type ='deposit'")
        result = cursor.fetchone()

        # ✅ Extract values safely
        total_fees = result[0] if result[0] else 0
        total_payments = result[1] if result[1] else 0
        total_received = result[2] if result[2] else 0
        profit = total_received - total_payments

        # ✅ Format numbers properly
        total_fees = round(total_fees)
        total_payments = round(total_payments)
        total_received = round(total_received)
        profit = round(profit)

        # ✅ Prepare response message
        message = (
            f"📊 *ملخص المعاملات:* \n\n"
            f"💵 *إجمالي الرسوم:* `{total_fees}` SYP\n"
            f"💰 *إجمالي المدفوعات:* `{total_payments}` SYP\n"
            f"📥 *إجمالي المبالغ المستلمة:* `{total_received}` SYP\n"
            f"💴 *إجمالي الربح:* `{profit}` SYP"
        )

        await send_message(message, parse_mode="Markdown")

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await send_message("❌ *حدث خطأ أثناء جلب البيانات!*", parse_mode="Markdown")

    finally:
        # ✅ Ensure proper database connection closure
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    
    
async def show_daily_financial_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch and display the financial summary for today."""
    
    # ✅ Detect whether the update is a message or callback query
    if update.message:
        user_id = update.message.from_user.id
        send_message = update.message.reply_text
    elif update.callback_query:
        user_id = update.callback_query.from_user.id
        send_message = update.callback_query.message.reply_text
    else:
        return  # Prevent crashes if neither exists

    try:
        # ✅ Connect to MySQL Database
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Fetch daily financial summary
        cursor.execute("""
            SELECT 
                SUM(fee) AS total_fees, 
                SUM(final_amount) AS total_payments
                
            FROM transactions
            WHERE DATE(timestamp) = CURDATE()
        """)

        result = cursor.fetchone()

        cursor.execute("""
                       select sum(amount) from transactions where transaction_type = 'deposit' 
                       and DATE(timestamp) = CURDATE()
                       """)
        results = cursor.fetchone()

        # ✅ Extract values safely
        total_fees = result[0] if result[0] else 0
        total_payments = result[1] if result[1] else 0
        total_received = round(results[0]) if results else 0
        profit = total_received - total_payments

        # ✅ Format numbers properly
        total_fees = round(total_fees)
        total_payments = round(total_payments)
        total_received = round(total_received)
        profit = round(profit)

        # ✅ Prepare response message
        message = (
            f"📅 *التقرير المالي لهذا اليوم:* 📊\n\n"
            f"💵 *إجمالي الرسوم:* `{total_fees}` SYP\n"
            f"💰 *إجمالي المدفوعات:* `{total_payments}` SYP\n"
            f"📥 *إجمالي المبالغ المستلمة:* `{total_received}` SYP\n"
            f"💴 *إجمالي الربح:* `{profit}` SYP"
        )

        await send_message(message, parse_mode="Markdown")

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await send_message("❌ *حدث خطأ أثناء جلب البيانات!*", parse_mode="Markdown")

    finally:
        # ✅ Ensure proper database connection closure
        if cursor:
            cursor.close()
        if conn:
            conn.close()


async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcasts a message (or photo with caption) from the admin bot to all users of bot.py."""
    
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    query = update.callback_query

    # ✅ Fetch broadcast content
    message_text = context.user_data.get("broadcast_message", None)
    photo_file_id = context.user_data.get("broadcast_photo", None)

    # ✅ Validate input
    if not message_text and not photo_file_id:
        await query.message.reply_text("❌ *لا توجد رسالة للبث!*", parse_mode="Markdown")
        return

    # ✅ Connect to MySQL
    try:
        conn = connect_db()
        cursor = conn.cursor()

        # ✅ Fetch user IDs
        cursor.execute("SELECT user_id FROM accounts WHERE user_id IS NOT NULL")
        users = cursor.fetchall()

    except mysql.connector.Error as err:
        print(f"❌ MySQL Error: {err}")
        await query.message.reply_text("❌ *حدث خطأ أثناء جلب المستخدمين!*", parse_mode="Markdown")
        return

    finally:
        cursor.close()
        conn.close()

    # ✅ Ensure there are users to send the message
    if not users:
        await query.message.reply_text("❌ *لا يوجد مستخدمون مسجلون لإرسال الرسالة لهم!*", parse_mode="Markdown")
        return

    failed_count = 0
    sent_count = 0

    # ✅ Send messages/photos to all users
    for user in users:
        user_id = user[0]  # Extract user ID

        try:
            if photo_file_id and message_text:
                # ✅ Send Photo with Caption
                await context.bot.send_photo(chat_id=int(user_id), photo=photo_file_id, caption=message_text, parse_mode="Markdown")

            elif photo_file_id:
                # ✅ Send Photo Only
                await context.bot.send_photo(chat_id=int(user_id), photo=photo_file_id, caption="📢 رسالة جديدة!", parse_mode="Markdown")

            elif message_text:
                # ✅ Send Text Only
                await context.bot.send_message(chat_id=int(user_id), text=message_text, parse_mode="Markdown")

            sent_count += 1

        except Exception as e:
            print(f"❌ Failed to send message to {user_id}: {e}")  # Debugging
            failed_count += 1

    # ✅ Report results
    await query.message.reply_text(
        f"✅ *تم إرسال الرسالة إلى {sent_count} مستخدم بنجاح!*\n"
        f"❌ *فشل إرسالها إلى {failed_count} مستخدمين.*", 
        parse_mode="Markdown"
    )


async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels the broadcast process."""
    query = update.callback_query
    context.user_data["state"] = None
    await query.message.reply_text("🚫 *تم إلغاء إرسال الرسالة!*", parse_mode="Markdown")
    
    
    
    
# ✅ Register Handlers & Start the Bot
app = ApplicationBuilder().token(ADMIN_BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))
app.add_handler(CommandHandler("admin", admin_panel))
app.add_handler(CallbackQueryHandler(handle_admin_buttons))

if __name__ == "__main__":
    print("🚀 Admin bot is running...")
    app.run_polling()