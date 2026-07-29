#!/usr/bin/env python3
"""
Backup script - creates a zip of the bot excluding botrun folders
"""
import os
import zipfile
import time
from datetime import datetime

def create_backup(base_dir="/root/mast3", backup_dir=None):
    """
    Create a backup zip of the bot, excluding botrun* folders and temp files.
    Returns the path to the created backup file.
    """
    if backup_dir is None:
        backup_dir = base_dir

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"bot_backup_{timestamp}.zip"
    backup_path = os.path.join(backup_dir, backup_filename)

    # Patterns to exclude
    exclude_patterns = [
        'botrun',  # All botrun* folders (tmux sockets)
        '__pycache__',
        '.pyc',
        'bot_backup_',  # Previous backups
        '.git',
        '.claude',
    ]

    print(f"🗜️  Creating backup: {backup_filename}")

    files_added = 0
    with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(base_dir):
            # Filter out excluded directories
            dirs[:] = [d for d in dirs if not any(pattern in d for pattern in exclude_patterns)]

            # Skip if current directory should be excluded
            rel_root = os.path.relpath(root, base_dir)
            if any(pattern in rel_root for pattern in exclude_patterns):
                continue

            for file in files:
                # Skip excluded files
                if any(pattern in file for pattern in exclude_patterns):
                    continue

                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, base_dir)

                try:
                    zipf.write(file_path, arcname)
                    files_added += 1
                except Exception as e:
                    print(f"⚠️  Skipped {arcname}: {e}")

    file_size = os.path.getsize(backup_path) / (1024 * 1024)  # MB
    print(f"✅ Backup created: {backup_filename}")
    print(f"📦 Files: {files_added} | Size: {file_size:.2f} MB")

    return backup_path

if __name__ == "__main__":
    backup_path = create_backup()
    print(f"Backup saved to: {backup_path}")
