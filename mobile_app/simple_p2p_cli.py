#!/usr/bin/env python3
"""
Simple Mobile P2P CLI Tool

This tool provides a command-line interface for testing the LibP2PMobileHost
implementation with peer-to-peer communication capabilities.
"""

import asyncio
import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mobile_app.libp2p_host import LibP2PMobileHost, P2PPeer

logger = logging.getLogger(__name__)


class P2PCLI:
    """Command-line interface for P2P operations."""
    
    def __init__(self, host: LibP2PMobileHost):
        self.host = host
        self.running = True
        
        # Set up message handlers
        self.host.set_message_handler('chat', self.on_chat_message)
        self.host.set_message_handler('file', self.on_file_message)
        self.host.set_peer_discovery_handler(self.on_peer_discovered)
        self.host.set_peer_disconnected_handler(self.on_peer_disconnected)
    
    def on_chat_message(self, peer_id: str, message: str):
        """Handle incoming chat messages."""
        print(f"\n📨 [{peer_id}]: {message}")
        self.show_prompt()
    
    def on_file_message(self, peer_id: str, filename: str, file_data_hex: str):
        """Handle incoming file messages."""
        try:
            # Convert hex back to bytes
            file_data = bytes.fromhex(file_data_hex)
            
            # Save file
            save_path = Path(f"received_{filename}")
            with open(save_path, 'wb') as f:
                f.write(file_data)
            
            print(f"\n📎 File received from {peer_id}: {filename} ({len(file_data)} bytes)")
            print(f"   Saved as: {save_path}")
            self.show_prompt()
            
        except Exception as e:
            print(f"\n❌ Error saving file from {peer_id}: {e}")
            self.show_prompt()
    
    def on_peer_discovered(self, peer: P2PPeer):
        """Handle peer discovery."""
        print(f"\n🔍 Peer discovered: {peer.display_name} ({peer.peer_id})")
        self.show_prompt()
    
    def on_peer_disconnected(self, peer_id: str):
        """Handle peer disconnection."""
        print(f"\n💔 Peer disconnected: {peer_id}")
        self.show_prompt()
    
    def show_prompt(self):
        """Show the command prompt."""
        print("p2p> ", end="", flush=True)
    
    def show_help(self):
        """Show available commands."""
        print("""
Available commands:
  help                          - Show this help message
  info                          - Show host information and connection details
  peers                         - List discovered and connected peers
  dial <multiaddr>              - Connect using full multiaddr (e.g., /ip4/127.0.0.1/tcp/9000/p2p/QmPeer...)
  chat <peer_id> <message>      - Send a chat message to a connected peer
  file <peer_id> <file_path>    - Send a file to a connected peer
  quit                          - Exit the application
        """)
    
    def show_info(self):
        """Show host information."""
        addresses = self.host.get_listen_addresses()
        addr_display = ', '.join(addresses) if addresses else "None (host may not be listening)"
        
        print(f"""
Host Information:
  Peer ID: {self.host.get_peer_id()}
  Listen Addresses: {addr_display}
  Connected Peers: {len(self.host.get_connected_peers())}
  Discovered Peers: {len(self.host.get_discovered_peers())}
  
Connection Info (for QR sharing):
  {self.host.get_connection_info()}
        """)
    
    def list_peers(self):
        """List discovered peers."""
        peers = self.host.get_discovered_peers()
        connected_peers = {p.peer_id for p in self.host.get_connected_peers()}
        
        if not peers:
            print("No peers discovered yet.")
            return
        
        print("\nDiscovered Peers:")
        for peer in peers:
            status = "🟢 Connected" if peer.peer_id in connected_peers else "🔴 Disconnected"
            print(f"  {status} {peer.display_name}")
            print(f"    ID: {peer.peer_id}")
            print(f"    Address: {peer.address}:{peer.port}")
    
    async def dial_multiaddr(self, multiaddr_str: str):
        """Connect using a full multiaddr string."""
        try:
            from multiaddr import Multiaddr
            from libp2p.peer.peerinfo import info_from_p2p_addr
            
            maddr = Multiaddr(multiaddr_str)
            peer_info = info_from_p2p_addr(maddr)
            
            success = await self.host.dial_peer_info(peer_info)
            if success:
                print(f"✅ Connected to peer {peer_info.peer_id}")
            else:
                print(f"❌ Failed to connect to {multiaddr_str}")
                
        except Exception as e:
            print(f"❌ Dial failed: {e}")
    
    async def send_chat(self, peer_id_str: str, message: str):
        """Send a chat message to a peer."""
        peers = {p.peer_id: p for p in self.host.get_discovered_peers()}
        
        if peer_id_str not in peers:
            print(f"❌ Peer {peer_id_str} not found. Use 'peers' to list available peers.")
            return
        
        success = await self.host.send_chat_message(peers[peer_id_str], message)
        if success:
            print(f"✅ Message sent to {peer_id_str}")
        else:
            print(f"❌ Failed to send message to {peer_id_str}")
    
    async def send_file(self, peer_id_str: str, file_path: str):
        """Send a file to a peer."""
        peers = {p.peer_id: p for p in self.host.get_discovered_peers()}
        
        if peer_id_str not in peers:
            print(f"❌ Peer {peer_id_str} not found. Use 'peers' to list available peers.")
            return
        
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            return
        
        success = await self.host.send_file(peers[peer_id_str], file_path)
        if success:
            print(f"✅ File sent to {peer_id_str}: {file_path}")
        else:
            print(f"❌ Failed to send file to {peer_id_str}")
    
    async def run(self):
        """Run the CLI interface."""
        self.show_prompt()
        
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                line = await loop.run_in_executor(None, sys.stdin.readline)
                if not line: break
                
                line = line.strip()
                if not line:
                    self.show_prompt()
                    continue
                
                parts = line.split()
                command = parts[0].lower()
                
                if command == 'help':
                    self.show_help()
                elif command == 'info':
                    self.show_info()
                elif command == 'peers':
                    self.list_peers()
                elif command == 'dial' and len(parts) >= 2:
                    await self.dial_multiaddr(parts[1])
                elif command == 'chat' and len(parts) >= 3:
                    await self.send_chat(parts[1], ' '.join(parts[2:]))
                elif command == 'file' and len(parts) >= 3:
                    await self.send_file(parts[1], parts[2])
                elif command in ['quit', 'exit']:
                    self.running = False
                else:
                    print("❌ Unknown command. Type 'help' for available commands.")
                
                if self.running:
                    self.show_prompt()
                    
            except Exception as e:
                logger.error(f"CLI Error: {e}", exc_info=True)
                self.show_prompt()

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Simple Mobile P2P CLI Tool')
    parser.add_argument('--port', type=int, default=0, help='Port to listen on (0 for auto)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--force-asyncio', action='store_true', help='Force use of asyncio even on desktop')
    
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    host = None
    try:
        print("🚀 Preparing LibP2P Host...")
        host = LibP2PMobileHost(port=args.port, force_asyncio=args.force_asyncio)
        await host.start()
        
        print(f"""
🚀 Simple Mobile P2P CLI Started
Host: {host.get_peer_id()}
Type 'help' for available commands.
        """)
        
        async with host.run():
            print("✅ Host is now running and listening.")
            cli = P2PCLI(host)
            await cli.run()
            
    except Exception as e:
        logger.error(f"An error occurred during startup: {e}", exc_info=True)
    finally:
        if host and host.is_running:
            await host.stop()
        print("👋 Goodbye!")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
