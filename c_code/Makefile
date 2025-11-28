CC = gcc
CFLAGS = -Wall -pthread
TARGET = server client

all: $(TARGET)

server: server.c
	$(CC) $(CFLAGS) server.c -o server

client: client.c
	$(CC) $(CFLAGS) client.c -o client

clean:
	rm -f $(TARGET)

.PHONY: all clean