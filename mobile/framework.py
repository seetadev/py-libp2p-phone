"""
Mobile Framework Integration for py-libp2p

This module provides utilities and abstractions for deploying py-libp2p
applications on mobile platforms including:
- Kivy (Android/iOS)
- BeeWare/Toga (native mobile apps)
- Pyodide (Progressive Web Apps)

The framework handles platform-specific optimizations and provides
a unified API for mobile P2P applications.
"""

import sys
import platform
import asyncio
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import logging

from .host import MobileP2PHost


logger = logging.getLogger(__name__)


class PlatformDetector:
    """Detect the current mobile platform and capabilities"""
    
    @staticmethod
    def is_android() -> bool:
        """Check if running on Android"""
        return hasattr(sys, 'getandroidapilevel') or 'android' in sys.platform.lower()
    
    @staticmethod
    def is_ios() -> bool:
        """Check if running on iOS"""
        return sys.platform == 'ios'
    
    @staticmethod
    def is_pyodide() -> bool:
        """Check if running in Pyodide (browser/WASM)"""
        return 'pyodide' in sys.modules
    
    @staticmethod
    def is_kivy_app() -> bool:
        """Check if running in a Kivy application"""
        try:
            import kivy
            return True
        except ImportError:
            return False
    
    @staticmethod
    def is_beeware_app() -> bool:
        """Check if running in a BeeWare/Toga application"""
        try:
            import toga
            return True
        except ImportError:
            return False
    
    @staticmethod
    def get_platform_info() -> Dict[str, Any]:
        """Get comprehensive platform information"""
        return {
            'platform': platform.platform(),
            'system': platform.system(),
            'machine': platform.machine(),
            'is_android': PlatformDetector.is_android(),
            'is_ios': PlatformDetector.is_ios(),
            'is_pyodide': PlatformDetector.is_pyodide(),
            'is_kivy': PlatformDetector.is_kivy_app(),
            'is_beeware': PlatformDetector.is_beeware_app(),
            'is_mobile': PlatformDetector.is_android() or PlatformDetector.is_ios(),
            'python_version': platform.python_version(),
        }


class MobileAppFramework:
    """
    Unified framework for mobile P2P applications
    
    This class provides platform-specific optimizations and handles
    the integration with various mobile frameworks.
    """
    
    def __init__(self, app_name: str = "MobileP2P", port: int = 9000):
        self.app_name = app_name
        self.port = port
        self.host: Optional[MobileP2PHost] = None
        self.platform_info = PlatformDetector.get_platform_info()
        
        # Platform-specific configurations
        self.config = self._get_platform_config()
        
        logger.info(f"Initialized {app_name} for platform: {self.platform_info['platform']}")
    
    def _get_platform_config(self) -> Dict[str, Any]:
        """Get platform-specific configuration"""
        config = {
            'network_timeout': 30,
            'max_connections': 10,
            'buffer_size': 8192,
            'enable_discovery': True,
            'data_directory': 'data',
        }
        
        if self.platform_info['is_android']:
            # Android-specific optimizations
            config.update({
                'network_timeout': 45,  # Mobile networks can be slower
                'max_connections': 5,   # Conserve resources
                'data_directory': '/data/data/org.example.app/files',
            })
        
        elif self.platform_info['is_ios']:
            # iOS-specific optimizations
            config.update({
                'network_timeout': 45,
                'max_connections': 5,
                'data_directory': '~/Documents',
            })
        
        elif self.platform_info['is_pyodide']:
            # Browser/WASM optimizations
            config.update({
                'network_timeout': 60,  # Network requests in browser
                'max_connections': 3,   # Limited by browser
                'enable_discovery': False,  # May not work in browser
                'data_directory': '/tmp',
            })
        
        return config
    
    async def initialize_host(self, host_ip: str = "127.0.0.1") -> MobileP2PHost:
        """Initialize the mobile P2P host with platform optimizations"""
        if self.host:
            return self.host
        
        # Adjust IP binding for mobile platforms
        if self.platform_info['is_android'] or self.platform_info['is_ios']:
            # Mobile devices often need to bind to all interfaces
            host_ip = "0.0.0.0"
        elif self.platform_info['is_pyodide']:
            # Browser environments have networking restrictions
            host_ip = "127.0.0.1"
        
        self.host = MobileP2PHost(port=self.port, host_ip=host_ip)
        
        # Apply platform-specific configurations
        await self._apply_platform_optimizations()
        
        return self.host
    
    async def _apply_platform_optimizations(self):
        """Apply platform-specific optimizations to the host"""
        if not self.host:
            return
        
        # Set up data directory
        data_dir = Path(self.config['data_directory'])
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Platform-specific network optimizations
        if self.platform_info['is_android']:
            await self._optimize_for_android()
        elif self.platform_info['is_ios']:
            await self._optimize_for_ios()
        elif self.platform_info['is_pyodide']:
            await self._optimize_for_browser()
    
    async def _optimize_for_android(self):
        """Android-specific optimizations"""
        logger.info("Applying Android optimizations")
        # TODO: Implement Android-specific network optimizations
        # - Handle background app restrictions
        # - Optimize for battery usage
        # - Handle network state changes
    
    async def _optimize_for_ios(self):
        """iOS-specific optimizations"""
        logger.info("Applying iOS optimizations")
        # TODO: Implement iOS-specific optimizations
        # - Handle app state transitions
        # - Optimize for iOS networking restrictions
        # - Handle background execution limits
    
    async def _optimize_for_browser(self):
        """Browser/WASM-specific optimizations"""
        logger.info("Applying browser optimizations")
        # TODO: Implement browser-specific optimizations
        # - Use WebRTC for peer connections
        # - Handle CORS restrictions
        # - Optimize for limited resources
    
    def create_kivy_app(self) -> 'KivyP2PApp':
        """Create a Kivy-based mobile application"""
        if not self.platform_info['is_kivy']:
            raise RuntimeError("Kivy not available on this platform")
        
        from .kivy_app import KivyP2PApp
        return KivyP2PApp(framework=self)
    
    def create_beeware_app(self) -> 'BeeWareP2PApp':
        """Create a BeeWare/Toga-based mobile application"""
        if not self.platform_info['is_beeware']:
            raise RuntimeError("BeeWare/Toga not available on this platform")
        
        from .beeware_app import BeeWareP2PApp
        return BeeWareP2PApp(framework=self)
    
    def create_web_app(self) -> 'WebP2PApp':
        """Create a web-based application for Pyodide"""
        from .web_app import WebP2PApp
        return WebP2PApp(framework=self)
    
    async def run_headless(self, event_handlers: Optional[Dict[str, Callable]] = None):
        """Run the P2P host in headless mode (no UI)"""
        if not self.host:
            await self.initialize_host()
        
        # Set up event handlers if provided
        if event_handlers:
            if 'chat' in event_handlers:
                self.host.set_chat_handler(event_handlers['chat'])
            if 'file' in event_handlers:
                self.host.set_file_handler(event_handlers['file'])
            if 'peer_connected' in event_handlers:
                self.host.set_peer_connected_handler(event_handlers['peer_connected'])
            if 'peer_disconnected' in event_handlers:
                self.host.set_peer_disconnected_handler(event_handlers['peer_disconnected'])
        
        # Run the host
        async with self.host.run():
            logger.info(f"Mobile P2P host running in headless mode")
            logger.info(f"Peer ID: {self.host.get_peer_id()}")
            logger.info(f"Address: {self.host.get_full_address()}")
            
            # Keep running until interrupted
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down headless mode")


