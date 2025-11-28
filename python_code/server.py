#!/usr/bin/env python3
"""
TCP Chat Server - Python Implementation
Handles multiple clients concurrently using threading.
"""

import socket
import threading
import signal
import sys
from datetime import datetime

DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = 2006
BUFFER_SIZE = 1024
MAX_CLIENTS = 100
SERVER_NAME = "Server"


class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}
        self.clients_lock = threading.Lock()
        self.running = False
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(MAX_CLIENTS)
            self.running = True
            
            print(f"Server started on {self.host}:{self.port}")
            
            input_thread = threading.Thread(target=self.server_input_handler, daemon=True)
            input_thread.start()
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                except Exception as e:
                    if self.running:
                        print(f"Accept error: {e}")
                        
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.shutdown()
    
    def signal_handler(self, sig, frame):
        print("\nShutting down server...")
        self.shutdown()
        sys.exit(0)
    
    def get_timestamp(self):
        return datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
    
    def add_client(self, client_socket, address, name="Anonymous"):
        with self.clients_lock:
            self.clients[client_socket] = {'name': name, 'address': address}
    
    def remove_client(self, client_socket):
        with self.clients_lock:
            if client_socket in self.clients:
                del self.clients[client_socket]
    
    def set_client_name(self, client_socket, name):
        with self.clients_lock:
            if client_socket in self.clients:
                self.clients[client_socket]['name'] = name
    
    def get_client_name(self, client_socket):
        with self.clients_lock:
            return self.clients.get(client_socket, {}).get('name', 'Unknown')
    
    def get_client_count(self):
        with self.clients_lock:
            return len(self.clients)
    
    def get_client_list(self):
        with self.clients_lock:
            return [info['name'] for info in self.clients.values()]
    
    def broadcast(self, message, sender_socket=None):
        with self.clients_lock:
            disconnected = []
            for client_socket in self.clients:
                if client_socket != sender_socket:
                    try:
                        client_socket.sendall(message.encode('utf-8'))
                    except:
                        disconnected.append(client_socket)
            for sock in disconnected:
                del self.clients[sock]
    
    def broadcast_to_all(self, message):
        with self.clients_lock:
            disconnected = []
            for client_socket in self.clients:
                try:
                    client_socket.sendall(message.encode('utf-8'))
                except:
                    disconnected.append(client_socket)
            for sock in disconnected:
                del self.clients[sock]
    
    def send_to_client(self, client_socket, message):
        try:
            client_socket.sendall(message.encode('utf-8'))
        except:
            pass
    
    def print_prompt(self):
        print("\r\033[K> ", end='', flush=True)
    
    def server_input_handler(self):
        while self.running:
            try:
                self.print_prompt()
                message = input()
                if not message:
                    continue
                
                if message == "/quit":
                    self.signal_handler(None, None)
                elif message == "/list":
                    users = self.get_client_list()
                    print(f"Online users ({len(users)}): {', '.join(users) if users else 'None'}")
                elif message == "/help":
                    print("Commands: /list, /quit, /help, or type message to broadcast")
                else:
                    timestamp = self.get_timestamp()
                    print(f"\r\033[K{timestamp} [{SERVER_NAME}]: {message}")
                    self.broadcast_to_all(f"{timestamp} [{SERVER_NAME}]: {message}\n")
            except EOFError:
                break
            except Exception as e:
                if self.running:
                    print(f"Input error: {e}")
                break
    
    def handle_client(self, client_socket, address):
        self.add_client(client_socket, address)
        named = False
        
        try:
            self.send_to_client(client_socket, "Enter name: ")
            
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                
                message = data.decode('utf-8').strip()
                if not message:
                    continue
                
                if not named:
                    self.set_client_name(client_socket, message)
                    named = True
                    timestamp = self.get_timestamp()
                    print(f"{timestamp} {message} joined")
                    self.broadcast(f"{message} joined\n")
                    continue
                
                if message.startswith('/'):
                    if message == "/quit":
                        break
                    elif message == "/list":
                        users = self.get_client_list()
                        self.send_to_client(client_socket, f"Online: {', '.join(users)}\n")
                    elif message == "/help":
                        self.send_to_client(client_socket, "Commands: /nick <name>, /list, /help, /quit\n")
                    elif message.startswith("/nick "):
                        new_name = message[6:].strip()
                        if new_name:
                            old_name = self.get_client_name(client_socket)
                            timestamp = self.get_timestamp()
                            print(f"{timestamp} {old_name} -> {new_name}")
                            self.broadcast(f"{old_name} is now {new_name}\n")
                            self.set_client_name(client_socket, new_name)
                    else:
                        self.send_to_client(client_socket, "Unknown command. /help for commands.\n")
                    continue
                
                timestamp = self.get_timestamp()
                sender_name = self.get_client_name(client_socket)
                print(f"{timestamp} [{sender_name}]: {message}")
                self.broadcast(f"{timestamp} [{sender_name}]: {message}\n", client_socket)
                
        except ConnectionResetError:
            pass
        except Exception as e:
            print(f"Client error: {e}")
        finally:
            timestamp = self.get_timestamp()
            client_name = self.get_client_name(client_socket)
            print(f"{timestamp} {client_name} left")
            self.broadcast(f"{client_name} left\n", client_socket)
            self.remove_client(client_socket)
            client_socket.close()
    
    def shutdown(self):
        self.running = False
        with self.clients_lock:
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


def main():
    import argparse
    parser = argparse.ArgumentParser(description='TCP Chat Server')
    parser.add_argument('--host', '-H', default=DEFAULT_IP, help=f'Host IP (default: {DEFAULT_IP})')
    parser.add_argument('--port', '-p', type=int, default=DEFAULT_PORT, help=f'Port (default: {DEFAULT_PORT})')
    args = parser.parse_args()
    
    server = ChatServer(args.host, args.port)
    server.start()


if __name__ == "__main__":
    main()
