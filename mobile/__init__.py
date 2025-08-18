"""
Mobile P2P Framework for py-libp2p

This module provides a complete mobile-ready abstraction layer for py-libp2p,
enabling real peer-to-peer networking on mobile devices including Android, iOS,
and Progressive Web Apps.

Core Features:
1. P2P Connectivity - Direct peer-to-peer connections
2. Chat Messaging - Real-time messaging between peers  
3. File Transfer - Secure file sharing over P2P networks

Mobile Platform Support:
- Android (via Kivy/BeeWare)
- iOS (via Kivy/BeeWare) 
- Progressive Web Apps (via Pyodide)
- Desktop (development/testing)

Usage:
    from mobile import create_mobile_host, MobileAppFramework
    
    # Simple host creation
    host = create_mobile_host(port=9000)
    
    # Full framework with mobile optimizations
    framework = MobileAppFramework("MyP2PApp")
    host = await framework.initialize_host()
"""

# Core mobile P2P components
from .host import MobileP2PHost, create_mobile_host, MobilePeer
from .framework import (
    MobileAppFramework,
    PlatformDetector,
    MobileNetworking,
    MobileStorage,
    create_mobile_framework,
    quick_start_headless,
    detect_best_framework,
)

# Legacy compatibility layer
from .runtime import AsyncRuntimeAdapter, is_mobile_runtime, get_runtime_adapter
from .transport import MobileTCPTransport, MobileTCPListener
from .io import MobileAsyncStream, MobileBufferedStream
from .factory import create_tcp_transport, get_transport_class

__version__ = "0.1.0"
__author__ = "py-libp2p-phone contributors"

__all__ = [
    # Core mobile P2P functionality
    "MobileP2PHost",
    "create_mobile_host", 
    "MobilePeer",
    
    # Mobile framework
    "MobileAppFramework",
    "create_mobile_framework",
    "quick_start_headless",
    
    # Platform utilities
    "PlatformDetector",
    "MobileNetworking", 
    "MobileStorage",
    "detect_best_framework",
    
    # Legacy compatibility - transport layer
    "AsyncRuntimeAdapter",
    "is_mobile_runtime", 
    "get_runtime_adapter",
    "MobileTCPTransport",
    "MobileTCPListener",
    "MobileAsyncStream",
    "MobileBufferedStream",
    "create_tcp_transport",
    "get_transport_class",
]
