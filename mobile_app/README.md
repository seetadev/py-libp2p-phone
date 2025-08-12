# P2P Mobile Chat - Mobile libp2p Implementation

A mobile peer-to-peer chat and file sharing application built with Kivy and py-libp2p, demonstrating decentralized networking on mobile devices.

## Features

- **Peer Discovery**: Connect to peers via QR codes or manual address entry
- **Decentralized Chat**: Send messages directly between mobile devices
- **File Sharing**: Share files peer-to-peer without servers
- **Multi-platform**: Android, iOS (future), and PWA (future) support
- **Offline-first**: Works without internet connectivity for local networking

## Architecture

The app uses a modularized py-libp2p implementation optimized for mobile:

- **Mobile Runtime Adapter**: Abstracts asyncio/trio differences for mobile compatibility
- **Simplified Host**: Core libp2p host with essential P2P features
- **Protocol Implementations**: Chat and file sharing protocols
- **Kivy UI**: Touch-optimized interface for mobile devices

## Quick Start

### Prerequisites

- Python 3.10+
- Android SDK (for Android builds)
- Buildozer (for packaging)

### Development Setup

1. **Clone and setup environment:**
   ```bash
   git clone <repository-url>
   cd py-libp2p-phone
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -e .[mobile]
   ```

3. **Run on desktop (for development):**
   ```bash
   cd mobile_app
   python main.py
   ```

### Android Build

1. **Install Buildozer:**
   ```bash
   pip install buildozer
   ```

2. **Initialize and build:**
   ```bash
   cd mobile_app
   buildozer init
   buildozer android debug
   ```

3. **Install on device:**
   ```bash
   buildozer android deploy
   ```

## Usage

### Connecting Peers

1. **Start the app** on two or more devices
2. **Generate QR code** on one device (Discovery screen)
3. **Scan QR code** or manually enter peer address on other devices
4. **Connected peers** will appear in the peer list

### Chat

1. **Switch to Chat screen**
2. **Type messages** and tap Send
3. **Messages sync** automatically between connected peers

### File Sharing

1. **Switch to Files screen**
2. **Select a file** from the file browser
3. **Tap Share** to send to connected peers
4. **Received files** are saved to the downloads folder

## Building for Production

### Android (Google Play)

1. **Create release build:**
   ```bash
   buildozer android release
   ```

2. **Sign the APK:**
   ```bash
   jarsigner -verbose -sigalg SHA1withRSA -digestalg SHA1 \
     -keystore my-release-key.keystore \
     bin/p2pmobile-0.1-armeabi-v7a-release-unsigned.apk \
     alias_name
   ```

3. **Align the APK:**
   ```bash
   zipalign -v 4 \
     bin/p2pmobile-0.1-armeabi-v7a-release-unsigned.apk \
     bin/p2pmobile-0.1-armeabi-v7a-release.apk
   ```

### iOS (Future)

iOS builds will use BeeWare/Toga:

```bash
pip install briefcase
briefcase create iOS
briefcase build iOS
briefcase package iOS
```

### PWA (Future)

PWA builds will use Pyodide:

```bash
pip install pyodide-build
pyodide build
```

## Development

### Project Structure

```
mobile_app/
├── main.py              # Main Kivy application
├── mobile_host.py       # Mobile libp2p host implementation
├── mobile_abc.py        # Abstract base classes
├── mobile_swarm.py      # Connection management
├── mobile_stream.py     # Stream implementations
├── peer_id.py          # Peer ID utilities
├── buildozer.spec      # Android build configuration
└── assets/             # App assets (icons, etc.)
```

### Adding New Protocols

1. **Create protocol class:**
   ```python
   class MyProtocol:
       PROTOCOL_ID = "/p2p-mobile/myprotocol/1.0.0"
       
       def __init__(self, host: MobileHost):
           self.host = host
           host.set_stream_handler(self.PROTOCOL_ID, self._handle_stream)
       
       async def _handle_stream(self, stream: IStream):
           # Handle incoming streams
           pass
   ```

2. **Register in main app:**
   ```python
   my_protocol = MyProtocol(self.host)
   ```

### Testing

Run tests on desktop before building for mobile:

```bash
python -m pytest tests/
```

Test on Android emulator:

```bash
buildozer android debug
buildozer android deploy run
```

## Troubleshooting

### Common Issues

1. **Build failures**: Ensure Android SDK and NDK are properly installed
2. **Permission errors**: Check Android permissions in buildozer.spec
3. **Network issues**: Verify devices are on the same network for local P2P
4. **QR scanning**: Ensure camera permissions are granted

### Debug Mode

Enable verbose logging in buildozer.spec:

```ini
[buildozer]
log_level = 2
```

View Android logs:

```bash
buildozer android logcat
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**
3. **Make changes** and add tests
4. **Run tests** and linting
5. **Submit a pull request**

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings for public methods
- Test on both desktop and mobile

## Roadmap

- [x] Basic mobile P2P networking
- [x] Chat functionality
- [x] File sharing
- [x] QR code peer discovery
- [ ] iOS support (BeeWare)
- [ ] PWA support (Pyodide)
- [ ] Group chat
- [ ] Voice messages
- [ ] End-to-end encryption
- [ ] DHT peer discovery
- [ ] Relay server support

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: GitHub issues for bug reports
- **Discussions**: GitHub discussions for questions
- **Discord**: [libp2p Discord](https://discord.gg/libp2p) for community support
