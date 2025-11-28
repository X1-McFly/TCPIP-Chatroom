#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <pthread.h>
#include <time.h>

#define IP "127.0.0.1"
#define PORT 2006
#define BUFFER_SIZE 1024

int sockfd;
volatile int running = 1;
char my_name[64] = "";

void get_time(char *buffer, size_t size) {
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    snprintf(buffer, size, "%02d/%02d/%04d-%02d:%02d:%02d",
             tm_info->tm_mon + 1, tm_info->tm_mday, tm_info->tm_year + 1900,
             tm_info->tm_hour, tm_info->tm_min, tm_info->tm_sec);
}

void print_prompt() {
    printf("> ");
    fflush(stdout);
}

void clear_line() {
    printf("\r\033[K");
    fflush(stdout);
}

void *receive_handler(void *arg) {
    char buffer[BUFFER_SIZE];
    int bytes;
    
    while (running) {
        bytes = recv(sockfd, buffer, BUFFER_SIZE - 1, 0);
        if (bytes > 0) {
            buffer[bytes] = '\0';
            clear_line();
            printf("%s", buffer);
            print_prompt();
        } else if (bytes == 0) {
            printf("\nDisconnected from server.\n");
            running = 0;
            break;
        } else {
            if (running) {
                perror("recv");
            }
            break;
        }
    }
    
    return NULL;
}

int main() {
    struct sockaddr_in server_addr;
    char buffer[BUFFER_SIZE];
    pthread_t recv_thread;
    
    // Create socket
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }
    
    // Set up server address
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(PORT);
    server_addr.sin_addr.s_addr = inet_addr(IP);
    
    // Connect to server
    if (connect(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("connect");
        close(sockfd);
        exit(EXIT_FAILURE);
    }
    
    // Start receive thread
    if (pthread_create(&recv_thread, NULL, receive_handler, NULL) != 0) {
        perror("pthread_create");
        close(sockfd);
        exit(EXIT_FAILURE);
    }
    
    // Main loop - send messages
    while (running) {
        print_prompt();
        if (fgets(buffer, BUFFER_SIZE, stdin) == NULL) {
            break;
        }
        
        // Clear the typed input line (move up, clear line)
        printf("\033[A\r\033[K");
        fflush(stdout);
        
        // Check for exit command before sending
        char temp[BUFFER_SIZE];
        strncpy(temp, buffer, BUFFER_SIZE);
        char *newline = strchr(temp, '\n');
        if (newline) *newline = '\0';
        
        if (strcmp(temp, ":exit") == 0 || strcmp(temp, ":quit") == 0) {
            send(sockfd, buffer, strlen(buffer), 0);
            running = 0;
            break;
        }
        
        // Store name from first message
        if (strlen(my_name) == 0) {
            strncpy(my_name, temp, sizeof(my_name) - 1);
        } else {
            // Show own message with timestamp
            char time_str[32];
            get_time(time_str, sizeof(time_str));
            printf("\r\033[K%s [%s]: %s\n", time_str, my_name, temp);
        }
        
        if (send(sockfd, buffer, strlen(buffer), 0) < 0) {
            perror("send");
            break;
        }
    }
    
    running = 0;
    close(sockfd);
    pthread_cancel(recv_thread);
    pthread_join(recv_thread, NULL);
    
    return 0;
}