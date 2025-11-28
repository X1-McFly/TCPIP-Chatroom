#!/usr/bin/env python3

# TCP Chat Client - Python Implementation
# Uses threading for concurrent send/receive.


import socket
import threading
import signal
import sys
from datetime import datetime

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 2006
BUFFER_SIZE = 1024


class ChatClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        self.my_name = ""
    
    def get_timestamp(self):
        return datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
    
    def connect(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            print(f"Connecting to {self.host}:{self.port}...")
            self.socket.connect((self.host, self.port))
            self.running = True
            return True
        except ConnectionRefusedError:
            print("Connection refused. Is the server running?")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def print_prompt(self):
        print("> ", end='', flush=True)
    
    def clear_line(self):
        print("\r\033[K", end='', flush=True)
    
    def signal_handler(self, sig, frame):
        self.running = False
        if self.socket:
            self.socket.close()
        print("\nDisconnected.")
        sys.exit(0)
    
    def receive_handler(self):
        while self.running:
            try:
                data = self.socket.recv(BUFFER_SIZE)
                if data:
                    message = data.decode('utf-8')
                    self.clear_line()
                    print(message, end='', flush=True)
                    self.print_prompt()
                else:
                    print("\nDisconnected from server.")
                    self.running = False
                    break
            except ConnectionResetError:
                print("\nConnection lost.")
                self.running = False
                break
            except OSError:
                break
            except Exception as e:
                if self.running:
                    print(f"\nReceive error: {e}")
                break
    
    def start(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        if not self.connect():
            return
        
        recv_thread = threading.Thread(target=self.receive_handler, daemon=True)
        recv_thread.start()
        
        try:
            while self.running:
                self.print_prompt()
                message = input()
                self.clear_line()
                print("\033[A\r\033[K", end='', flush=True)
                
                if not self.running:
                    break
                
                if message == "/quit":
                    try:
                        self.socket.sendall(message.encode('utf-8'))
                    except:
                        pass
                    break
                
                if not self.my_name:
                    self.my_name = message
                elif message.startswith("/nick "):
                    self.my_name = message[6:].strip()
                elif not message.startswith('/'):
                    timestamp = self.get_timestamp()
                    print(f"{timestamp} [{self.my_name}]: {message}")
                
                try:
                    self.socket.sendall((message + '\n').encode('utf-8'))
                except:
                    print("Failed to send message.")
                    break
                    
        except EOFError:
            pass
        finally:
            self.disconnect()
    
    def disconnect(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description='TCP Chat Client')
    parser.add_argument('--host', '-H', default=DEFAULT_IP, help=f'Server IP (default: {DEFAULT_IP})')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT, help=f'Port (default: {DEFAULT_PORT})')
    args = parser.parse_args()
    
    client = ChatClient(args.host, args.port)
    client.start()


if __name__ == "__main__":
    main()
