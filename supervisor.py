#!/usr/bin/env python3
"""
Bot Supervisor - Auto-restart every 20 minutes with backup
"""
import os
import sys
import time
import signal
import subprocess
import json
from datetime import datetime
from pathlib import Path

# Configuration
BOT_SCRIPT = "/root/mast3/bot.py"
RESTART_INTERVAL = 1200  # 20 minutes in seconds
STATE_FILE = "/root/mast3/.supervisor_state.json"
BASE_DIR = "/root/mast3"

# Telegram config (imported from bot config)
sys.path.insert(0, BASE_DIR)
try:
    from CONFIG.config import BOT_TOKEN, ADMIN_ID
    import telebot
    TELEGRAM_ENABLED = True
except Exception as e:
    print(f"⚠️  Telegram disabled: {e}")
    TELEGRAM_ENABLED = False
    BOT_TOKEN = None
    ADMIN_ID = None

class BotSupervisor:
    def __init__(self):
        self.bot_process = None
        self.restart_count = 0
        self.start_time = time.time()
        self.load_state()

        if TELEGRAM_ENABLED:
            self.telegram_bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
        else:
            self.telegram_bot = None

    def load_state(self):
        """Load supervisor state from file"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.restart_count = state.get('restart_count', 0)
                    print(f"📊 Loaded state: {self.restart_count} previous restarts")
            except Exception as e:
                print(f"⚠️  Could not load state: {e}")

    def save_state(self):
        """Save supervisor state to file"""
        try:
            state = {
                'restart_count': self.restart_count,
                'last_restart': datetime.now().isoformat(),
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save state: {e}")

    def send_telegram_message(self, message):
        """Send message to admin via Telegram"""
        if not self.telegram_bot or not ADMIN_ID:
            return
        try:
            self.telegram_bot.send_message(ADMIN_ID, message, parse_mode="HTML")
        except Exception as e:
            print(f"⚠️  Telegram send failed: {e}")

    def create_backup(self):
        """Create backup and send to admin"""
        print("🗜️  Creating backup...")
        try:
            from backup_bot import create_backup
            backup_path = create_backup(BASE_DIR)

            # Send backup to admin via Telegram
            if self.telegram_bot and ADMIN_ID:
                try:
                    with open(backup_path, 'rb') as f:
                        self.telegram_bot.send_document(
                            ADMIN_ID,
                            f,
                            caption=f"🔄 <b>Auto-Restart Backup #{self.restart_count}</b>\n"
                                    f"⏰ Time: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                                    f"📦 Size: <code>{os.path.getsize(backup_path) / (1024*1024):.2f} MB</code>",
                            parse_mode="HTML"
                        )
                    print("✅ Backup sent to admin")
                except Exception as e:
                    print(f"⚠️  Could not send backup: {e}")

            return backup_path
        except Exception as e:
            print(f"❌ Backup failed: {e}")
            return None

    def start_bot(self):
        """Start the bot process"""
        print(f"\n{'='*60}")
        print(f"🚀 Starting bot (Restart #{self.restart_count})")
        print(f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        try:
            self.bot_process = subprocess.Popen(
                [sys.executable, BOT_SCRIPT],
                cwd=BASE_DIR,
                stdout=sys.stdout,
                stderr=sys.stderr
            )

            # Send startup notification
            if self.restart_count > 0:
                self.send_telegram_message(
                    f"🔄 <b>Bot Auto-Restarted</b>\n"
                    f"<blockquote>🔢 Restart: <code>#{self.restart_count}</code>\n"
                    f"⏰ Time: <code>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</code>\n"
                    f"🌐 Proxy batch will start from #1\n"
                    f"✅ All systems resuming...</blockquote>"
                )

            return True
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
            return False

    def check_active_checks(self):
        """Check if there are any active checks running"""
        try:
            from HOME import state
            with state.active_checks_lock:
                # Filter out non-critical keys (file uploads, etc)
                critical_checks = {
                    k: v for k, v in state.active_checks.items()
                    if not k.startswith('file_')
                }
                return len(critical_checks) > 0, len(critical_checks)
        except Exception as e:
            print(f"⚠️  Could not check active checks: {e}")
            return False, 0

    def wait_for_checks_to_complete(self, max_wait_minutes=10):
        """Wait for all active checks to complete before stopping"""
        max_wait_seconds = max_wait_minutes * 60
        start_wait = time.time()

        has_checks, count = self.check_active_checks()

        if not has_checks:
            print("✅ No active checks running")
            return True

        print(f"\n{'='*60}")
        print(f"⏳ Waiting for {count} active check(s) to complete...")
        print(f"   Max wait: {max_wait_minutes} minutes")
        print(f"{'='*60}\n")

        # Send notification
        self.send_telegram_message(
            f"⏳ <b>Restart Pending</b>\n"
            f"<blockquote>🔍 Active checks: <code>{count}</code>\n"
            f"⏱️ Waiting for completion (max {max_wait_minutes} min)\n"
            f"✅ Will restart after checks finish</blockquote>"
        )

        last_count = count
        while True:
            has_checks, count = self.check_active_checks()

            if not has_checks:
                elapsed = time.time() - start_wait
                print(f"✅ All checks completed in {elapsed:.1f}s")
                return True

            # Show update if count changed
            if count != last_count:
                print(f"⏳ {count} check(s) still running...")
                last_count = count

            # Check timeout
            elapsed = time.time() - start_wait
            if elapsed >= max_wait_seconds:
                print(f"⚠️  Timeout reached ({max_wait_minutes} min)")
                print(f"⚠️  {count} check(s) still running - will stop anyway")
                self.send_telegram_message(
                    f"⚠️ <b>Restart Timeout</b>\n"
                    f"<blockquote>⏱️ Waited {max_wait_minutes} min\n"
                    f"🔍 {count} check(s) still running\n"
                    f"🛑 Forcing restart now</blockquote>"
                )
                return False

            time.sleep(5)  # Check every 5 seconds

    def stop_bot(self):
        """Gracefully stop the bot process"""
        if not self.bot_process:
            return

        print(f"\n{'='*60}")
        print(f"🛑 Stopping bot for scheduled restart...")
        print(f"{'='*60}\n")

        try:
            # Send SIGTERM for graceful shutdown
            self.bot_process.terminate()

            # Wait up to 10 seconds for graceful shutdown
            for i in range(10):
                if self.bot_process.poll() is not None:
                    print("✅ Bot stopped gracefully")
                    return
                time.sleep(1)

            # Force kill if still running
            print("⚠️  Force killing bot...")
            self.bot_process.kill()
            self.bot_process.wait()
            print("✅ Bot stopped (forced)")

        except Exception as e:
            print(f"⚠️  Error stopping bot: {e}")

    def run(self):
        """Main supervisor loop"""
        print("""
