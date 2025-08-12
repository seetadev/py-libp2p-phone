"""
Integration test for the mobile P2P application.

This script demonstrates the real libp2p integration working with
peer discovery and messaging.
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from p2p_host import RealMobileHost
from mobile_abc import P2PPeer

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MobileAppIntegrationTest:
    """Integration test for the mobile app."""
    
    def __init__(self):
        self.hosts = []
        self.running = True
    
    async def create_test_hosts(self, count: int = 2):
        """Create multiple test hosts for peer-to-peer testing."""
        print(f"Creating {count} test hosts...")
        
        for i in range(count):
            port = 9000 + i
            host = RealMobileHost(port)
            
            # Set up message handlers
            def make_chat_handler(host_id):
                def handler(peer_id: str, message: str):
                    print(f"🏠 Host {host_id} - 📨 Chat from {peer_id}: {message}")
                return handler
            
            def make_file_handler(host_id):
                def handler(peer_id: str, filename: str, file_data: bytes):
                    print(f"🏠 Host {host_id} - 📎 File '{filename}' from {peer_id} ({len(file_data)} bytes)")
                return handler
            
            def make_discovery_handler(host_id):
                def handler(peer: P2PPeer):
                    print(f"🏠 Host {host_id} - 🔍 Discovered peer: {peer}")
                return handler
            
            host.set_message_handler('chat', make_chat_handler(i))
            host.set_message_handler('file', make_file_handler(i))
            host.set_peer_discovery_handler(make_discovery_handler(i))
            
            # Start the host
            await host.start()
            self.hosts.append(host)
            
            print(f"✅ Host {i} started: {host.get_peer_id()} on {host.get_listen_addresses()}")
    
    async def test_peer_discovery(self):
        """Test peer discovery between hosts."""
        print("\n🔍 Testing peer discovery...")
        
        # Wait for discovery to happen
        await asyncio.sleep(15)  # Give time for discovery
        
        for i, host in enumerate(self.hosts):
            peers = host.get_discovered_peers()
            print(f"🏠 Host {i} discovered {len(peers)} peers:")
            for peer in peers:
                print(f"   - {peer}")
    
    async def test_chat_messaging(self):
        """Test chat messaging between hosts."""
        print("\n💬 Testing chat messaging...")
        
        if len(self.hosts) >= 2:
            host1, host2 = self.hosts[0], self.hosts[1]
            
            # Get peers for messaging
            peers1 = host1.get_discovered_peers()
            peers2 = host2.get_discovered_peers()
            
            # Send messages if peers are discovered
            if peers1:
                peer = peers1[0]
                print(f"📤 Host 0 sending chat to {peer}")
                success = await host1.send_chat_message(peer, "Hello from Host 0!")
                print(f"   Message sent: {success}")
            
            if peers2:
                peer = peers2[0]
                print(f"📤 Host 1 sending chat to {peer}")
                success = await host2.send_chat_message(peer, "Hello from Host 1!")
                print(f"   Message sent: {success}")
            
            # Wait for messages to be processed
            await asyncio.sleep(2)
    
    async def test_manual_connection(self):
        """Test manual peer connection (simulating QR code scan)."""
        print("\n🔗 Testing manual peer connection...")
        
        if len(self.hosts) >= 2:
            host1, host2 = self.hosts[0], self.hosts[1]
            
            # Manually add each other as peers
            host2_info = host2.get_connection_info()
            peer = host1.add_manual_peer(
                address=host2_info['address'],
                port=host2_info['port'],
                display_name=f"Manual Peer - {host2_info['display_name']}"
            )
            
            print(f"🏠 Host 0 manually added peer: {peer}")
            
            # Test messaging to manual peer
            success = await host1.send_chat_message(peer, "Hello via manual connection!")
            print(f"   Manual message sent: {success}")
            
            await asyncio.sleep(2)
    
    async def run_tests(self):
        """Run all integration tests."""
        try:
            print("🚀 Starting Mobile P2P Integration Tests")
            print("=" * 60)
            
            # Create test hosts
            await self.create_test_hosts(2)
            
            # Test discovery
            await self.test_peer_discovery()
            
            # Test chat messaging
            await self.test_chat_messaging()
            
            # Test manual connection
            await self.test_manual_connection()
            
            print("\n✅ All tests completed!")
            print("=" * 60)
            
            # Keep hosts running for interactive testing
            print("\n🎮 Interactive mode - You can now:")
            print("   - Connect with the CLI tool: python cli_test.py 9002")
            print("   - Send messages between the test hosts")
            print("   - Press Ctrl+C to stop")
            
            try:
                while self.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Stopping tests...")
                self.running = False
            
        except Exception as e:
            print(f"❌ Test failed: {e}")
            logger.exception("Integration test failed")
        
        finally:
            # Clean up
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up test hosts."""
        print("\n🧹 Cleaning up...")
        for i, host in enumerate(self.hosts):
            try:
                await host.stop()
                print(f"✅ Host {i} stopped")
            except Exception as e:
                print(f"❌ Error stopping host {i}: {e}")


async def main():
    """Main test function."""
    test = MobileAppIntegrationTest()
    await test.run_tests()


if __name__ == '__main__':
    print("Mobile P2P Integration Test")
    print("This test demonstrates the real libp2p integration")
    print("You can also test with the CLI tool while this runs")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Test failed: {e}")
        logging.exception("Test failed")
