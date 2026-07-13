import os
import subprocess
import shutil
import re
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ======= FLASK WEB SERVER (FOR RENDER) =======
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "FlixFox Mod Bot is running!"

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

# Start Flask in a background thread
threading.Thread(target=run_flask, daemon=True).start()

# ======= CONFIG =======
TOKEN = "8606279165:AAH6TY0bdqdgLRcLWgHx-yITU6FT-s05mXs"  # REPLACE WITH YOUR TOKEN
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======= PATHS =======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
MODDED_DIR = os.path.join(BASE_DIR, "modded")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MODDED_DIR, exist_ok=True)

APKTOOL_JAR = os.path.join(BASE_DIR, "apktool.jar")
UBER_SIGNER_JAR = os.path.join(BASE_DIR, "uber-apk-signer.jar")

# ======= MODDING ENGINE =======
def mod_apk(input_path, output_path):
    try:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        work_dir = os.path.join(TEMP_DIR, base_name)
        decompiled_dir = os.path.join(work_dir, "decompiled")
        rebuilt_apk = os.path.join(work_dir, "rebuild.apk")

        shutil.rmtree(work_dir, ignore_errors=True)
        os.makedirs(work_dir, exist_ok=True)

        # Decompile
        subprocess.run(
            ["java", "-jar", APKTOOL_JAR, "d", input_path, "-o", decompiled_dir, "-f"],
            check=True,
            capture_output=True
        )

        # Patch smali
        smali_root = os.path.join(decompiled_dir, "smali")
        if not os.path.exists(smali_root):
            smali_root = os.path.join(decompiled_dir, "smali_classes2")

        for root, dirs, files in os.walk(smali_root):
            for file in files:
                if not file.endswith(".smali"):
                    continue
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    original = content

                    # Premium checks
                    content = re.sub(
                        r'(invoke-virtual .*?->isPremium\\(\\)Z).*?move-result v(\d+)',
                        r'const/4 v\2, 0x1',
                        content,
                        flags=re.DOTALL
                    )
                    content = re.sub(
                        r'(invoke-virtual .*?->isVip\\(\\)Z).*?move-result v(\d+)',
                        r'const/4 v\2, 0x1',
                        content,
                        flags=re.DOTALL
                    )
                    # Download limit
                    content = re.sub(
                        r'(const/4 v\d+, 0x5)',
                        r'const v\d+, 0x270F',
                        content
                    )
                    # Ads
                    content = re.sub(
                        r'(invoke-virtual .*?->shouldShowAd\\(\\)Z).*?move-result v(\d+)',
                        r'const/4 v\2, 0x0',
                        content,
                        flags=re.DOTALL
                    )
                    # SecShell bypass
                    if "SecShell" in path:
                        content = re.sub(
                            r'(invoke-virtual .*?->check\\(\\)Z).*?move-result v(\d+)',
                            r'const/4 v\2, 0x1',
                            content,
                            flags=re.DOTALL
                        )

                    if content != original:
                        with open(path, "w", encoding="utf-8", errors="ignore") as f:
                            f.write(content)
                except Exception:
                    pass

        # Rebuild
        subprocess.run(
            ["java", "-jar", APKTOOL_JAR, "b", decompiled_dir, "-o", rebuilt_apk],
            check=True,
            capture_output=True
        )

        # Sign
        subprocess.run(
            ["java", "-jar", UBER_SIGNER_JAR, "--apks", rebuilt_apk, "--out", work_dir, "--overwrite"],
            check=True,
            capture_output=True
        )

        signed_files = [f for f in os.listdir(work_dir) if f.endswith(".apk") and "signed" in f.lower()]
        if signed_files:
            shutil.copy(os.path.join(work_dir, signed_files[0]), output_path)
            return True, output_path, None
        return False, None, "Signing failed"
    except Exception as e:
        return False, None, str(e)

# ======= TELEGRAM HANDLERS =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 *FlixFox APK Modder Bot*\n\n"
        "Send me a FlixFox APK file and I'll:\n"
        "✅ Remove all ads\n"
        "✅ Unlock Premium content\n"
        "✅ Remove download limits (9999/day)\n"
        "✅ Bypass SecShell protection\n\n"
        "Just send the .apk file and wait a minute.",
        parse_mode="Markdown"
    )

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_obj = await update.message.document.get_file()
    file_name = update.message.document.file_name

    if not file_name.endswith(".apk"):
        await update.message.reply_text("❌ Please send a valid .apk file.")
        return

    await update.message.reply_text("🔧 Processing your APK... This takes 1-3 minutes.")

    input_path = os.path.join(TEMP_DIR, file_name)
    await file_obj.download_to_drive(input_path)

    output_name = file_name.replace(".apk", "_MOD.apk")
    output_path = os.path.join(MODDED_DIR, output_name)

    success, result_path, error = mod_apk(input_path, output_path)

    if success:
        await update.message.reply_text(
            "✅ *Modding successful!*\n\n"
            "🔓 Premium content\n"
            "📥 Unlimited downloads (9999/day)\n"
            "🚫 No ads\n"
            "🛡️ SecShell bypassed",
            parse_mode="Markdown"
        )
        await update.message.reply_document(
            document=open(result_path, "rb"),
            filename=output_name
        )
        os.remove(input_path)
        os.remove(result_path)
    else:
        await update.message.reply_text(f"❌ Failed: {error}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Help*\n\n"
        "Send me a FlixFox APK. I'll mod it.\n"
        "No ads, unlimited downloads, premium unlocked.",
        parse_mode="Markdown"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.Document.APK, handle_apk))
    logger.info("Bot started. Waiting for APKs...")
    app.run_polling()

if __name__ == "__main__":
    main()