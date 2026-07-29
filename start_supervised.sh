#!/bin/bash
# Start the bot with supervisor (auto-restart every 20 minutes)

cd /root/mast3

echo "🚀 Starting Bot Supervisor..."
echo "   - Auto-restart: Every 20 minutes"
echo "   - Backup: On each restart"
echo "   - Proxy: Resets to batch #1 each restart"
echo ""

# Make scripts executable
chmod +x backup_bot.py
chmod +x supervisor.py
chmod +x bot.py

# Run supervisor
python3 supervisor.py
