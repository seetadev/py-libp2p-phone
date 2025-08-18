# Mobile P2P Application Examples

Complete working examples demonstrating the mobile py-libp2p framework across Android, iOS, and Progressive Web Apps.

## 🎯 Core Deliverables Demonstrated

This directory showcases all three core deliverables:

1. **🔗 P2P Connectivity** - Direct peer connections across platforms
2. **💬 Chat Messaging** - Real-time peer-to-peer messaging
3. **📁 File Transfer** - Efficient file sharing between peers

## 📱 Available Examples

### `asyncio_cli.py` - Interactive P2P CLI
A feature-complete command-line interface demonstrating all mobile P2P capabilities.

**Features:**
- ✅ Connect to peers via multiaddr
- ✅ Send/receive chat messages in real-time
- ✅ Transfer files between peers
- ✅ Automatic peer discovery
- ✅ Connection management
- ✅ Rich user interface with emojis

**Usage:**
```bash
# Terminal 1 - Start first peer
python asyncio_cli.py --port 9001

# Terminal 2 - Start second peer  
python asyncio_cli.py --port 9002

# In Terminal 1, connect to peer 2
📱 > connect /ip4/127.0.0.1/tcp/9002

# Send a chat message
📱 > chat Hello from peer 1!

# Send a file
📱 > file path/to/your/file.txt
```

## 🚀 Quick Start Guide

### 1. Setup Environment

```bash
# Navigate to mobile app directory
cd mobile_app

# Install dependencies
pip install -r requirements-desktop.txt

# Verify installation
python -c "import mobile.asyncio_host; print('Mobile framework ready!')"
```

### 2. Run Your First P2P Network

**Start the first peer:**
```bash
python asyncio_cli.py --port 9001
```

**Start the second peer (in another terminal):**
```bash
python asyncio_cli.py --port 9002
```

**Connect the peers:**
In the first terminal:
```
📱 > connect /ip4/127.0.0.1/tcp/9002
✅ Connected successfully!
```

**Test chat messaging:**
```
📱 > chat Hello P2P world!
```

**Test file transfer:**
```
📱 > file README.md
```

### 3. Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `connect <addr>` | Connect to a peer | `connect /ip4/192.168.1.100/tcp/9002` |
| `chat <message>` | Send chat message | `chat Hello everyone!` |
| `file <path>` | Send file to peers | `file document.pdf` |
| `peers` | List connected peers | `peers` |
| `messages` | Show chat history | `messages` |
| `files` | Show received files | `files` |
| `help` | Show all commands | `help` |
| `quit` | Exit application | `quit` |

## 📦 Mobile Platform Deployment

### Android Deployment (Kivy)

**Install Kivy and Buildozer:**
```bash
pip install kivy buildozer
```

**Configure Android build:**
The `buildozer.spec` file is pre-configured for Android deployment.

**Build APK:**
```bash
buildozer android debug
```

**Install on device:**
```bash
buildozer android deploy
```

### iOS Deployment (BeeWare)

**Install BeeWare:**
```bash
pip install toga briefcase
```

**Create iOS app:**
```bash
briefcase create iOS
briefcase build iOS
briefcase run iOS
```

### PWA Deployment (Pyodide)

**Install Pyodide tools:**
```bash
pip install pyodide-build
```

**Build for browser:**
```bash
pyodide build
```

**Serve locally:**
```bash
python -m http.server 8000
# Open http://localhost:8000 in browser
```

## 🔧 Configuration Files

### `buildozer.spec`
Pre-configured for Android deployment with all necessary permissions:
- Internet access
- Network state monitoring
- Wake lock for background operation

### `requirements-desktop.txt`
All dependencies needed for desktop development and testing.

## 🎮 Demo Scenarios

### Scenario 1: Local Chat Network
Perfect for testing on your local machine:

1. Start 3 peers on different ports (9001, 9002, 9003)
2. Connect them in a mesh network
3. Send chat messages between all peers
4. Observe real-time message propagation

### Scenario 2: File Sharing Network
Demonstrate file transfer capabilities:

1. Start 2 peers
2. Connect them
3. Share different file types (text, images, documents)
4. Verify file integrity on receiving end

### Scenario 3: Cross-Platform Network
Test platform compatibility:

1. Run one peer on desktop
2. Deploy another peer to Android/iOS
3. Connect across platforms
4. Exchange messages and files

## 📊 Performance Monitoring

The CLI includes built-in monitoring:
- Connection status indicators
- Message delivery confirmations
- File transfer progress
- Peer discovery events
- Error reporting with context

## 🐛 Troubleshooting

### Common Issues

**Port Already in Use:**
```bash
# Use a different port
python asyncio_cli.py --port 9003
```

**Connection Refused:**
- Ensure the target peer is running
- Check firewall settings
- Verify the correct IP address and port

**File Transfer Fails:**
- Check file permissions
- Ensure sufficient disk space
- Verify file path exists

**Import Errors:**
```bash
# Ensure you're in the mobile_app directory
cd mobile_app

# Verify mobile module is available
python -c "import mobile; print('Mobile module found')"
```

### Debug Mode

Run with verbose logging:
```bash
python asyncio_cli.py --port 9001 --debug
```

## 🎯 Next Steps

After exploring these examples:

1. **Customize the CLI** - Modify `asyncio_cli.py` for your use case
2. **Build Mobile Apps** - Use the deployment guides above
3. **Extend Functionality** - Add new P2P protocols using the mobile framework
4. **Scale Up** - Test with more peers and different network topologies

## 📚 API Reference

For detailed API documentation, see the main `mobile/README.md` file.

## 🤝 Contributing

To add new examples:
1. Create new Python files in this directory
2. Import from `mobile.asyncio_host`
3. Follow the patterns in `asyncio_cli.py`
4. Update this README with your example

## 📄 License

Same as py-libp2p: MIT AND Apache-2.0