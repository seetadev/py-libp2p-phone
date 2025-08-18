#!/usr/bin/env python3
"""
Mobile P2P CLI using pure asyncio implementation
This bypasses all trio compatibility issues
"""

import asyncio
import argparse
import sys
from pathlib import Path
import logging
from typing import Optional

# Add the parent directory to the path so we can import mobile
sys.path.insert(0, str(Path(__file__).parent.parent))

from mobile.asyncio_host import AsyncioMobileHost

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


class MobileCLI:
    """Command-line interface for mobile P2P functionality"""
    
    def __init__(self, host: str, port: int):
        self.host_addr = host
        self.port = port
        self.mobile_host = AsyncioMobileHost(host, port)
        self.running = False
        
    async def start(self):
        """Start the mobile P2P host"""
        print("🌟 Mobile P2P CLI (Asyncio Version)")
        print("=" * 40)
        print("Demonstrating the three core deliverables:")
        print("1. 🔗 P2P Connectivity")
        print("2. 💬 Chat Messaging") 
        print("3. 📁 File Transfer")
        print()
        
        try:
            async with self.mobile_host.run():
                self.running = True
                print("🚀 Mobile P2P Host is running!")
                print(f"📍 Your address: /ip4/{self.host_addr}/tcp/{self.port}")
                print()
                print("Available commands:")
                print("  connect <address>  - Connect to a peer (e.g., /ip4/127.0.0.1/tcp/9002)")
                print("  chat <message>     - Send a chat message to all peers")
                print("  file <path>        - Send a file to all peers")
                print("  peers              - List connected peers")
                print("  messages           - Show received chat messages")
                print("  files              - Show received files")
                print("  help               - Show this help")
                print("  quit               - Exit the application")
                print()
                
                # Start command loop
                await self.command_loop()
                
        except Exception as e:
            print(f"❌ Error: {e}")
            logger.exception("Error in mobile P2P host")
    
    async def command_loop(self):
        """Main command processing loop"""
        while self.running:
            try:
                # Simple input - in a real mobile app this would be replaced by UI
                print("📱 >", end=" ", flush=True)
                
                # Use asyncio to read input without blocking
                loop = asyncio.get_event_loop()
                command = await loop.run_in_executor(None, input)
                
                await self.process_command(command.strip())
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Error processing command: {e}")
    
    async def process_command(self, command: str):
        """Process a user command"""
        if not command:
            return
            
        parts = command.split(' ', 1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "connect":
            await self.cmd_connect(args)
        elif cmd == "chat":
            await self.cmd_chat(args)
        elif cmd == "file":
            await self.cmd_file(args)
        elif cmd == "peers":
            await self.cmd_peers()
        elif cmd == "messages":
            await self.cmd_messages()
        elif cmd == "files":
            await self.cmd_files()
        elif cmd == "help":
            await self.cmd_help()
        elif cmd in ["quit", "exit", "q"]:
            self.running = False
        else:
            print(f"❓ Unknown command: {cmd}. Type 'help' for available commands.")
    
    async def cmd_connect(self, address: str):
        """Connect to a peer"""
        if not address:
            print("❌ Please provide a peer address (e.g., /ip4/127.0.0.1/tcp/9002)")
            return
            
        print(f"🔗 Connecting to peer: {address}")
        success = await self.mobile_host.connect_to_peer(address)
        
        if success:
            print("✅ Connected successfully!")
        else:
            print("❌ Failed to connect")
    
    async def cmd_chat(self, message: str):
        """Send a chat message"""
        if not message:
            print("❌ Please provide a message to send")
            return
            
        peers = self.mobile_host.get_connected_peers()
        if not peers:
            print("❌ No connected peers. Connect to a peer first.")
            return
            
        print(f"💬 Sending message: {message}")
        success = await self.mobile_host.send_chat_message(message)
        
        if success:
            print("✅ Message sent!")
        else:
            print("❌ Failed to send message")
    
    async def cmd_file(self, file_path: str):
        """Send a file"""
        if not file_path:
            print("❌ Please provide a file path")
            return
            
        peers = self.mobile_host.get_connected_peers()
        if not peers:
            print("❌ No connected peers. Connect to a peer first.")
            return
            
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return
            
        print(f"📁 Sending file: {file_path}")
        success = await self.mobile_host.send_file(file_path)
        
        if success:
            print("✅ File sent!")
        else:
            print("❌ Failed to send file")
    
    async def cmd_peers(self):
        """List connected peers"""
        peers = self.mobile_host.get_connected_peers()
        
        if peers:
            print(f"🔗 Connected peers ({len(peers)}):")
            for peer in peers:
                print(f"  • {peer}")
        else:
            print("📭 No connected peers")
    
    async def cmd_messages(self):
        """Show received chat messages"""
        messages = self.mobile_host.get_chat_messages()
        
        if messages:
            print(f"💬 Chat messages ({len(messages)}):")
            for msg in messages[-10:]:  # Show last 10 messages
                from_peer = msg['from'][:8] + "..." if len(msg['from']) > 8 else msg['from']
                print(f"  [{from_peer}] {msg['message']}")
        else:
            print("📭 No chat messages")
    
    async def cmd_files(self):
        """Show received files"""
        files = self.mobile_host.get_file_transfers()
        
        if files:
            print(f"📁 Received files ({len(files)}):")
            for transfer_id, file_info in files.items():
                from_peer = file_info['from'][:8] + "..." if len(file_info['from']) > 8 else file_info['from']
                print(f"  [{from_peer}] {file_info['filename']} ({file_info['size']} bytes)")
        else:
            print("📭 No received files")
    
    async def cmd_help(self):
        """Show help"""
        print("📚 Available commands:")
        print("  connect <address>  - Connect to a peer (e.g., /ip4/127.0.0.1/tcp/9002)")
        print("  chat <message>     - Send a chat message to all peers")
        print("  file <path>        - Send a file to all peers")
        print("  peers              - List connected peers")
        print("  messages           - Show received chat messages")
        print("  files              - Show received files")
        print("  help               - Show this help")
        print("  quit               - Exit the application")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Mobile P2P CLI")
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host address to bind to (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Port to bind to (default: 9000)"
    )
    
    args = parser.parse_args()
    
    cli = MobileCLI(args.host, args.port)
    await cli.start()


if __name__ == "__main__":
    asyncio.run(main())
