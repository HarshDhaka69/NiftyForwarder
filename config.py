#!/usr/bin/env python3
"""
Configuration file for Telegram Message Forwarder
Fill in your details below
"""

# ===== TELEGRAM API CREDENTIALS =====
# Get these from https://my.telegram.org/auth
API_ID = 12345678  # Your API ID (integer)
API_HASH = 'your_api_hash_here'  # Your API Hash (string)

# ===== PHONE NUMBER =====
# Your phone number with country code (optional - will be asked if not provided)
PHONE_NUMBER = '+1234567890'  # Example: '+1234567890'

# ===== TARGET CHANNELS =====
# Channels to monitor for new messages
# Can be username, invite link, or channel ID
TARGET_CHANNELS = [
    '@channel_username1',
    'https://t.me/channel_username2',
    '@private_channel',
    'https://t.me/+AbCdEfGhIjKlMnOp',  # Private channel invite link
    # Add more channels here
]

# ===== SOURCE CHANNELS =====
# Channels where messages will be forwarded to
# Can be username, invite link, or channel ID
SOURCE_CHANNELS = [
    '@destination_channel1',
    'https://t.me/destination_channel2',
    '@private_destination',
    'https://t.me/+XyZaBcDeFgHiJkLm',  # Private channel invite link
    # Add more channels here
]

# ===== ADVANCED SETTINGS =====
# Enable/disable forwarding from specific types
FORWARD_FROM_CHANNELS = True
FORWARD_FROM_GROUPS = True
FORWARD_FROM_PRIVATE_CHATS = True

# Message filtering (optional)
IGNORE_MEDIA = False  # Set to True to ignore media messages
IGNORE_FORWARDS = False  # Set to True to ignore already forwarded messages
IGNORE_BOTS = False  # Set to True to ignore messages from bots

# Rate limiting (seconds between forwards)
FORWARD_DELAY = 1  # Delay between forwarding to different channels

# ===== LOGGING SETTINGS =====
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE = True
LOG_FILE_NAME = 'NiftyForwarder.log'

# ===== EXAMPLE CONFIGURATIONS =====
"""
Example 1: Monitor public channels and forward to private group
TARGET_CHANNELS = [
    '@technews',
    '@cryptonews',
    'https://t.me/worldnews'
]

SOURCE_CHANNELS = [
    'https://t.me/+Your_Private_Group_Link'
]

Example 2: Monitor private channels and forward to public channel
TARGET_CHANNELS = [
    'https://t.me/+Private_Channel_Link_1',
    'https://t.me/+Private_Channel_Link_2'
]

SOURCE_CHANNELS = [
    '@your_public_channel'
]

Example 3: Cross-forward between multiple channels
TARGET_CHANNELS = [
    '@source_channel_1',
    '@source_channel_2'
]

SOURCE_CHANNELS = [
    '@destination_channel_1',
    '@destination_channel_2',
    '@destination_channel_3'
]
"""

# ===== VALIDATION =====
def validate_config():
    """Validate configuration settings"""
    errors = []
    
    if not API_ID or API_ID == 12345678:
        errors.append("API_ID not configured")
        
    if not API_HASH or API_HASH == 'your_api_hash_here':
        errors.append("API_HASH not configured")
        
    if not TARGET_CHANNELS:
        errors.append("TARGET_CHANNELS list is empty")
        
    if not SOURCE_CHANNELS:
        errors.append("SOURCE_CHANNELS list is empty")
        
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
        
    return True

if __name__ == "__main__":
    if validate_config():
        print("Configuration is valid!")
    else:
        print("Please fix the configuration errors above.")