# Mobile py-libp2p Framework

A mobile-compatible abstraction layer for py-libp2p that enables peer-to-peer networking on Android, iOS, and Progressive Web Apps (PWA).

## Overview

This module provides a complete mobile framework that wraps py-libp2p to work on mobile platforms by solving the trio compatibility issues and providing platform-specific optimizations.

### Supported Platforms

- **Android** - via Kivy or BeeWare
- **iOS** - via BeeWare/Toga
- **Progressive Web Apps (PWA)** - via Pyodide/WASM

## Core Components

### 🚀 `asyncio_host.py` - Main Mobile P2P Host
The primary interface for mobile P2P applications. Provides:
- **P2P Connectivity** - Connect to peers across networks
- **Chat Messaging** - Real-time peer-to-peer messaging
- **File Transfer** - Send/receive files between peers
- **Peer Discovery** - Find nearby peers automatically

```python
from mobile.asyncio_host import MobileP2PHost

# Create and start a mobile P2P host
host = MobileP2PHost(port=9001)
async with host.run():
    # Connect to peer
    await host.connect_to_peer("/ip4/192.168.1.100/tcp/9002")
    
    # Send chat message
    await host.send_chat_message("Hello from mobile!")
    
    # Send file
    await host.send_file("photo.jpg")
```

### 🏗️ `framework.py` - Mobile App Framework
Platform detection and mobile app integration utilities:

```python
from mobile.framework import PlatformDetector, MobileAppFramework

# Detect platform
if PlatformDetector.is_android():
    print("Running on Android")
elif PlatformDetector.is_ios():
    print("Running on iOS")
elif PlatformDetector.is_pyodide():
    print("Running as PWA")

# Create mobile app
app = MobileAppFramework()
await app.initialize()
```

### ⚙️ `runtime.py` - Async Runtime Adapter
Handles trio/asyncio compatibility for cross-platform deployment:

```python
from mobile.runtime import get_runtime_adapter

adapter = get_runtime_adapter()
if adapter.use_asyncio:
    # Use asyncio-based implementation
    pass
```

### 🌐 `transport.py` - Mobile Transport Layer
Asyncio-based transport implementations that work on mobile:

```python
from mobile.transport import MobileTCPTransport

transport = MobileTCPTransport()
# Automatically works on all mobile platforms
```

### 🏭 `factory.py` - Transport Factory
Automatically chooses the right transport for the platform:

```python
from mobile.factory import create_tcp_transport

transport = create_tcp_transport()
# Returns MobileTCPTransport on mobile, regular TCP on desktop
```

### 📡 `io.py` - Mobile I/O Abstractions
Stream and I/O utilities optimized for mobile networking.

## Quick Start

### 1. Installation

```bash
# Install the mobile framework
pip install -e .

# For Android development
pip install kivy buildozer

# For iOS development  
pip install toga

# For PWA development
pip install pyodide-build
```

### 2. Basic Usage

```python
import asyncio
from mobile.asyncio_host import MobileP2PHost

async def main():
    # Create mobile P2P host
    host = MobileP2PHost(port=9001)
    
    async with host.run():
        print(f"Peer ID: {host.peer_id}")
        print(f"Listening on: {host.listen_addresses}")
        
        # Your P2P application logic here
        await asyncio.sleep(60)  # Keep running

if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Platform-Specific Setup

#### Android (Kivy)
```bash
# Install Kivy
pip install kivy

# Build APK
buildozer android debug
```

#### iOS (BeeWare)
```bash
# Install BeeWare
pip install toga

# Create iOS app
briefcase create iOS
briefcase build iOS
```

#### PWA (Pyodide)
```bash
# Build for browser
pyodide build

# Serve locally
python -m http.server 8000
```

## Key Features

### ✅ Three Core Deliverables
1. **P2P Connectivity** - Direct peer-to-peer connections
2. **Chat Messaging** - Real-time messaging between peers  
3. **File Transfer** - Efficient file sharing

### ✅ Mobile Optimizations
- **Battery Efficient** - Optimized for mobile power constraints
- **Network Adaptive** - Handles mobile network switching
- **Memory Efficient** - Designed for mobile memory limits
- **Touch Friendly** - Mobile UI considerations

### ✅ Cross-Platform
- **Unified API** - Same code works on all platforms
- **Platform Detection** - Automatic platform optimization
- **Graceful Fallbacks** - Works even with limited capabilities

## Architecture

```
Mobile Framework Architecture:

┌─────────────────────────────────────────┐
│           Mobile Application            │
├─────────────────────────────────────────┤
│         Mobile P2P Host                 │
│    (asyncio_host.py)                   │
├─────────────────────────────────────────┤
│  Platform Detection │  Runtime Adapter  │
│   (framework.py)    │   (runtime.py)    │
├─────────────────────────────────────────┤
│  Mobile Transport  │   Mobile I/O       │
│  (transport.py)    │    (io.py)         │
├─────────────────────────────────────────┤
│            py-libp2p Core               │
│         (libp2p directory)              │
└─────────────────────────────────────────┘
```

## Design Principles

1. **No Core Modifications** - Never modify the `libp2p/` directory
2. **Asyncio First** - Use asyncio for mobile compatibility
3. **Platform Agnostic** - Single codebase for all platforms
4. **Performance Optimized** - Mobile-specific optimizations
5. **Developer Friendly** - Simple, intuitive API

## Troubleshooting

### Common Issues

**Trio Compatibility Error**:
```
AttributeError: 'RunContext' object has no attribute 'runner'
```
**Solution**: Use `asyncio_host.py` instead of the trio-based components.

**Import Errors on Mobile**:
- Make sure all dependencies are included in your mobile build
- Use the mobile-specific implementations

**Connection Issues**:
- Check firewall settings
- Ensure peers are on the same network or use proper NAT traversal
- Verify port availability

## Examples

See the `mobile_app/` directory for complete working examples including:
- Command-line interface
- Mobile app configurations
- Cross-platform deployment scripts

## Contributing

When adding new features:
1. Maintain asyncio compatibility
2. Test on all target platforms
3. Follow the "no core modifications" principle
4. Add comprehensive documentation

## License

Same as py-libp2p: MIT AND Apache-2.0
