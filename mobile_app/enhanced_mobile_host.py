"""
Enhanced Mobile Host with LibP2P Runtime Integration

This module provides a mobile-compatible P2P host that integrates with
the mobile runtime adapter for optimal mobile performance.
"""

import asyncio
import socket
import json
import logging
import threading
from typing import Optional, Dict, List, Callable, Any
from pathlib import Path
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Mobile runtime integration
from mobile.runtime import get_runtime_adapter, AsyncRuntimeAdapter
from mobile.transport import MobileTCPTransport
from mobile.io import MobileAsyncStream

logger = logging.getLogger(__name__)


@dataclass
class P2PPeer:
    """P2P Peer representation."""
    peer_id: str
    address: str
    port: int
    display_name: str


class IP2PHost(ABC):
    """P2P Host interface."""
    
    @abstractmethod
    def get_peer_id(self) -> str:
        pass
    
    @abstractmethod
    def get_listen_addresses(self) -> List[str]:
        pass


class EnhancedMobileHost(IP2PHost):
    """
    Enhanced mobile host that integrates the mobile runtime adapter
    with the proven P2P functionality.
    
    This combines the working socket-based P2P implementation with
    the mobile runtime adapter for better mobile compatibility.
    """
    
    def __init__(self, port: int = 8888):
        self.port = port
        self.peer_id = f"mobile_{socket.gethostname()}_{port}"
        self.display_name = f"Enhanced Mobile Device {port}"
        
        # Mobile runtime integration
        self.runtime_adapter: Optional[AsyncRuntimeAdapter] = None
        self.mobile_transport: Optional[MobileTCPTransport] = None
        
        # Peer management
        self.discovered_peers: Dict[str, P2PPeer] = {}
        self.connections: Dict[str, socket.socket] = {}
        self.mobile_streams: Dict[str, MobileAsyncStream] = {}
        self.running = False
        self.is_running = False
        
        # Event handlers
        self.on_peer_discovered: Optional[Callable[[P2PPeer], None]] = None
        self.on_message_received: Optional[Callable[[str, str, dict], None]] = None
        self.on_file_received: Optional[Callable[[str, str, bytes], None]] = None
        self.on_peer_disconnected: Optional[Callable[[str], None]] = None
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Networking components
        self.server_socket: Optional[socket.socket] = None
        self.discovery_socket: Optional[socket.socket] = None
        self.discovery_task: Optional[asyncio.Task] = None
        
        logger.info(f"Initialized EnhancedMobileHost with peer_id: {self.peer_id}")
    
    async def start(self) -> None:
        """Start the enhanced mobile host with runtime adapter integration."""
        try:
            # Initialize mobile runtime adapter
            self.runtime_adapter = get_runtime_adapter()
            logger.info(f"Using runtime: {self.runtime_adapter.runtime_name}")
            
            # Create mobile transport
            self.mobile_transport = MobileTCPTransport()
            logger.info("Mobile transport initialized")
            
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            
            # Get actual port
            self.port = self.server_socket.getsockname()[1]
            self.peer_id = f"enhanced_mobile_{self.port}"
            
            self.server_socket.listen(5)
            self.is_running = True
            
            # Start server using mobile runtime adapter
            if self.runtime_adapter.use_asyncio:
                # Use asyncio for mobile compatibility
                await self._start_asyncio_server()
            else:
                # Fallback to thread-based server
                await self._start_threaded_server()
            
            # Start peer discovery using mobile-compatible async tasks
            await self._start_mobile_discovery()
            
            logger.info(f"Enhanced mobile host started on port {self.port} with ID {self.peer_id}")
            
        except Exception as e:
            logger.error(f"Failed to start enhanced mobile host: {e}")
            raise
    
    async def _start_asyncio_server(self) -> None:
        """Start server using asyncio for mobile compatibility."""
        async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
            """Handle incoming client connection with mobile stream."""
            try:
                stream = MobileAsyncStream(reader, writer)
                await self._handle_mobile_client(stream)
            except Exception as e:
                logger.debug(f"Mobile client handling failed: {e}")
                if not writer.is_closing():
                    writer.close()
                    await writer.wait_closed()
        
        # Ensure server socket is available
        if self.server_socket is None:
            raise RuntimeError("Server socket not initialized")
        
        # Convert socket to asyncio server
        loop = asyncio.get_running_loop()
        self.server_socket.setblocking(False)
        
        async def accept_connections():
            """Accept connections asynchronously."""
            while self.is_running and self.server_socket:
                try:
                    # Accept connection asynchronously
                    client_socket, addr = await loop.sock_accept(self.server_socket)
                    
                    # Convert to asyncio streams
                    reader, writer = await asyncio.open_connection(sock=client_socket)
                    
                    # Handle client in background task
                    asyncio.create_task(handle_client(reader, writer))
                    
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Error accepting connection: {e}")
                    break
        
        # Start accepting connections
        asyncio.create_task(accept_connections())
        logger.info("Asyncio server started for mobile compatibility")
    
    async def _start_threaded_server(self) -> None:
        """Fallback threaded server for non-mobile environments."""
        def server_loop():
            """Traditional threaded server loop."""
            while self.is_running and self.server_socket:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=asyncio.run,
                        args=(self._handle_socket_client(client_socket, address),),
                        daemon=True
                    )
                    client_thread.start()
                except Exception as e:
                    if self.is_running:
                        logger.error(f"Server error: {e}")
                    break
        
        # Start server in background thread
        server_thread = threading.Thread(target=server_loop, daemon=True)
        server_thread.start()
        logger.info("Threaded server started as fallback")
    
    async def _handle_mobile_client(self, stream: MobileAsyncStream) -> None:
        """Handle client connection using mobile async stream."""
        try:
            while not stream.closed:
                # Read message length first (4 bytes)
                length_data = await stream.read(4)
                if len(length_data) != 4:
                    break
                
                message_length = int.from_bytes(length_data, 'big')
                
                # Read the actual message
                message_data = await stream.read(message_length)
                if len(message_data) != message_length:
                    break
                
                try:
                    message = json.loads(message_data.decode('utf-8'))
                    await self._mobile_process_message(message, stream)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received in mobile stream")
                
        except Exception as e:
            logger.error(f"Mobile client handler error: {e}")
        finally:
            await stream.close()
    
    async def _handle_socket_client(self, client_socket: socket.socket, address) -> None:
        """Handle client using traditional socket (fallback)."""
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    await self._socket_process_message(message, client_socket)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received in socket")
                
        except Exception as e:
            logger.error(f"Socket client handler error: {e}")
        finally:
            client_socket.close()
    
    async def _mobile_process_message(self, message: dict, stream: MobileAsyncStream) -> None:
        """Process message received via mobile stream."""
        msg_type = message.get('type')
        peer_id = message.get('peer_id')
        
        if msg_type == 'chat':
            content = message.get('content')
            handler = self.message_handlers.get('chat')
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(peer_id, content)
                    else:
                        handler(peer_id, content)
                except Exception as e:
                    logger.error(f"Error in mobile chat handler: {e}")
        
        elif msg_type == 'file':
            filename = message.get('filename')
            content = message.get('content', '')
            # Handle base64 encoded files
            import base64
            try:
                file_data = base64.b64decode(content)
            except Exception:
                file_data = content.encode('utf-8') if isinstance(content, str) else content
            
            handler = self.message_handlers.get('file')
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(peer_id, filename, file_data)
                    else:
                        handler(peer_id, filename, file_data)
                except Exception as e:
                    logger.error(f"Error in mobile file handler: {e}")
        
        elif msg_type == 'peer_discovery':
            # Handle peer discovery
            peer_info = message.get('peer_info', {})
            peer = P2PPeer(
                peer_id=peer_info.get('peer_id', peer_id),
                address=peer_info.get('address', 'unknown'),
                port=peer_info.get('port', 0),
                display_name=peer_info.get('display_name', peer_id)
            )
            await self._mobile_add_discovered_peer(peer)
    
    async def _socket_process_message(self, message: dict, client_socket: socket.socket) -> None:
        """Process message received via traditional socket (fallback)."""
        # Similar to mobile process but with socket
        msg_type = message.get('type')
        peer_id = message.get('peer_id')
        
        if msg_type == 'chat':
            content = message.get('content')
            handler = self.message_handlers.get('chat')
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(peer_id, content)
                    else:
                        handler(peer_id, content)
                except Exception as e:
                    logger.error(f"Error in socket chat handler: {e}")
        
        # Similar handling for other message types...
    
    async def _start_mobile_discovery(self) -> None:
        """Start peer discovery using mobile-compatible async tasks."""
        if self.runtime_adapter and self.runtime_adapter.use_asyncio:
            # Use asyncio-based discovery
            self.discovery_task = asyncio.create_task(self._mobile_discovery_task())
        else:
            # Fallback to threaded discovery
            discovery_thread = threading.Thread(target=self._threaded_discovery, daemon=True)
            discovery_thread.start()
        
        logger.info("Mobile-compatible peer discovery started")
    
    async def _mobile_discovery_task(self) -> None:
        """Mobile runtime compatible discovery task."""
        # Set up UDP listener for discovery responses
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discovery_socket.bind(('', self.port + 10000))  # Use a different port for discovery
        discovery_socket.setblocking(False)  # Non-blocking for asyncio
        
        loop = asyncio.get_running_loop()
        
        while self.is_running:
            try:
                # Listen for discovery messages using asyncio
                try:
                    data, addr = await loop.sock_recvfrom(discovery_socket, 1024)
                    try:
                        message = json.loads(data.decode('utf-8'))
                        if message.get('type') == 'peer_discovery':
                            peer_info = message.get('peer_info', {})
                            if peer_info.get('peer_id') != self.peer_id:  # Don't add ourselves
                                peer = P2PPeer(
                                    peer_id=peer_info.get('peer_id', 'unknown'),
                                    address=peer_info.get('address', addr[0]),
                                    port=peer_info.get('port', 0),
                                    display_name=peer_info.get('display_name', 'Unknown Mobile Device')
                                )
                                await self._mobile_add_discovered_peer(peer)
                    except (json.JSONDecodeError, KeyError):
                        pass  # Ignore invalid messages
                except asyncio.TimeoutError:
                    pass  # Continue to send discovery
                
                # Send discovery broadcast every 10 seconds
                broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                discovery_message = {
                    'type': 'peer_discovery',
                    'peer_info': {
                        'peer_id': self.peer_id,
                        'address': '127.0.0.1',  # For local testing
                        'port': self.port,
                        'display_name': f"Enhanced Mobile Device {self.port}"
                    }
                }
                
                message_data = json.dumps(discovery_message).encode('utf-8')
                
                # Broadcast to discovery ports
                for port in range(10000 + 9000, 10000 + 9010):  # Discovery ports for 9000-9009
                    if port != self.port + 10000:  # Don't send to ourselves
                        try:
                            await loop.sock_sendto(broadcast_socket, message_data, ('127.0.0.1', port))
                        except:
                            pass  # Ignore errors for unavailable ports
                
                broadcast_socket.close()
                
                # Wait before next discovery cycle
                await asyncio.sleep(10)  # Discovery every 10 seconds
                
            except Exception as e:
                logger.error(f"Mobile discovery error: {e}")
                await asyncio.sleep(5)
        
        discovery_socket.close()
    
    def _threaded_discovery(self) -> None:
        """Fallback threaded discovery for non-mobile environments."""
        # Similar to original discovery but in thread
        asyncio.run(self._mobile_discovery_task())
    
    async def _mobile_add_discovered_peer(self, peer: P2PPeer) -> None:
        """Add a discovered peer using mobile-compatible async."""
        if peer.peer_id != self.peer_id and peer.peer_id not in self.discovered_peers:
            self.discovered_peers[peer.peer_id] = peer
            logger.info(f"Mobile discovered peer: {peer}")
            
            if self.on_peer_discovered:
                try:
                    if asyncio.iscoroutinefunction(self.on_peer_discovered):
                        await self.on_peer_discovered(peer)
                    else:
                        self.on_peer_discovered(peer)
                except Exception as e:
                    logger.error(f"Error in mobile peer discovery callback: {e}")
    
    async def stop(self) -> None:
        """Stop the enhanced mobile host."""
        try:
            self.is_running = False
            
            # Cancel discovery task
            if self.discovery_task:
                self.discovery_task.cancel()
                try:
                    await self.discovery_task
                except asyncio.CancelledError:
                    pass
            
            # Close all mobile streams
            for stream in self.mobile_streams.values():
                await stream.close()
            self.mobile_streams.clear()
            
            # Close connections
            for conn in self.connections.values():
                conn.close()
            self.connections.clear()
            
            # Close server socket
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            
            logger.info("Enhanced mobile host stopped")
            
        except Exception as e:
            logger.error(f"Error stopping enhanced mobile host: {e}")
    
    # IP2PHost interface implementation
    
    def get_peer_id(self) -> str:
        """Get the peer ID of this host."""
        return self.peer_id
    
    def get_listen_addresses(self) -> List[str]:
        """Get the addresses this host is listening on."""
        return [f"127.0.0.1:{self.port}"]  # For local testing
    
    def get_discovered_peers(self) -> List[P2PPeer]:
        """Get list of discovered peers."""
        return list(self.discovered_peers.values())
    
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs."""
        return list(self.connections.keys())
    
    def set_message_handler(self, handler_type: str, handler: Callable) -> None:
        """Set a message handler for a specific type."""
        self.message_handlers[handler_type] = handler
    
    def set_peer_discovery_handler(self, handler: Callable[[P2PPeer], None]) -> None:
        """Set peer discovery handler."""
        self.on_peer_discovered = handler
    
    def set_peer_disconnected_handler(self, handler: Callable[[str], None]) -> None:
        """Set peer disconnected handler."""
        self.on_peer_disconnected = handler
    
    async def connect_to_peer(self, peer: P2PPeer) -> bool:
        """Connect to a peer using mobile transport if available."""
        try:
            if self.mobile_transport and self.runtime_adapter and self.runtime_adapter.use_asyncio:
                # Try mobile transport for connection
                # Note: For now we'll use socket fallback since multiaddr is not available
                # In a full implementation, we'd create a simple address format
                logger.info(f"Using mobile-compatible transport for {peer}")
                
            # Use socket connection (works with mobile runtime)
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            if self.runtime_adapter and self.runtime_adapter.use_asyncio:
                # Use asyncio for connection
                loop = asyncio.get_running_loop()
                await loop.sock_connect(peer_socket, (peer.address, peer.port))
            else:
                # Fallback to blocking connect
                peer_socket.connect((peer.address, peer.port))
            
            peer_key = f"{peer.address}:{peer.port}"
            self.connections[peer_key] = peer_socket
            
            logger.info(f"Enhanced mobile connected to peer {peer}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to peer {peer}: {e}")
            return False
    
    async def send_chat_message(self, peer: P2PPeer, message: str) -> bool:
        """Send a chat message to a peer."""
        return await self._send_message(peer, 'chat', {'content': message})
    
    async def send_file(self, peer: P2PPeer, file_path: str) -> bool:
        """Send a file to a peer."""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                logger.error(f"File {file_path} does not exist")
                return False
            
            with open(file_path_obj, 'rb') as f:
                file_data = f.read()
            
            # For simplicity, send file as base64 encoded string
            import base64
            file_content = base64.b64encode(file_data).decode('utf-8')
            
            return await self._send_message(peer, 'file', {
                'filename': file_path_obj.name,
                'content': file_content
            })
            
        except Exception as e:
            logger.error(f"Failed to send file: {e}")
            return False
    
    async def _send_message(self, peer: P2PPeer, msg_type: str, data: dict) -> bool:
        """Send a message to a peer using mobile-compatible transport."""
        peer_key = f"{peer.address}:{peer.port}"
        
        # Connect if not already connected
        if peer_key not in self.connections:
            success = await self.connect_to_peer(peer)
            if not success:
                return False
        
        message = {
            'type': msg_type,
            'peer_id': self.peer_id,
            **data
        }
        
        try:
            peer_socket = self.connections[peer_key]
            message_data = json.dumps(message).encode('utf-8')
            
            if self.runtime_adapter and self.runtime_adapter.use_asyncio:
                # Use asyncio for sending
                loop = asyncio.get_running_loop()
                await loop.sock_sendall(peer_socket, message_data)
            else:
                # Fallback to synchronous send
                peer_socket.send(message_data)
                
            logger.info(f"Enhanced mobile sent {msg_type} message to {peer}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send message to {peer}: {e}")
            # Remove broken connection
            if peer_key in self.connections:
                del self.connections[peer_key]
                if self.on_peer_disconnected:
                    self.on_peer_disconnected(peer.peer_id)
            return False
    
    def add_manual_peer(self, address: str, port: int, display_name: str = "") -> P2PPeer:
        """Manually add a peer (for QR code scanning)."""
        peer_id = f"manual_{address}_{port}"
        peer = P2PPeer(
            peer_id=peer_id,
            address=address,
            port=port,
            display_name=display_name or f"Enhanced Device at {address}:{port}"
        )
        
        self.discovered_peers[peer_id] = peer
        
        if self.on_peer_discovered:
            try:
                if asyncio.iscoroutinefunction(self.on_peer_discovered):
                    asyncio.create_task(self.on_peer_discovered(peer))
                else:
                    self.on_peer_discovered(peer)
            except Exception as e:
                logger.error(f"Error in peer discovery callback: {e}")
        
        return peer
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for QR code generation."""
        return {
            'peer_id': self.peer_id,
            'address': '127.0.0.1',  # For local testing
            'port': self.port,
            'display_name': f"Enhanced Mobile Device {self.port}",
            'runtime': self.runtime_adapter.runtime_name if self.runtime_adapter else 'unknown'
        }


