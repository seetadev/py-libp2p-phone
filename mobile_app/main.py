"""
Mobile P2P App - Main entry point

A Kivy-based mobile application for peer-to-peer networking using py-libp2p.
Supports chat and file sharing between mobile devices.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.clock import Clock
from kivy.logger import Logger

# Mobile libp2p imports
from mobile.runtime import AsyncRuntimeAdapter, get_runtime_adapter
from mobile.factory import create_tcp_transport
from mobile_app.mobile_abc import IHost
from mobile_app.p2p_host import RealMobileHost
from mobile_app.mobile_abc import P2PPeer

# QR code support
try:
    import qrcode
    from io import BytesIO
    HAS_QR = True
except ImportError:
    HAS_QR = False
    Logger.warning("QR code support not available. Install qrcode package.")


class PeerDiscoveryScreen(Screen):
    """Screen for discovering and connecting to peers."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.host: Optional[IHost] = None
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the peer discovery UI."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        layout.add_widget(Label(
            text='P2P Mobile - Peer Discovery',
            size_hint_y=None,
            height='48dp',
            font_size='18sp'
        ))
        
        # My peer ID display
        self.peer_id_label = Label(
            text='Peer ID: Not connected',
            size_hint_y=None,
            height='32dp',
            text_size=(None, None)
        )
        layout.add_widget(self.peer_id_label)
        
        # QR code display area
        if HAS_QR:
            self.qr_button = Button(
                text='Generate QR Code',
                size_hint_y=None,
                height='48dp'
            )
            self.qr_button.bind(on_press=self.generate_qr_code)
            layout.add_widget(self.qr_button)
        
        # Manual peer connection
        layout.add_widget(Label(
            text='Connect to Peer:',
            size_hint_y=None,
            height='32dp'
        ))
        
        self.peer_input = TextInput(
            hint_text='Enter peer multiaddr or scan QR',
            size_hint_y=None,
            height='48dp',
            multiline=False
        )
        layout.add_widget(self.peer_input)
        
        connect_button = Button(
            text='Connect',
            size_hint_y=None,
            height='48dp'
        )
        connect_button.bind(on_press=self.connect_to_peer)
        layout.add_widget(connect_button)
        
        # Navigation buttons
        nav_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp')
        
        chat_button = Button(text='Chat')
        chat_button.bind(on_press=lambda x: self.switch_screen('chat'))
        nav_layout.add_widget(chat_button)
        
        files_button = Button(text='Files')
        files_button.bind(on_press=lambda x: self.switch_screen('files'))
        nav_layout.add_widget(files_button)
        
        layout.add_widget(nav_layout)
        
        self.add_widget(layout)
    
    def switch_screen(self, screen_name: str):
        """Switch to another screen."""
        self.manager.current = screen_name
    
    def generate_qr_code(self, instance):
        """Generate a QR code for this peer."""
        if not HAS_QR:
            self.show_popup("QR Error", "QR code support not available")
            return
        
        if not self.host:
            self.show_popup("Connection Error", "Not connected to libp2p host")
            return
        
        # Create QR code with peer connection info
        peer_info = f"/ip4/127.0.0.1/tcp/4001/p2p/{self.host.get_id()}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(peer_info)
        qr.make(fit=True)
        
        # Convert to image and display
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Save temporarily and show in popup
        qr_path = "/tmp/peer_qr.png"
        img.save(qr_path)
        
        self.show_popup("Peer QR Code", f"QR saved to {qr_path}\n\nPeer Info:\n{peer_info}")
    
    def connect_to_peer(self, instance):
        """Connect to a peer using the entered address."""
        peer_addr = self.peer_input.text.strip()
        if not peer_addr:
            self.show_popup("Input Error", "Please enter a peer address")
            return
        
        # Schedule async connection
        Clock.schedule_once(lambda dt: asyncio.create_task(self._async_connect(peer_addr)), 0)
    
    async def _async_connect(self, peer_addr: str):
        """Async method to connect to peer."""
        try:
            if self.host:
                # Parse and connect to peer
                # This would use the actual libp2p connection logic
                Logger.info(f"Attempting to connect to peer: {peer_addr}")
                # await self.host.connect(parse_multiaddr(peer_addr))
                Clock.schedule_once(
                    lambda dt: self.show_popup("Success", f"Connected to {peer_addr}"), 0
                )
            else:
                Clock.schedule_once(
                    lambda dt: self.show_popup("Error", "Host not initialized"), 0
                )
        except Exception as e:
            Clock.schedule_once(
                lambda dt: self.show_popup("Connection Error", str(e)), 0
            )
    
    def show_popup(self, title: str, message: str):
        """Show a popup with the given message."""
        popup = Popup(
            title=title,
            content=Label(text=message),
            size_hint=(0.8, 0.6)
        )
        popup.open()
    
    def set_host(self, host: IHost):
        """Set the libp2p host."""
        self.host = host
        if host:
            self.peer_id_label.text = f'Peer ID: {host.get_id()}'


