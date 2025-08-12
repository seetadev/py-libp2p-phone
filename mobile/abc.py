"""
Mobile-specific interfaces for libp2p compatibility.

This module provides abstract base classes and interfaces needed for mobile
libp2p implementation without depending on external libp2p packages.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Optional, Sequence, List
from collections.abc import Awaitable

from multiaddr import Multiaddr


class IListener(ABC):
    """Interface for network listeners."""
    
    @abstractmethod
    async def listen(self, maddr: Multiaddr, nursery: Any) -> bool:
        """Start listening on the given multiaddress."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the listener."""
        pass
    
    @abstractmethod
    def get_addresses(self) -> List[Multiaddr]:
        """Get the addresses this listener is bound to."""
        pass


class IRawConnection(ABC):
    """Interface for raw network connections."""
    
    @abstractmethod
    async def read(self, n: int = -1) -> bytes:
        """Read data from the connection."""
        pass
    
    @abstractmethod
    async def write(self, data: bytes) -> None:
        """Write data to the connection."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the connection."""
        pass
    
    @abstractmethod
    def get_remote_addr(self) -> Multiaddr:
        """Get the remote address."""
        pass


class ITransport(ABC):
    """Interface for transport implementations."""
    
    @abstractmethod
    async def dial(self, maddr: Multiaddr) -> IRawConnection:
        """Dial a connection to the given multiaddress."""
        pass
    
    @abstractmethod
    def create_listener(self, handler: Callable) -> IListener:
        """Create a listener with the given handler."""
        pass
    
    @abstractmethod
    def can_dial(self, maddr: Multiaddr) -> bool:
        """Check if this transport can dial the given multiaddress."""
        pass


class IHost(ABC):
    """Interface for libp2p host."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start the host."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the host."""
        pass
    
    @abstractmethod
    def get_id(self) -> str:
        """Get the peer ID."""
        pass
    
    @abstractmethod
    def get_addrs(self) -> List[Multiaddr]:
        """Get listen addresses."""
        pass
    
    @abstractmethod
    async def connect(self, peer_info: Any) -> None:
        """Connect to a peer."""
        pass
    
    @abstractmethod
    async def new_stream(self, peer_id: Any, protocols: List[str]) -> Any:
        """Open a new stream to a peer."""
        pass
    
    @abstractmethod
    def set_stream_handler(self, protocol: str, handler: Callable) -> None:
        """Set a stream handler for a protocol."""
        pass


class IStream(ABC):
    """Interface for streams."""
    
    @abstractmethod
    async def read(self, n: int = -1) -> bytes:
        """Read data from the stream."""
        pass
    
    @abstractmethod
    async def write(self, data: bytes) -> None:
        """Write data to the stream."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the stream."""
        pass
    
    @abstractmethod
    def get_remote_peer(self) -> str:
        """Get the remote peer ID."""
        pass


# Type aliases
THandler = Callable[[IRawConnection], Awaitable[None]]
TProtocol = str
