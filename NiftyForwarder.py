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
import time
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

def setup_logging():
    """Setup logging configuration"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configure logging
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    
    if config.LOG_TO_FILE:
        handlers.append(logging.FileHandler(f'logs/{config.LOG_FILE_NAME}'))
    
    logging.basicConfig(
        level=log_level,
        format=log_format,
        handlers=handlers
    )
    
    return logging.getLogger(__name__)

class NiftyForwarder:
    def __init__(self):
        self.client = None
        self.session_file = 'NiftyForwarder_session'
        self.target_channels = config.TARGET_CHANNELS
        self.source_channels = config.SOURCE_CHANNELS
        self.api_id = config.API_ID
        self.api_hash = config.API_HASH
        self.phone = config.PHONE_NUMBER
        self.logger = logging.getLogger(__name__)
        
    async def initialize_client(self):
        """Initialize Telegram client and handle authentication"""
        try:
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            await self.client.start()
            
            # Check if user is authorized
            if not await self.client.is_user_authorized():
                self.logger.info("User not authorized. Starting authentication process...")
                await self.authenticate()
            else:
                self.logger.info("Session found and user is authorized!")
                
            # Get user info
            me = await self.client.get_me()
            self.logger.info(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'No username'})")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize client: {e}")
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
                
            self.logger.info("Authentication successful!")
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
            
    async def get_entity_info(self, entity_link):
        """Get entity information from channel/group link"""
        try:
            # Handle private invite links
            if '+' in entity_link and 't.me' in entity_link:
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
        """Setup event handlers for monitoring target channels"""
        self.logger.info("Setting up event handlers...")
        
        # Get all target entities
        target_entities = []
        for target in self.target_channels:
            entity = await self.get_entity_info(target)
            if entity:
                target_entities.append(entity)
                entity_name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
                self.logger.info(f"✅ Added target: {entity_name}")
            else:
                self.logger.warning(f"❌ Failed to add target: {target}")
                
        if not target_entities:
            self.logger.error("No valid target channels found!")
            return False
            
        # Get all source entities
        source_entities = []
        for source in self.source_channels:
            entity = await self.get_entity_info(source)
            if entity:
                source_entities.append(entity)
                entity_name = getattr(entity, 'title', None) or getattr(entity, 'first_name', 'Unknown')
                self.logger.info(f"✅ Added source: {entity_name}")
            else:
                self.logger.warning(f"❌ Failed to add source: {source}")
                
        if not source_entities:
            self.logger.error("No valid source channels found!")
            return False
            
        # Register event handler for new messages
        @self.client.on(events.NewMessage(chats=target_entities))
        async def handle_new_message(event):
            await self.forward_message(event, source_entities)
            
        self.logger.info(f"🎯 Event handlers set up for {len(target_entities)} target(s) and {len(source_entities)} source(s)")
        return True
        
    async def forward_message(self, event, source_entities):
        """Forward message to all source channels"""
        try:
            # Check message filters
            if not self.should_forward_message(event):
                return
                
            # Get sender info
            sender = await event.get_sender()
            chat = await event.get_chat()
            
            # Log message details
            sender_name = getattr(sender, 'first_name', '') or getattr(sender, 'title', 'Unknown')
            chat_name = getattr(chat, 'title', '') or getattr(chat, 'first_name', 'Unknown')
            
            self.logger.info(f"📨 New message from {sender_name} in {chat_name}")
            
            # Forward to all source channels
            forwarded_count = 0
            for source_entity in source_entities:
                try:
                    # Apply rate limiting
                    await asyncio.sleep(config.FORWARD_DELAY)
                    
                    # Forward the message
                    await self.client.forward_messages(
                        entity=source_entity,
                        messages=event.message,
                        from_peer=event.chat_id
                    )
                    
                    source_name = getattr(source_entity, 'title', '') or getattr(source_entity, 'first_name', 'Unknown')
                    self.logger.info(f"✅ Message forwarded to {source_name}")
                    forwarded_count += 1
                    
                except FloodWaitError as e:
                    self.logger.warning(f"⏳ Rate limited for {e.seconds} seconds")
                    await asyncio.sleep(e.seconds)
                    
                    # Retry forwarding after wait
                    try:
                        await self.client.forward_messages(
                            entity=source_entity,
                            messages=event.message,
                            from_peer=event.chat_id
                        )
                        forwarded_count += 1
                    except Exception as retry_error:
                        self.logger.error(f"❌ Retry failed for {source_entity}: {retry_error}")
                    
                except Exception as e:
                    self.logger.error(f"❌ Failed to forward message to {source_entity}: {e}")
                    
            self.logger.info(f"📊 Message forwarded to {forwarded_count}/{len(source_entities)} channels")
                    
        except Exception as e:
            self.logger.error(f"❌ Error in forward_message: {e}")
            
    def should_forward_message(self, event):
        """Check if message should be forwarded based on filters"""
        message = event.message
        
        # Check media filter
        if config.IGNORE_MEDIA and message.media:
            self.logger.debug("⏭️ Skipping media message")
            return False
            
        # Check forwards filter
        if config.IGNORE_FORWARDS and message.forward:
            self.logger.debug("⏭️ Skipping forwarded message")
            return False
            
        # Check bots filter
        if config.IGNORE_BOTS and message.from_id and hasattr(message.from_id, 'user_id'):
            try:
                sender = event.sender
                if sender and getattr(sender, 'bot', False):
                    self.logger.debug("⏭️ Skipping bot message")
                    return False
            except:
                pass
                
        return True
            
    async def run(self):
        """Main running loop"""
        try:
            self.logger.info("🚀 Starting NiftyForwarder...")
            
            # Initialize client
            await self.initialize_client()
            
            # Setup event handlers
            if not await self.setup_event_handlers():
                self.logger.error("❌ Failed to setup event handlers. Exiting...")
                return
                
            self.logger.info("🎉 NiftyForwarder is now running 24/7. Press Ctrl+C to stop.")
            self.logger.info("📞 Need help? Contact @ItsHarshX for support!")
            
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
                
    def start(self):
        """Start the forwarder"""
        try:
            # Print banner
            print_banner()
            
            # Run the async main function
            asyncio.run(self.run())
            
        except KeyboardInterrupt:
            self.logger.info("⏹️  NiftyForwarder stopped by user.")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start NiftyForwarder: {e}")
            self.logger.error("📞 Contact @ItsHarshX for troubleshooting!")
            raise

def main():
    """Main function with retry logic"""
    # Setup logging first
    logger = setup_logging()
    
    # Validate configuration
    if not config.validate_config():
        logger.error("❌ Configuration validation failed!")
        logger.error("📞 Need help? Contact @ItsHarshX")
        sys.exit(1)
    
    # Retry logic for robustness
    max_retries = 3
    retry_delay = 30
    
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Starting attempt {attempt + 1}/{max_retries}")
            
            # Create and start forwarder
            forwarder = NiftyForwarder()
            forwarder.start()
            
            # If we reach here, the forwarder ran successfully
            break
            
        except KeyboardInterrupt:
            logger.info("⏹️  NiftyForwarder stopped by user.")
            break
            
        except Exception as e:
            logger.error(f"❌ Attempt {attempt + 1} failed: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"⏳ Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error("❌ All retry attempts failed!")
                logger.error("📞 Contact @ItsHarshX for assistance!")
                sys.exit(1)

if __name__ == "__main__":
    main()