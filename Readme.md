# Telegram Message Forwarder

A Python script that automatically monitors target Telegram channels and forwards new messages to source channels in real-time. Works with public channels, private channels, and groups.

## Features

- 🔄 **Real-time Forwarding**: Instantly forwards messages from target channels to source channels
- 🔐 **Session Management**: Saves login session - no need to re-authenticate on restart
- 📱 **Multi-Channel Support**: Monitor multiple channels and forward to multiple destinations
- 🔒 **Private Channel Support**: Works with private channels and groups using invite links
- 📊 **Comprehensive Logging**: Detailed logs with timestamps for monitoring and debugging
- ⚡ **Rate Limiting**: Built-in rate limiting to avoid Telegram API limits
- 🛡️ **Error Handling**: Robust error handling with automatic retry mechanisms
- 24/7 **Continuous Operation**: Designed to run continuously without interruption

## Requirements

- Python 3.7+
- Telegram API credentials (API ID and API Hash)
- Active Telegram account

# 🚀 NiftyForwarder Installation Guide

## 📱 Installation on Termux (Android)

### Step 1: Install Required Packages
```bash
# Update package list
pkg update && pkg upgrade -y

# Install Python and Git
pkg install python git -y

# Install additional dependencies
pkg install build-essential libffi openssl -y
```

### Step 2: Clone the Repository
```bash
# Clone NiftyForwarder repository
git clone https://github.com/HarshDhaka69/NiftyForwarder.git

# Navigate to the project directory
cd NiftyForwarder
```

### Step 3: Install Python Dependencies
```bash
# Install pip if not available
python -m ensurepip --upgrade

# Install required packages
pip install telethon asyncio

# Alternative if above fails
pip install --upgrade pip
pip install telethon
```

### Step 4: Configuration
```bash
# Create config file
nano config.py
```

Add the following configuration:
```python
# Telegram API Configuration
API_ID = 12345678  # Your API ID from my.telegram.org
API_HASH = "your_api_hash_here"  # Your API Hash from my.telegram.org
PHONE_NUMBER = "+1234567890"  # Your phone number with country code

# Target channels to monitor (where messages come from)
TARGET_CHANNELS = [
    "@channel1",
    "@channel2",
    "https://t.me/channel3"
]

# Source channels to forward to (where messages go)
SOURCE_CHANNELS = [
    "@mychannel1",
    "@mychannel2",
    "https://t.me/mychannel3"
]
```

### Step 5: Run NiftyForwarder
```bash
# Make the script executable
chmod +x NiftyForwarder.py

# Run the forwarder
python NiftyForwarder.py
```

### Step 6: Keep Running in Background (Optional)
```bash
# Install screen for background execution
pkg install screen

# Run in background
screen -S NiftyForwarder python NiftyForwarder.py

# Detach from screen (Ctrl+A then D)
# To reattach: screen -r NiftyForwarder
```

---

## 💻 Installation on Windows