# Factory functions for easy app creation

def create_mobile_framework(app_name: str = "MobileP2P", port: int = 9000) -> MobileAppFramework:
    """Create a mobile application framework instance"""
    return MobileAppFramework(app_name=app_name, port=port)


async def quick_start_headless(port: int = 9000, **event_handlers) -> MobileAppFramework:
    """Quick start a headless P2P application"""
    framework = create_mobile_framework(port=port)
    await framework.run_headless(event_handlers=event_handlers)
    return framework


def detect_best_framework() -> str:
    """Detect the best available mobile framework for the current platform"""
    info = PlatformDetector.get_platform_info()
    
    if info['is_kivy']:
        return 'kivy'
    elif info['is_beeware']:
        return 'beeware'
    elif info['is_pyodide']:
        return 'web'
    elif info['is_android'] or info['is_ios']:
        return 'mobile'
    else:
        return 'desktop'


# Platform-specific utilities

class MobileNetworking:
    """Mobile-specific networking utilities"""
    
    @staticmethod
    def get_local_ip() -> str:
        """Get the local IP address suitable for mobile networking"""
        import socket
        
        try:
            # Connect to a remote address to determine local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
    @staticmethod
    def is_network_available() -> bool:
        """Check if network connectivity is available"""
        import socket
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(3)
                s.connect(("8.8.8.8", 53))
                return True
        except Exception:
            return False
    
    @staticmethod
    def get_wifi_ssid() -> Optional[str]:
        """Get current WiFi SSID (platform-dependent)"""
        # This would need platform-specific implementation
        return None


class MobileStorage:
    """Mobile-specific storage utilities"""
    
    @staticmethod
    def get_app_data_dir(app_name: str) -> Path:
        """Get the appropriate application data directory"""
        info = PlatformDetector.get_platform_info()
        
        if info['is_android']:
            return Path(f"/data/data/org.{app_name.lower()}/files")
        elif info['is_ios']:
            return Path.home() / "Documents" / app_name
        else:
            return Path.home() / f".{app_name.lower()}"
    
    @staticmethod
    def get_downloads_dir() -> Path:
        """Get the downloads directory"""
        info = PlatformDetector.get_platform_info()
        
        if info['is_android']:
            return Path("/storage/emulated/0/Download")
        elif info['is_ios']:
            return Path.home() / "Downloads"
        else:
            return Path.home() / "Downloads"


# Export main classes and functions
__all__ = [
    'MobileAppFramework',
    'PlatformDetector', 
    'MobileNetworking',
    'MobileStorage',
    'create_mobile_framework',
    'quick_start_headless',
    'detect_best_framework',
]
