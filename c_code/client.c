#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <pthread.h>
#include <time.h>
#include <signal.h>

#define DEFAULT_IP "127.0.0.1"
#define DEFAULT_PORT 2006
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

void handle_signal(int sig) {
    running = 0;
    close(sockfd);
    printf("\nDisconnected.\n");
    exit(0);
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
            if (running) perror("recv");
            break;
        }
    }
    return NULL;
}

int main(int argc, char *argv[]) {
    struct sockaddr_in server_addr;
    char buffer[BUFFER_SIZE];
    pthread_t recv_thread;
    
    char *ip = DEFAULT_IP;
    int port = DEFAULT_PORT;
    
    if (argc >= 2) {
        ip = argv[1];
    }
    if (argc >= 3) {
        port = atoi(argv[2]);
        if (port <= 0 || port > 65535) {
            fprintf(stderr, "Invalid port. Using default %d\n", DEFAULT_PORT);
            port = DEFAULT_PORT;
        }
    }
    
    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }
    
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    if (inet_pton(AF_INET, ip, &server_addr.sin_addr) <= 0) {
        fprintf(stderr, "Invalid address: %s\n", ip);
        close(sockfd);
        exit(EXIT_FAILURE);
    }
    
    printf("Connecting to %s:%d...\n", ip, port);
    if (connect(sockfd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("connect");
        close(sockfd);
        exit(EXIT_FAILURE);
    }
    
    if (pthread_create(&recv_thread, NULL, receive_handler, NULL) != 0) {
        perror("pthread_create");
        close(sockfd);
        exit(EXIT_FAILURE);
    }
    
    while (running) {
        print_prompt();
        if (fgets(buffer, BUFFER_SIZE, stdin) == NULL) break;
        
        printf("\033[A\r\033[K");
        fflush(stdout);
        
        char temp[BUFFER_SIZE];
        strncpy(temp, buffer, BUFFER_SIZE);
        char *newline = strchr(temp, '\n');
        if (newline) *newline = '\0';
        
        if (strcmp(temp, "/quit") == 0) {
            send(sockfd, buffer, strlen(buffer), 0);
            running = 0;
            break;
        }
        
        if (strlen(my_name) == 0) {
            strncpy(my_name, temp, sizeof(my_name) - 1);
        } else if (strncmp(temp, "/nick ", 6) == 0) {
            strncpy(my_name, temp + 6, sizeof(my_name) - 1);
        } else if (temp[0] != '/') {
            char time_str[32];
            get_time(time_str, sizeof(time_str));
            printf("%s [%s]: %s\n", time_str, my_name, temp);
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