### Step 1: Install Python
1. Download Python from [python.org](https://www.python.org/downloads/)
2. During installation, check "Add Python to PATH"
3. Verify installation:
```cmd
python --version
pip --version
```

### Step 2: Install Git
1. Download Git from [git-scm.com](https://git-scm.com/downloads)
2. Install with default settings
3. Verify installation:
```cmd
git --version
```

### Step 3: Clone the Repository
```cmd
# Open Command Prompt or PowerShell
# Navigate to desired directory
cd C:\Users\%USERNAME%\Desktop

# Clone repository
git clone https://github.com/HarshDhaka69/NiftyForwarder.git

# Navigate to project directory
cd NiftyForwarder
```

### Step 4: Install Dependencies
```cmd
# Install required packages
pip install telethon asyncio

# If you encounter SSL errors, try:
pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org telethon
```

### Step 5: Configuration
Create `config.py` file in the project directory:

```python
# Telegram API Configuration
API_ID = 12345678  # Your API ID from my.telegram.org
API_HASH = "your_api_hash_here"  # Your API Hash from my.telegram.org
PHONE_NUMBER = "+1234567890"  # Your phone number with country code

# Target channels to monitor (where messages come from)
TARGET_CHANNELS = [
    "@channel1",
    "@channel2",
    "https://t.me/channel3"
]

# Source channels to forward to (where messages go)
SOURCE_CHANNELS = [
    "@mychannel1",
    "@mychannel2",
    "https://t.me/mychannel3"
]
```

### Step 6: Run NiftyForwarder
```cmd
# Run the forwarder
python NiftyForwarder.py
```

### Step 7: Run as Windows Service (Optional)
Create `run_nifty.bat`:
```batch
@echo off
cd /d "C:\path\to\NiftyForwarder"
python NiftyForwarder.py
pause
```

---

## 🔧 Getting Telegram API Credentials

### Step 1: Create Telegram App
1. Go to [my.telegram.org](https://my.telegram.org)
2. Login with your phone number
3. Click "API Development Tools"
4. Fill in the form:
   - App title: `NiftyForwarder`
   - Short name: `NiftyForwarder`
   - Platform: `Desktop`
   - Description: `Message forwarding bot`

### Step 2: Get Credentials
After creating the app, you'll receive:
- **API ID**: A numeric value (e.g., 12345678)
- **API Hash**: An alphanumeric string (e.g., "1a2b3c4d5e6f7g8h9i0j")

⚠️ **Important**: Keep these credentials secure and never share them publicly!

---

## 📋 Configuration Examples

### Example 1: Basic Setup
```python
API_ID = 12345678
API_HASH = "abcd1234efgh5678ijkl"
PHONE_NUMBER = "+1234567890"

TARGET_CHANNELS = ["@news_channel"]
SOURCE_CHANNELS = ["@my_channel"]
```

### Example 2: Multiple Channels
```python
API_ID = 12345678
API_HASH = "abcd1234efgh5678ijkl"
PHONE_NUMBER = "+1234567890"

TARGET_CHANNELS = [
    "@tech_news",
    "@crypto_updates",
    "https://t.me/market_signals"
]

SOURCE_CHANNELS = [
    "@my_tech_channel",
    "@my_crypto_channel",
    "https://t.me/my_signals"
]
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. Import Error
```
ModuleNotFoundError: No module named 'telethon'
```
**Solution:**
```bash
pip install --upgrade telethon
```

#### 2. Authentication Error
```
SessionPasswordNeededError
```
**Solution:** Enter your 2FA password when prompted

#### 3. Channel Access Error
```
ChatAdminRequiredError
```
**Solution:** Ensure you're admin in target channels or they're public

#### 4. Rate Limiting
```
FloodWaitError
```
**Solution:** The script automatically handles this, just wait

### Performance Tips
- Run on a stable internet connection
- Use screen/tmux on Linux for background execution
- Monitor logs for any issues
- Regular updates: `git pull origin main`

---

## 🔄 Updating NiftyForwarder

### Update via Git
```bash
# Navigate to project directory
cd NiftyForwarder

# Pull latest changes
git pull origin main

# Reinstall dependencies if needed
pip install --upgrade telethon
```

---

## Configuration

### Basic Setup

Edit `config.py`:

```python
# API Credentials
API_ID = 12345678  # Your API ID
API_HASH = 'your_api_hash_here'  # Your API Hash
PHONE_NUMBER = '+1234567890'  # Your phone number (optional)

# Target channels to monitor
TARGET_CHANNELS = [
    '@channel_username',
    'https://t.me/channel_name',
    'https://t.me/+InviteLinkForPrivateChannel'
]

# Source channels to forward messages to
SOURCE_CHANNELS = [
    '@destination_channel',
    'https://t.me/your_channel',
    'https://t.me/+PrivateGroupInviteLink'
]
```

### Channel/Group Format Options

You can use any of these formats:

- **Username**: `@channelname`
- **Public Link**: `https://t.me/channelname`
- **Private Invite Link**: `https://t.me/+AbCdEfGhIjKlMnOp`
- **Channel ID**: `-1001234567890` (for advanced users)

## Usage

### First Run

1. **Run the script:**
   ```bash
   python forward.py
   ```

2. **Authentication:**
   - Enter your phone number (if not in config)
   - Enter the verification code sent to your Telegram
   - Enter 2FA password if enabled
   - Session will be saved as `forwarder_session.session`

### Subsequent Runs

```bash
python forward.py
```

The script will automatically use the saved session - no re-authentication needed!

### Running 24/7

For continuous operation:

**Linux/Mac:**
```bash
nohup python forward.py &
```

**Windows:**
```batch
python forward.py
```

**Using screen (Linux):**
```bash
screen -S forwarder
python forward.py
# Press Ctrl+A then D to detach
```

## File Structure

```
telegram-forwarder/
├── forward.py          # Main script
├── config.py           # Configuration file
├── requirements.txt    # Dependencies
├── README.md          # This file
├── forwarder.log      # Log file (created when running)
└── forwarder_session.session  # Session file (created on first run)
```

## Logging

The script creates detailed logs in `forwarder.log`:

- Message forwarding events
- Authentication status
- Error messages
- Rate limiting notifications
- Channel connection status

## Advanced Features

### Message Filtering

Edit `config.py` to enable filtering:

```python
IGNORE_MEDIA = True      # Skip media messages
IGNORE_FORWARDS = True   # Skip already forwarded messages
IGNORE_BOTS = True      # Skip messages from bots
```

### Rate Limiting

Adjust forwarding delay:

```python
FORWARD_DELAY = 2  # Seconds between forwards
```

## Troubleshooting

### Common Issues

1. **Authentication Error:**
   - Check API_ID and API_HASH
   - Ensure phone number format is correct (+country_code)
   - Delete session file and try again

2. **Channel Not Found:**
   - Verify channel username/link
   - Make sure you're a member of private channels
   - Check if channel exists and is accessible

3. **Permission Denied:**
   - Ensure bot has admin rights in source channels
   - Check if you can manually send messages to the channel

4. **Rate Limiting:**
   - Increase FORWARD_DELAY in config
   - The script automatically handles rate limits

### Debug Mode

For detailed debugging, edit `config.py`:

```python
LOG_LEVEL = 'DEBUG'
```

## Security Notes

- Keep your API credentials secure
- Don't share your session file
- Use environment variables for sensitive data in production
- The script only forwards messages - it doesn't store or modify them

## Limitations

- Respects Telegram's rate limits
- Requires active internet connection
- Some channels may restrict forwarding
- Private channels require invite links or membership

## Legal Disclaimer

This tool is for educational and personal use only. Users are responsible for:
- Complying with Telegram's Terms of Service
- Respecting copyright and privacy laws
- Getting permission before forwarding messages from private channels
- Following local laws and regulations

## Support

For issues and questions:
1. Check the logs in `forwarder.log`
2. Verify your configuration in `config.py`
3. Ensure all dependencies are installed
4. Check Telegram API status

## Updates

The script automatically handles most Telegram API changes through the Telethon library. Keep your dependencies updated:

```bash
pip install --upgrade telethon
```

---

**Happy Forwarding! 🚀**