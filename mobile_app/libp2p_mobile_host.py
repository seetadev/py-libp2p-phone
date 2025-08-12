"""
Mobile LibP2P Host Implementation

This module provides a complete libp2p host implementation for mobile applications,
using the mobile runtime adapter and transport layer for cross-platform compatibility.
"""

import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any, Sequence
from pathlib import Path

import multiaddr
from multiaddr import Multiaddr

# Mobile runtime imports
from mobile.runtime import get_runtime_adapter, AsyncRuntimeAdapter
from mobile.factory import create_tcp_transport, get_transport_class
from mobile.io import MobileAsyncStream

# LibP2P core imports
from libp2p.abc import IHost, INetworkService
from libp2p.crypto.keys import KeyPair
from libp2p.crypto.rsa import create_new_key_pair
from libp2p.peer.id import ID
from libp2p.peer.peerstore import PeerStore
from libp2p.peer.peerinfo import PeerInfo
from libp2p.host.basic_host import BasicHost
from libp2p.network.swarm import Swarm
from libp2p.custom_types import TProtocol

# Local interfaces
from mobile_app.mobile_abc import IP2PHost, P2PPeer

logger = logging.getLogger(__name__)


class MobileLibP2PHost(IP2PHost):
    """
    Mobile-compatible LibP2P host implementation.
    
    This host uses the mobile runtime adapter and transport layer to provide
    full libp2p functionality on mobile platforms while maintaining compatibility
    with desktop environments.
    """
    
    def __init__(self, 
                 port: int = 0,
                 key_pair: Optional[KeyPair] = None,
                 enable_mdns: bool = True,
                 listen_addrs: Optional[Sequence[str]] = None):
        """
        Initialize the mobile libp2p host.
        
        Args:
            port: Port to listen on (0 for random)
            key_pair: Cryptographic key pair (generated if None)
            enable_mdns: Enable mDNS peer discovery
            listen_addrs: List of addresses to listen on
        """
        # Initialize mobile runtime adapter
        self.runtime_adapter = get_runtime_adapter()
        
        # Generate or use provided key pair
        self.key_pair = key_pair or create_new_key_pair()
        self.peer_id = ID.from_pubkey(self.key_pair.public_key)
        
        # Configuration
        self.port = port
        self.enable_mdns = enable_mdns
        
        # Parse listen addresses
        if listen_addrs is None:
            self.listen_addrs = [Multiaddr(f"/ip4/0.0.0.0/tcp/{port}")]
        else:
            self.listen_addrs = [Multiaddr(addr) for addr in listen_addrs]
        
        # LibP2P components
        self.host: Optional[IHost] = None
        self.swarm: Optional[INetworkService] = None
        self.peerstore: Optional[PeerStore] = None
        
        # Mobile-specific state
        self.discovered_peers: Dict[str, P2PPeer] = {}
        self.connections: Dict[str, INetStream] = {}
        self.is_running = False
        
        # Event handlers
        self.on_peer_discovered: Optional[Callable[[P2PPeer], None]] = None
        self.on_message_received: Optional[Callable[[str, str, dict], None]] = None
        self.on_file_received: Optional[Callable[[str, str, bytes], None]] = None
        self.on_peer_disconnected: Optional[Callable[[str], None]] = None
        
        # Protocol handlers
        self.protocol_handlers: Dict[str, Callable] = {}
        
        logger.info(f"Initialized MobileLibP2PHost with peer_id: {self.peer_id}")
    
    async def start(self) -> None:
        """Start the mobile libp2p host."""
        try:
            logger.info("Starting mobile libp2p host...")
            
            # Create the libp2p host with mobile transport
            self.host = new_host(
                key_pair=self.key_pair,
                peerstore_opt=self.peerstore,
                enable_mDNS=self.enable_mdns,
                listen_addrs=self.listen_addrs
            )
            
            # Get the underlying swarm for transport management
            self.swarm = self.host.get_network()
            
            # Create and add our mobile transport to the swarm
            transport = create_tcp_transport()
            self.swarm.add_transport(transport)
            
            # Set up protocol handlers
            await self._setup_protocols()
            
            # Start listening using the runtime adapter
            async with self.runtime_adapter.create_nursery() as nursery:
                # Start the host
                await nursery.start_soon(self.host.start)
                
                # Update actual listening addresses and port
                listen_addresses = self.host.get_addrs()
                if listen_addresses:
                    # Extract actual port from first TCP address
                    for addr in listen_addresses:
                        tcp_port = addr.value_for_protocol("tcp")
                        if tcp_port:
                            self.port = int(tcp_port)
                            break
                
                self.is_running = True
                
                # Start peer discovery if enabled
                if self.enable_mdns:
                    await self._start_mdns_discovery(nursery)
                
                logger.info(f"Mobile libp2p host started on port {self.port}")
                logger.info(f"Peer ID: {self.peer_id}")
                logger.info(f"Listen addresses: {[str(addr) for addr in listen_addresses]}")
                
        except Exception as e:
            logger.error(f"Failed to start mobile libp2p host: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the mobile libp2p host."""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            # Close all connections
            for stream in self.connections.values():
                await stream.close()
            self.connections.clear()
            
            # Stop the host
            if self.host:
                await self.host.close()
            
            logger.info("Mobile libp2p host stopped")
            
        except Exception as e:
            logger.error(f"Error stopping mobile libp2p host: {e}")
    
    async def _setup_protocols(self) -> None:
        """Set up libp2p protocol handlers."""
        if not self.host:
            logger.warning("Cannot setup protocols: host not initialized")
            return
            
        # Chat protocol
        self.host.set_stream_handler(TProtocol("/mobile/chat/1.0.0"), self._handle_chat_stream)
        
        # File transfer protocol
        self.host.set_stream_handler(TProtocol("/mobile/file/1.0.0"), self._handle_file_stream)
        
        # Peer discovery protocol
        self.host.set_stream_handler(TProtocol("/mobile/discovery/1.0.0"), self._handle_discovery_stream)
    
    async def _start_mdns_discovery(self, nursery) -> None:
        """Start mDNS-based peer discovery."""
        try:
            # Create mDNS discovery service
            mdns = MDNSDiscovery(
                self.host,
                interval=10.0,  # Discovery interval in seconds
                discovery_timeout=5.0  # Timeout for each discovery round
            )
            
            # Start mDNS discovery
            await nursery.start_soon(mdns.start)
            
            # Set up peer discovery callback
            mdns.set_discovery_callback(self._on_peer_discovered_mdns)
            
            logger.info("mDNS peer discovery started")
            
        except Exception as e:
            logger.warning(f"Failed to start mDNS discovery: {e}")
    
    async def _on_peer_discovered_mdns(self, peer_info: PeerInfo) -> None:
        """Handle peer discovered via mDNS."""
        try:
            # Convert PeerInfo to P2PPeer
            peer = self._peer_info_to_p2p_peer(peer_info)
            
            # Add to discovered peers
            if peer.peer_id not in self.discovered_peers:
                self.discovered_peers[peer.peer_id] = peer
                
                # Notify callback
                if self.on_peer_discovered:
                    await self._safe_call_handler(self.on_peer_discovered, peer)
                
                logger.info(f"Discovered peer via mDNS: {peer}")
        
        except Exception as e:
            logger.error(f"Error handling mDNS peer discovery: {e}")
    
    def _peer_info_to_p2p_peer(self, peer_info: PeerInfo) -> P2PPeer:
        """Convert libp2p PeerInfo to P2PPeer."""
        peer_id_str = str(peer_info.peer_id)
        
        # Extract address and port from multiaddrs
        address = "127.0.0.1"  # Default fallback
        port = 0
        
        for maddr in peer_info.addrs:
            ip4_addr = maddr.value_for_protocol("ip4")
            tcp_port = maddr.value_for_protocol("tcp")
            
            if ip4_addr and tcp_port:
                address = ip4_addr
                port = int(tcp_port)
                break
        
        return P2PPeer(
            peer_id=peer_id_str,
            address=address,
            port=port,
            display_name=f"Mobile Device {peer_id_str[:8]}"
        )
    
    async def _handle_chat_stream(self, stream: INetStream) -> None:
        """Handle incoming chat stream."""
        try:
            # Read the chat message
            data = await stream.read()
            message_str = data.decode('utf-8')
            
            # Parse JSON message
            import json
            message = json.loads(message_str)
            
            peer_id = str(stream.get_remote_peer())
            content = message.get('content', '')
            
            # Notify message handler
            if self.on_message_received:
                await self._safe_call_handler(self.on_message_received, peer_id, 'chat', {'content': content})
            
            logger.debug(f"Received chat message from {peer_id}: {content}")
            
        except Exception as e:
            logger.error(f"Error handling chat stream: {e}")
        finally:
            await stream.close()
    
    async def _handle_file_stream(self, stream: INetStream) -> None:
        """Handle incoming file transfer stream."""
        try:
            # Read file metadata first
            metadata_data = await stream.read(1024)  # Read metadata
            metadata_str = metadata_data.decode('utf-8')
            
            import json
            metadata = json.loads(metadata_str)
            filename = metadata.get('filename', 'unknown')
            file_size = metadata.get('size', 0)
            
            # Read file content
            file_data = b""
            while len(file_data) < file_size:
                chunk = await stream.read(8192)
                if not chunk:
                    break
                file_data += chunk
            
            peer_id = str(stream.get_remote_peer())
            
            # Notify file handler
            if self.on_file_received:
                await self._safe_call_handler(self.on_file_received, peer_id, filename, file_data)
            
            logger.info(f"Received file '{filename}' from {peer_id} ({len(file_data)} bytes)")
            
        except Exception as e:
            logger.error(f"Error handling file stream: {e}")
        finally:
            await stream.close()
    
    async def _handle_discovery_stream(self, stream: INetStream) -> None:
        """Handle peer discovery stream."""
        try:
            # This could be used for custom discovery protocols
            # For now, we rely on mDNS
            peer_id = str(stream.get_remote_peer())
            logger.debug(f"Discovery stream from {peer_id}")
            
        except Exception as e:
            logger.error(f"Error handling discovery stream: {e}")
        finally:
            await stream.close()
    
    async def _safe_call_handler(self, handler: Callable, *args, **kwargs) -> None:
        """Safely call a handler function."""
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(*args, **kwargs)
            else:
                handler(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in handler: {e}")
    
    # IP2PHost interface implementation
    
    def get_peer_id(self) -> str:
        """Get the peer ID of this host."""
        return str(self.peer_id)
    
    def get_listen_addresses(self) -> List[str]:
        """Get the addresses this host is listening on."""
        if self.host:
            return [str(addr) for addr in self.host.get_addrs()]
        return []
    
    def get_discovered_peers(self) -> List[P2PPeer]:
        """Get list of discovered peers."""
        return list(self.discovered_peers.values())
    
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs."""
        return list(self.connections.keys())
    
    def set_message_handler(self, handler_type: str, handler: Callable) -> None:
        """Set a message handler for a specific type."""
        if handler_type == 'chat':
            self.on_message_received = handler
        elif handler_type == 'file':
            self.on_file_received = handler
    
    def set_peer_discovery_handler(self, handler: Callable[[P2PPeer], None]) -> None:
        """Set peer discovery handler."""
        self.on_peer_discovered = handler
    
    def set_peer_disconnected_handler(self, handler: Callable[[str], None]) -> None:
        """Set peer disconnected handler."""
        self.on_peer_disconnected = handler
    
    async def connect_to_peer(self, peer: P2PPeer) -> bool:
        """Connect to a peer using libp2p."""
        try:
            # Create multiaddr from peer information
            maddr = Multiaddr(f"/ip4/{peer.address}/tcp/{peer.port}")
            
            # Convert peer_id string to ID object
            peer_id = ID.from_base58(peer.peer_id) if isinstance(peer.peer_id, str) else peer.peer_id
            
            # Create PeerInfo
            peer_info = PeerInfo(peer_id, [maddr])
            
            # Connect to peer
            await self.host.connect(peer_info)
            
            logger.info(f"Connected to peer: {peer}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer}: {e}")
            return False
    
    async def send_chat_message(self, peer: P2PPeer, message: str) -> bool:
        """Send a chat message to a peer."""
        try:
            # Create multiaddr and peer info
            maddr = Multiaddr(f"/ip4/{peer.address}/tcp/{peer.port}")
            peer_id = ID.from_base58(peer.peer_id) if isinstance(peer.peer_id, str) else peer.peer_id
            peer_info = PeerInfo(peer_id, [maddr])
            
            # Open stream to peer
            stream = await self.host.new_stream(peer_info, [TProtocol("/mobile/chat/1.0.0")])
            
            # Send message
            import json
            message_data = json.dumps({'content': message}).encode('utf-8')
            await stream.write(message_data)
            await stream.close()
            
            logger.info(f"Sent chat message to {peer}: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send chat message to {peer}: {e}")
            return False
    
    async def send_file(self, peer: P2PPeer, file_path: str) -> bool:
        """Send a file to a peer."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"File {file_path} does not exist")
                return False
            
            # Create multiaddr and peer info
            maddr = Multiaddr(f"/ip4/{peer.address}/tcp/{peer.port}")
            peer_id = ID.from_base58(peer.peer_id) if isinstance(peer.peer_id, str) else peer.peer_id
            peer_info = PeerInfo(peer_id, [maddr])
            
            # Open stream to peer
            stream = await self.host.new_stream(peer_info, [TProtocol("/mobile/file/1.0.0")])
            
            # Send file metadata
            import json
            file_size = file_path_obj.stat().st_size
            metadata = json.dumps({
                'filename': file_path_obj.name,
                'size': file_size
            }).encode('utf-8')
            
            await stream.write(metadata)
            
            # Send file content in chunks
            with open(file_path_obj, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    await stream.write(chunk)
            
            await stream.close()
            
            logger.info(f"Sent file '{file_path_obj.name}' to {peer}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send file to {peer}: {e}")
            return False
    
    def add_manual_peer(self, address: str, port: int, display_name: str = "") -> P2PPeer:
        """Manually add a peer (for QR code scanning)."""
        # For manual peers, we'll generate a peer ID based on address:port
        # In a real implementation, this would come from the QR code
        peer_id = f"manual_{address}_{port}"
        
        peer = P2PPeer(
            peer_id=peer_id,
            address=address,
            port=port,
            display_name=display_name or f"Manual Device {address}:{port}"
        )
        
        self.discovered_peers[peer_id] = peer
        
        if self.on_peer_discovered:
            try:
                self.on_peer_discovered(peer)
            except Exception as e:
                logger.error(f"Error in peer discovery callback: {e}")
        
        return peer
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for QR code generation."""
        return {
            'peer_id': str(self.peer_id),
            'address': '127.0.0.1',  # For local testing
            'port': self.port,
            'display_name': f"Mobile Device {self.port}",
            'addrs': self.get_listen_addresses()
        }


# Factory functions

async def create_mobile_libp2p_host(
    port: int = 0,
    enable_mdns: bool = True,
    listen_addrs: Optional[Sequence[str]] = None
) -> MobileLibP2PHost:
    """
    Create and start a mobile libp2p host.
    
    Args:
        port: Port to listen on (0 for random)
        enable_mdns: Enable mDNS peer discovery
        listen_addrs: List of addresses to listen on
        
    Returns:
        MobileLibP2PHost: The created and started host
    """
    host = MobileLibP2PHost(
        port=port,
        enable_mdns=enable_mdns,
        listen_addrs=listen_addrs
    )
    await host.start()
    return host


# Test function
async def test_mobile_libp2p_host():
    """Test the mobile libp2p host."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing MobileLibP2PHost...")
    
    try:
        # Create host
        host = await create_mobile_libp2p_host(port=9000, enable_mdns=True)
        
        # Set up message handlers
        def on_chat(peer_id: str, msg_type: str, data: dict):
            print(f"📨 Chat from {peer_id}: {data.get('content')}")
        
        def on_file(peer_id: str, filename: str, file_data: bytes):
            print(f"📎 File '{filename}' from {peer_id} ({len(file_data)} bytes)")
        
        def on_peer_discovered(peer: P2PPeer):
            print(f"🔍 Discovered peer: {peer}")
        
        host.set_message_handler('chat', on_chat)
        host.set_message_handler('file', on_file)
        host.set_peer_discovery_handler(on_peer_discovered)
        
        print(f"Host started: {host.get_peer_id()}")
        print(f"Addresses: {host.get_listen_addresses()}")
        print("Host is running... (Press Ctrl+C to stop)")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping host...")
            await host.stop()
    
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_mobile_libp2p_host())

import asyncio
import logging
from typing import Optional, Dict, List, Callable, Any
from pathlib import Path

# Mobile runtime imports
from mobile.runtime import get_runtime_adapter, AsyncRuntimeAdapter
from mobile.factory import create_tcp_transport

# Mobile app interfaces
from mobile_app.mobile_abc import IP2PHost, P2PPeer

logger = logging.getLogger(__name__)


class LibP2PMobileHost(IP2PHost):
    """
    Mobile host implementation using real libp2p protocols.
    
    This implementation properly integrates with the mobile runtime adapter
    and uses libp2p for all networking operations.
    """
    
    def __init__(self, port: int = 0):
        self.port = port
        self.runtime_adapter: Optional[AsyncRuntimeAdapter] = None
        self.host: Optional[IHost] = None
        self.swarm: Optional[INetworkService] = None
        self.peer_store: Optional[PeerStore] = None
        self.mdns_discovery: Optional[MDNSDiscovery] = None
        
        # Peer management
        self.discovered_peers: Dict[str, P2PPeer] = {}
        self.is_running = False
        
        # Event handlers
        self.on_peer_discovered: Optional[Callable[[P2PPeer], None]] = None
        self.on_message_received: Optional[Callable[[str, str, dict], None]] = None
        self.on_file_received: Optional[Callable[[str, str, bytes], None]] = None
        self.message_handlers: Dict[str, Callable] = {}
        
        logger.info(f"Initialized LibP2PMobileHost for port {port}")
    
    async def start(self) -> None:
        """Start the libp2p mobile host."""
        try:
            # Get runtime adapter for mobile compatibility
            self.runtime_adapter = get_runtime_adapter()
            logger.info(f"Using runtime: {self.runtime_adapter.runtime_name}")
            
            # Create key pair for this peer
            key_pair = await create_new_key_pair()
            peer_id = ID.from_pubkey(key_pair.public_key)
            
            logger.info(f"Generated peer ID: {peer_id}")
            
            # Create peer store
            self.peer_store = PeerStore()
            
            # Create transport
            transport = create_tcp_transport()
            
            # Create swarm
            self.swarm = Swarm(
                peer_id=peer_id,
                peerstore=self.peer_store,
                upgrader=None,  # Will be set up by host
            )
            
            # Add transport to swarm
            self.swarm.add_transport(transport)
            
            # Create basic host
            self.host = BasicHost(
                network=self.swarm,
                router=None,  # No routing for basic setup
            )
            
            # Set up listen address
            listen_addr = f"/ip4/0.0.0.0/tcp/{self.port}"
            listen_multiaddr = Multiaddr(listen_addr)
            
            # Start listening
            await self.host.get_network().listen(listen_multiaddr)
            
            # Get actual listening addresses
            listen_addrs = self.host.get_addrs()
            if listen_addrs:
                # Extract actual port from first address
                tcp_port = listen_addrs[0].value_for_protocol("tcp")
                if tcp_port:
                    self.port = int(tcp_port)
            
            logger.info(f"LibP2P host listening on: {listen_addrs}")
            
            # Set up stream handlers
            await self._setup_stream_handlers()
            
            # Start peer discovery
            await self._start_discovery()
            
            self.is_running = True
            logger.info(f"LibP2P mobile host started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start LibP2P mobile host: {e}")
            raise
    
    async def _setup_stream_handlers(self) -> None:
        """Set up libp2p stream handlers for chat and file transfer."""
        if not self.host:
            return
        
        # Chat protocol handler
        async def chat_handler(stream):
            """Handle incoming chat messages."""
            try:
                # Read message length (4 bytes)
                length_bytes = await stream.read(4)
                if len(length_bytes) != 4:
                    return
                
                message_length = int.from_bytes(length_bytes, 'big')
                
                # Read the actual message
                message_bytes = await stream.read(message_length)
                message = message_bytes.decode('utf-8')
                
                # Get peer ID
                peer_id = str(stream.muxed_conn.peer_id)
                
                # Call handler
                handler = self.message_handlers.get('chat')
                if handler:
                    handler(peer_id, message)
                
                # Close stream
                await stream.close()
                
            except Exception as e:
                logger.error(f"Error handling chat stream: {e}")
        
        # File transfer protocol handler  
        async def file_handler(stream):
            """Handle incoming file transfers."""
            try:
                # Read filename length (4 bytes)
                filename_len_bytes = await stream.read(4)
                if len(filename_len_bytes) != 4:
                    return
                
                filename_length = int.from_bytes(filename_len_bytes, 'big')
                
                # Read filename
                filename_bytes = await stream.read(filename_length)
                filename = filename_bytes.decode('utf-8')
                
                # Read file size (4 bytes)
                file_size_bytes = await stream.read(4)
                if len(file_size_bytes) != 4:
                    return
                
                file_size = int.from_bytes(file_size_bytes, 'big')
                
                # Read file data
                file_data = await stream.read(file_size)
                
                # Get peer ID
                peer_id = str(stream.muxed_conn.peer_id)
                
                # Call handler
                handler = self.message_handlers.get('file')
                if handler:
                    handler(peer_id, filename, file_data)
                
                # Close stream
                await stream.close()
                
            except Exception as e:
                logger.error(f"Error handling file stream: {e}")
        
        # Register protocol handlers
        self.host.set_stream_handler("/mobile/chat/1.0.0", chat_handler)
        self.host.set_stream_handler("/mobile/file/1.0.0", file_handler)
        
        logger.info("Stream handlers registered")
    
    async def _start_discovery(self) -> None:
        """Start peer discovery using mDNS."""
        try:
            if not self.host:
                return
            
            # Create mDNS discovery
            self.mdns_discovery = MDNSDiscovery(self.host)
            
            # Set up discovery handler
            async def on_peer_found(peer_info: PeerInfo) -> None:
                """Handle discovered peers."""
                try:
                    peer_id = str(peer_info.peer_id)
                    
                    # Convert to our peer format
                    if peer_info.addrs:
                        addr = peer_info.addrs[0]
                        ip = addr.value_for_protocol("ip4")
                        port = addr.value_for_protocol("tcp")
                        
                        if ip and port:
                            peer = P2PPeer(
                                peer_id=peer_id,
                                address=ip,
                                port=int(port),
                                display_name=f"LibP2P Device {port}"
                            )
                            
                            # Add to discovered peers
                            if peer_id not in self.discovered_peers:
                                self.discovered_peers[peer_id] = peer
                                
                                # Call discovery handler
                                if self.on_peer_discovered:
                                    self.on_peer_discovered(peer)
                                    
                                logger.info(f"Discovered peer via mDNS: {peer}")
                
                except Exception as e:
                    logger.error(f"Error processing discovered peer: {e}")
            
            # Start discovery
            await self.mdns_discovery.start(on_peer_found)
            logger.info("mDNS peer discovery started")
            
        except Exception as e:
            logger.error(f"Failed to start peer discovery: {e}")
    
    async def stop(self) -> None:
        """Stop the libp2p mobile host."""
        try:
            self.is_running = False
            
            # Stop discovery
            if self.mdns_discovery:
                await self.mdns_discovery.stop()
            
            # Close host
            if self.host:
                await self.host.close()
            
            logger.info("LibP2P mobile host stopped")
            
        except Exception as e:
            logger.error(f"Error stopping host: {e}")
    
    def get_peer_id(self) -> str:
        """Get the peer ID of this host."""
        if self.host:
            return str(self.host.get_id())
        return "unknown"
    
    def get_listen_addresses(self) -> List[str]:
        """Get the addresses this host is listening on."""
        if self.host:
            addrs = self.host.get_addrs()
            return [str(addr) for addr in addrs]
        return []
    
    def get_discovered_peers(self) -> List[P2PPeer]:
        """Get list of discovered peers."""
        return list(self.discovered_peers.values())
    
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs."""
        if self.host and self.host.get_network():
            connections = self.host.get_network().connections()
            return [str(conn.peer_id) for conn in connections]
        return []
    
    def set_message_handler(self, handler_type: str, handler: Callable) -> None:
        """Set a message handler for a specific type."""
        self.message_handlers[handler_type] = handler
    
    def set_peer_discovery_handler(self, handler: Callable[[P2PPeer], None]):
        """Set peer discovery handler."""
        self.on_peer_discovered = handler
    
    async def connect_to_peer(self, peer: P2PPeer) -> bool:
        """Connect to a peer using libp2p."""
        try:
            if not self.host:
                return False
            
            # Create multiaddr for the peer
            peer_addr = f"/ip4/{peer.address}/tcp/{peer.port}"
            multiaddr = Multiaddr(peer_addr)
            
            # Create peer info
            peer_id = ID.from_string(peer.peer_id) if peer.peer_id != "unknown" else None
            if not peer_id:
                logger.error(f"Invalid peer ID for connection: {peer.peer_id}")
                return False
            
            peer_info = PeerInfo(peer_id, [multiaddr])
            
            # Connect to peer
            await self.host.connect(peer_info)
            logger.info(f"Connected to peer: {peer}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer}: {e}")
            return False
    
    async def send_chat_message(self, peer: P2PPeer, message: str) -> bool:
        """Send a chat message to a peer using libp2p streams."""
        try:
            if not self.host:
                return False
            
            # Create peer ID
            peer_id = ID.from_string(peer.peer_id) if peer.peer_id != "unknown" else None
            if not peer_id:
                logger.error(f"Invalid peer ID for chat: {peer.peer_id}")
                return False
            
            # Open stream
            stream = await self.host.new_stream(peer_id, ["/mobile/chat/1.0.0"])
            
            # Send message
            message_bytes = message.encode('utf-8')
            message_length = len(message_bytes)
            
            # Write length first
            await stream.write(message_length.to_bytes(4, 'big'))
            # Write message
            await stream.write(message_bytes)
            
            # Close stream
            await stream.close()
            
            logger.info(f"Sent chat message to {peer}: {message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send chat message to {peer}: {e}")
            return False
    
    async def send_file(self, peer: P2PPeer, file_path: str) -> bool:
        """Send a file to a peer using libp2p streams."""
        try:
            if not self.host:
                return False
            
            # Check if file exists
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"File {file_path} does not exist")
                return False
            
            # Create peer ID
            peer_id = ID.from_string(peer.peer_id) if peer.peer_id != "unknown" else None
            if not peer_id:
                logger.error(f"Invalid peer ID for file transfer: {peer.peer_id}")
                return False
            
            # Open stream
            stream = await self.host.new_stream(peer_id, ["/mobile/file/1.0.0"])
            
            # Read file
            with open(file_path_obj, 'rb') as f:
                file_data = f.read()
            
            filename = file_path_obj.name
            filename_bytes = filename.encode('utf-8')
            
            # Send filename length and filename
            await stream.write(len(filename_bytes).to_bytes(4, 'big'))
            await stream.write(filename_bytes)
            
            # Send file size and data
            await stream.write(len(file_data).to_bytes(4, 'big'))
            await stream.write(file_data)
            
            # Close stream
            await stream.close()
            
            logger.info(f"Sent file to {peer}: {filename} ({len(file_data)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send file to {peer}: {e}")
            return False
    
    def add_manual_peer(self, address: str, port: int, display_name: str = "") -> P2PPeer:
        """Manually add a peer (for QR code scanning)."""
        peer_id = f"manual_{address}_{port}"
        peer = P2PPeer(
            peer_id=peer_id,
            address=address,
            port=port,
            display_name=display_name or f"Manual Peer at {address}:{port}"
        )
        
        self.discovered_peers[peer_id] = peer
        
        if self.on_peer_discovered:
            try:
                self.on_peer_discovered(peer)
            except Exception as e:
                logger.error(f"Error in peer discovery callback: {e}")
        
        return peer
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for QR code generation."""
        return {
            'peer_id': self.get_peer_id(),
            'addresses': self.get_listen_addresses(),
            'port': self.port,
            'display_name': f"LibP2P Mobile Device {self.port}"
        }


# Factory function for creating the libp2p mobile host
async def create_libp2p_mobile_host(port: int = 0) -> LibP2PMobileHost:
    """Create and start a libp2p mobile host."""
    host = LibP2PMobileHost(port)
    await host.start()
    return host


# Test function
async def test_libp2p_mobile_host():
    """Test the libp2p mobile host."""
    print("Testing LibP2PMobileHost...")
    
    try:
        # Create host
        host = LibP2PMobileHost(0)
        
        # Set up message handlers
        def on_chat(peer_id: str, message: str):
            print(f"📨 Chat from {peer_id}: {message}")
        
        def on_file(peer_id: str, filename: str, file_data: bytes):
            print(f"📎 File '{filename}' from {peer_id} ({len(file_data)} bytes)")
        
        def on_peer_discovered(peer: P2PPeer):
            print(f"🔍 Discovered peer: {peer}")
        
        host.set_message_handler('chat', on_chat)
        host.set_message_handler('file', on_file)
        host.set_peer_discovery_handler(on_peer_discovered)
        
        # Start host
        await host.start()
        
        print(f"Host started: {host.get_peer_id()}")
        print(f"Addresses: {host.get_listen_addresses()}")
        print("Host is running... (Press Ctrl+C to stop)")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping host...")
            await host.stop()
            
    except Exception as e:
        print(f"Test failed: {e}")
        logger.exception("Test failed")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_libp2p_mobile_host())
