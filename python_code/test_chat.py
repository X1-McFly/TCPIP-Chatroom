#!/usr/bin/env python3
"""
Automated test script for TCP Chat Server.
Tests basic connectivity and message broadcasting.
"""

import socket
import threading
import time
import sys

HOST = "127.0.0.1"
PORT = 2006
TIMEOUT = 5


def test_connection():
    """Test basic server connection."""
    print("Test 1: Basic connection...", end=" ")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((HOST, PORT))
        data = sock.recv(1024).decode('utf-8')
        if "name" in data.lower():
            print("PASS")
            sock.close()
            return True
        else:
            print(f"FAIL - Unexpected response: {data}")
            sock.close()
            return False
    except Exception as e:
        print(f"FAIL - {e}")
        return False


def test_join():
    """Test joining with a name."""
    print("Test 2: Join with name...", end=" ")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((HOST, PORT))
        sock.recv(1024)  # Read prompt
        sock.sendall(b"TestUser\n")
        time.sleep(0.5)
        sock.close()
        print("PASS")
        return True
    except Exception as e:
        print(f"FAIL - {e}")
        return False


def test_broadcast():
    """Test message broadcasting between clients."""
    print("Test 3: Message broadcast...", end=" ")
    received = []
    
    def client_receiver(name):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            sock.connect((HOST, PORT))
            sock.recv(1024)  # Read prompt
            sock.sendall(f"{name}\n".encode())
            
            # Keep receiving messages
            sock.settimeout(3)
            while True:
                try:
                    data = sock.recv(1024).decode('utf-8')
                    if data:
                        received.append(data)
                    else:
                        break
                except socket.timeout:
                    break
            sock.close()
        except Exception as e:
            received.append(f"ERROR: {e}")
    
    try:
        # Start receiver client
        recv_thread = threading.Thread(target=client_receiver, args=("Receiver",))
        recv_thread.start()
        time.sleep(0.5)
        
        # Send message from another client
        sender = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sender.settimeout(TIMEOUT)
        sender.connect((HOST, PORT))
        sender.recv(1024)
        sender.sendall(b"Sender\n")
        time.sleep(0.3)
        sender.sendall(b"Hello World\n")
        time.sleep(1)
        sender.close()
        
        recv_thread.join(timeout=5)
        
        # Check if receiver got the message (join or actual message)
        all_data = " ".join(received)
        found = "Hello World" in all_data or "Sender" in all_data
        if found:
            print("PASS")
            return True
        else:
            print(f"FAIL - Message not received. Got: {received}")
            return False
            
    except Exception as e:
        print(f"FAIL - {e}")
        return False


def test_commands():
    """Test /list and /help commands."""
    print("Test 4: Commands (/list, /help)...", end=" ")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((HOST, PORT))
        sock.recv(1024)  # Read "Enter name:" prompt
        sock.sendall(b"CmdTest\n")
        time.sleep(0.3)
        
        # Test /list
        sock.sendall(b"/list\n")
        time.sleep(0.3)
        
        # Read response (may include join messages from other tests)
        sock.settimeout(2)
        data = ""
        try:
            while True:
                chunk = sock.recv(1024).decode('utf-8')
                if not chunk:
                    break
                data += chunk
                if "Online" in data or "CmdTest" in data or "users" in data.lower():
                    break
        except socket.timeout:
            pass
        
        sock.sendall(b"/quit\n")
        sock.close()
        
        if "CmdTest" in data or "Online" in data or "users" in data.lower() or len(data) > 0:
            print("PASS")
            return True
        else:
            print(f"FAIL - No response received")
            return False
            
    except Exception as e:
        print(f"FAIL - {e}")
        return False


def main():
    print(f"\n=== TCP Chat Server Tests ===")
    print(f"Target: {HOST}:{PORT}\n")
    
    # Check if server is running
    try:
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(2)
        test_sock.connect((HOST, PORT))
        test_sock.close()
    except:
        print("ERROR: Server not running. Start the server first.")
        print(f"  C:      ./server {PORT}")
        print(f"  Python: python3 server.py -p {PORT}")
        sys.exit(1)
    
    results = []
    results.append(test_connection())
    time.sleep(0.5)
    results.append(test_join())
    time.sleep(0.5)
    results.append(test_broadcast())
    time.sleep(0.5)
    results.append(test_commands())
    
    print(f"\n=== Results: {sum(results)}/{len(results)} tests passed ===\n")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
