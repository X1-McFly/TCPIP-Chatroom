import socket
import threading
import sys

from datetime import datetime

IP = "127.0.0.1"
PORT = 2006
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
    
    def receive_handler(self):
        """Thread function to receive messages from server"""
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
                # Socket was closed
                break
            except Exception as e:
                if self.running:
                    print(f"\nReceive error: {e}")
                break
    
    def start(self):
        if not self.connect():
            return
        
        # Start receive thread
        recv_thread = threading.Thread(target=self.receive_handler, daemon=True)
        recv_thread.start()
        
        # Main loop - send messages
        try:
            while self.running:
                self.print_prompt()
                message = input()
                self.clear_line()  # Clear the typed input line
                print("\033[A\r\033[K", end='', flush=True)  # Move up and clear prompt line
                
                if not self.running:
                    break
                
                # Check for exit command
                if message in [':exit', ':quit']:
                    try:
                        self.socket.sendall(message.encode('utf-8'))
                    except:
                        pass
                    break
                
                # Store name from first message, don't print it
                if not self.my_name:
                    self.my_name = message
                else:
                    # Show own message with timestamp
                    timestamp = self.get_timestamp()
                    print(f"{timestamp} [{self.my_name}]: {message}")
                
                try:
                    self.socket.sendall((message + '\n').encode('utf-8'))
                except:
                    print("Failed to send message.")
                    break
                    
        except KeyboardInterrupt:
            print("\nClosing connection...")
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
    client = ChatClient(IP, PORT)
    client.start()


if __name__ == "__main__":
    main()
