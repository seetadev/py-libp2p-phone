#!/usr/bin/env python3
"""
A more robust LibP2P host for mobile applications, using the official
`new_host` constructor for a more complete and compliant implementation.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Callable, Awaitable

# Ensure project root is in path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from libp2p import new_host
from libp2p.crypto.key import KeyPair
from libp2p.crypto.rsa import generate_new_key_pair
from libp2p.network.stream.net_stream_interface import INetStream
from libp2p.peer.id import ID as PeerID
from libp2p.peer.peerinfo import PeerInfo
from libp2p.typing import TProtocol
from multiaddr import Multiaddr

from mobile.runtime import get_runtime_adapter, AsyncRuntimeAdapter

# Protocol definitions
CHAT_PROTOCOL = TProtocol("/mobile/chat/1.0.0")
FILE_PROTOCOL = TProtocol("/mobile/file/1.0.0")

logger = logging.getLogger(__name__)

@dataclass
class P2PPeer:
    """Represents a discovered or connected peer."""
    peer_id: str
    address: str
    port: int
    display_name: str

class LibP2PMobileHost:
    """
    Manages a libp2p host, including setup, peer discovery, and communication.
    This version uses the standard `libp2p.new_host` function.
    """

    def __init__(self, port: int = 0, force_asyncio: bool = False):
        self.port = port
        self.force_asyncio = force_asyncio
        self.host = None
        self.key_pair: KeyPair = generate_new_key_pair()
        self.is_running = False
        
        self.runtime: AsyncRuntimeAdapter = get_runtime_adapter(force_asyncio=self.force_asyncio)
        
        # Handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.peer_discovery_handler: Optional[Callable[[P2PPeer], None]] = None
        self.peer_disconnected_handler: Optional[Callable[[str], None]] = None
        
        # Peer tracking
        self.connected_peers: Dict[PeerID, INetStream] = {}
        self.discovered_peers: Dict[str, P2PPeer] = {}

    async def start(self):
        """
        Prepare the host but do not start listening yet.
        This sets up the host object with its configuration.
        """
        if self.host:
            logger.warning("Host already started.")
            return

        listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{self.port}")
        
        # Use the runtime adapter to select the async backend
        self.host = await new_host(
            listen_addrs=[listen_addr],
            identity=self.key_pair,
            # The `new_host` function will use the currently running event loop,
            # which is determined by our runtime adapter's context.
        )
        
        # Set up protocol handlers
        self.host.set_stream_handler(CHAT_PROTOCOL, self._chat_stream_handler)
        self.host.set_stream_handler(FILE_PROTOCOL, self._file_stream_handler)
        
        logger.info(f"Host prepared with ID: {self.host.get_id().to_string()}")
        logger.info(f"Will listen on: {listen_addr}")

    def run(self):
        """
        Returns an async context manager to run the host.
        This will start the host's network listeners and manage its lifecycle.
        """
        if not self.host:
            raise RuntimeError("Host has not been started. Call start() first.")
        
        return self.host.run(
            started_callback=self._on_host_started,
            finished_callback=self._on_host_finished
        )

    async def _on_host_started(self):
        """Callback when the host has started listening."""
        self.is_running = True
        logger.info("Host is now running and listening for connections.")
        for addr in self.host.get_listen_addrs():
            logger.info(f"  - {addr.to_string()}/p2p/{self.host.get_id().to_string()}")

    async def _on_host_finished(self):
        """Callback when the host has stopped."""
        self.is_running = False
        logger.info("Host has stopped.")

    async def stop(self):
        """Stop the libp2p host."""
        if self.host and self.is_running:
            await self.host.close()
            self.host = None
            self.is_running = False
            logger.info("Host stopped and closed.")

    # --- Peer and Connection Management ---

    async def dial_peer_info(self, peer_info: PeerInfo) -> bool:
        """Connect to a peer using their PeerInfo."""
        if not self.host:
            return False
        try:
            await self.host.connect(peer_info)
            logger.info(f"Successfully connected to {peer_info.peer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {peer_info.peer_id}: {e}")
            return False

    # --- Information Retrieval ---

    def get_peer_id(self) -> Optional[str]:
        """Get the host's peer ID as a string."""
        return self.host.get_id().to_string() if self.host else None

    def get_listen_addresses(self) -> List[str]:
        """Get the addresses the host is listening on."""
        if not self.host or not self.is_running:
            return []
        return [addr.to_string() for addr in self.host.get_listen_addrs()]

    def get_connection_info(self) -> str:
        """Get a shareable connection string (full multiaddr)."""
        if not self.host or not self.is_running:
            return "Host not running."
        
        addrs = self.get_listen_addresses()
        if not addrs:
            return "No listen addresses available."
            
        # Prefer non-local addresses if available
        public_addr = next((a for a in addrs if "127.0.0.1" not in a), addrs[0])
        return f"{public_addr}/p2p/{self.get_peer_id()}"

    def get_connected_peers(self) -> List[P2PPeer]:
        """Get a list of currently connected peers."""
        return [self.discovered_peers[p.to_string()] for p in self.connected_peers.keys()]

    def get_discovered_peers(self) -> List[P2PPeer]:
        """Get a list of all discovered peers."""
        return list(self.discovered_peers.values())

    # --- Protocol Handlers ---

    async def _chat_stream_handler(self, stream: INetStream):
        """Handle incoming chat messages."""
        peer_id = stream.muxed_conn.peer_id.to_string()
        logger.info(f"Chat stream opened from {peer_id}")
        
        try:
            data = await stream.read()
            message = data.decode('utf-8')
            
            if 'chat' in self.message_handlers:
                self.message_handlers['chat'](peer_id, message)
                
        except Exception as e:
            logger.error(f"Error in chat stream with {peer_id}: {e}")
        finally:
            await stream.close()

    async def _file_stream_handler(self, stream: INetStream):
        """Handle incoming file transfers."""
        peer_id = stream.muxed_conn.peer_id.to_string()
        logger.info(f"File stream opened from {peer_id}")
        
        try:
            # Protocol: filename_len (4 bytes) | filename (utf-8) | file_data
            header = await stream.read(4)
            filename_len = int.from_bytes(header, 'big')
            
            filename_bytes = await stream.read(filename_len)
            filename = filename_bytes.decode('utf-8')
            
            file_data = await stream.read()
            
            if 'file' in self.message_handlers:
                # Pass data as hex to avoid issues with binary data in some contexts
                self.message_handlers['file'](peer_id, filename, file_data.hex())
                
        except Exception as e:
            logger.error(f"Error in file stream with {peer_id}: {e}")
        finally:
            await stream.close()

    # --- Public Methods for Sending Data ---

    async def send_chat_message(self, peer: P2PPeer, message: str) -> bool:
        """Send a chat message to a peer."""
        if not self.host:
            return False
        try:
            peer_id = PeerID.from_string(peer.peer_id)
            stream = await self.host.new_stream(peer_id, [CHAT_PROTOCOL])
            await stream.write(message.encode('utf-8'))
            await stream.close()
            logger.info(f"Chat message sent to {peer.peer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send chat message to {peer.peer_id}: {e}")
            return False

    async def send_file(self, peer: P2PPeer, file_path: str) -> bool:
        """Send a file to a peer."""
        if not self.host:
            return False
        try:
            p = Path(file_path)
            if not p.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            filename_bytes = p.name.encode('utf-8')
            filename_len_bytes = len(filename_bytes).to_bytes(4, 'big')
            file_data = p.read_bytes()
            
            peer_id = PeerID.from_string(peer.peer_id)
            stream = await self.host.new_stream(peer_id, [FILE_PROTOCOL])
            
            await stream.write(filename_len_bytes)
            await stream.write(filename_bytes)
            await stream.write(file_data)
            
            await stream.close()
            logger.info(f"File '{p.name}' sent to {peer.peer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send file to {peer.peer_id}: {e}")
            return False

    # --- Handler Registration ---

    def set_message_handler(self, protocol: str, handler: Callable):
        """Set a handler for a specific message protocol."""
        self.message_handlers[protocol] = handler

    def set_peer_discovery_handler(self, handler: Callable[[P2PPeer], None]):
        """Set a handler for when a peer is discovered."""
        self.peer_discovery_handler = handler

    def set_peer_disconnected_handler(self, handler: Callable[[str], None]):
        """Set a handler for when a peer disconnects."""
        self.peer_disconnected_handler = handler
