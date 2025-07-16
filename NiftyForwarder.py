#!/usr/bin/env python3
"""
NiftyForwarder - Telegram Message Forwarder with Keyword Filtering
Author: @ItsHarshX
Description: Monitors source channels and forwards messages containing specific keywords to target channels.
Features persistent message mapping for handling edits/deletions across restarts.
Support: Contact @ItsHarshX for support and updates
"""

import asyncio
import logging
import os
import sys
import time
import re
import json
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import PeerChannel, PeerChat, PeerUser

# Default configuration
DEFAULT_CONFIG = {
    'LOG_LEVEL': 'INFO',
    'LOG_TO_FILE': True,
    'LOG_FILE_NAME': 'nifty_forwarder.log',
    'FORWARD_DELAY': 2,
    'IGNORE_MEDIA': False,
    'IGNORE_FORWARDS': False,
    'IGNORE_BOTS': False
}

def print_banner():
    """Print the NiftyPool ASCII banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║      ███╗   ██╗██╗███████╗████████╗██╗   ██╗    ██████╗  ██████╗  ██████╗ ██╗       ║
║      ████╗  ██║██║██╔════╝╚══██╔══╝╚██╗ ██╔╝    ██╔══██╗██╔═══██╗██╔═══██╗██║       ║
║      ██╔██╗ ██║██║█████╗     ██║    ╚████╔╝     ██████╔╝██║   ██║██║   ██║██║       ║
║      ██║╚██╗██║██║██╔══╝     ██║     ╚██╔╝      ██╔═══╝ ██║   ██║██║   ██║██║       ║
║      ██║ ╚████║██║██║        ██║      ██║       ██║     ╚██████╔╝╚██████╔╝███████╗  ║
║      ╚═╝  ╚═══╝╚═╝╚═╝        ╚═╝      ╚═╝       ╚═╝      ╚═════╝  ╚═════╝ ╚══════╝  ║
║                                                                                      ║
║                    🚀 Advanced Telegram Message Forwarder with Keywords 🚀          ║
║                                                                                      ║
║                              📞 Contact Support: @ItsHarshX                         ║
║                              📧 For updates and assistance                          ║
║                                                                                      ║
║                        ✨ Forward messages with keyword filtering ✨               ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    log_level = getattr(logging, DEFAULT_CONFIG['LOG_LEVEL'].upper(), logging.INFO)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if DEFAULT_CONFIG['LOG_TO_FILE']:
        handlers.append(logging.FileHandler(f'logs/{DEFAULT_CONFIG["LOG_FILE_NAME"]}'))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

class SettingsManager:
    """Manages persistent settings for the forwarder"""
    
    def __init__(self, settings_file='nifty_settings.json'):
        self.settings_file = settings_file
        self.settings = self.load_settings()
        
    def load_settings(self):
        """Load settings from file"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"❌ Error loading settings: {e}")
                return {}
        return {}
        
    def save_settings(self):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            return True
        except Exception as e:
            print(f"❌ Error saving settings: {e}")
            return False
            
    def get(self, key, default=None):
        """Get setting value"""
        return self.settings.get(key, default)
        
    def set(self, key, value):
        """Set setting value"""
        self.settings[key] = value
        
    def has_complete_setup(self):
        """Check if all required settings are present"""
        required_settings = ['api_id', 'api_hash', 'phone_number', 'source_channels', 'target_channels', 'keywords']
        return all(self.get(key) for key in required_settings)

