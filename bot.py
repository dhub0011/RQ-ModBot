import os
import subprocess
import shutil
import re
import logging
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import asyncio

# ======= FLASK WEB SERVER =======
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "FlixFox Mod Bot is running!"

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    flask_app.run(host='0.0.0.0', port=8080)

threading.Thread(target=run_flask, daemon=True).start()

# ======= CONFIG =======
TOKEN = "8606279165:AAH6TY0bdqdgLRcLWgHx-yITU6FT-s05mXs"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======= PATHS =======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(BASE_DIR, "temp")
MODDED_DIR = os.path.join(BASE_DIR, "modded")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(MODDED_DIR, exist_ok=True)

APKTOOL_JAR = os.path.join(BASE_DIR, "apktool_3.0.2.jar")
UBER_SIGNER_JAR = os.path.join(BASE_DIR, "uber-apk-signer-1.2.1.jar")

# ======= MODDING ENGINE =======
def mod_apk(input_path, output_path):
    try:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        work_dir = os.path.join(TEMP_DIR, base_name)
        decompiled_dir = os.path.join(work_dir, "decompiled")
        rebuilt_apk = os.path.join(work_dir, "rebuild.apk")

        shutil.rmtree(work_dir, ignore_errors=True)
        os.makedirs(work_dir, exist_ok=True)

        logger.info(f"Decompiling {input_path}...")
        subprocess.run(
            ["java", "-jar", APKTOOL_JAR, "d", input_path, "-o", decompiled_dir, "-f"],
            check=True,
            capture_output=True,
            timeout=120
        )

        smali_root = os.path.join(decompiled_dir, "smali")
        if not os.path.exists(smali_root):
            smali_root = os.path.join(decompiled_dir, "smali_classes2")

        logger.info("Patching smali files...")
        for root, dirs, files in os.walk(smali_root):
            for file in files:
                if not file.endswith(".smali"):
                    continue
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    original = content

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
                    content = re.sub(
                        r'(const/4 v\d+, 0x5)',
                        r'const v\d+, 0x270F',
                        content
                    )
                    content = re.sub(
                        r'(invoke-virtual .*?->shouldShowAd\\(\\)Z).*?move-result v(\d+)',
                        r'const/4 v\2, 0x0',
                        content,
                        flags=re.DOTALL
                    )
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
                except Exception as e:
                    logger.warning(f"Could not patch {path}: {e}")

        logger.info("Rebuilding APK...")
        subprocess.run(
            ["java", "-jar", APKTOOL_JAR, "b", decompiled_dir, "-o", rebuilt_apk],
            check=True,
            capture_output=True,
            timeout=120
        )

        logger.info("Signing APK...")
        subprocess.run(
            ["java", "-jar", UBER_SIGNER_JAR, "--apks", rebuilt_apk, "--out", work_dir, "--overwrite"],
            check=True,
            capture_output=True,
            timeout=60
        )

        signed_files = [f for f in os.listdir(work_dir) if f.endswith(".apk") and "signed" in f.lower()]
        if signed_files:
            shutil.copy(os.path.join(work_dir, signed_files[0]), output_path)
            logger.info(f"Modded APK saved to {output_path}")
            return True, output_path, None
        return False, None, "Signing failed"
    except subprocess.TimeoutExpired:
        return False, None, "Processing timed out (APK too large or complex)"
    except Exception as e:
        logger.error(f"Modding error: {str(e)}")
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
        "⚠️ *Note:* For large files (>50MB), processing may take 3-5 minutes.",
        parse_mode="Markdown"
    )

async def handle_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file_obj = await update.message.document.get_file()
        file_name = update.message.document.file_name

        if not file_name.endswith(".apk"):
            await update.message.reply_text("❌ Please send a valid .apk file.")
            return

        await update.message.reply_text(
            "🔧 *Processing your APK...*\n"
            "📥 Downloading file...\n"
            "⏳ This takes 2-5 minutes for large files.",
            parse_mode="Markdown"
        )

        input_path = os.path.join(TEMP_DIR, file_name)
        await file_obj.download_to_drive(input_path)

        await update.message.reply_text("🛠️ *Modding in progress...*\nDecompiling, patching, and rebuilding...", parse_mode="Markdown")

        output_name = file_name.replace(".apk", "_MOD.apk")
        output_path = os.path.join(MODDED_DIR, output_name)

        success, result_path, error = mod_apk(input_path, output_path)

        if success:
            await update.message.reply_text(
                "✅ *Modding successful!*\n\n"
                "🔓 Premium content unlocked\n"
                "📥 Unlimited downloads (9999/day)\n"
                "🚫 Ads removed\n"
                "🛡️ SecShell bypassed\n\n"
                "📤 Uploading your modded APK...",
                parse_mode="Markdown"
            )
            await update.message.reply_document(
                document=open(result_path, "rb"),
                filename=output_name,
                caption="🎬 *FlixFox MOD - Fully Unlocked*"
            )
            os.remove(input_path)
            os.remove(result_path)
        else:
            await update.message.reply_text(f"❌ *Modding failed:*\n{error}", parse_mode="Markdown")
            os.remove(input_path)

    except Exception as e:
        await update.message.reply_text(f"❌ *Error:* {str(e)}", parse_mode="Markdown")
        logger.error(f"Handler error: {str(e)}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Help*\n\n"
        "1. Send me a FlixFox APK file\n"
        "2. Wait 2-5 minutes\n"
        "3. Download the modded APK\n\n"
        "✅ No ads\n"
        "✅ Unlimited downloads\n"
        "✅ Premium unlocked",
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