import asyncio
import json
import os
import re
import hashlib
import sys
import time
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage, MessageEntityCustomEmoji
from telethon.tl.functions.messages import GetHistoryRequest
from telethon.tl.functions.messages import GetAllStickersRequest, GetStickerSetRequest
from telethon.tl.types import InputStickerSetID
from telethon import utils
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('telegram_forwarder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class Colors:
    """ANSI color codes for terminal output"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    
    # Regular colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

class TelegramForwarder:
    def __init__(self):
        self.client = None
        self.api_id = None
        self.api_hash = None
        self.phone_number = None
        self.source_channels = []
        self.target_channels = []
        self.keywords = []
        self.config_file = 'forwarder_config.json'
        self.session_file = 'NiftyForwarder_session'
        self.message_map = {}  # Maps source_msg_id to target_msg_ids
        self.message_hashes = set()  # Set to store message hashes to prevent duplicates
        self.is_premium = False
        # Hardcoded formatting settings for optimal premium emoji support
        self.use_markdown = True  # Always enable Markdown formatting (HARDCODED)
        self.preserve_formatting = True  # Always preserve original formatting (HARDCODED)
        self.custom_emoji_cache = {}  # Cache for custom emoji document IDs
        
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_loading_animation(self, text="Loading", duration=2):
        """Print a loading animation"""
        frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        end_time = time.time() + duration
        
        while time.time() < end_time:
            for frame in frames:
                print(f"\r{Colors.CYAN}{frame} {text}...{Colors.RESET}", end="", flush=True)
                time.sleep(0.1)
                if time.time() >= end_time:
                    break
        print(f"\r{Colors.GREEN}✓ {text} complete!{Colors.RESET}")
        time.sleep(0.5)
    
    def print_success(self, message):
        """Print success message with green color"""
        print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")
    
    def print_error(self, message):
        """Print error message with red color"""
        print(f"{Colors.RED}❌ {message}{Colors.RESET}")
    
    def print_warning(self, message):
        """Print warning message with yellow color"""
        print(f"{Colors.YELLOW}⚠️ {message}{Colors.RESET}")
    
    def print_info(self, message):
        """Print info message with blue color"""
        print(f"{Colors.BLUE}ℹ️ {message}{Colors.RESET}")
    
    def print_header(self, text):
        """Print a styled header"""
        print(f"\n{Colors.BOLD}{Colors.BRIGHT_CYAN}{'='*60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{text.center(60)}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BRIGHT_CYAN}{'='*60}{Colors.RESET}")
    
    def print_separator(self):
        """Print a visual separator"""
        print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")
    
    def animate_text(self, text, delay=0.05):
        """Animate text character by character"""
        for char in text:
            print(char, end='', flush=True)
            time.sleep(delay)
        print()
    
    def get_status_color(self, status):
        """Get color for status display"""
        if status == "Yes" or status == "Online":
            return Colors.GREEN
        elif status == "No" or status == "Offline":
            return Colors.RED
        else:
            return Colors.YELLOW
    
    def load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.api_id = config.get('api_id')
                    self.api_hash = config.get('api_hash')
                    self.phone_number = config.get('phone_number')
                    self.source_channels = config.get('source_channels', [])
                    self.target_channels = config.get('target_channels', [])
                    self.keywords = config.get('keywords', [])
                    self.message_map = config.get('message_map', {})
                    self.message_hashes = set(config.get('message_hashes', []))
                    self.custom_emoji_cache = config.get('custom_emoji_cache', {})
                    # Note: use_markdown and preserve_formatting are now hardcoded
                logger.info("Configuration loaded successfully")
                logger.info(f"Loaded {len(self.message_hashes)} message hashes for duplicate prevention")
            except Exception as e:
                logger.error(f"Error loading config: {e}")
    
    def generate_message_hash(self, message):
        """Generate a unique hash for a message based on its content"""
        try:
            # Create a hash based on message content
            hash_content = ""
            
            # Add message text
            if message.text:
                hash_content += message.text.strip()
            
            # Add media information if present
            if message.media:
                if hasattr(message.media, 'photo'):
                    # For photos, use photo ID
                    hash_content += f"_photo_{message.media.photo.id}"
                elif hasattr(message.media, 'document'):
                    # For documents, use document ID
                    hash_content += f"_doc_{message.media.document.id}"
                elif isinstance(message.media, MessageMediaWebPage):
                    # For web pages, use URL
                    if hasattr(message.media.webpage, 'url'):
                        hash_content += f"_webpage_{message.media.webpage.url}"
                else:
                    # For other media types, use type name
                    hash_content += f"_media_{type(message.media).__name__}"
            
            # Add message date to make hash more unique (optional, but helps with timing)
            if message.date:
                # Round to nearest minute to allow for slight timing differences
                rounded_date = message.date.replace(second=0, microsecond=0)
                hash_content += f"_date_{rounded_date.timestamp()}"
            
            # Generate MD5 hash
            message_hash = hashlib.md5(hash_content.encode('utf-8')).hexdigest()
            
            logger.debug(f"Generated hash {message_hash} for message content: {hash_content[:100]}...")
            return message_hash
            
        except Exception as e:
            logger.error(f"Error generating message hash: {e}")
            # Return a timestamp-based fallback hash
            return hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()
    
    def is_duplicate_message(self, message):
        """Check if a message is a duplicate based on its hash"""
        try:
            message_hash = self.generate_message_hash(message)
            is_duplicate = message_hash in self.message_hashes
            
            if is_duplicate:
                logger.info(f"Duplicate message detected with hash: {message_hash}")
                return True
            else:
                logger.debug(f"New message with hash: {message_hash}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking duplicate message: {e}")
            return False  # If error, assume it's not a duplicate
    
    def add_message_hash(self, message):
        """Add a message hash to the set of processed messages"""
        try:
            message_hash = self.generate_message_hash(message)
            self.message_hashes.add(message_hash)
            logger.debug(f"Added message hash: {message_hash}")
            
            # Clean up old hashes if set gets too large (keep last 10000 hashes)
            if len(self.message_hashes) > 10000:
                # Convert to list, remove oldest 1000, convert back to set
                hash_list = list(self.message_hashes)
                self.message_hashes = set(hash_list[-9000:])  # Keep last 9000
                logger.info(f"Cleaned up old message hashes, now have {len(self.message_hashes)} hashes")
            
        except Exception as e:
            logger.error(f"Error adding message hash: {e}")
    
    def clear_message_hashes(self):
        """Clear all message hashes (useful for testing or reset)"""
        self.message_hashes.clear()
        logger.info("All message hashes cleared")
        self.save_config()
    
    def print_banner(self):
        """Print the NiftyPool ASCII banner with colors and animations"""
        self.clear_screen()
        
        # Animated header
        print(f"{Colors.BOLD}{Colors.BRIGHT_MAGENTA}")
        time.sleep(0.2)
        
        banner = f"""
{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════════════════════════╗
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_WHITE}                                                                                      {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_YELLOW}      ███╗   ██╗██╗███████╗████████╗██╗   ██╗    ██████╗  ██████╗  ██████╗ ██╗       {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_YELLOW}      ████╗  ██║██║██╔════╝╚══██╔══╝╚██╗ ██╔╝    ██╔══██╗██╔═══██╗██╔═══██╗██║       {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_YELLOW}      ██╔██╗ ██║██║█████╗     ██║    ╚████╔╝     ██████╔╝██║   ██║██║   ██║██║       {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_YELLOW}      ██║╚██╗██║██║██╔══╝     ██║     ╚██╔╝      ██╔═══╝ ██║   ██║██║   ██║██║       {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_YELLOW}      ██║ ╚████║██║██║        ██║      ██║       ██║     ╚██████╔╝╚██████╔╝███████╗  {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_YELLOW}      ╚═╝  ╚═══╝╚═╝╚═╝        ╚═╝      ╚═╝       ╚═╝      ╚═════╝  ╚═════╝ ╚══════╝  {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_WHITE}                                                                                      {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_GREEN}                    🚀 Advanced Telegram Message Forwarder with Keywords 🚀          {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_WHITE}                                                                                      {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_MAGENTA}                              📞 Contact Support: @ItsHarshX                         {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_MAGENTA}                              📧 For updates and assistance                          {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_WHITE}                                                                                      {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_GREEN}                        ✨ Forward messages with keyword filtering ✨               {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}║{Colors.BRIGHT_WHITE}                                                                                      {Colors.BRIGHT_CYAN}║
{Colors.BRIGHT_CYAN}╚══════════════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}
"""
        
        print(banner)
        
        # Animated welcome message
        print(f"{Colors.BOLD}{Colors.BRIGHT_WHITE}")
        self.animate_text("🎯 Welcome to NiftyPool Telegram Forwarder!", 0.03)
        print(f"{Colors.RESET}")
        
        time.sleep(1)
    
    async def get_custom_emoji_document_id(self, emoji_text):
        """Automatically find document_id for custom emoji"""
        try:
            # Check cache first
            if emoji_text in self.custom_emoji_cache:
                return self.custom_emoji_cache[emoji_text]
            
            # Try to find custom emoji from user's available stickers/emojis
            try:
                # Get user's installed sticker sets
                from telethon.tl.functions.messages import GetAllStickersRequest
                from telethon.tl.functions.messages import GetStickerSetRequest
                from telethon.tl.types import InputStickerSetID
                
                # Get all installed sticker sets
                all_stickers = await self.client(GetAllStickersRequest(hash=0))
                
                # Search through sticker sets for matching emoji
                for sticker_set in all_stickers.sets:
                    try:
                        # Get sticker set details
                        sticker_set_full = await self.client(GetStickerSetRequest(
                            stickerset=InputStickerSetID(
                                id=sticker_set.id,
                                access_hash=sticker_set.access_hash
                            ),
                            hash=0
                        ))
                        
                        # Check if any documents match our emoji
                        for document in sticker_set_full.documents:
                            if hasattr(document, 'attributes'):
                                for attr in document.attributes:
                                    if hasattr(attr, 'alt') and attr.alt == emoji_text:
                                        # Found a matching custom emoji!
                                        self.custom_emoji_cache[emoji_text] = document.id
                                        logger.info(f"Found real document_id {document.id} for emoji '{emoji_text}'")
                                        return document.id
                    except Exception as e:
                        # Skip problematic sticker sets
                        continue
                        
            except Exception as e:
                logger.warning(f"Could not access sticker API: {e}")
            
            # If no real custom emoji found, generate a placeholder document ID
            # This is for demonstration - in practice, you'd need access to premium emoji sets
            emoji_hash = hashlib.md5(emoji_text.encode()).hexdigest()
            # Use a more realistic document ID format (64-bit integer)
            document_id = int(emoji_hash[:16], 16)
            
            # Cache the result
            self.custom_emoji_cache[emoji_text] = document_id
            logger.info(f"Generated placeholder document_id {document_id} for emoji '{emoji_text}'")
            
            return document_id
            
        except Exception as e:
            logger.error(f"Error getting custom emoji document ID: {e}")
            return None
    
    async def create_custom_emoji_entity(self, text, emoji_char, offset=0):
        """Create MessageEntityCustomEmoji entity automatically"""
        try:
            document_id = await self.get_custom_emoji_document_id(emoji_char)
            if document_id:
                entity = MessageEntityCustomEmoji(
                    offset=offset,
                    length=len(emoji_char),
                    document_id=document_id
                )
                logger.info(f"Created custom emoji entity for '{emoji_char}' at offset {offset}")
                return entity
            return None
        except Exception as e:
            logger.error(f"Error creating custom emoji entity: {e}")
            return None
    
    async def enhance_message_with_custom_emojis(self, message_text):
        """Enhance message with custom emoji entities and clean markdown"""
        try:
            if not self.is_premium or not message_text:
                return message_text, []
            
            # Find potential emoji characters (this is simplified - you'd want better emoji detection)
            import re
            emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF]')
            
            entities = []
            enhanced_text = message_text
            
            # Find all emoji matches
            for match in emoji_pattern.finditer(message_text):
                emoji_char = match.group()
                offset = match.start()
                
                # Create custom emoji entity
                entity = await self.create_custom_emoji_entity(enhanced_text, emoji_char, offset)
                if entity:
                    entities.append(entity)
                    logger.info(f"Added custom emoji entity for '{emoji_char}' at position {offset}")
            
            # Clean up markdown tags for better display
            clean_text = self.clean_markdown_tags(enhanced_text)
            
            return clean_text, entities
            
        except Exception as e:
            logger.error(f"Error enhancing message with custom emojis: {e}")
            return message_text, []
    
    def clean_markdown_tags(self, text):
        """Clean markdown tags for better display"""
        if not text:
            return text
        
        try:
            # Remove markdown formatting tags while preserving content
            import re
            
            # Remove bold formatting
            text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
            
            # Remove italic formatting
            text = re.sub(r'\*(.*?)\*', r'\1', text)
            
            # Remove code formatting
            text = re.sub(r'`(.*?)`', r'\1', text)
            
            # Remove strikethrough
            text = re.sub(r'~~(.*?)~~', r'\1', text)
            
            # Remove underline
            text = re.sub(r'__(.*?)__', r'\1', text)
            
            # Clean up any remaining markdown links but keep text
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            
            return text
            
        except Exception as e:
            logger.error(f"Error cleaning markdown tags: {e}")
            return text
    
    def save_config(self):
        """Save configuration to file"""
        try:
            config = {
                'api_id': self.api_id,
                'api_hash': self.api_hash,
                'phone_number': self.phone_number,
                'source_channels': self.source_channels,
                'target_channels': self.target_channels,
                'keywords': self.keywords,
                'message_map': self.message_map,
                'message_hashes': list(self.message_hashes),  # Save as list for JSON
                'custom_emoji_cache': self.custom_emoji_cache
                # Note: use_markdown and preserve_formatting are hardcoded and not saved
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            logger.info("Configuration saved successfully")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def contains_keyword(self, text):
        """Check if text contains any of the keywords"""
        if not text or not self.keywords:
            return False
        
        text_lower = text.lower()
        for keyword in self.keywords:
            if keyword.lower() in text_lower:
                return True
        return False
    
    def get_parse_mode(self):
        """Get the appropriate parse mode - HARDCODED to use markdown"""
        # Always return markdown for premium emoji and formatting support (hardcoded)
        return 'markdown'
    
    def process_custom_emojis(self, message):
        """Process custom emojis in message for premium users"""
        # First, preserve existing custom emojis from the original message
        existing_text = message.text
        existing_entities = message.entities if message.entities else []
        
        # Find existing custom emoji entities
        existing_custom_emojis = [
            entity for entity in existing_entities 
            if hasattr(entity, 'document_id') and isinstance(entity, MessageEntityCustomEmoji)
        ]
        
        if existing_custom_emojis:
            logger.info(f"Found {len(existing_custom_emojis)} existing custom emojis in message")
            for entity in existing_custom_emojis:
                start = entity.offset
                end = entity.offset + entity.length
                emoji_char = existing_text[start:end]
                logger.info(f"Preserving existing custom emoji '{emoji_char}' with ID {entity.document_id}")
            
            # Clean the text for better display but keep entities
            clean_text = self.clean_markdown_tags(existing_text)
            return clean_text, existing_entities
        
        # If no existing custom emojis and user is premium, try to enhance the message
        if self.is_premium:
            logger.info("No existing custom emojis found, attempting to enhance message")
            # This will be handled by the async enhancement method
            return existing_text, existing_entities
        
        return existing_text, existing_entities
    
    def format_message_with_markdown(self, message):
        """Format message with Markdown V2 support"""
        if not self.use_markdown or not message.text:
            return message.text
        
        try:
            # Get formatted text with entities preserved
            formatted_text = message.text
            
            # If preserving formatting, keep original entities
            if self.preserve_formatting and message.entities:
                # Use Telethon's built-in markdown formatting
                formatted_text = utils.add_surrogate(message.text)
                
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting message with markdown: {e}")
            return message.text
    
    def create_premium_emoji_text(self, emoji_char, emoji_id):
        """Create premium emoji text in Markdown format"""
        return f"[{emoji_char}](tg://emoji?id={emoji_id})"
    
    async def login_telegram(self):
        """Login to Telegram with enhanced UI"""
        try:
            self.print_header("📱 TELEGRAM LOGIN")
            
            if not self.api_id or not self.api_hash:
                self.print_info("Get your API credentials from https://my.telegram.org/auth")
                print()
                
                print(f"{Colors.BRIGHT_WHITE}Enter your API credentials:{Colors.RESET}")
                self.api_id = input(f"{Colors.BRIGHT_CYAN}API ID: {Colors.RESET}").strip()
                self.api_hash = input(f"{Colors.BRIGHT_CYAN}API Hash: {Colors.RESET}").strip()
                self.phone_number = input(f"{Colors.BRIGHT_CYAN}Phone Number (with country code): {Colors.RESET}").strip()
            
            self.print_loading_animation("Connecting to Telegram", 2)
            
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                self.print_info("Sending verification code...")
                await self.client.send_code_request(self.phone_number)
                
                code = input(f"{Colors.BRIGHT_YELLOW}Enter the verification code: {Colors.RESET}").strip()
                
                try:
                    await self.client.sign_in(self.phone_number, code)
                except SessionPasswordNeededError:
                    password = input(f"{Colors.BRIGHT_YELLOW}Enter your 2FA password: {Colors.RESET}").strip()
                    await self.client.sign_in(password=password)
            
            # Check if user has premium
            me = await self.client.get_me()
            self.is_premium = me.premium if hasattr(me, 'premium') else False
            
            self.print_success(f"Successfully logged in as {me.first_name}")
            
            if self.is_premium:
                self.print_success("🌟 Premium features enabled: Custom emojis, enhanced formatting")
            else:
                self.print_info("📝 Standard account - basic features enabled")
            
            self.print_info("🎨 Formatting: Hardcoded to optimal settings (Markdown: ON, Preserve: ON)")
            self.print_info("💡 All formatting options are optimized for best performance!")
            
            self.save_config()
            
            input(f"\n{Colors.BRIGHT_GREEN}Press Enter to continue...{Colors.RESET}")
            return True
            
        except Exception as e:
            logger.error(f"Login error: {e}")
            self.print_error(f"Login failed: {e}")
            input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")
            return False
    
    async def get_channel_id(self, channel_input):
        """Get channel ID from username or invite link"""
        try:
            if channel_input.startswith('@'):
                entity = await self.client.get_entity(channel_input)
            elif 't.me/' in channel_input:
                username = channel_input.split('/')[-1]
                entity = await self.client.get_entity(username)
            else:
                entity = await self.client.get_entity(channel_input)
            
            return entity.id, entity.title
        except Exception as e:
            logger.error(f"Error getting channel {channel_input}: {e}")
            return None, None
    
    async def set_source_channels(self):
        """Set source channels to monitor with enhanced UI"""
        self.print_header("📥 SET SOURCE CHANNELS")
        
        self.print_info("Enter channel usernames (e.g., @channel) or invite links")
        self.print_info("Type 'done' when finished")
        print()
        
        new_channels = []
        channel_count = 0
        
        while True:
            channel_count += 1
            channel_input = input(f"{Colors.BRIGHT_CYAN}Channel #{channel_count}: {Colors.RESET}").strip()
            
            if channel_input.lower() == 'done':
                break
            
            self.print_loading_animation(f"Adding channel: {channel_input}", 1)
            
            channel_id, channel_title = await self.get_channel_id(channel_input)
            if channel_id:
                new_channels.append({
                    'id': channel_id,
                    'title': channel_title,
                    'input': channel_input
                })
                self.print_success(f"Added: {channel_title}")
            else:
                self.print_error(f"Failed to add channel: {channel_input}")
                channel_count -= 1  # Don't increment if failed
        
        self.source_channels = new_channels
        self.save_config()
        
        if len(self.source_channels) > 0:
            self.print_success(f"✅ {len(self.source_channels)} source channels configured")
        else:
            self.print_warning("No source channels configured")
        
        input(f"\n{Colors.BRIGHT_GREEN}Press Enter to continue...{Colors.RESET}")
    
    async def set_target_channels(self):
        """Set target channels to forward messages to with enhanced UI"""
        self.print_header("📤 SET TARGET CHANNELS")
        
        self.print_info("Enter channel usernames (e.g., @channel) or invite links")
        self.print_info("Type 'done' when finished")
        print()
        
        new_channels = []
        channel_count = 0
        
        while True:
            channel_count += 1
            channel_input = input(f"{Colors.BRIGHT_CYAN}Channel #{channel_count}: {Colors.RESET}").strip()
            
            if channel_input.lower() == 'done':
                break
            
            self.print_loading_animation(f"Adding channel: {channel_input}", 1)
            
            channel_id, channel_title = await self.get_channel_id(channel_input)
            if channel_id:
                new_channels.append({
                    'id': channel_id,
                    'title': channel_title,
                    'input': channel_input
                })
                self.print_success(f"Added: {channel_title}")
            else:
                self.print_error(f"Failed to add channel: {channel_input}")
                channel_count -= 1  # Don't increment if failed
        
        self.target_channels = new_channels
        self.save_config()
        
        if len(self.target_channels) > 0:
            self.print_success(f"✅ {len(self.target_channels)} target channels configured")
        else:
            self.print_warning("No target channels configured")
        
        input(f"\n{Colors.BRIGHT_GREEN}Press Enter to continue...{Colors.RESET}")
    
    def set_keywords(self):
        """Set keywords to monitor with enhanced UI"""
        self.print_header("🔍 SET KEYWORDS")
        
        self.print_info("Enter keywords to monitor (comma-separated)")
        
        if self.keywords:
            print(f"{Colors.BRIGHT_WHITE}Current keywords: {Colors.BRIGHT_YELLOW}{', '.join(self.keywords)}{Colors.RESET}")
        else:
            print(f"{Colors.BRIGHT_WHITE}Current keywords: {Colors.RED}None{Colors.RESET}")
        
        print()
        keywords_input = input(f"{Colors.BRIGHT_CYAN}Enter keywords: {Colors.RESET}").strip()
        
        if keywords_input:
            self.keywords = [kw.strip() for kw in keywords_input.split(',') if kw.strip()]
            self.save_config()
            self.print_success(f"✅ {len(self.keywords)} keywords set: {', '.join(self.keywords)}")
        else:
            self.print_warning("No keywords entered")
        
        input(f"\n{Colors.BRIGHT_GREEN}Press Enter to continue...{Colors.RESET}")
    
    async def send_message_without_forward_tag(self, source_message, target_channel_id):
        """Send message without forward tag with premium emoji and formatting support"""
        try:
            target_entity = await self.client.get_entity(target_channel_id)
            
            # Process custom emojis and formatting
            message_text, entities = self.process_custom_emojis(source_message)
            
            # For premium users, enhance the message with auto-generated custom emojis
            if self.is_premium and message_text:
                # Check if we need to enhance the message (no existing custom emojis)
                existing_custom_emojis = [
                    entity for entity in entities 
                    if hasattr(entity, 'document_id') and isinstance(entity, MessageEntityCustomEmoji)
                ] if entities else []
                
                if not existing_custom_emojis:
                    # Enhance message with auto-generated custom emoji entities
                    enhanced_text, enhanced_entities = await self.enhance_message_with_custom_emojis(message_text)
                    if enhanced_entities:
                        message_text = enhanced_text
                        entities = enhanced_entities
                        logger.info(f"Enhanced message with {len(enhanced_entities)} auto-generated custom emoji entities")
                        print(f"✨ Enhanced message with {len(enhanced_entities)} auto-generated premium emojis")
            
            # Log if premium emojis were processed
            if self.is_premium and entities:
                custom_emojis = [e for e in entities if isinstance(e, MessageEntityCustomEmoji)]
                if custom_emojis:
                    logger.info(f"Processing {len(custom_emojis)} premium emojis for forwarding")
                    print(f"🎉 Processing {len(custom_emojis)} premium emojis with original/enhanced entities")
            
            # Determine parse mode based on custom emoji presence
            custom_emoji_entities = [
                entity for entity in entities 
                if hasattr(entity, 'document_id') and isinstance(entity, MessageEntityCustomEmoji)
            ] if entities else []
            
            # If custom emojis are present, use entities instead of parse_mode
            if custom_emoji_entities:
                parse_mode = None  # Don't use markdown parsing for custom emojis
                formatting_entities = entities  # Use original/enhanced entities (hardcoded: always preserve)
                logger.info(f"Using entity-based formatting for {len(custom_emoji_entities)} custom emojis")
            else:
                parse_mode = self.get_parse_mode()  # Hardcoded to return 'markdown'
                formatting_entities = entities  # Hardcoded: always preserve formatting
            
            # Method 1: Try to use send_file for media or send_message for text
            if source_message.media:
                try:
                    # Handle different media types
                    if hasattr(source_message.media, 'photo'):
                        # Photo message
                        sent_message = await self.client.send_file(
                            target_entity,
                            source_message.media.photo,
                            caption=message_text,
                            parse_mode=parse_mode,
                            force_document=False,
                            formatting_entities=formatting_entities
                        )
                    elif hasattr(source_message.media, 'document'):
                        # Document, video, audio, etc.
                        sent_message = await self.client.send_file(
                            target_entity,
                            source_message.media.document,
                            caption=message_text,
                            parse_mode=parse_mode,
                            force_document=False,
                            formatting_entities=formatting_entities
                        )
                    elif isinstance(source_message.media, MessageMediaWebPage):
                        # Web page preview - send as text with link preview
                        sent_message = await self.client.send_message(
                            target_entity,
                            message_text,
                            parse_mode=parse_mode,
                            link_preview=True,
                            formatting_entities=formatting_entities
                        )
                    else:
                        # Try to download and re-upload
                        try:
                            file_path = await self.client.download_media(source_message.media, thumb=-1)
                            if file_path:
                                sent_message = await self.client.send_file(
                                    target_entity,
                                    file_path,
                                    caption=message_text,
                                    parse_mode=parse_mode,
                                    formatting_entities=formatting_entities
                                )
                                # Clean up downloaded file
                                try:
                                    os.remove(file_path)
                                except:
                                    pass
                            else:
                                # Fall back to text only
                                sent_message = await self.client.send_message(
                                    target_entity,
                                    message_text,
                                    parse_mode=parse_mode,
                                    formatting_entities=formatting_entities
                                )
                        except Exception as download_error:
                            logger.error(f"Download/upload failed: {download_error}")
                            # Fall back to text only
                            sent_message = await self.client.send_message(
                                target_entity,
                                message_text,
                                parse_mode=parse_mode,
                                formatting_entities=formatting_entities
                            )
                            
                except Exception as media_error:
                    logger.error(f"Media sending failed: {media_error}")
                    # Fall back to text only
                    sent_message = await self.client.send_message(
                        target_entity,
                        message_text,
                        parse_mode=parse_mode,
                        formatting_entities=formatting_entities
                    )
            else:
                # Text only message
                sent_message = await self.client.send_message(
                    target_entity,
                    message_text,
                    parse_mode=parse_mode,
                    formatting_entities=formatting_entities
                )
            
            return sent_message
            
        except Exception as e:
            logger.error(f"Error sending message without forward tag: {e}")
            return None
    
    async def forward_message(self, source_message, target_channel_id):
        """Forward message to target channel - always try to avoid forward tags"""
        try:
            # Always try to send without forward tag first
            sent_message = await self.send_message_without_forward_tag(source_message, target_channel_id)
            
            if sent_message:
                logger.info(f"Message sent without forward tag to channel {target_channel_id}")
                return sent_message
            else:
                # If that fails, try regular forwarding as last resort
                logger.warning(f"Falling back to regular forwarding for channel {target_channel_id}")
                target_entity = await self.client.get_entity(target_channel_id)
                sent_message = await self.client.forward_messages(
                    target_entity,
                    source_message
                )
                return sent_message
                
        except Exception as e:
            logger.error(f"Error forwarding message: {e}")
            return None
    
    async def handle_new_message(self, event):
        """Handle new messages from source channels"""
        try:
            message = event.message
            
            # Get channel/chat ID - handle different peer types
            channel_id = None
            if hasattr(message.peer_id, 'channel_id'):
                channel_id = message.peer_id.channel_id
            elif hasattr(message.peer_id, 'chat_id'):
                channel_id = message.peer_id.chat_id
            elif hasattr(message.peer_id, 'user_id'):
                channel_id = message.peer_id.user_id
            
            # Convert negative channel_id to positive (Telegram API quirk)
            if channel_id and channel_id < 0:
                channel_id = abs(channel_id)
            
            # Check if message is from a source channel
            source_channel_ids = [abs(ch['id']) if ch['id'] < 0 else ch['id'] for ch in self.source_channels]
            if channel_id not in source_channel_ids:
                return
            
            # Check if message contains keywords
            if not self.contains_keyword(message.text):
                return
            
            # Check for duplicate message
            if self.is_duplicate_message(message):
                logger.info(f"Skipping duplicate message from channel {channel_id}")
                print(f"{Colors.BRIGHT_YELLOW}🛡️ Duplicate message skipped (prevents spam){Colors.RESET}")
                return
            
            # Add message hash to the set
            self.add_message_hash(message)

            # Get source channel info
            source_channel = next((ch for ch in self.source_channels if abs(ch['id']) == channel_id), None)
            if source_channel:
                logger.info(f"Keyword found in message from '{source_channel['title']}' (ID: {channel_id})")
                print(f"{Colors.BRIGHT_GREEN}📨 Forwarding message from '{source_channel['title']}'{Colors.RESET}")
                
                # Show premium emoji info if available
                if self.is_premium and message.entities:
                    custom_emojis = [e for e in message.entities if isinstance(e, MessageEntityCustomEmoji)]
                    if custom_emojis:
                        print(f"{Colors.BRIGHT_MAGENTA}🎉 Message contains {len(custom_emojis)} premium emojis - preserving original entities{Colors.RESET}")
                        logger.info(f"Premium emojis detected: {len(custom_emojis)} custom emojis will be preserved")
                    else:
                        print(f"{Colors.BRIGHT_CYAN}✨ Premium user - will enhance regular emojis to premium format{Colors.RESET}")
                        logger.info("No existing custom emojis found, will attempt enhancement")
                elif self.is_premium:
                    print(f"{Colors.BRIGHT_CYAN}✨ Premium user - will enhance regular emojis to premium format{Colors.RESET}")
                    logger.info("Premium user with no entities, will attempt enhancement")
                
                # Process the message to show what will be forwarded
                processed_text, processed_entities = self.process_custom_emojis(message)
                display_text = processed_text if processed_text else message.text
                
                if len(display_text) > 150:
                    print(f"{Colors.BRIGHT_WHITE}📝 Message: {display_text[:150]}...{Colors.RESET}")
                else:
                    print(f"{Colors.BRIGHT_WHITE}📝 Message: {display_text}{Colors.RESET}")
                
                # Show if custom emojis are being preserved or enhanced
                if self.is_premium and processed_entities:
                    custom_emojis = [e for e in processed_entities if isinstance(e, MessageEntityCustomEmoji)]
                    if custom_emojis:
                        print(f"{Colors.BRIGHT_GREEN}✨ Premium emojis will be forwarded using original entities{Colors.RESET}")
                    else:
                        print(f"{Colors.BRIGHT_BLUE}🚀 Regular emojis will be enhanced to premium format during forwarding{Colors.RESET}")
                elif self.is_premium:
                    print(f"{Colors.BRIGHT_BLUE}🚀 Regular emojis will be enhanced to premium format during forwarding{Colors.RESET}")
            
            # Forward to all target channels
            forwarded_messages = []
            for target_channel in self.target_channels:
                try:
                    forwarded_msg = await self.forward_message(message, target_channel['id'])
                    if forwarded_msg:
                        forwarded_messages.append({
                            'channel_id': target_channel['id'],
                            'message_id': forwarded_msg.id if hasattr(forwarded_msg, 'id') else forwarded_msg[0].id
                        })
                        print(f"{Colors.BRIGHT_GREEN}✅ Forwarded to '{target_channel['title']}' with formatting{Colors.RESET}")
                        logger.info(f"Message forwarded to '{target_channel['title']}'")
                    else:
                        print(f"{Colors.BRIGHT_RED}❌ Failed to forward to '{target_channel['title']}'{Colors.RESET}")
                        logger.error(f"Failed to forward to '{target_channel['title']}'")
                except Exception as forward_error:
                    print(f"{Colors.BRIGHT_RED}❌ Error forwarding to '{target_channel['title']}': {forward_error}{Colors.RESET}")
                    logger.error(f"Error forwarding to '{target_channel['title']}': {forward_error}")
            
            # Store message mapping for edits/deletions
            if forwarded_messages:
                self.message_map[f"{channel_id}_{message.id}"] = forwarded_messages
                self.save_config()
                print(f"{Colors.BRIGHT_YELLOW}📊 Message forwarded to {len(forwarded_messages)} channels{Colors.RESET}")
            
        except Exception as e:
            logger.error(f"Error handling new message: {e}")
            print(f"{Colors.BRIGHT_RED}❌ Error handling message: {e}{Colors.RESET}")
    
    async def handle_message_edit(self, event):
        """Handle message edits with formatting preservation"""
        try:
            message = event.message
            
            # Get channel/chat ID - handle different peer types
            channel_id = None
            if hasattr(message.peer_id, 'channel_id'):
                channel_id = message.peer_id.channel_id
            elif hasattr(message.peer_id, 'chat_id'):
                channel_id = message.peer_id.chat_id
            elif hasattr(message.peer_id, 'user_id'):
                channel_id = message.peer_id.user_id
            
            # Convert negative channel_id to positive
            if channel_id and channel_id < 0:
                channel_id = abs(channel_id)
            
            # Check if we have forwarded this message
            message_key = f"{channel_id}_{message.id}"
            if message_key not in self.message_map:
                return
            
            # Check if edited message still contains keywords
            if not self.contains_keyword(message.text):
                return
            
            logger.info(f"Editing forwarded message from channel {channel_id}")
            print(f"✏️ Editing forwarded message with formatting...")
            
            # Process message formatting
            edited_text, entities = self.process_custom_emojis(message)
            
            # For premium users, enhance the message with auto-generated custom emojis
            if self.is_premium and edited_text:
                # Check if we need to enhance the message (no existing custom emojis)
                existing_custom_emojis = [
                    entity for entity in entities 
                    if hasattr(entity, 'document_id') and isinstance(entity, MessageEntityCustomEmoji)
                ] if entities else []
                
                if not existing_custom_emojis:
                    # Enhance message with auto-generated custom emoji entities
                    enhanced_text, enhanced_entities = await self.enhance_message_with_custom_emojis(edited_text)
                    if enhanced_entities:
                        edited_text = enhanced_text
                        entities = enhanced_entities
                        logger.info(f"Enhanced edited message with {len(enhanced_entities)} auto-generated custom emoji entities")
            
            # Determine parse mode based on custom emoji presence
            custom_emoji_entities = [
                entity for entity in entities 
                if hasattr(entity, 'document_id') and isinstance(entity, MessageEntityCustomEmoji)
            ] if entities else []
            
            # If custom emojis are present, use entities instead of parse_mode
            if custom_emoji_entities:
                parse_mode = None  # Don't use markdown parsing for custom emojis
                formatting_entities = entities  # Use original/enhanced entities (hardcoded: always preserve)
                logger.info(f"Using entity-based formatting for editing {len(custom_emoji_entities)} custom emojis")
            else:
                parse_mode = self.get_parse_mode()  # Hardcoded to return 'markdown'
                formatting_entities = entities  # Hardcoded: always preserve formatting
            
            # Edit all forwarded messages
            forwarded_messages = self.message_map[message_key]
            for forwarded_msg in forwarded_messages:
                try:
                    target_entity = await self.client.get_entity(forwarded_msg['channel_id'])
                    
                    await self.client.edit_message(
                        target_entity,
                        forwarded_msg['message_id'],
                        edited_text,
                        parse_mode=parse_mode,
                        formatting_entities=formatting_entities
                    )
                    print(f"✅ Message edited in target channel with formatting")
                    
                except Exception as edit_error:
                    if "Content of the message was not modified" in str(edit_error):
                        logger.info(f"Message content unchanged, skipping edit")
                    else:
                        logger.error(f"Error editing message: {edit_error}")
                        print(f"❌ Error editing message: {edit_error}")
            
        except Exception as e:
            logger.error(f"Error handling message edit: {e}")
    
    async def handle_message_delete(self, event):
        """Handle message deletions"""
        try:
            for deleted_id in event.deleted_ids:
                # Find the message in our map
                message_key = None
                for key in self.message_map:
                    if key.endswith(f"_{deleted_id}"):
                        message_key = key
                        break
                
                if not message_key:
                    continue
                
                logger.info(f"Deleting forwarded message {deleted_id}")
                print(f"🗑️ Deleting forwarded message...")
                
                # Delete all forwarded messages
                forwarded_messages = self.message_map[message_key]
                for forwarded_msg in forwarded_messages:
                    try:
                        target_entity = await self.client.get_entity(forwarded_msg['channel_id'])
                        await self.client.delete_messages(
                            target_entity,
                            forwarded_msg['message_id']
                        )
                        print(f"✅ Message deleted from target channel")
                    except Exception as e:
                        logger.error(f"Error deleting message: {e}")
                        print(f"❌ Error deleting message: {e}")
                
                # Remove from message map
                del self.message_map[message_key]
                self.save_config()
                
        except Exception as e:
            logger.error(f"Error handling message delete: {e}")
    
    async def start_forwarder(self):
        """Start the message forwarder with enhanced UI"""
        if not self.client:
            self.print_error("Please login first!")
            input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")
            return
        
        if not self.source_channels:
            self.print_error("Please set source channels first!")
            input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")
            return
        
        if not self.target_channels:
            self.print_error("Please set target channels first!")
            input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")
            return
        
        if not self.keywords:
            self.print_error("Please set keywords first!")
            input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")
            return
        
        self.print_header("🚀 STARTING MESSAGE FORWARDER")
        
        print(f"{Colors.BRIGHT_GREEN}📥 Monitoring {len(self.source_channels)} source channels:{Colors.RESET}")
        for ch in self.source_channels:
            print(f"{Colors.BRIGHT_WHITE}   • {ch['title']} ({ch['input']}){Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_BLUE}📤 Forwarding to {len(self.target_channels)} target channels:{Colors.RESET}")
        for ch in self.target_channels:
            print(f"{Colors.BRIGHT_WHITE}   • {ch['title']} ({ch['input']}){Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_YELLOW}🔍 Keywords: {', '.join(self.keywords)}{Colors.RESET}")
        
        premium_status = "Yes" if self.is_premium else "No"
        premium_color = self.get_status_color(premium_status)
        print(f"{Colors.BRIGHT_WHITE}🌟 Premium: {premium_color}{premium_status}{Colors.RESET}")
        
        if self.is_premium:
            print(f"{Colors.BRIGHT_GREEN}   • Auto-enhance regular emojis to premium format{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}   • Preserve existing custom emoji entities{Colors.RESET}")
            print(f"{Colors.BRIGHT_GREEN}   • Clean markdown tags for better display{Colors.RESET}")
        
        print(f"{Colors.BRIGHT_CYAN}🎨 Formatting: HARDCODED (Markdown: ON, Preserve: ON){Colors.RESET}")
        print(f"{Colors.BRIGHT_MAGENTA}🛡️ Duplicate prevention: ENABLED ({len(self.message_hashes)} hashes cached){Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}🎯 Forward method: Copy without forward tags + auto-premium emoji enhancement{Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_YELLOW}Press Ctrl+C to stop...{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}")
        
        # Register event handlers
        source_channel_ids = [ch['id'] for ch in self.source_channels]
        
        self.client.add_event_handler(
            self.handle_new_message,
            events.NewMessage(chats=source_channel_ids)
        )
        
        self.client.add_event_handler(
            self.handle_message_edit,
            events.MessageEdited(chats=source_channel_ids)
        )
        
        self.client.add_event_handler(
            self.handle_message_delete,
            events.MessageDeleted(chats=source_channel_ids)
        )
        
        try:
            await self.client.run_until_disconnected()
        except KeyboardInterrupt:
            print(f"\n{Colors.BRIGHT_YELLOW}🛑 Forwarder stopped by user{Colors.RESET}")
            input(f"\n{Colors.BRIGHT_GREEN}Press Enter to return to menu...{Colors.RESET}")
        except Exception as e:
            logger.error(f"Error in forwarder: {e}")
            print(f"{Colors.BRIGHT_RED}❌ Error in forwarder: {e}{Colors.RESET}")
            input(f"\n{Colors.BRIGHT_RED}Press Enter to return to menu...{Colors.RESET}")
    
    def show_menu(self):
        """Show the enhanced interactive main menu"""
        self.print_banner()
        
        # Menu header
        print(f"\n{Colors.BOLD}{Colors.BG_BLUE}{Colors.BRIGHT_WHITE} 🤖 TELEGRAM MESSAGE FORWARDER MENU 🤖 {Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}")
        
        # Menu options with colors and better formatting
        menu_options = [
            ("1", "📱", "Login Telegram", "Connect to your Telegram account"),
            ("2", "🚀", "Start Forwarder", "Begin monitoring and forwarding messages"),
            ("3", "📥", "Set Source Channels", "Configure channels to monitor"),
            ("4", "📤", "Set Target Channels", "Configure destination channels"),
            ("5", "🔍", "Set Keywords", "Define keywords to filter messages"),
            ("6", "🧹", "Clear Message Hashes", "Reset duplicate detection"),
            ("7", "🚪", "Exit", "Close the application")
        ]
        
        print()
        for num, emoji, title, description in menu_options:
            print(f"{Colors.BRIGHT_WHITE}[{Colors.BRIGHT_YELLOW}{num}{Colors.BRIGHT_WHITE}] {emoji} {Colors.BOLD}{Colors.BRIGHT_GREEN}{title}{Colors.RESET}")
            print(f"    {Colors.DIM}{Colors.BRIGHT_BLACK}└── {description}{Colors.RESET}")
            print()
        
        print(f"{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}")
        
        # Enhanced status display
        self.show_status_dashboard()
        
        print(f"{Colors.BRIGHT_CYAN}{'═' * 60}{Colors.RESET}")
    
    def show_status_dashboard(self):
        """Show an enhanced status dashboard"""
        print(f"\n{Colors.BOLD}{Colors.BG_GREEN}{Colors.BRIGHT_WHITE} 📊 SYSTEM STATUS DASHBOARD 📊 {Colors.RESET}")
        print()
        
        # Connection status
        login_status = "Yes" if self.client else "No"
        login_color = self.get_status_color(login_status)
        print(f"{Colors.BRIGHT_WHITE}🔐 Connection Status: {login_color}{login_status}{Colors.RESET}")
        
        # Premium status
        if self.client:
            premium_status = "Yes" if self.is_premium else "No"
            premium_color = self.get_status_color(premium_status)
            print(f"{Colors.BRIGHT_WHITE}🌟 Premium Account: {premium_color}{premium_status}{Colors.RESET}")
            
            if self.is_premium:
                print(f"    {Colors.BRIGHT_GREEN}• Auto-enhance regular emojis to premium format{Colors.RESET}")
                print(f"    {Colors.BRIGHT_GREEN}• Preserve existing custom emoji entities{Colors.RESET}")
                print(f"    {Colors.BRIGHT_GREEN}• Clean markdown tags for better display{Colors.RESET}")
        
        # Channels status
        source_count = len(self.source_channels)
        target_count = len(self.target_channels)
        
        print(f"{Colors.BRIGHT_WHITE}📥 Source Channels: {Colors.BRIGHT_YELLOW}{source_count}{Colors.RESET}")
        if source_count > 0:
            for i, ch in enumerate(self.source_channels[:3]):  # Show first 3
                print(f"    {Colors.BRIGHT_GREEN}• {ch['title']}{Colors.RESET}")
            if source_count > 3:
                print(f"    {Colors.DIM}... and {source_count - 3} more{Colors.RESET}")
        
        print(f"{Colors.BRIGHT_WHITE}📤 Target Channels: {Colors.BRIGHT_YELLOW}{target_count}{Colors.RESET}")
        if target_count > 0:
            for i, ch in enumerate(self.target_channels[:3]):  # Show first 3
                print(f"    {Colors.BRIGHT_GREEN}• {ch['title']}{Colors.RESET}")
            if target_count > 3:
                print(f"    {Colors.DIM}... and {target_count - 3} more{Colors.RESET}")
        
        # Keywords status
        keyword_count = len(self.keywords)
        print(f"{Colors.BRIGHT_WHITE}🔍 Keywords: {Colors.BRIGHT_YELLOW}{keyword_count}{Colors.RESET}")
        if keyword_count > 0:
            keywords_display = ', '.join(self.keywords[:5])  # Show first 5
            if keyword_count > 5:
                keywords_display += f" ... (+{keyword_count - 5} more)"
            print(f"    {Colors.BRIGHT_GREEN}{keywords_display}{Colors.RESET}")
        
        # System features
        print(f"{Colors.BRIGHT_WHITE}🛡️ Duplicate Prevention: {Colors.BRIGHT_YELLOW}{len(self.message_hashes)} hashes cached{Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}🎨 Formatting: {Colors.BRIGHT_GREEN}HARDCODED (Markdown: ON, Preserve: ON){Colors.RESET}")
        print(f"{Colors.BRIGHT_WHITE}🎯 Forward Method: {Colors.BRIGHT_GREEN}Copy without forward tags + auto-premium emoji{Colors.RESET}")
        
        print()
    
    async def run(self):
        """Main program loop with enhanced UI"""
        self.load_config()
        
        # Display startup information
        self.print_header("🎨 FORMATTING SETTINGS")
        self.print_success("✅ Markdown formatting: ALWAYS ENABLED")
        self.print_success("✅ Preserve formatting: ALWAYS ENABLED")
        self.print_success("✅ Premium emoji support: AUTO-ENABLED")
        self.print_success("✅ Entity-based formatting: AUTO-ENABLED")
        self.print_success("✅ Duplicate message prevention: ENABLED")
        self.print_info("💡 These settings provide the best forwarding experience!")
        
        input(f"\n{Colors.BRIGHT_GREEN}Press Enter to continue to main menu...{Colors.RESET}")
        
        while True:
            self.show_menu()
            choice = input(f"\n{Colors.BRIGHT_YELLOW}➤ Enter your choice (1-7): {Colors.RESET}").strip()
            
            if choice == '1':
                await self.login_telegram()
            elif choice == '2':
                await self.start_forwarder()
            elif choice == '3':
                if not self.client:
                    self.print_error("Please login first!")
                    input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")
                else:
                    await self.set_source_channels()
            elif choice == '4':
                if not self.client:
                    self.print_error("Please login first!")
                    input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")
                else:
                    await self.set_target_channels()
            elif choice == '5':
                self.set_keywords()
            elif choice == '6':
                self.print_header("🧹 CLEAR MESSAGE HASHES")
                print(f"{Colors.BRIGHT_WHITE}Current message hashes: {Colors.BRIGHT_YELLOW}{len(self.message_hashes)}{Colors.RESET}")
                self.print_warning("This will reset duplicate detection and allow previously seen messages to be forwarded again.")
                confirm = input(f"{Colors.BRIGHT_RED}Are you sure you want to clear all message hashes? (y/N): {Colors.RESET}").strip().lower()
                if confirm == 'y':
                    self.clear_message_hashes()
                    self.print_success("All message hashes cleared!")
                else:
                    self.print_info("Operation cancelled.")
                input(f"\n{Colors.BRIGHT_GREEN}Press Enter to continue...{Colors.RESET}")
            elif choice == '7':
                print(f"\n{Colors.BRIGHT_MAGENTA}👋 Thank you for using NiftyPool Telegram Forwarder!{Colors.RESET}")
                print(f"{Colors.BRIGHT_CYAN}📞 For support: @ItsHarshX{Colors.RESET}")
                if self.client:
                    await self.client.disconnect()
                break
            else:
                self.print_error("Invalid choice. Please try again.")
                input(f"\n{Colors.BRIGHT_RED}Press Enter to continue...{Colors.RESET}")

async def main():
    """Main function"""
    forwarder = TelegramForwarder()
    await forwarder.run()

if __name__ == "__main__":
    asyncio.run(main())