╔══════════════════════════════════════════════════════════╗
║          🤖 BOT SUPERVISOR - AUTO RESTART                ║
║          Restart Interval: 20 minutes                    ║
╚══════════════════════════════════════════════════════════╝
        """)

        # Send supervisor start notification
        self.send_telegram_message(
            f"🎯 <b>Supervisor Started</b>\n"
            f"<blockquote>⏱️ Auto-restart: Every 20 minutes\n"
            f"🔄 Previous restarts: <code>{self.restart_count}</code>\n"
            f"📦 Backup: On each restart\n"
            f"🌐 Proxy: Resets to batch #1 each restart</blockquote>"
        )

        while True:
            try:
                # Start the bot
                if not self.start_bot():
                    print("❌ Failed to start bot, retrying in 30s...")
                    time.sleep(30)
                    continue

                # Wait for restart interval
                print(f"\n⏳ Next restart in {RESTART_INTERVAL//60} minutes...")
                time.sleep(RESTART_INTERVAL)

                # Wait for active checks to complete (max 10 min)
                self.wait_for_checks_to_complete(max_wait_minutes=10)

                # Stop the bot
                self.stop_bot()

                # Increment restart counter
                self.restart_count += 1
                self.save_state()

                # Create backup
                self.create_backup()

                # Brief pause before restart
                print("⏳ Restarting in 5 seconds...")
                time.sleep(5)

            except KeyboardInterrupt:
                print("\n\n🛑 Supervisor stopped by user")
                self.stop_bot()
                self.send_telegram_message(
                    f"🛑 <b>Supervisor Stopped</b>\n"
                    f"<blockquote>Total restarts: <code>{self.restart_count}</code>\n"
                    f"Stopped by user</blockquote>"
                )
                break
            except Exception as e:
                print(f"❌ Supervisor error: {e}")
                print("⏳ Retrying in 30s...")
                time.sleep(30)

def main():
    supervisor = BotSupervisor()
    supervisor.run()

if __name__ == "__main__":
    main()
