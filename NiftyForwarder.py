#!/usr/bin/env python3
"""
NiftyForwarder - Telegram Message Forwarder
Author: @ItsHarshX
Description: Monitors target channels and forwards new messages to source channels
Support: Contact @ItsHarshX for support and updates
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import PeerChannel, PeerChat, PeerUser
import config

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
║                        🚀 Advanced Telegram Message Forwarder 🚀                    ║
║                                                                                      ║
║                              📞 Contact Support: @ItsHarshX                         ║
║                              📧 For updates and assistance                          ║
║                                                                                      ║
║                        ✨ Forward messages with style and precision ✨             ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
"""
    print(banner)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('NiftyForwarder.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class NiftyForwarder:
    def __init__(self):
        self.client = None
        self.session_file = 'NiftyForwarder_session'
        self.target_channels = config.TARGET_CHANNELS
        self.source_channels = config.SOURCE_CHANNELS
        self.api_id = config.API_ID
        self.api_hash = config.API_HASH
        self.phone = config.PHONE_NUMBER
        
    async def initialize_client(self):
        """Initialize Telegram client and handle authentication"""
        try:
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            await self.client.start()
            
            # Check if user is authorized
            if not await self.client.is_user_authorized():
                logger.info("User not authorized. Starting authentication process...")
                await self.authenticate()
            else:
                logger.info("Session found and user is authorized!")
                
            # Get user info
            me = await self.client.get_me()
            logger.info(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'No username'})")
            
        except Exception as e:
            logger.error(f"Failed to initialize client: {e}")
            raise
            
    async def authenticate(self):
        """Handle user authentication"""
        try:
            if not self.phone:
                self.phone = input("Enter your phone number (with country code): ")
                
            await self.client.send_code_request(self.phone)
            code = input("Enter the verification code: ")
            
            try:
                await self.client.sign_in(self.phone, code)
            except SessionPasswordNeededError:
                password = input("Enter your 2FA password: ")
                await self.client.sign_in(password=password)
                
            logger.info("Authentication successful!")
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
            
    async def get_entity_info(self, entity_link):
        """Get entity information from channel/group link"""
        try:
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
            logger.error(f"Failed to get entity info for {entity_link}: {e}")
            return None
            
    async def setup_event_handlers(self):
        """Setup event handlers for monitoring target channels"""
        logger.info("Setting up event handlers...")
        
        # Get all target entities
        target_entities = []
        for target in self.target_channels:
            entity = await self.get_entity_info(target)
            if entity:
                target_entities.append(entity)
                logger.info(f"✅ Added target: {entity.title if hasattr(entity, 'title') else entity.first_name}")
            else:
                logger.warning(f"❌ Failed to add target: {target}")
                
        if not target_entities:
            logger.error("No valid target channels found!")
            return False
            
        # Get all source entities
        source_entities = []
        for source in self.source_channels:
            entity = await self.get_entity_info(source)
            if entity:
                source_entities.append(entity)
                logger.info(f"✅ Added source: {entity.title if hasattr(entity, 'title') else entity.first_name}")
            else:
                logger.warning(f"❌ Failed to add source: {source}")
                
        if not source_entities:
            logger.error("No valid source channels found!")
            return False
            
        # Register event handler for new messages
        @self.client.on(events.NewMessage(chats=target_entities))
        async def handle_new_message(event):
            await self.forward_message(event, source_entities)
            
        logger.info(f"🎯 Event handlers set up for {len(target_entities)} target(s) and {len(source_entities)} source(s)")
        return True
        
    async def forward_message(self, event, source_entities):
        """Forward message to all source channels"""
        try:
            # Get sender info
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            # Log message details
            sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', 'Unknown')
            chat_name = getattr(chat, 'title', '') or getattr(chat, 'first_name', 'Unknown')
            
            logger.info(f"📨 New message from {sender_name} in {chat_name}")
            
            # Forward to all source channels
            for source_entity in source_entities:
                try:
                    await asyncio.sleep(1)  # Rate limiting
                    
                    # Forward the message
                    await self.client.forward_messages(
                        entity=source_entity,
                        messages=event.message,
                        from_peer=event.chat_id
                    )
                    
                    source_name = getattr(source_entity, 'title', '') or getattr(source_entity, 'first_name', 'Unknown')
                    logger.info(f"✅ Message forwarded to {source_name}")
                    
                except FloodWaitError as e:
                    logger.warning(f"⏳ Rate limited for {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to forward message to {source_entity}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in forward_message: {e}")
            
    async def run(self):
        """Main running loop"""
        try:
            logger.info("🚀 Starting NiftyForwarder...")
            
            # Initialize client
            await self.initialize_client()
            
            # Setup event handlers
            if not await self.setup_event_handlers():
                logger.error("❌ Failed to setup event handlers. Exiting...")
                return
                
            logger.info("🎉 NiftyForwarder is now running 24/7. Press Ctrl+C to stop.")
            logger.info("📞 Need help? Contact @ItsHarshX for support!")
            
            # Keep the client running
            await self.client.run_until_disconnected()
            
        except KeyboardInterrupt:
            logger.info("⏹️  Received interrupt signal. Stopping...")
            
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            logger.error("📞 Contact @ItsHarshX for assistance!")
            
        finally:
            if self.client:
                await self.client.disconnect()
                logger.info("🔌 Client disconnected.")
                
    def start(self):
        """Start the forwarder"""
        try:
            # Print banner
            print_banner()
            
            # Run the async main function
            asyncio.run(self.run())
            
        except KeyboardInterrupt:
            logger.info("⏹️  NiftyForwarder stopped by user.")
            
        except Exception as e:
            logger.error(f"❌ Failed to start NiftyForwarder: {e}")
            logger.error("📞 Contact @ItsHarshX for troubleshooting!")

def main():
    """Main function"""
    # Check if config is properly set
    if not all([config.API_ID, config.API_HASH]):
        logger.error("❌ Please configure API_ID and API_HASH in config.py")
        logger.error("📞 Need help? Contact @ItsHarshX")
        sys.exit(1)
        
    if not config.TARGET_CHANNELS or not config.SOURCE_CHANNELS:
        logger.error("❌ Please configure TARGET_CHANNELS and SOURCE_CHANNELS in config.py")
        logger.error("📞 Need help? Contact @ItsHarshX")
        sys.exit(1)
        
    # Create and start forwarder
    forwarder = NiftyForwarder()
    forwarder.start()

if __name__ == "__main__":
    main()