# Factory functions

async def create_enhanced_mobile_host(port: int = 0) -> EnhancedMobileHost:
    """Create and start an enhanced mobile host."""
    host = EnhancedMobileHost(port)
    await host.start()
    return host


# Test function
async def test_enhanced_mobile_host():
    """Test the enhanced mobile host."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Testing EnhancedMobileHost...")
    
    try:
        # Create host
        host = await create_enhanced_mobile_host(port=9200)
        
        # Set up message handlers
        def on_chat(peer_id: str, message: str):
            print(f"📨 Enhanced chat from {peer_id}: {message}")
        
        def on_file(peer_id: str, filename: str, file_data: bytes):
            print(f"📎 Enhanced file '{filename}' from {peer_id} ({len(file_data)} bytes)")
        
        def on_peer_discovered(peer: P2PPeer):
            print(f"🔍 Enhanced discovered peer: {peer}")
        
        host.set_message_handler('chat', on_chat)
        host.set_message_handler('file', on_file)
        host.set_peer_discovery_handler(on_peer_discovered)
        
        print(f"Enhanced host started: {host.get_peer_id()}")
        print(f"Runtime: {host.runtime_adapter.runtime_name if host.runtime_adapter else 'unknown'}")
        print(f"Addresses: {host.get_listen_addresses()}")
        print("Enhanced host is running... (Press Ctrl+C to stop)")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping enhanced host...")
            await host.stop()
    
    except Exception as e:
        logger.error(f"Enhanced test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(test_enhanced_mobile_host())
