#!/usr/bin/env python3
"""
Ethical Android Device Demo Server
For educational purposes only - demonstrates legitimate client-server communication
"""

import socket
import json
import threading
from datetime import datetime

class DeviceDemoServer:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False

    def start(self):
        """Start the server and listen for connections"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"[+] Server listening on {self.host}:{self.port}")
            print(f"[+] Waiting for Android device connections...")
            print(f"[+] Press Ctrl+C to stop\n")

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"\n[+] New connection from: {address[0]}:{address[1]}")
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except KeyboardInterrupt:
                    print("\n[!] Server shutting down...")
                    self.running = False
                    break

        except Exception as e:
            print(f"[!] Error starting server: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()

    def handle_client(self, client_socket, address):
        """Handle individual client connection"""
        try:
            while self.running:
                data = client_socket.recv(4096)
                if not data:
                    break

                try:
                    message = json.loads(data.decode('utf-8'))
                    self.log_message(message, address)

                    # Send acknowledgment
                    response = {
                        "status": "received",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Data logged successfully"
                    }
                    client_socket.send(json.dumps(response).encode('utf-8'))

                except json.JSONDecodeError:
                    print(f"[!] Invalid JSON received from {address}")

        except Exception as e:
            print(f"[!] Error handling client {address}: {e}")
        finally:
            client_socket.close()
            print(f"[-] Connection closed: {address[0]}:{address[1]}")

    def log_message(self, message, address):
        """Log received message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{timestamp}] Message from {address[0]}:")
        print("=" * 50)

        # Pretty print the device info
        if 'device_info' in message:
            info = message['device_info']
            print(f"Device Model: {info.get('model', 'Unknown')}")
            print(f"Android Version: {info.get('android_version', 'Unknown')}")
            print(f"App Version: {info.get('app_version', 'Unknown')}")
            print(f"Is Emulator: {info.get('is_emulator', 'Unknown')}")
            print(f"Device ID: {info.get('device_id', 'Unknown')}")
            print(f"IP Address: {info.get('ip_address', 'Unknown')}")

        if 'permissions' in message:
            print(f"\nGranted Permissions:")
            for perm in message['permissions']:
                print(f"  ✓ {perm}")

        if 'status' in message:
            print(f"\nStatus: {message['status']}")

        print("=" * 50)

if __name__ == "__main__":
    server = DeviceDemoServer(host='0.0.0.0', port=8000)
    server.start()