"""
Simplified Mobile P2P App - Desktop Testing Version

This version works without Kivy dependencies for desktop testing.
It demonstrates the mobile P2P functionality using a simple console interface.
"""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional, List
import threading
import time

# Add path for imports
sys.path.insert(0, str(Path(__file__).parent))

from p2p_host import RealMobileHost
from mobile_abc import P2PPeer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleMobileApp:
    """Simplified mobile app for desktop testing."""
    
    def __init__(self, port: int = 0):
        self.host: Optional[RealMobileHost] = None
        self.port = port
        self.running = True
        self.discovered_peers: List[P2PPeer] = []
        
    async def start(self):
        """Start the mobile app."""
        try:
            print(f"🚀 Starting Simple Mobile P2P App on port {self.port}")
            print("=" * 60)
            
            # Create and start host
            self.host = RealMobileHost(self.port)
            
            # Set up message handlers
            self.host.set_message_handler('chat', self._on_chat_message)
            self.host.set_message_handler('file', self._on_file_received)
            self.host.set_peer_discovery_handler(self._on_peer_discovered)
            
            # Start the host
            await self.host.start()
            
            print(f"📱 Mobile host started:")
            print(f"   Peer ID: {self.host.get_peer_id()}")
            print(f"   Addresses: {self.host.get_listen_addresses()}")
            print(f"   Port: {self.host.port}")
            print()
            
            # Start user interface
            await self._start_ui()
            
        except Exception as e:
            print(f"❌ Failed to start mobile app: {e}")
            logger.exception("Failed to start app")
    
    def _on_chat_message(self, peer_id: str, message: str):
        """Handle incoming chat messages."""
        print(f"\n📨 Chat from {peer_id}: {message}")
        print("> ", end="", flush=True)
    
    def _on_file_received(self, peer_id: str, filename: str, file_data: bytes):
        """Handle incoming files."""
        print(f"\n📎 File '{filename}' from {peer_id} ({len(file_data)} bytes)")
        print("> ", end="", flush=True)
    
    def _on_peer_discovered(self, peer: P2PPeer):
        """Handle peer discovery."""
        if peer not in self.discovered_peers:
            self.discovered_peers.append(peer)
            print(f"\n🔍 Discovered peer: {peer}")
            print("> ", end="", flush=True)
    
    async def _start_ui(self):
        """Start the user interface."""
        print("📱 Simple Mobile P2P App Ready!")
        print("Available commands:")
        print("  peers          - List discovered peers")
        print("  connect <num>  - Connect to peer by number")
        print("  chat <num> <message> - Send chat to peer")
        print("  file <num> <path>    - Send file to peer")
        print("  manual <addr> <port> - Manually add peer")
        print("  info           - Show app info")
        print("  help           - Show this help")
        print("  quit           - Exit app")
        print("=" * 60)
        
        # Start input loop in background thread
        input_thread = threading.Thread(target=self._input_loop, daemon=True)
        input_thread.start()
        
        # Keep app running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
            self.running = False
        
        # Clean up
        if self.host:
            await self.host.stop()
    
    def _input_loop(self):
        """Handle user input in a separate thread."""
        while self.running:
            try:
                command = input("> ").strip().split()
                if not command:
                    continue
                
                asyncio.run_coroutine_threadsafe(
                    self._handle_command(command), 
                    asyncio.get_event_loop()
                )
                
            except (EOFError, KeyboardInterrupt):
                self.running = False
                break
            except Exception as e:
                print(f"❌ Input error: {e}")
    
    async def _handle_command(self, command: List[str]):
        """Handle user commands."""
        cmd = command[0].lower()
        
        if cmd == 'quit' or cmd == 'exit':
            self.running = False
            
        elif cmd == 'peers':
            self._show_peers()
            
        elif cmd == 'connect':
            if len(command) >= 2:
                try:
                    peer_num = int(command[1])
                    await self._connect_peer(peer_num)
                except ValueError:
                    print("❌ Invalid peer number")
            else:
                print("Usage: connect <peer_number>")
        
        elif cmd == 'chat':
            if len(command) >= 3:
                try:
                    peer_num = int(command[1])
                    message = ' '.join(command[2:])
                    await self._send_chat(peer_num, message)
                except ValueError:
                    print("❌ Invalid peer number")
            else:
                print("Usage: chat <peer_number> <message>")
        
        elif cmd == 'file':
            if len(command) >= 3:
                try:
                    peer_num = int(command[1])
                    file_path = command[2]
                    await self._send_file(peer_num, file_path)
                except ValueError:
                    print("❌ Invalid peer number")
            else:
                print("Usage: file <peer_number> <file_path>")
        
        elif cmd == 'manual':
            if len(command) >= 3:
                try:
                    address = command[1]
                    port = int(command[2])
                    display_name = command[3] if len(command) > 3 else f"Manual-{address}-{port}"
                    self._add_manual_peer(address, port, display_name)
                except ValueError:
                    print("❌ Invalid port number")
            else:
                print("Usage: manual <address> <port> [display_name]")
        
        elif cmd == 'info':
            self._show_info()
        
        elif cmd == 'help':
            self._show_help()
        
        else:
            print(f"❌ Unknown command: {cmd}. Type 'help' for available commands.")
    
    def _show_peers(self):
        """Show discovered peers."""
        if not self.discovered_peers:
            print("🔍 No peers discovered yet")
            return
        
        print(f"🔍 Discovered {len(self.discovered_peers)} peers:")
        for i, peer in enumerate(self.discovered_peers):
            print(f"   {i}: {peer}")
    
    async def _connect_peer(self, peer_num: int):
        """Connect to a peer."""
        if not self.host:
            print("❌ Host not ready")
            return
        
        if peer_num < 0 or peer_num >= len(self.discovered_peers):
            print("❌ Invalid peer number")
            return
        
        peer = self.discovered_peers[peer_num]
        success = await self.host.connect_to_peer(peer)
        if success:
            print(f"✅ Connected to {peer}")
        else:
            print(f"❌ Failed to connect to {peer}")
    
    async def _send_chat(self, peer_num: int, message: str):
        """Send chat message to peer."""
        if not self.host:
            print("❌ Host not ready")
            return
        
        if peer_num < 0 or peer_num >= len(self.discovered_peers):
            print("❌ Invalid peer number")
            return
        
        peer = self.discovered_peers[peer_num]
        success = await self.host.send_chat_message(peer, message)
        if success:
            print(f"✅ Sent chat to {peer}: {message}")
        else:
            print(f"❌ Failed to send chat to {peer}")
    
    async def _send_file(self, peer_num: int, file_path: str):
        """Send file to peer."""
        if not self.host:
            print("❌ Host not ready")
            return
        
        if peer_num < 0 or peer_num >= len(self.discovered_peers):
            print("❌ Invalid peer number")
            return
        
        peer = self.discovered_peers[peer_num]
        success = await self.host.send_file(peer, file_path)
        if success:
            print(f"✅ Sent file to {peer}: {file_path}")
        else:
            print(f"❌ Failed to send file to {peer}")
    
    def _add_manual_peer(self, address: str, port: int, display_name: str):
        """Manually add a peer."""
        if not self.host:
            print("❌ Host not ready")
            return
        
        peer = self.host.add_manual_peer(address, port, display_name)
        print(f"✅ Manually added peer: {peer}")
    
    def _show_info(self):
        """Show app information."""
        if self.host:
            print(f"📱 Mobile P2P App Info:")
            print(f"   Peer ID: {self.host.get_peer_id()}")
            print(f"   Port: {self.host.port}")
            print(f"   Addresses: {self.host.get_listen_addresses()}")
            print(f"   Connected peers: {len(self.host.get_connected_peers())}")
            print(f"   Discovered peers: {len(self.discovered_peers)}")
        else:
            print("❌ Host not ready")
    
    def _show_help(self):
        """Show help information."""
        print("📱 Simple Mobile P2P App Commands:")
        print("   peers          - List discovered peers")
        print("   connect <num>  - Connect to peer by number")
        print("   chat <num> <message> - Send chat to peer")
        print("   file <num> <path>    - Send file to peer")
        print("   manual <addr> <port> - Manually add peer")
        print("   info           - Show app info")
        print("   help           - Show this help")
        print("   quit           - Exit app")


async def main():
    """Main function."""
    import sys
    
    port = 0
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("❌ Invalid port number")
            sys.exit(1)
    
    app = SimpleMobileApp(port)
    await app.start()


if __name__ == '__main__':
    print("Simple Mobile P2P App - Desktop Testing Version")
    print("This demonstrates mobile P2P functionality without Kivy dependencies")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ App failed: {e}")
        logging.exception("App failed")
