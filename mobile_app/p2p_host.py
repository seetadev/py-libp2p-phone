"""
Enhanced P2P Host Implementation for Mobile Application

This module provides an enhanced P2P networking implementation that integrates 
with the mobile runtime adapter while maintaining robust P2P functionality.
"""

import asyncio
import socket
import json
import logging
import threading
from typing import Optional, Dict, List, Callable, Any
from pathlib import Path

# Mobile runtime integration
try:
    from mobile.runtime import get_runtime_adapter, AsyncRuntimeAdapter
    MOBILE_RUNTIME_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("Mobile runtime adapter available - using mobile-compatible implementation")
except ImportError:
    MOBILE_RUNTIME_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.info("Mobile runtime adapter not available - using basic implementation")

from mobile_app.mobile_abc import IP2PHost, P2PPeer


class RealMobileHost(IP2PHost):
    """Real P2P networking implementation for mobile apps with mobile runtime integration."""
    
    def __init__(self, port: int = 8888):
        self.port = port
        self.peer_id = f"mobile_{socket.gethostname()}_{port}"
        self.display_name = f"Mobile Device {port}"
        
        # Initialize mobile runtime adapter if available
        self.runtime_adapter: Optional[AsyncRuntimeAdapter] = None
        if MOBILE_RUNTIME_AVAILABLE:
            try:
                self.runtime_adapter = get_runtime_adapter()
                logger.info(f"Using mobile runtime: {self.runtime_adapter.runtime_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize mobile runtime adapter: {e}")
        
        # Peer management
        self.discovered_peers: Dict[str, P2PPeer] = {}
        self.connections: Dict[str, socket.socket] = {}
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
        self.discovery_thread: Optional[threading.Thread] = None
        
        logger.info(f"Initialized RealMobileHost with peer_id: {self.peer_id}")
        if self.runtime_adapter:
            logger.info(f"Mobile runtime compatibility: {self.runtime_adapter.use_asyncio}")
    
    async def start(self):
        """Start the mobile host with mobile runtime integration."""
        try:
            logger.info("Starting enhanced mobile P2P host...")
            
            # Use mobile runtime adapter for task coordination if available
            if self.runtime_adapter:
                # Start with mobile runtime coordination
                await self._start_with_mobile_runtime()
            else:
                # Start with basic implementation
                await self._start_basic()
                
        except Exception as e:
            logger.error(f"Failed to start mobile host: {e}")
            raise
    
    async def _start_with_mobile_runtime(self):
        """Start the host using mobile runtime adapter."""
        if not self.runtime_adapter:
            logger.error("Mobile runtime adapter not available")
            await self._start_basic()
            return
            
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        
        # Get actual port
        self.port = self.server_socket.getsockname()[1]
        self.peer_id = f"mobile_{self.port}"
        
        self.server_socket.listen(5)
        self.is_running = True
        
        # Use mobile runtime nursery for task coordination
        async with self.runtime_adapter.create_nursery() as nursery:
            # Start server task
            await nursery.start_soon(self._mobile_server_task)
            
            # Start discovery task
            await nursery.start_soon(self._mobile_discovery_task)
            
            logger.info(f"Mobile host started on port {self.port} with mobile runtime")
    
    async def _start_basic(self):
        """Start the host using basic implementation."""
        # Create server socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', self.port))
        
        # Get actual port
        self.port = self.server_socket.getsockname()[1]
        self.peer_id = f"mobile_{self.port}"
        
        self.server_socket.listen(5)
        self.is_running = True
        
        # Start server in background thread
        server_thread = threading.Thread(target=self._server_loop, daemon=True)
        server_thread.start()
        
        logger.info(f"Mobile host started on port {self.port} with basic runtime")
        
        # Start peer discovery
        discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True)
        discovery_thread.start()
    
    async def _mobile_server_task(self):
        """Mobile runtime compatible server task."""
        while self.is_running and self.server_socket:
            try:
                # Use asyncio-compatible socket operations
                self.server_socket.settimeout(1.0)
                try:
                    client_socket, address = self.server_socket.accept()
                    # Handle client in separate task
                    if self.runtime_adapter and self.runtime_adapter.use_asyncio:
                        # Create asyncio task for client handling
                        asyncio.create_task(self._mobile_handle_client(client_socket, address))
                    else:
                        # Use thread for client handling
                        client_thread = threading.Thread(
                            target=self._handle_client,
                            args=(client_socket, address),
                            daemon=True
                        )
                        client_thread.start()
                except socket.timeout:
                    continue
            except Exception as e:
                if self.is_running:
                    logger.error(f"Mobile server task error: {e}")
                break
    
    async def _mobile_handle_client(self, client_socket: socket.socket, address):
        """Mobile runtime compatible client handler."""
        try:
            # Set socket to non-blocking for asyncio compatibility
            client_socket.setblocking(False)
            
            while True:
                try:
                    # Use asyncio for non-blocking read
                    data = await asyncio.get_event_loop().sock_recv(client_socket, 4096)
                    if not data:
                        break
                    
                    message = json.loads(data.decode('utf-8'))
                    await self._mobile_process_message(message, client_socket)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                except Exception as e:
                    logger.error(f"Client handler error: {e}")
                    break
                
        except Exception as e:
            logger.error(f"Mobile client handler error: {e}")
        finally:
            client_socket.close()
    
    async def _mobile_process_message(self, message: dict, client_socket: socket.socket):
        """Mobile runtime compatible message processor."""
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
                    logger.error(f"Error in chat handler: {e}")
        
        elif msg_type == 'file':
            filename = message.get('filename')
            content = message.get('content', '')
            file_data = content.encode('utf-8') if isinstance(content, str) else content
            handler = self.message_handlers.get('file')
            if handler:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(peer_id, filename, file_data)
                    else:
                        handler(peer_id, filename, file_data)
                except Exception as e:
                    logger.error(f"Error in file handler: {e}")
        
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
    
    async def _mobile_discovery_task(self):
        """Mobile runtime compatible discovery task."""
        # Set up UDP listener for discovery responses
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discovery_socket.bind(('', self.port + 10000))  # Use a different port for discovery
        discovery_socket.setblocking(False)  # Non-blocking for asyncio
        
        while self.is_running:
            try:
                # Listen for discovery messages using asyncio
                try:
                    data, addr = await asyncio.get_event_loop().sock_recvfrom(discovery_socket, 1024)
                    try:
                        message = json.loads(data.decode('utf-8'))
                        if message.get('type') == 'peer_discovery':
                            peer_info = message.get('peer_info', {})
                            if peer_info.get('peer_id') != self.peer_id:  # Don't add ourselves
                                peer = P2PPeer(
                                    peer_id=peer_info.get('peer_id', 'unknown'),
                                    address=peer_info.get('address', addr[0]),
                                    port=peer_info.get('port', 0),
                                    display_name=peer_info.get('display_name', 'Unknown Device')
                                )
                                await self._mobile_add_discovered_peer(peer)
                    except (json.JSONDecodeError, KeyError):
                        pass  # Ignore invalid messages
                except BlockingIOError:
                    pass  # No data available
                
                # Send discovery broadcast every 10 seconds
                broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                discovery_message = {
                    'type': 'peer_discovery',
                    'peer_info': {
                        'peer_id': self.peer_id,
                        'address': '127.0.0.1',  # For local testing
                        'port': self.port,
                        'display_name': f"Mobile Device {self.port}"
                    }
                }
                
                message_data = json.dumps(discovery_message).encode('utf-8')
                
                # Broadcast to discovery ports
                for port in range(10000 + 9000, 10000 + 9010):  # Discovery ports for 9000-9009
                    if port != self.port + 10000:  # Don't send to ourselves
                        try:
                            await asyncio.get_event_loop().sock_sendto(broadcast_socket, message_data, ('127.0.0.1', port))
                        except:
                            pass  # Ignore errors for unavailable ports
                
                broadcast_socket.close()
                
                # Wait before next discovery cycle
                await asyncio.sleep(10)  # Discovery every 10 seconds
                
            except Exception as e:
                logger.error(f"Mobile discovery error: {e}")
                await asyncio.sleep(5)
        
        discovery_socket.close()
    
    async def _mobile_add_discovered_peer(self, peer: P2PPeer):
        """Mobile runtime compatible peer discovery handler."""
        if peer.peer_id != self.peer_id and peer.peer_id not in self.discovered_peers:
            self.discovered_peers[peer.peer_id] = peer
            logger.info(f"Discovered peer: {peer}")
            
            if self.on_peer_discovered:
                try:
                    if asyncio.iscoroutinefunction(self.on_peer_discovered):
                        await self.on_peer_discovered(peer)
                    else:
                        self.on_peer_discovered(peer)
                except Exception as e:
                    logger.error(f"Error in peer discovery callback: {e}")
    
    def _server_loop(self):
        """Server loop to accept connections."""
        while self.is_running and self.server_socket:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.is_running:
                    logger.error(f"Server error: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, address):
        """Handle incoming client connection."""
        try:
            while True:
                data = client_socket.recv(4096)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self._process_message(message, client_socket)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: dict, client_socket: socket.socket):
        """Process incoming message."""
        msg_type = message.get('type')
        peer_id = message.get('peer_id')
        
        if msg_type == 'chat':
            content = message.get('content')
            handler = self.message_handlers.get('chat')
            if handler:
                try:
                    handler(peer_id, content)
                except Exception as e:
                    logger.error(f"Error in chat handler: {e}")
        
        elif msg_type == 'file':
            filename = message.get('filename')
            content = message.get('content', '')
            file_data = content.encode('utf-8') if isinstance(content, str) else content
            handler = self.message_handlers.get('file')
            if handler:
                try:
                    handler(peer_id, filename, file_data)
                except Exception as e:
                    logger.error(f"Error in file handler: {e}")
        
        elif msg_type == 'peer_discovery':
            # Handle peer discovery
            peer_info = message.get('peer_info', {})
            peer = P2PPeer(
                peer_id=peer_info.get('peer_id', peer_id),
                address=peer_info.get('address', 'unknown'),
                port=peer_info.get('port', 0),
                display_name=peer_info.get('display_name', peer_id)
            )
            self._add_discovered_peer(peer)
    
    def _discovery_loop(self):
        """Simple peer discovery using broadcast."""
        # Set up UDP listener for discovery responses
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        discovery_socket.bind(('', self.port + 10000))  # Use a different port for discovery
        discovery_socket.settimeout(1.0)  # Non-blocking with timeout
        
        while self.is_running:
            try:
                # Listen for discovery messages
                try:
                    data, addr = discovery_socket.recvfrom(1024)
                    try:
                        message = json.loads(data.decode('utf-8'))
                        if message.get('type') == 'peer_discovery':
                            peer_info = message.get('peer_info', {})
                            if peer_info.get('peer_id') != self.peer_id:  # Don't add ourselves
                                peer = P2PPeer(
                                    peer_id=peer_info.get('peer_id', 'unknown'),
                                    address=peer_info.get('address', addr[0]),
                                    port=peer_info.get('port', 0),
                                    display_name=peer_info.get('display_name', 'Unknown Device')
                                )
                                self._add_discovered_peer(peer)
                    except (json.JSONDecodeError, KeyError):
                        pass  # Ignore invalid messages
                except socket.timeout:
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
                        'display_name': f"Mobile Device {self.port}"
                    }
                }
                
                message_data = json.dumps(discovery_message).encode('utf-8')
                
                # Broadcast to discovery ports
                for port in range(10000 + 9000, 10000 + 9010):  # Discovery ports for 9000-9009
                    if port != self.port + 10000:  # Don't send to ourselves
                        try:
                            broadcast_socket.sendto(message_data, ('127.0.0.1', port))
                        except:
                            pass  # Ignore errors for unavailable ports
                
                broadcast_socket.close()
                
                # Wait before next discovery cycle
                threading.Event().wait(10)  # Discovery every 10 seconds
                
            except Exception as e:
                logger.error(f"Discovery error: {e}")
                threading.Event().wait(5)
        
        discovery_socket.close()
    
    def _add_discovered_peer(self, peer: P2PPeer):
        """Add a discovered peer."""
        if peer.peer_id != self.peer_id and peer.peer_id not in self.discovered_peers:
            self.discovered_peers[peer.peer_id] = peer
            logger.info(f"Discovered peer: {peer}")
            
            if self.on_peer_discovered:
                try:
                    self.on_peer_discovered(peer)
                except Exception as e:
                    logger.error(f"Error in peer discovery callback: {e}")
    
    async def stop(self):
        """Stop the mobile host."""
        self.is_running = False
        
        # Close connections
        for conn in self.connections.values():
            conn.close()
        self.connections.clear()
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        logger.info("Mobile host stopped")
    
    def get_peer_id(self) -> str:
        """Get the peer ID."""
        return self.peer_id
    
    def get_listen_addresses(self) -> List[str]:
        """Get listen addresses."""
        return [f"127.0.0.1:{self.port}"]  # For local testing
    
    def get_discovered_peers(self) -> List[P2PPeer]:
        """Get discovered peers."""
        return list(self.discovered_peers.values())
    
    def get_connected_peers(self) -> List[str]:
        """Get connected peer IDs."""
        return list(self.connections.keys())
    
    def set_message_handler(self, handler_type: str, handler: Callable):
        """Set a message handler."""
        self.message_handlers[handler_type] = handler
    
    def set_peer_discovery_handler(self, handler: Callable[[P2PPeer], None]):
        """Set peer discovery handler."""
        self.on_peer_discovered = handler
    
    def set_peer_disconnected_handler(self, handler: Callable[[str], None]):
        """Set peer disconnected handler."""
        self.on_peer_disconnected = handler
    
    async def connect_to_peer(self, peer: P2PPeer) -> bool:
        """Connect to a peer."""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer.address, peer.port))
            
            peer_key = f"{peer.address}:{peer.port}"
            self.connections[peer_key] = peer_socket
            
            logger.info(f"Connected to peer {peer}")
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
        """Send a message to a peer."""
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
            peer_socket.send(message_data)
            logger.info(f"Sent {msg_type} message to {peer}")
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
            display_name=display_name or f"Device at {address}:{port}"
        )
        
        self.discovered_peers[peer_id] = peer
        
        if self.on_peer_discovered:
            try:
                self.on_peer_discovered(peer)
            except Exception as e:
                logger.error(f"Error in peer discovery callback: {e}")
        
        return peer
    
    def get_connection_info(self) -> dict:
        """Get connection information for QR code generation."""
        return {
            'peer_id': self.peer_id,
            'address': '127.0.0.1',  # For local testing
            'port': self.port,
            'display_name': f"Mobile Device {self.port}"
        }


# Factory function for creating the real mobile host
async def create_mobile_host(port: int = 0) -> RealMobileHost:
    """Create and start a mobile host."""
    host = RealMobileHost(port)
    await host.start()
    return host


# Test function
def test_real_mobile_host():
    """Test the real mobile host."""
    print("Testing RealMobileHost...")
    
    async def run_test():
        try:
            # Create host
            host = RealMobileHost(8002)
            
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
    
    asyncio.run(run_test())


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_real_mobile_host()
