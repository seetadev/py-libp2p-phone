"""
Mobile P2P Host Implementation using asyncio instead of trio
This completely bypasses trio compatibility issues by implementing a pure asyncio solution
"""

import asyncio
import json
import logging
import socket
from typing import Dict, List, Optional, Any, Callable, Tuple
from contextlib import asynccontextmanager
import time
from pathlib import Path

# Core networking imports
import multiaddr
from libp2p.crypto.rsa import create_new_key_pair
from libp2p.peer.id import ID
from libp2p.peer.peerinfo import PeerInfo

# Set up logging
logger = logging.getLogger(__name__)


class AsyncioPeerConnection:
    """Represents a connection to a peer using pure asyncio"""
    
    def __init__(self, peer_id: str, host: str, port: int):
        self.peer_id = peer_id
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.connected = False
        self.last_seen = time.time()
        
    async def connect(self) -> bool:
        """Connect to the peer"""
        try:
            self.reader, self.writer = await asyncio.open_connection(
                self.host, self.port
            )
            self.connected = True
            self.last_seen = time.time()
            logger.info(f"Connected to peer {self.peer_id} at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to peer {self.peer_id}: {e}")
            return False
    
    async def send_message(self, protocol: str, data: bytes) -> bool:
        """Send a message to the peer"""
        if not self.connected or not self.writer:
            return False
            
        try:
            # Create a simple message format: protocol_length|protocol|data_length|data
            protocol_bytes = protocol.encode('utf-8')
            message = (
                len(protocol_bytes).to_bytes(4, 'big') +
                protocol_bytes +
                len(data).to_bytes(4, 'big') +
                data
            )
            
            self.writer.write(message)
            await self.writer.drain()
            self.last_seen = time.time()
            return True
        except Exception as e:
            logger.error(f"Failed to send message to peer {self.peer_id}: {e}")
            await self.disconnect()
            return False
    
    async def receive_message(self) -> Optional[Tuple[str, bytes]]:
        """Receive a message from the peer"""
        if not self.connected or not self.reader:
            return None
            
        try:
            # Read protocol length
            protocol_len_bytes = await self.reader.readexactly(4)
            protocol_len = int.from_bytes(protocol_len_bytes, 'big')
            
            # Read protocol
            protocol_bytes = await self.reader.readexactly(protocol_len)
            protocol = protocol_bytes.decode('utf-8')
            
            # Read data length
            data_len_bytes = await self.reader.readexactly(4)
            data_len = int.from_bytes(data_len_bytes, 'big')
            
            # Read data
            data = await self.reader.readexactly(data_len)
            
            self.last_seen = time.time()
            return protocol, data
        except Exception as e:
            logger.error(f"Failed to receive message from peer {self.peer_id}: {e}")
            await self.disconnect()
            return None
    
    async def disconnect(self):
        """Disconnect from the peer"""
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
        self.connected = False
        self.reader = None
        self.writer = None