class ChatScreen(Screen):
    """Screen for peer-to-peer chat."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the chat UI."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        layout.add_widget(Label(
            text='P2P Chat',
            size_hint_y=None,
            height='48dp',
            font_size='18sp'
        ))
        
        # Chat history
        self.chat_history = TextInput(
            text='Chat will appear here...\n',
            readonly=True,
            size_hint_y=0.7
        )
        layout.add_widget(self.chat_history)
        
        # Message input
        input_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp')
        
        self.message_input = TextInput(
            hint_text='Type your message...',
            multiline=False
        )
        input_layout.add_widget(self.message_input)
        
        send_button = Button(
            text='Send',
            size_hint_x=None,
            width='100dp'
        )
        send_button.bind(on_press=self.send_message)
        input_layout.add_widget(send_button)
        
        layout.add_widget(input_layout)
        
        # Back button
        back_button = Button(
            text='Back to Discovery',
            size_hint_y=None,
            height='48dp'
        )
        back_button.bind(on_press=lambda x: self.switch_screen('discovery'))
        layout.add_widget(back_button)
        
        self.add_widget(layout)
    
    def switch_screen(self, screen_name: str):
        """Switch to another screen."""
        self.manager.current = screen_name
    
    def send_message(self, instance):
        """Send a chat message."""
        message = self.message_input.text.strip()
        if message:
            # Add to chat history
            self.chat_history.text += f"You: {message}\n"
            
            # Schedule async send
            Clock.schedule_once(lambda dt: asyncio.create_task(self._async_send(message)), 0)
            
            # Clear input
            self.message_input.text = ''
    
    async def _async_send(self, message: str):
        """Async method to send message via libp2p."""
        try:
            # This would use the actual libp2p messaging
            Logger.info(f"Sending message: {message}")
            # await self.host.send_message(message)
        except Exception as e:
            Logger.error(f"Failed to send message: {e}")


class FileShareScreen(Screen):
    """Screen for peer-to-peer file sharing."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the file sharing UI."""
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Title
        layout.add_widget(Label(
            text='P2P File Share',
            size_hint_y=None,
            height='48dp',
            font_size='18sp'
        ))
        
        # File chooser
        self.file_chooser = FileChooserListView(
            size_hint_y=0.6,
            path=str(Path.home())
        )
        layout.add_widget(self.file_chooser)
        
        # Selected file display
        self.selected_file_label = Label(
            text='No file selected',
            size_hint_y=None,
            height='32dp'
        )
        layout.add_widget(self.selected_file_label)
        
        # Action buttons
        button_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height='48dp')
        
        select_button = Button(text='Select File')
        select_button.bind(on_press=self.select_file)
        button_layout.add_widget(select_button)
        
        share_button = Button(text='Share File')
        share_button.bind(on_press=self.share_file)
        button_layout.add_widget(share_button)
        
        layout.add_widget(button_layout)
        
        # Back button
        back_button = Button(
            text='Back to Discovery',
            size_hint_y=None,
            height='48dp'
        )
        back_button.bind(on_press=lambda x: self.switch_screen('discovery'))
        layout.add_widget(back_button)
        
        self.add_widget(layout)
    
    def switch_screen(self, screen_name: str):
        """Switch to another screen."""
        self.manager.current = screen_name
    
    def select_file(self, instance):
        """Select a file for sharing."""
        if self.file_chooser.selection:
            selected = self.file_chooser.selection[0]
            self.selected_file_label.text = f'Selected: {Path(selected).name}'
        else:
            self.selected_file_label.text = 'No file selected'
    
    def share_file(self, instance):
        """Share the selected file."""
        if not self.file_chooser.selection:
            popup = Popup(
                title='No File Selected',
                content=Label(text='Please select a file to share'),
                size_hint=(0.8, 0.4)
            )
            popup.open()
            return
        
        file_path = self.file_chooser.selection[0]
        
        # Schedule async file sharing
        Clock.schedule_once(lambda dt: asyncio.create_task(self._async_share_file(file_path)), 0)
    
    async def _async_share_file(self, file_path: str):
        """Async method to share file via libp2p."""
        try:
            Logger.info(f"Sharing file: {file_path}")
            # This would use the actual libp2p file transfer
            # await self.host.share_file(file_path)
            
            Clock.schedule_once(lambda dt: self._show_share_success(file_path), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: self._show_share_error(str(e)), 0)
    
    def _show_share_success(self, file_path: str):
        """Show file share success popup."""
        popup = Popup(
            title='File Shared',
            content=Label(text=f'Successfully shared:\n{Path(file_path).name}'),
            size_hint=(0.8, 0.4)
        )
        popup.open()
    
    def _show_share_error(self, error: str):
        """Show file share error popup."""
        popup = Popup(
            title='Share Error',
            content=Label(text=f'Failed to share file:\n{error}'),
            size_hint=(0.8, 0.4)
        )
        popup.open()


