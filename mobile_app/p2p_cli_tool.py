"""
Command-line P2P testing tool for mobile application.

This tool allows testing the P2P functionality from the command line
without requiring GUI libraries.
"""

import asyncio
import socket
import json
import logging
import threading
import time
from typing import Optional, Dict, List, Callable

logger = logging.getLogger(__name__)


class SimplePeer:
    """Simple peer representation."""
    
    def __init__(self, peer_id: str, address: str, port: int):
        self.peer_id = peer_id
        self.address = address
        self.port = port
    
    def __str__(self):
        return f"{self.peer_id}@{self.address}:{self.port}"


class SimpleP2PNode:
    """Simple P2P node for command-line testing."""
    
    def __init__(self, port: int = 0):
        self.port = port
        self.peer_id = f"peer_{port}"
        self.server_socket: Optional[socket.socket] = None
        self.connections: Dict[str, socket.socket] = {}
        self.message_handlers: Dict[str, Callable] = {}
        self.is_running = False
        self._discovery_peers: List[SimplePeer] = []
        
    def start(self):
        """Start the P2P node."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('localhost', self.port))
        
        # Get the actual port if 0 was specified
        self.port = self.server_socket.getsockname()[1]
        self.peer_id = f"peer_{self.port}"
        
        self.server_socket.listen(5)
        self.is_running = True
        
        # Start server in background thread
        server_thread = threading.Thread(target=self._server_loop, daemon=True)
        server_thread.start()
        
        print(f"P2P node started on port {self.port} with ID {self.peer_id}")
        return self.port
    
    def _server_loop(self):
        """Server loop to accept connections."""
        while self.is_running and self.server_socket:
            try:
                client_socket, address = self.server_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
            except Exception as e:
                if self.is_running:
                    logger.error(f"Server error: {e}")
                break
    
    def _handle_client(self, client_socket: socket.socket, address):
        """Handle incoming client connection."""
        try:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self._process_message(message, client_socket)
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received")
                
        except Exception as e:
            logger.error(f"Client handler error: {e}")
        finally:
            client_socket.close()
    
    def _process_message(self, message: dict, client_socket: socket.socket):
        """Process incoming message."""
        msg_type = message.get('type')
        peer_id = message.get('peer_id')
        
        if msg_type == 'chat':
            content = message.get('content')
            print(f"📨 Received chat from {peer_id}: {content}")
            
        elif msg_type == 'file':
            filename = message.get('filename')
            content = message.get('content', '')
            print(f"📎 Received file '{filename}' from {peer_id} ({len(content)} bytes)")
    
    def connect_to_peer(self, address: str, port: int) -> bool:
        """Connect to a peer."""
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((address, port))
            
            peer_key = f"{address}:{port}"
            self.connections[peer_key] = peer_socket
            
            # Add to discovery peers
            peer = SimplePeer(f"peer_{port}", address, port)
            if peer not in self._discovery_peers:
                self._discovery_peers.append(peer)
            
            print(f"✅ Connected to peer at {address}:{port}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to {address}:{port}: {e}")
            return False
    
    def send_message(self, peer_address: str, peer_port: int, msg_type: str, content: str):
        """Send a message to a peer."""
        peer_key = f"{peer_address}:{peer_port}"
        
        if peer_key not in self.connections:
            success = self.connect_to_peer(peer_address, peer_port)
            if not success:
                print(f"Cannot connect to {peer_key}")
                return
        
        message = {
            'type': msg_type,
            'peer_id': self.peer_id,
            'content': content
        }
        
        if msg_type == 'file':
            message['filename'] = content.split('/')[-1] if '/' in content else content
        
        try:
            peer_socket = self.connections[peer_key]
            peer_socket.send(json.dumps(message).encode('utf-8'))
            print(f"✉️  Sent {msg_type} message to {peer_key}")
        except Exception as e:
            print(f"❌ Failed to send message to {peer_key}: {e}")
            # Remove broken connection
            if peer_key in self.connections:
                del self.connections[peer_key]
    
    def get_discovery_peers(self) -> List[SimplePeer]:
        """Get list of discovered peers."""
        return self._discovery_peers
    
    def stop(self):
        """Stop the P2P node."""
        self.is_running = False
        
        for conn in self.connections.values():
            conn.close()
        self.connections.clear()
        
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        
        print(f"P2P node {self.peer_id} stopped")


class P2PCommandLine:
    """Command-line interface for P2P testing."""
    
    def __init__(self):
        self.node: Optional[SimpleP2PNode] = None
        self.running = True
    
    def start(self, port: int = 0):
        """Start the P2P node and command interface."""
        self.node = SimpleP2PNode(port)
        actual_port = self.node.start()
        
        print("\n🚀 P2P Mobile - Command Line Testing")
        print("=" * 50)
        print(f"Node ID: {self.node.peer_id}")
        print(f"Listening on: localhost:{actual_port}")
        print("\nAvailable commands:")
        print("  connect <address> <port>  - Connect to a peer")
        print("  chat <address> <port> <message>  - Send a chat message")
        print("  file <address> <port> <filename>  - Send a file (mock)")
        print("  peers  - List connected peers")
        print("  info   - Show node information")
        print("  help   - Show this help")
        print("  quit   - Exit the application")
        print("=" * 50)
        
        self.command_loop()
    
    def command_loop(self):
        """Main command loop."""
        while self.running:
            try:
                command = input(f"\n[{self.node.peer_id}]> ").strip().split()
                if not command:
                    continue
                
                cmd = command[0].lower()
                
                if cmd == 'quit' or cmd == 'exit':
                    self.running = False
                    
                elif cmd == 'connect':
                    if len(command) >= 3:
                        address = command[1]
                        try:
                            port = int(command[2])
                            self.node.connect_to_peer(address, port)
                        except ValueError:
                            print("❌ Invalid port number")
                    else:
                        print("Usage: connect <address> <port>")
                
                elif cmd == 'chat':
                    if len(command) >= 4:
                        address = command[1]
                        try:
                            port = int(command[2])
                            message = ' '.join(command[3:])
                            self.node.send_message(address, port, 'chat', message)
                        except ValueError:
                            print("❌ Invalid port number")
                    else:
                        print("Usage: chat <address> <port> <message>")
                
                elif cmd == 'file':
                    if len(command) >= 4:
                        address = command[1]
                        try:
                            port = int(command[2])
                            filename = command[3]
                            self.node.send_message(address, port, 'file', filename)
                        except ValueError:
                            print("❌ Invalid port number")
                    else:
                        print("Usage: file <address> <port> <filename>")
                
                elif cmd == 'peers':
                    peers = self.node.get_discovery_peers()
                    if peers:
                        print("Connected peers:")
                        for peer in peers:
                            print(f"  - {peer}")
                    else:
                        print("No connected peers")
                
                elif cmd == 'info':
                    print(f"Node ID: {self.node.peer_id}")
                    print(f"Port: {self.node.port}")
                    print(f"Connected peers: {len(self.node.get_discovery_peers())}")
                
                elif cmd == 'help':
                    print("\nAvailable commands:")
                    print("  connect <address> <port>  - Connect to a peer")
                    print("  chat <address> <port> <message>  - Send a chat message")
                    print("  file <address> <port> <filename>  - Send a file (mock)")
                    print("  peers  - List connected peers")
                    print("  info   - Show node information")
                    print("  help   - Show this help")
                    print("  quit   - Exit the application")
                
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                self.running = False
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def stop(self):
        """Stop the command-line interface."""
        if self.node:
            self.node.stop()


def main():
    """Main entry point."""
    logging.basicConfig(level=logging.WARNING)  # Reduce log noise
    
    import sys
    
    port = 0
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print("Invalid port number")
            sys.exit(1)
    
    cli = P2PCommandLine()
    try:
        cli.start(port)
    finally:
        cli.stop()


if __name__ == '__main__':
    main()