class AsyncioMobileHost:
    """
    Pure asyncio implementation of mobile P2P host
    Completely bypasses trio to avoid compatibility issues
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port
        self.peer_id = None
        self.key_pair = None
        self.server = None
        self.running = False
        
        # Peer management
        self.peers: Dict[str, AsyncioPeerConnection] = {}
        self.message_handlers: Dict[str, Callable] = {}
        
        # Protocol handlers
        self.chat_messages: List[Dict] = []
        self.file_transfers: Dict[str, Dict] = {}
        
        # Initialize default protocols
        self._register_default_handlers()
        
    def _register_default_handlers(self):
        """Register default protocol handlers"""
        self.message_handlers["/mobile/chat/1.0.0"] = self._handle_chat_message
        self.message_handlers["/mobile/file/1.0.0"] = self._handle_file_message
        self.message_handlers["/mobile/discovery/1.0.0"] = self._handle_discovery_message
        
    async def _handle_chat_message(self, peer_id: str, data: bytes):
        """Handle incoming chat messages"""
        try:
            message = json.loads(data.decode('utf-8'))
            self.chat_messages.append({
                'from': peer_id,
                'message': message.get('text', ''),
                'timestamp': time.time()
            })
            logger.info(f"📨 Chat from {peer_id[:8]}...: {message.get('text', '')}")
        except Exception as e:
            logger.error(f"Error handling chat message: {e}")
    
    async def _handle_file_message(self, peer_id: str, data: bytes):
        """Handle incoming file messages"""
        try:
            file_data = json.loads(data.decode('utf-8'))
            transfer_id = file_data.get('transfer_id')
            
            if transfer_id:
                self.file_transfers[transfer_id] = {
                    'from': peer_id,
                    'filename': file_data.get('filename'),
                    'size': file_data.get('size'),
                    'data': file_data.get('data'),
                    'timestamp': time.time()
                }
                logger.info(f"📁 File from {peer_id[:8]}...: {file_data.get('filename')}")
        except Exception as e:
            logger.error(f"Error handling file message: {e}")
    
    async def _handle_discovery_message(self, peer_id: str, data: bytes):
        """Handle peer discovery messages"""
        try:
            discovery_data = json.loads(data.decode('utf-8'))
            logger.info(f"🔍 Discovery from {peer_id[:8]}...: {discovery_data}")
        except Exception as e:
            logger.error(f"Error handling discovery message: {e}")
    
    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client connections"""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"New connection from {client_addr}")
        
        try:
            while True:
                # Read protocol length
                protocol_len_bytes = await reader.readexactly(4)
                protocol_len = int.from_bytes(protocol_len_bytes, 'big')
                
                # Read protocol
                protocol_bytes = await reader.readexactly(protocol_len)
                protocol = protocol_bytes.decode('utf-8')
                
                # Read data length
                data_len_bytes = await reader.readexactly(4)
                data_len = int.from_bytes(data_len_bytes, 'big')
                
                # Read data
                data = await reader.readexactly(data_len)
                
                # Handle the message
                if protocol in self.message_handlers:
                    await self.message_handlers[protocol](f"peer_{client_addr[0]}_{client_addr[1]}", data)
                else:
                    logger.warning(f"Unknown protocol: {protocol}")
                    
        except asyncio.IncompleteReadError:
            logger.info(f"Client {client_addr} disconnected")
        except Exception as e:
            logger.error(f"Error handling client {client_addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
    
    async def initialize(self):
        """Initialize the host with identity"""
        # Generate key pair and peer ID
        self.key_pair = create_new_key_pair()
        self.peer_id = ID.from_pubkey(self.key_pair.public_key)
        
        logger.info(f"Generated identity for mobile host")
        logger.info(f"Peer ID: {self.peer_id}")
        
    @asynccontextmanager
    async def run(self):
        """Run the mobile host"""
        if not self.peer_id:
            await self.initialize()
        
        # Start the server
        self.server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port
        )
        
        self.running = True
        
        logger.info(f"Mobile P2P Host started on {self.host}:{self.port}")
        logger.info(f"Peer ID: {self.peer_id}")
        logger.info(f"Listen addresses: ['/ip4/{self.host}/tcp/{self.port}']")
        
        try:
            yield self
        finally:
            # Cleanup
            self.running = False
            
            # Close all peer connections
            for peer in self.peers.values():
                await peer.disconnect()
            self.peers.clear()
            
            # Close server
            if self.server:
                self.server.close()
                await self.server.wait_closed()
            
            logger.info("Mobile P2P Host stopped")
    
    async def connect_to_peer(self, peer_address: str) -> bool:
        """Connect to a peer using a multiaddr-like address"""
        try:
            # Parse address - expect format like /ip4/127.0.0.1/tcp/9002
            parts = peer_address.strip('/').split('/')
            if len(parts) >= 4 and parts[0] == 'ip4' and parts[2] == 'tcp':
                host = parts[1]
                port = int(parts[3])
                
                peer_id = f"peer_{host}_{port}"
                
                if peer_id in self.peers and self.peers[peer_id].connected:
                    logger.info(f"Already connected to peer {peer_id}")
                    return True
                
                # Create and connect to peer
                peer = AsyncioPeerConnection(peer_id, host, port)
                if await peer.connect():
                    self.peers[peer_id] = peer
                    
                    # Send discovery message
                    discovery_data = {
                        'peer_id': str(self.peer_id),
                        'listen_addr': f'/ip4/{self.host}/tcp/{self.port}',
                        'timestamp': time.time()
                    }
                    
                    await peer.send_message(
                        "/mobile/discovery/1.0.0",
                        json.dumps(discovery_data).encode('utf-8')
                    )
                    
                    return True
                else:
                    return False
            else:
                logger.error(f"Invalid peer address format: {peer_address}")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to peer {peer_address}: {e}")
            return False
    
    async def send_chat_message(self, message: str, target_peer: Optional[str] = None) -> bool:
        """Send a chat message to a peer or all peers"""
        chat_data = {
            'text': message,
            'from': str(self.peer_id),
            'timestamp': time.time()
        }
        
        data = json.dumps(chat_data).encode('utf-8')
        success = False
        
        if target_peer and target_peer in self.peers:
            # Send to specific peer
            success = await self.peers[target_peer].send_message("/mobile/chat/1.0.0", data)
        else:
            # Send to all connected peers
            for peer in self.peers.values():
                if peer.connected:
                    result = await peer.send_message("/mobile/chat/1.0.0", data)
                    success = success or result
        
        if success:
            logger.info(f"💬 Sent chat message: {message}")
        
        return success
    
    async def send_file(self, file_path: str, target_peer: Optional[str] = None) -> bool:
        """Send a file to a peer or all peers"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Read file data
            with open(file_path, 'rb') as f:
                file_content = f.read()
            
            # Create file transfer data
            transfer_id = f"transfer_{int(time.time())}_{file_path.name}"
            file_data = {
                'transfer_id': transfer_id,
                'filename': file_path.name,
                'size': len(file_content),
                'data': file_content.hex(),  # Convert to hex for JSON
                'from': str(self.peer_id),
                'timestamp': time.time()
            }
            
            data = json.dumps(file_data).encode('utf-8')
            success = False
            
            if target_peer and target_peer in self.peers:
                # Send to specific peer
                success = await self.peers[target_peer].send_message("/mobile/file/1.0.0", data)
            else:
                # Send to all connected peers
                for peer in self.peers.values():
                    if peer.connected:
                        result = await peer.send_message("/mobile/file/1.0.0", data)
                        success = success or result
            
            if success:
                logger.info(f"📁 Sent file: {file_path.name} ({len(file_content)} bytes)")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending file {file_path}: {e}")
            return False
    
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs"""
        return [peer_id for peer_id, peer in self.peers.items() if peer.connected]
    
    def get_chat_messages(self) -> List[Dict]:
        """Get all received chat messages"""
        return self.chat_messages.copy()
    
    def get_file_transfers(self) -> Dict[str, Dict]:
        """Get all received file transfers"""
        return self.file_transfers.copy()
