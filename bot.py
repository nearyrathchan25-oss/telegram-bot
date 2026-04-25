from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, filters, ContextTypes
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os

# ================= CONFIG =================
BOT_TOKEN = os.getenv("8794568726:AAGa9e8AxaZJrlTpSLutS2FXq5oU18J_xRI")

ASK_CLASS, SELECT_NAME, UPLOAD_VIDEO = range(3)

# ================= GOOGLE SHEETS =================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)

sheet_students = client.open("StudentBot").worksheet("Students")
sheet_submissions = client.open("StudentBot").worksheet("Submissions")

# ================= LOAD DATA =================
def load_classes():
    data = sheet_students.get_all_records()
    classes = {}

    for row in data:
        cls = row["Class"]
        name = row["Name"]

        if cls not in classes:
            classes[cls] = []
        classes[cls].append(name)

    return classes

classes = load_classes()

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global classes
    classes = load_classes()

    keyboard = [[c] for c in classes.keys()]

    await update.message.reply_text(
        "Select your class:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return ASK_CLASS

# ================= CLASS =================
async def ask_class(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_class = update.message.text

    if user_class not in classes:
        await update.message.reply_text("Invalid class. Try again.")
        return ASK_CLASS

    context.user_data["class"] = user_class

    keyboard = [[n] for n in classes[user_class]]

    await update.message.reply_text(
        "Select your name:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    )
    return SELECT_NAME

# ================= NAME =================
async def select_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    user_class = context.user_data["class"]

    if name not in classes[user_class]:
        await update.message.reply_text("Invalid name. Try again.")
        return SELECT_NAME

    context.user_data["name"] = name

    await update.message.reply_text("Upload your video:")
    return UPLOAD_VIDEO

# ================= VIDEO =================
async def upload_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.video:
        await update.message.reply_text("Please upload a video.")
        return UPLOAD_VIDEO

    student_class = context.user_data["class"]
    student_name = context.user_data["name"]

    file_id = update.message.video.file_id

    sheet_submissions.append_row([
        student_class,
        student_name,
        file_id,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

    await update.message.reply_text("✅ Submitted successfully!")
    return ConversationHandler.END

# ================= MAIN =================
app = ApplicationBuilder().token(BOT_TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        ASK_CLASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_class)],
        SELECT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_name)],
        UPLOAD_VIDEO: [MessageHandler(filters.VIDEO, upload_video)],
    },
    fallbacks=[]
)

app.add_handler(conv_handler)

app.run_polling()