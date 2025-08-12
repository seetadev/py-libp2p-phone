"""
P2P Mobile Interfaces

Simple interfaces for the mobile P2P application.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Callable, Dict, Any


class P2PPeer:
    """Represents a peer in the P2P network."""
    
    def __init__(self, peer_id: str, address: str, port: int, display_name: str = ""):
        self.peer_id = peer_id
        self.address = address
        self.port = port
        self.display_name = display_name or peer_id
    
    def __str__(self):
        return f"{self.display_name} ({self.address}:{self.port})"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'peer_id': self.peer_id,
            'address': self.address,
            'port': self.port,
            'display_name': self.display_name
        }


class IP2PHost(ABC):
    """Interface for a P2P host."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the P2P host."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the P2P host."""
        pass
    
    @abstractmethod
    def get_peer_id(self) -> str:
        """Get the peer ID of this host."""
        pass
    
    @abstractmethod
    def get_listen_addresses(self) -> List[str]:
        """Get the addresses this host is listening on."""
        pass
    
    @abstractmethod
    def get_discovered_peers(self) -> List[P2PPeer]:
        """Get list of discovered peers."""
        pass
    
    @abstractmethod
    def get_connected_peers(self) -> List[str]:
        """Get list of connected peer IDs."""
        pass
    
    @abstractmethod
    def set_message_handler(self, handler_type: str, handler: Callable) -> None:
        """Set a message handler for a specific type."""
        pass
    
    @abstractmethod
    async def connect_to_peer(self, peer: P2PPeer) -> bool:
        """Connect to a peer."""
        pass
    
    @abstractmethod
    async def send_chat_message(self, peer: P2PPeer, message: str) -> bool:
        """Send a chat message to a peer."""
        pass
    
    @abstractmethod
    async def send_file(self, peer: P2PPeer, file_path: str) -> bool:
        """Send a file to a peer."""
        pass
    
    @abstractmethod
    def add_manual_peer(self, address: str, port: int, display_name: str = "") -> P2PPeer:
        """Manually add a peer (for QR code scanning)."""
        pass
    
    @abstractmethod
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information for QR code generation."""
        pass
