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

from libp2p import new_host, generate_new_rsa_identity
from libp2p.crypto.keys import KeyPair
from libp2p.peer.id import ID as PeerID
from libp2p.peer.peerinfo import PeerInfo
from libp2p.abc import INetStream
from libp2p.custom_types import TProtocol
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
        # Generate a keypair using the repo helper
        self.key_pair: KeyPair = generate_new_rsa_identity()
        self.is_running = False
        
        self.runtime: AsyncRuntimeAdapter = get_runtime_adapter(force_asyncio=self.force_asyncio)
        
        # Handlers
        self.message_handlers: Dict[str, Callable] = {}
        self.peer_discovery_handler: Optional[Callable[[P2PPeer], None]] = None
        self.peer_disconnected_handler: Optional[Callable[[str], None]] = None
        
        # Peer tracking
        self.connected_peers: Dict[PeerID, INetStream] = {}
        self.discovered_peers: Dict[str, P2PPeer] = {}
        # Listen addresses to use when running the host
        self.listen_addrs: List[Multiaddr] = []

    async def connect_to_peer(self, address: str, port: int) -> bool:
        """Connect to a peer by address and port."""
        if not self.host:
            logger.error("Host not started")
            return False
        
        try:
            # Create a temporary peer ID for this manual connection
            manual_peer_id = f"manual_{address}_{port}"
            
            # Add this to discovered peers for tracking
            if manual_peer_id not in self.discovered_peers:
                self.discovered_peers[manual_peer_id] = P2PPeer(
                    peer_id=manual_peer_id,
                    address=address,
                    port=port,
                    display_name=f"Manual {address}:{port}"
                )
            
            logger.info(f"Attempting to connect to peer at {address}:{port}")
            
            # Try to connect using multiaddr
            maddr = Multiaddr(f"/ip4/{address}/tcp/{port}")
            
            # We need to discover the actual peer ID first via a bootstrap connection
            logger.info("Attempting connection to manual peer - discovery needed")
            logger.info(f"Attempting to connect to {maddr}")
            
            # Direct connection without peer ID (will fail but helps with discovery)
            try:
                # Use dial method to try connecting
                await self.host.get_network().dial_peer(maddr)
                logger.info(f"Successfully connected to {address}:{port}")
                return True
            except Exception as e:
                logger.error(f"Connection attempt failed: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Failed to connect to peer {address}:{port}: {e}")
            return False

    async def start(self):
        """
        Start the host and begin listening for connections.
        """
        if self.host:
            logger.warning("Host already started.")
            return

        logger.info(f"Using runtime: {self.runtime.runtime_name}")

        try:
            # Prepare listen address and create the host (non-blocking)
            listen_addr = Multiaddr(f"/ip4/0.0.0.0/tcp/{self.port}")
            self.listen_addrs = [listen_addr]

            # Create host instance (synchronous in this repo API)
            self.host = new_host(key_pair=self.key_pair, listen_addrs=self.listen_addrs)

            # Register protocol handlers (BasicHost handles negotiation)
            self.host.set_stream_handler(CHAT_PROTOCOL, self._chat_stream_handler)
            self.host.set_stream_handler(FILE_PROTOCOL, self._file_stream_handler)

            logger.info("LibP2P host prepared; call run() to start listening")
            logger.info(f"Peer ID (prepared): {str(self.host.get_id())}")
            self.is_running = False

        except Exception as e:
            logger.error(f"Failed to start LibP2P mobile host: {e}")
            if self.host:
                try:
                    await self.host.close()
                except Exception:
                    pass
                self.host = None
            raise

    def run(self):
        """
        Returns an async context manager to run the host.
        This will start the host's network listeners and manage its lifecycle.
        """
        if not self.host:
            raise RuntimeError("Host has not been started. Call start() first.")

        # Return the host's async context manager which will start listeners
        return self.host.run(self.listen_addrs)

    async def _on_host_started(self):
        """Callback when the host has started listening."""
        # Note: BasicHost doesn't call this callback. Keep for compatibility.
        self.is_running = True
        try:
            addrs = [str(a) for a in self.host.get_addrs()]
        except Exception:
            addrs = []
        logger.info(f"Host is now running. listen_addrs={addrs}")

    async def _on_host_finished(self):
        """Callback when the host has stopped."""
        self.is_running = False
        logger.info("Host has stopped.")

    async def stop(self):
        """Stop the libp2p host."""
        if self.host:
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
        if not self.host:
            return []
        try:
            return [str(a) for a in self.host.get_addrs()]
        except Exception:
            return []

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
        # Map connected peer IDs to P2PPeer entries where possible
        connected = []
        try:
            live_ids = self.host.get_connected_peers()
        except Exception:
            live_ids = []
        for pid in live_ids:
            pid_str = str(pid)
            if pid_str in self.discovered_peers:
                connected.append(self.discovered_peers[pid_str])
            else:
                connected.append(P2PPeer(peer_id=pid_str, address="", port=0, display_name=pid_str))
        return connected

    def get_discovered_peers(self) -> List[P2PPeer]:
        """Get a list of all discovered peers."""
        return list(self.discovered_peers.values())

    # --- Protocol Handlers ---

    async def send_chat_message(self, peer: P2PPeer, message: str) -> bool:
        """Send a chat message to a peer."""
        if not self.host:
            return False
        try:
            # Convert peer id string to ID if necessary
            if isinstance(peer.peer_id, str):
                peer_id = PeerID.from_base58(peer.peer_id)
            else:
                peer_id = peer.peer_id
            stream = await self.host.new_stream(peer_id, [CHAT_PROTOCOL])
            await stream.write(message.encode('utf-8'))
            await stream.close()
            logger.info(f"Chat message sent to {peer.peer_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to send chat message to {peer.peer_id}: {e}")
            return False

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
            
            peer_id = PeerID.from_base58(peer.peer_id)
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