class NiftyForwarder:
    def __init__(self):
        self.client = None
        self.session_file = 'NiftyForwarder_session'
        self.logger = logging.getLogger(__name__)
        self.settings_manager = SettingsManager()
        
        # ADD THIS LINE:
        self.message_mapping = {}  # Maps original_msg_id -> [forwarded_msg_id1, forwarded_msg_id2, ...]
        self.message_mapping_file = 'nifty_message_mapping.json'
        
        # Initialize settings
        self.api_id = None
        self.api_hash = None
        self.phone = None
        self.source_channels = []
        self.target_channels = []
        self.keywords = []
        self.case_sensitive = False
        
    def load_message_mapping(self):
        """Load message mapping from file"""
        try:
            if os.path.exists(self.message_mapping_file):
                with open(self.message_mapping_file, 'r') as f:
                    # Load as strings and convert keys to integers
                    data = json.load(f)
                    self.message_mapping = {int(k): v for k, v in data.items()}
                    self.logger.info(f"📁 Loaded {len(self.message_mapping)} message mappings from file")
            else:
                self.message_mapping = {}
                self.logger.info("📁 No existing message mapping file found, starting fresh")
        except Exception as e:
            self.logger.error(f"❌ Error loading message mapping: {e}")
            self.message_mapping = {}
            
    def save_message_mapping(self):
        """Save message mapping to file"""
        try:
            # Convert integer keys to strings for JSON compatibility
            data = {str(k): v for k, v in self.message_mapping.items()}
            with open(self.message_mapping_file, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.debug(f"💾 Saved message mapping with {len(self.message_mapping)} entries")
        except Exception as e:
            self.logger.error(f"❌ Error saving message mapping: {e}")
            
    def cleanup_old_mappings(self, max_age_days=30):
        """Clean up old message mappings to prevent file from growing too large"""
        try:
            if not self.message_mapping:
                return
                
            # For simplicity, we'll just keep the most recent 1000 mappings
            # In a production environment, you might want to implement time-based cleanup
            if len(self.message_mapping) > 1000:
                # Keep only the 1000 most recent mappings (assuming higher IDs are more recent)
                sorted_keys = sorted(self.message_mapping.keys(), reverse=True)
                keys_to_keep = sorted_keys[:1000]
                
                old_count = len(self.message_mapping)
                self.message_mapping = {k: self.message_mapping[k] for k in keys_to_keep}
                
                self.logger.info(f"🧹 Cleaned up message mapping: {old_count} -> {len(self.message_mapping)} entries")
                self.save_message_mapping()
        except Exception as e:
            self.logger.error(f"❌ Error cleaning up message mappings: {e}")
            
    def show_mapping_statistics(self):
        """Show detailed message mapping statistics for debugging"""
        if not self.message_mapping:
            print("📁 No message mappings found.")
            return
            
        print(f"📊 Message Mapping Statistics:")
        print(f"   Total entries: {len(self.message_mapping)}")
        
        # Show some sample mappings
        sample_size = min(5, len(self.message_mapping))
        if sample_size > 0:
            print(f"   Sample mappings (latest {sample_size}):")
            sorted_keys = sorted(self.message_mapping.keys(), reverse=True)
            for i, key in enumerate(sorted_keys[:sample_size]):
                forwarded_count = len(self.message_mapping[key])
                print(f"      Message {key} -> {forwarded_count} forwarded copies")
                
        # Show file size if it exists
        if os.path.exists(self.message_mapping_file):
            file_size = os.path.getsize(self.message_mapping_file)
            print(f"   File size: {file_size:,} bytes")
        
    def main_menu(self):
        """Main menu for the forwarder"""
        while True:
            print("\n🚀 NIFTY FORWARDER - MAIN MENU")
            print("=" * 40)
            
            # Check if settings exist
            if self.settings_manager.has_complete_setup():
                print("✅ Settings configured and ready!")
                self.display_current_settings()
                
                print("\n📋 MENU OPTIONS:")
                print("1. 🚀 Start NiftyForwarder")
                print("2. 🔧 Modify Settings")
                print("3. 📋 View Current Settings")
                print("4. 🗑️  Reset All Settings")
                print("5. ❌ Exit")
                
                choice = input("\nEnter your choice (1-5): ").strip()
                
                if choice == '1':
                    self.load_existing_settings()
                    return True  # Start the forwarder
                elif choice == '2':
                    self.modify_settings_menu()
                    continue  # Stay in main menu after modifying settings
                elif choice == '3':
                    self.display_current_settings()
                    input("\nPress Enter to continue...")
                    continue  # Stay in main menu
                elif choice == '4':
                    self.reset_all_settings()
                    continue  # Stay in main menu
                elif choice == '5':
                    print("👋 Goodbye!")
                    return False  # Exit
                else:
                    print("❌ Invalid choice! Please enter 1-5.")
            else:
                print("🆕 First time setup required!")
                print("\n📋 MENU OPTIONS:")
                print("1. 🔧 Complete Setup")
                print("2. ❌ Exit")
                
                choice = input("\nEnter your choice (1-2): ").strip()
                
                if choice == '1':
                    self.setup_all_settings()
                    continue  # Return to main menu after setup
                elif choice == '2':
                    print("👋 Goodbye!")
                    return False  # Exit
                else:
                    print("❌ Invalid choice! Please enter 1-2.")
                    
    def interactive_setup(self):
        """Interactive setup - now just calls main menu"""
        return self.main_menu()
            
    def display_current_settings(self):
        """Display current settings"""
        print("\n📋 CURRENT SETTINGS:")
        print("-" * 30)
        print(f"📱 Phone Number: {self.settings_manager.get('phone_number', 'Not set')}")
        print(f"🔑 API ID: {self.settings_manager.get('api_id', 'Not set')}")
        print(f"🔐 API Hash: {'*' * 20 if self.settings_manager.get('api_hash') else 'Not set'}")
        
        source_channels = self.settings_manager.get('source_channels', [])
        print(f"📥 Source Channels ({len(source_channels)}): {', '.join(source_channels) if source_channels else 'None'}")
        
        target_channels = self.settings_manager.get('target_channels', [])
        print(f"📤 Target Channels ({len(target_channels)}): {', '.join(target_channels) if target_channels else 'None'}")
        
        keywords = self.settings_manager.get('keywords', [])
        print(f"🔍 Keywords ({len(keywords)}): {', '.join(keywords) if keywords else 'None'}")
        print(f"🔤 Case Sensitive: {'Yes' if self.settings_manager.get('case_sensitive', False) else 'No'}")
        
        # Show message mapping statistics
        mapping_count = len(self.message_mapping) if hasattr(self, 'message_mapping') else 0
        print(f"📁 Message Mappings: {mapping_count} entries")
        if mapping_count > 0:
            print(f"📊 (For tracking edits/deletions across restarts)")
        
    def modify_settings_menu(self):
        """Menu for modifying existing settings"""
        while True:
            print("\n🔧 MODIFY SETTINGS")
            print("=" * 30)
            print("1. Change Account (API ID, API Hash, Phone)")
            print("2. Modify Source Channels")
            print("3. Modify Target Channels")
            print("4. Modify Keywords")
            print("5. Change All Settings")
            print("6. ⬅️  Back to Main Menu")
            
            choice = input("\nEnter your choice (1-6): ").strip()
            
            if choice == '1':
                self.setup_api_credentials()
                self.save_current_settings()
                print("✅ Account settings updated!")
                input("\nPress Enter to continue...")
            elif choice == '2':
                self.setup_source_channels()
                self.save_current_settings()
                print("✅ Source channels updated!")
                input("\nPress Enter to continue...")
            elif choice == '3':
                self.setup_target_channels()
                self.save_current_settings()
                print("✅ Target channels updated!")
                input("\nPress Enter to continue...")
            elif choice == '4':
                self.setup_keywords()
                self.save_current_settings()
                print("✅ Keywords updated!")
                input("\nPress Enter to continue...")
            elif choice == '5':
                self.setup_all_settings()
                input("\nPress Enter to continue...")
            elif choice == '6':
                break  # Return to main menu
            else:
                print("❌ Invalid choice! Please enter 1-6.")
                
    def reset_all_settings(self):
        """Reset all settings"""
        print("\n🗑️  RESET ALL SETTINGS")
        print("=" * 30)
        print("⚠️  This will delete all your saved settings!")
        print("You will need to reconfigure everything.")
        
        while True:
            confirm = input("\nAre you sure you want to reset all settings? (yes/no): ").strip().lower()
            if confirm in ['yes', 'y']:
                try:
                    # Clear settings
                    self.settings_manager.settings = {}
                    self.settings_manager.save_settings()
                    
                    # Remove session file
                    session_files = [f"{self.session_file}.session", f"{self.session_file}.session-journal"]
                    for file_path in session_files:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                    
                    # Remove message mapping file
                    if os.path.exists(self.message_mapping_file):
                        os.remove(self.message_mapping_file)
                        self.logger.info(f"📁 Deleted message mapping file: {self.message_mapping_file}")
                    
                    print("✅ All settings have been reset!")
                    input("\nPress Enter to continue...")
                    break
                except Exception as e:
                    print(f"❌ Error resetting settings: {e}")
                    input("\nPress Enter to continue...")
                    break
            elif confirm in ['no', 'n']:
                print("✅ Settings reset cancelled.")
                input("\nPress Enter to continue...")
                break
            else:
                print("❌ Please enter 'yes' or 'no'!")
                
    def setup_all_settings(self):
        """Setup all settings from scratch"""
        print("\n🔧 COMPLETE SETUP")
        print("=" * 30)
        
        self.setup_api_credentials()
        self.setup_source_channels()
        self.setup_target_channels()
        self.setup_keywords()
        
        # Save all settings
        if self.save_current_settings():
            print("\n✅ All settings saved successfully!")
        else:
            print("\n❌ Failed to save settings!")
            
    def setup_api_credentials(self):
        """Setup API credentials"""
        print("\n🔑 API CREDENTIALS SETUP")
        print("Get your API credentials from: https://my.telegram.org/auth")
        print("-" * 40)
        
        while True:
            try:
                api_id = input("Enter your API ID: ").strip()
                if api_id:
                    self.api_id = int(api_id)
                    break
                else:
                    print("❌ API ID cannot be empty!")
            except ValueError:
                print("❌ API ID must be a number!")
                
        while True:
            api_hash = input("Enter your API Hash: ").strip()
            if api_hash:
                self.api_hash = api_hash
                break
            else:
                print("❌ API Hash cannot be empty!")
                
        while True:
            phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
            if phone:
                self.phone = phone
                break
            else:
                print("❌ Phone number cannot be empty!")
                
        print("✅ API credentials configured!")
        
    def setup_source_channels(self):
        """Setup source channels (where messages are monitored)"""
        print("\n📥 SOURCE CHANNELS SETUP")
        print("These are channels/groups where messages will be monitored.")
        print("You can enter usernames (@channel) or invite links.")
        print("-" * 50)
        
        self.source_channels = []
        
        while True:
            channel = input("Enter source channel/group (or 'done' to finish): ").strip()
            if channel.lower() == 'done':
                if self.source_channels:
                    break
                else:
                    print("❌ You must add at least one source channel!")
                    continue
            elif channel:
                self.source_channels.append(channel)
                print(f"✅ Added source channel: {channel}")
            else:
                print("❌ Channel cannot be empty!")
                
        print(f"✅ {len(self.source_channels)} source channel(s) configured!")
        
    def setup_target_channels(self):
        """Setup target channels (where messages are forwarded)"""
        print("\n📤 TARGET CHANNELS SETUP")
        print("These are channels/groups where messages will be forwarded.")
        print("You can enter usernames (@channel) or invite links.")
        print("-" * 50)
        
        self.target_channels = []
        
        while True:
            channel = input("Enter target channel/group (or 'done' to finish): ").strip()
            if channel.lower() == 'done':
                if self.target_channels:
                    break
                else:
                    print("❌ You must add at least one target channel!")
                    continue
            elif channel:
                self.target_channels.append(channel)
                print(f"✅ Added target channel: {channel}")
            else:
                print("❌ Channel cannot be empty!")
                
        print(f"✅ {len(self.target_channels)} target channel(s) configured!")
        
    def setup_keywords(self):
        """Setup keywords for filtering messages"""
        print("\n🔍 KEYWORDS SETUP")
        print("Enter keywords that must be present in messages to forward them.")
        print("You can enter multiple keywords separated by commas.")
        print("Example: bitcoin,crypto,trading")
        print("-" * 40)
        
        while True:
            keyword_input = input("Enter keywords (comma-separated): ").strip()
            if keyword_input:
                self.keywords = [kw.strip() for kw in keyword_input.split(',') if kw.strip()]
                break
            else:
                print("❌ Please enter at least one keyword!")
        
        # Ask for case sensitivity
        while True:
            case_input = input("Should keyword matching be case-sensitive? (y/n): ").strip().lower()
            if case_input in ['y', 'yes']:
                self.case_sensitive = True
                break
            elif case_input in ['n', 'no']:
                self.case_sensitive = False
                break
            else:
                print("❌ Please enter 'y' or 'n'!")
        
        print(f"✅ Keywords configured: {', '.join(self.keywords)}")
        print(f"✅ Case sensitive: {'Yes' if self.case_sensitive else 'No'}")
        
    def load_existing_settings(self):
        """Load existing settings from file"""
        self.api_id = self.settings_manager.get('api_id')
        self.api_hash = self.settings_manager.get('api_hash')
        self.phone = self.settings_manager.get('phone_number')
        self.source_channels = self.settings_manager.get('source_channels', [])
        self.target_channels = self.settings_manager.get('target_channels', [])
        self.keywords = self.settings_manager.get('keywords', [])
        self.case_sensitive = self.settings_manager.get('case_sensitive', False)
        
        print("✅ Existing settings loaded!")
        
    def save_current_settings(self):
        """Save current settings to file"""
        self.settings_manager.set('api_id', self.api_id)
        self.settings_manager.set('api_hash', self.api_hash)
        self.settings_manager.set('phone_number', self.phone)
        self.settings_manager.set('source_channels', self.source_channels)
        self.settings_manager.set('target_channels', self.target_channels)
        self.settings_manager.set('keywords', self.keywords)
        self.settings_manager.set('case_sensitive', self.case_sensitive)
        
        return self.settings_manager.save_settings()
        
    async def initialize_client(self):
        """Initialize Telegram client and handle authentication"""
        try:
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            await self.client.start(phone=self.phone)
            
            # Check if user is authorized
            if not await self.client.is_user_authorized():
                self.logger.info("User not authorized. Starting authentication process...")
                await self.authenticate()
            else:
                self.logger.info("Session found and user is authorized!")
                
            # Load message mapping for handling edits/deletions
            self.load_message_mapping()
            
            # Get user info
            me = await self.client.get_me()
            self.logger.info(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'No username'})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize client: {e}")
            raise
            
    async def authenticate(self):
        """Handle user authentication"""
        try:
            # Request verification code
            await self.client.send_code_request(self.phone)
            
            while True:
                try:
                    code = input("Enter the verification code: ").strip()
                    if not code:
                        print("❌ Code cannot be empty!")
                        continue
                    
                    await self.client.sign_in(self.phone, code)
                    break
                    
                except SessionPasswordNeededError:
                    password = input("Enter your 2FA password: ").strip()
                    if password:
                        await self.client.sign_in(password=password)
                        break
                    else:
                        print("❌ Password cannot be empty!")
                        
                except Exception as e:
                    self.logger.error(f"Authentication error: {e}")
                    print("❌ Invalid code or authentication failed. Please try again.")
                    
            self.logger.info("Authentication successful!")
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
            
    async def get_entity_info(self, entity_link):
        """Get entity information from channel/group link"""
        try:
            # Handle private invite links
            if 'joinchat' in entity_link or '+' in entity_link:
                entity = await self.client.get_entity(entity_link)
                return entity
            
            # Extract username from link
            if '/' in entity_link:
                username = entity_link.split('/')[-1]
            else:
                username = entity_link
                
            # Remove @ if present
            if username.startswith('@'):
                username = username[1:]
                
            entity = await self.client.get_entity(username)
            return entity
            
        except Exception as e:
            self.logger.error(f"Failed to get entity info for {entity_link}: {e}")
            return None
            
    async def setup_event_handlers(self):
        """Setup event handlers for monitoring source channels"""
        self.logger.info("Setting up event handlers...")
        
        # Get all source entities (channels we monitor)
        source_entities = []
        for source in self.source_channels:
            entity = await self.get_entity_info(source)
            if entity:
                source_entities.append(entity)
                entity_name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
                self.logger.info(f"✅ Added source channel: {entity_name}")
            else:
                self.logger.warning(f"❌ Failed to add source channel: {source}")
                
        if not source_entities:
            self.logger.error("No valid source channels found!")
            return False
            
        # Get all target entities (channels we forward to)
        target_entities = []
        for target in self.target_channels:
            entity = await self.get_entity_info(target)
            if entity:
                target_entities.append(entity)
                entity_name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
                self.logger.info(f"✅ Added target channel: {entity_name}")
            else:
                self.logger.warning(f"❌ Failed to add target channel: {target}")
                
        if not target_entities:
            self.logger.error("No valid target channels found!")
            return False
            
        # Register event handler for new messages from source channels
        @self.client.on(events.NewMessage(chats=source_entities))
        async def handle_new_message(event):
            await self.forward_message(event, target_entities)
            
        # ADD THESE TWO NEW HANDLERS:
        @self.client.on(events.MessageEdited(chats=source_entities))
        async def handle_edited_message(event):
            await self.handle_message_edit(event, target_entities)

        @self.client.on(events.MessageDeleted)
        async def handle_deleted_message(event):
            await self.handle_message_deletion(event, target_entities)
            
        self.logger.info(f"🎯 Event handlers set up for {len(source_entities)} source(s) and {len(target_entities)} target(s)")
        return True
        
    def check_keyword_match(self, message_text):
        """Check if message contains any of the specified keywords"""
        if not self.keywords or not message_text:
            return False
            
        # Prepare text for matching
        text_to_check = message_text if self.case_sensitive else message_text.lower()
        
        # Check each keyword
        for keyword in self.keywords:
            keyword_to_check = keyword if self.case_sensitive else keyword.lower()
            
            # Check if keyword is present in the message
            if keyword_to_check in text_to_check:
                self.logger.info(f"🎯 Keyword match found: '{keyword}' in message")
                return True
                
        return False
        
    async def forward_message(self, event, target_entities):
        """Forward message to all target channels if it contains keywords"""
        try:
            # Get message text
            message_text = event.message.text or ""
            
            # Check if message contains keywords
            if not self.check_keyword_match(message_text):
                self.logger.debug(f"⏭️ Message skipped - no keyword match: '{message_text[:50]}...'")
                return
                
            # Check other message filters
            if not self.should_forward_message(event):
                return
                
            # Get sender info safely
            try:
                sender = await event.get_sender()
                chat = await event.get_chat()
                
                # Log message details
                sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', 'Unknown')
                chat_name = getattr(chat, 'title', '') or getattr(chat, 'first_name', 'Unknown')
                
                self.logger.info(f"📨 Keyword match! Forwarding message from {sender_name} in {chat_name}")
                self.logger.info(f"📝 Message preview: {message_text[:100]}...")
            except Exception as e:
                self.logger.warning(f"Could not get sender/chat info: {e}")
                self.logger.info(f"📨 Forwarding message with keyword match")
                self.logger.info(f"📝 Message preview: {message_text[:100]}...")
            
            # Forward to all target channels
            forwarded_count = 0
            forwarded_message_ids = []  # ADD THIS LINE
            
            for target_entity in target_entities:
                try:
                    # Apply rate limiting
                    await asyncio.sleep(DEFAULT_CONFIG['FORWARD_DELAY'])
                    
                    # Send message as new message (copy) instead of forward to avoid forward tags
                    sent_message = await self.client.send_message(  # CHANGE: store the returned message
                        entity=target_entity,
                        message=event.message
                    )
                    
                    # ADD THIS LINE:
                    forwarded_message_ids.append(sent_message.id)
                    
                    target_name = getattr(target_entity, 'title', '') or getattr(target_entity, 'first_name', 'Unknown')
                    self.logger.info(f"✅ Message sent to {target_name}")
                    forwarded_count += 1
                    
                except FloodWaitError as e:
                    self.logger.warning(f"⏳ Rate limited for {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                    
                    # Retry sending after wait
                    try:
                        sent_message = await self.client.send_message(
                            entity=target_entity,
                            message=event.message
                        )
                        forwarded_message_ids.append(sent_message.id)
                        forwarded_count += 1
                    except Exception as retry_error:
                        self.logger.error(f"❌ Retry failed for {target_entity}: {retry_error}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to send message to {target_entity}: {e}")
                    
            # ADD THIS AFTER THE LOOP:
            # Store message mapping for future edits/deletions
            if forwarded_message_ids:
                self.message_mapping[event.message.id] = forwarded_message_ids
                self.save_message_mapping()
                
                # Periodically clean up old mappings
                if len(self.message_mapping) % 100 == 0:  # Every 100 new messages
                    self.cleanup_old_mappings()
                
            self.logger.info(f"📊 Message sent to {forwarded_count}/{len(target_entities)} channels")
                    
        except Exception as e:
            self.logger.error(f"❌ Error in forward_message: {e}")
            
    async def handle_message_edit(self, event, target_entities):
        """Handle edited messages and update forwarded messages"""
        try:
            # Get message text
            message_text = event.message.text or ""
            
            # Check if message still contains keywords after edit
            if not self.check_keyword_match(message_text):
                self.logger.info(f"🔄 Edited message no longer contains keywords, considering deletion...")
                # Optionally delete the forwarded messages since they no longer match
                await self.handle_message_deletion_by_id(event.message.id, target_entities)
                return
            
            # Check if we have forwarded messages for this original message
            if event.message.id not in self.message_mapping:
                self.logger.debug(f"⏭️ No forwarded messages found for edited message ID: {event.message.id}")
                return
            
            forwarded_ids = self.message_mapping[event.message.id]
            
            self.logger.info(f"✏️ Handling message edit for {len(forwarded_ids)} forwarded messages")
            
            # Edit all forwarded messages
            for i, target_entity in enumerate(target_entities):
                if i < len(forwarded_ids):
                    try:
                        await asyncio.sleep(DEFAULT_CONFIG['FORWARD_DELAY'])
                        
                        # Edit the forwarded message
                        await self.client.edit_message(
                            entity=target_entity,
                            message=forwarded_ids[i],
                            text=event.message.text,
                            file=event.message.media
                        )
                        
                        target_name = getattr(target_entity, 'title', '') or getattr(target_entity, 'first_name', 'Unknown')
                        self.logger.info(f"✅ Message edited in {target_name}")
                        
                    except Exception as e:
                        self.logger.error(f"❌ Failed to edit message in {target_entity}: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ Error in handle_message_edit: {e}")

    async def handle_message_deletion(self, event, target_entities):
        """Handle deleted messages and delete forwarded messages"""
        try:
            # MessageDeleted event contains a list of deleted message IDs
            for deleted_id in event.deleted_ids:
                await self.handle_message_deletion_by_id(deleted_id, target_entities)
                    
        except Exception as e:
            self.logger.error(f"❌ Error in handle_message_deletion: {e}")

    async def handle_message_deletion_by_id(self, original_msg_id, target_entities):
        """Handle deletion of a specific message ID"""
        try:
            # Check if we have forwarded messages for this original message
            if original_msg_id not in self.message_mapping:
                self.logger.debug(f"⏭️ No forwarded messages found for deleted message ID: {original_msg_id}")
                return
            
            forwarded_ids = self.message_mapping[original_msg_id]
            
            self.logger.info(f"🗑️ Handling message deletion for {len(forwarded_ids)} forwarded messages")
            
            # Delete all forwarded messages
            for i, target_entity in enumerate(target_entities):
                if i < len(forwarded_ids):
                    try:
                        await asyncio.sleep(DEFAULT_CONFIG['FORWARD_DELAY'])
                        
                        # Delete the forwarded message
                        await self.client.delete_messages(
                            entity=target_entity,
                            message_ids=[forwarded_ids[i]]
                        )
                        
                        target_name = getattr(target_entity, 'title', '') or getattr(target_entity, 'first_name', 'Unknown')
                        self.logger.info(f"✅ Message deleted from {target_name}")
                        
                    except Exception as e:
                        self.logger.error(f"❌ Failed to delete message from {target_entity}: {e}")
            
            # Remove from mapping since messages are deleted
            del self.message_mapping[original_msg_id]
            self.save_message_mapping()
            
        except Exception as e:
            self.logger.error(f"❌ Error in handle_message_deletion_by_id: {e}")
            
    def should_forward_message(self, event):
        """Check if message should be forwarded based on filters"""
        message = event.message
        
        # Check media filter
        if DEFAULT_CONFIG['IGNORE_MEDIA'] and message.media:
            self.logger.debug("⏭️ Skipping media message")
            return False
            
        # Check forwards filter
        if DEFAULT_CONFIG['IGNORE_FORWARDS'] and message.forward:
            self.logger.debug("⏭️ Skipping forwarded message")
            return False
            
        # Check bots filter
        if DEFAULT_CONFIG['IGNORE_BOTS'] and message.from_id:
            try:
                # For newer Telethon versions, check if sender is a bot
                if hasattr(event, 'sender') and event.sender and getattr(event.sender, 'bot', False):
                    self.logger.debug("⏭️ Skipping bot message")
                    return False
            except:
                pass
                
        return True
            
    async def run(self):
        """Main running loop"""
        try:
            self.logger.info("🚀 Starting NiftyForwarder with Keyword Filtering...")
            
            # Initialize client
            await self.initialize_client()
            
            # Setup event handlers
            if not await self.setup_event_handlers():
                self.logger.error("❌ Failed to setup event handlers. Exiting...")
                return
                
            self.logger.info("🎉 NiftyForwarder is now running 24/7 with keyword filtering!")
            self.logger.info(f"🔍 Monitoring for keywords: {', '.join(self.keywords)}")
            self.logger.info(f"📁 Message mapping loaded: {len(self.message_mapping)} entries")
            self.logger.info("💾 Message mappings persist across restarts for edit/delete handling")
            self.logger.info("📞 Need help? Contact @ItsHarshX for support!")
            self.logger.info("⏹️  Press Ctrl+C to stop.")
            
            # Keep the client running
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            self.logger.info("⏹️  Received interrupt signal. Stopping...")
            
        except Exception as e:
            self.logger.error(f"❌ Unexpected error: {e}")
            self.logger.error("📞 Contact @ItsHarshX for assistance!")
            raise
            
        finally:
            if self.client:
                await self.client.disconnect()
                self.logger.info("🔌 Client disconnected.")
                
            # Save message mapping one final time before exit
            self.save_message_mapping()
            self.logger.info("💾 Final message mapping saved.")
                
    def start(self):
        """Start the forwarder"""
        try:
            # Print banner
            print_banner()
            
            # Show main menu and get user choice
            should_start = self.interactive_setup()
            
            if not should_start:
                print("👋 Exiting NiftyForwarder...")
                return
            
            # Save settings before starting
            if not self.save_current_settings():
                print("⚠️  Warning: Could not save settings!")
            
            print("\n🚀 Starting NiftyForwarder...")
            print("⏳ Please wait while we initialize...")
            
            # Run the async main function
            asyncio.run(self.run())
            
        except KeyboardInterrupt:
            self.logger.info("⏹️  NiftyForwarder stopped by user.")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start NiftyForwarder: {e}")
            self.logger.error("📞 Contact @ItsHarshX for assistance!")
            print(f"❌ Fatal error: {e}")
            print("📞 Contact @ItsHarshX for support!")
            
        finally:
            print("\n🔌 NiftyForwarder session ended.")
            print("📞 For support and updates, contact @ItsHarshX")


# Main execution
if __name__ == "__main__":
    # Setup logging
    logger = setup_logging()
    
    try:
        # Create and start the forwarder
        forwarder = NiftyForwarder()
        forwarder.start()
        
    except KeyboardInterrupt:
        logger.info("⏹️  Program interrupted by user.")
        
    except Exception as e:
        logger.error(f"❌ Critical error: {e}")
        print(f"❌ Critical error: {e}")
        print("📞 Contact @ItsHarshX for support!")
        
    finally:
        logger.info("🔌 Program ended.")
        print("\n👋 Thank you for using NiftyForwarder!")
        print("📞 For support and updates, contact @ItsHarshX")