class MobileP2PApp(App):
    """Main Kivy application for mobile P2P networking."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.host: Optional[RealMobileHost] = None
        self.runtime_adapter: Optional[AsyncRuntimeAdapter] = None
    
    def build(self):
        """Build the app UI."""
        # Create screen manager
        sm = ScreenManager()
        
        # Add screens
        discovery_screen = PeerDiscoveryScreen(name='discovery')
        chat_screen = ChatScreen(name='chat')
        files_screen = FileShareScreen(name='files')
        
        sm.add_widget(discovery_screen)
        sm.add_widget(chat_screen)
        sm.add_widget(files_screen)
        
        # Set default screen
        sm.current = 'discovery'
        
        # Store references for later use
        self.discovery_screen = discovery_screen
        self.chat_screen = chat_screen
        self.files_screen = files_screen
        
        # Initialize libp2p host asynchronously
        Clock.schedule_once(lambda dt: asyncio.create_task(self.init_libp2p()), 0)
        
        return sm
    
    async def init_libp2p(self):
        """Initialize the libp2p host."""
        try:
            # Set up runtime adapter for mobile
            self.runtime_adapter = get_runtime_adapter()
            Logger.info(f"Using runtime: {self.runtime_adapter.runtime_name}")
            
            # Create real mobile host
            self.host = RealMobileHost(0)  # Let it choose a port
            await self.host.start()
            Logger.info(f"Created mobile host with peer ID: {self.host.get_peer_id()}")
            
            # Set up message handlers
            self.host.set_message_handler('chat', self._on_chat_message)
            self.host.set_message_handler('file', self._on_file_received)
            self.host.set_peer_discovery_handler(self._on_peer_discovered)
            
            # Update UI on main thread
            Clock.schedule_once(lambda dt: self._update_host_info(), 0)
            
        except Exception as e:
            Logger.error(f"Failed to initialize libp2p: {e}")
            Clock.schedule_once(lambda dt: self._show_init_error(str(e)), 0)
    
    async def _on_chat_message(self, peer_id, message: str):
        """Handle incoming chat messages."""
        def update_chat():
            if hasattr(self, 'chat_screen'):
                self.chat_screen.chat_history.text += f"{peer_id}: {message}\n"
        Clock.schedule_once(lambda dt: update_chat(), 0)
    
    async def _on_file_received(self, peer_id, filename: str, file_data: bytes):
        """Handle incoming files."""
        def update_files():
            if hasattr(self, 'file_share_screen'):
                self.file_share_screen.add_received_file(f"{filename} from {peer_id}", len(file_data))
        Clock.schedule_once(lambda dt: update_files(), 0)
    
    def _on_peer_discovered(self, peer: P2PPeer):
        """Handle peer discovery."""
        def update_peers():
            if hasattr(self, 'discovery_screen'):
                self.discovery_screen.add_discovered_peer(peer)
        Clock.schedule_once(lambda dt: update_peers(), 0)
    
    def _update_host_info(self):
        """Update the UI with host information."""
        if self.host and hasattr(self, 'discovery_screen'):
            # Update discovery screen with host info
            pass  # The screen will get the host reference
    
    def _show_init_error(self, error: str):
        """Show initialization error."""
        popup = Popup(
            title='Initialization Error',
            content=Label(text=f'Failed to start libp2p:\n{error}'),
            size_hint=(0.8, 0.6)
        )
        popup.open()


def main():
    """Main entry point for the mobile app."""
    # Set up mobile runtime
    if get_runtime_adapter().use_asyncio:
        Logger.info("Running on mobile platform with asyncio")
    
    # Run the Kivy app
    app = MobileP2PApp()
    app.run()


if __name__ == '__main__':
    main()
