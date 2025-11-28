# TCP/IP Chat Room

A multi-client chat application implemented in both C and Python.

## Features

- **Multi-client support**: Server handles 100+ concurrent clients
- **Real-time messaging**: Messages broadcast to all connected clients
- **Nicknames**: Set name on join, change with `/nick`
- **Commands**: `/list`, `/help`, `/quit`, `/nick <name>`
- **Timestamps**: All messages include timestamps
- **Concurrent I/O**: Clients can send and receive simultaneously
- **Clean shutdown**: Handles Ctrl+C gracefully

## Building

### C Version
```bash
cd c_code
make
```

### Python Version
No build required. Requires Python 3.6+.

## Usage

### Server

**C:**
```bash
./server [port] [ip]
./server              # Default: 127.0.0.1:2006
./server 8080         # Custom port
./server 8080 0.0.0.0 # Listen on all interfaces
```

**Python:**
```bash
python3 server.py [-H host] [-p port]
python3 server.py                    # Default: 127.0.0.1:2006
python3 server.py -p 8080            # Custom port
python3 server.py -H 0.0.0.0 -p 8080 # Listen on all interfaces
```

### Client

**C:**
```bash
./client [ip] [port]
./client                    # Connect to 127.0.0.1:2006
./client 192.168.1.100 8080 # Connect to custom server
```

**Python:**
```bash
python3 client.py [-H host] [-p port]
python3 client.py                       # Connect to 127.0.0.1:2006
python3 client.py -H 192.168.1.100 -p 8080
```

## Commands

| Command | Description |
|---------|-------------|
| `/nick <name>` | Change your nickname |
| `/list` | List online users |
| `/help` | Show available commands |
| `/quit` | Disconnect from server |

## Architecture

### C Implementation
- Uses POSIX threads (`pthread`) for concurrency
- Raw socket API with `select`-free design (blocking I/O per thread)
- Mutex-protected client list for thread safety
- Signal handlers for clean shutdown

### Python Implementation
- Uses `threading` module for concurrency
- Object-oriented design with `ChatServer` and `ChatClient` classes
- Thread-safe client management with locks
- `argparse` for command-line argument handling

## Testing

### Manual Test Cases

1. **Basic connectivity**
   - Start server: `./server`
   - Connect client: `./client`
   - Enter name when prompted
   - Verify "X joined" message appears

2. **Multi-client messaging**
   - Start server
   - Connect 3+ clients with different names
   - Send message from Client A
   - Verify all other clients receive it
   - Verify sender sees their own message with timestamp

3. **Client disconnect handling**
   - Connect multiple clients
   - Disconnect one client (Ctrl+C or `/quit`)
   - Verify "X left" message broadcast to others
   - Verify server continues running
   - Verify other clients can still send messages

4. **Nickname change**
   - Connect and set initial name
   - Type `/nick NewName`
   - Send a message
   - Verify message shows new name

5. **Server broadcast**
   - Connect clients
   - Type message in server console
   - Verify all clients receive "[Server]: message"

6. **Invalid connection**
   - Try `./client 192.168.1.254 9999`
   - Verify clear error message (connection refused/timeout)

7. **Clean shutdown**
   - Start server with connected clients
   - Press Ctrl+C on server
   - Verify server exits cleanly
   - Verify clients detect disconnection

8. **Cross-implementation compatibility**
   - Start C server
   - Connect Python client
   - Verify messaging works both directions
   - Repeat with Python server and C client

### Automated Test (Python)

```bash
cd python_code
python3 test_chat.py
```

## File Structure

```
tcpip_chatroom/
├── c_code/
│   ├── Makefile
│   ├── server.c
│   └── client.c
├── python_code/
│   ├── server.py
│   ├── client.py
│   └── test_chat.py
└── README.md
```

## Protocol

Messages are newline-delimited text. Format:
- Client → Server: `message\n`
- Server → Client: `timestamp [username]: message\n`
- System messages: `username joined\n` or `username left\n`

## Author

Martin McCorkle
