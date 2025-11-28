import socket
import threading
from datetime import datetime

IP = "127.0.0.1"
PORT = 2006
BUFFER_SIZE = 1024
MAX_CLIENTS = 100
SERVER_NAME = "Server"


class ChatServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {socket: {'name': name, 'address': addr}}
        self.clients_lock = threading.Lock()
        self.running = False
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(MAX_CLIENTS)
            self.running = True
            
            print(f"Server started on port {self.port}")
            
            # Start server input thread
            input_thread = threading.Thread(
                target=self.server_input_handler,
                daemon=True
            )
            input_thread.start()
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    
                    # Start a thread to handle this client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"Error accepting connection: {e}")
                        
        except KeyboardInterrupt:
            print("\nServer stopping...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.shutdown()
    
    def get_timestamp(self):
        return datetime.now().strftime("%m/%d/%Y-%H:%M:%S")
    
    def add_client(self, client_socket, address, name="Anonymous"):
        with self.clients_lock:
            self.clients[client_socket] = {
                'name': name,
                'address': address
            }
    
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
            if client_socket in self.clients:
                return self.clients[client_socket]['name']
            return "Unknown"
    
    def broadcast(self, message, sender_socket=None):
        """Send message to all clients except the sender"""
        with self.clients_lock:
            disconnected = []
            for client_socket in self.clients:
                if client_socket != sender_socket:
                    try:
                        client_socket.sendall(message.encode('utf-8'))
                    except:
                        disconnected.append(client_socket)
            
            # Clean up disconnected clients
            for sock in disconnected:
                del self.clients[sock]
    
    def broadcast_to_all(self, message):
        """Send message to all connected clients"""
        with self.clients_lock:
            disconnected = []
            for client_socket in self.clients:
                try:
                    client_socket.sendall(message.encode('utf-8'))
                except:
                    disconnected.append(client_socket)
            
            for sock in disconnected:
                del self.clients[sock]
    
    def print_prompt(self):
        print("\r\033[K> ", end='', flush=True)
    
    def server_input_handler(self):
        """Handle server console input for broadcasting messages"""
        while self.running:
            try:
                self.print_prompt()
                message = input()
                
                if not message:
                    continue
                
                # Check for server commands
                if message in [':quit', ':exit']:
                    self.shutdown()
                    import os
                    os._exit(0)
                
                # Broadcast server message
                timestamp = self.get_timestamp()
                print(f"\r\033[K{timestamp} [{SERVER_NAME}]: {message}")
                
                broadcast_msg = f"{timestamp} [{SERVER_NAME}]: {message}\n"
                self.broadcast_to_all(broadcast_msg)
                
            except EOFError:
                break
            except Exception as e:
                if self.running:
                    print(f"Input error: {e}")
                break
    
    def handle_client(self, client_socket, address):
        """Handle a single client connection"""
        self.add_client(client_socket, address)
        named = False
        
        try:
            # Send welcome message
            welcome = "Enter name: "
            client_socket.sendall(welcome.encode('utf-8'))
            
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                
                message = data.decode('utf-8').strip()
                
                # Skip empty messages
                if not message:
                    continue
                
                # First message is the name
                if not named:
                    self.set_client_name(client_socket, message)
                    named = True
                    
                    timestamp = self.get_timestamp()
                    print(f"{timestamp} {message} joined")
                    
                    join_msg = f"{message} joined\n"
                    self.broadcast(join_msg)
                    continue
                
                # Check for exit command
                if message in [':exit', ':quit']:
                    break
                
                # Format and broadcast message
                timestamp = self.get_timestamp()
                sender_name = self.get_client_name(client_socket)
                
                print(f"{timestamp} [{sender_name}]: {message}")
                
                broadcast_msg = f"{timestamp} [{sender_name}]: {message}\n"
                self.broadcast(broadcast_msg, client_socket)
                
        except ConnectionResetError:
            pass
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            # Client disconnected
            timestamp = self.get_timestamp()
            client_name = self.get_client_name(client_socket)
            print(f"{timestamp} {client_name} left")
            
            leave_msg = f"{client_name} left\n"
            self.broadcast(leave_msg, client_socket)
            
            self.remove_client(client_socket)
            client_socket.close()
    
    def shutdown(self):
        self.running = False
        
        # Close all client connections
        with self.clients_lock:
            for client_socket in list(self.clients.keys()):
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass


def main():
    server = ChatServer(IP, PORT)
    server.start()


if __name__ == "__main__":
    main()
