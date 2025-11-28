#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <errno.h>
#include <time.h>
#include <pthread.h>
#include <signal.h>

#define DEFAULT_IP "127.0.0.1"
#define DEFAULT_PORT 2006
#define BACKLOG 10
#define MAX_CLIENTS 100
#define BUFFER_SIZE 1024
#define NAME_LEN 32
#define SERVER_NAME "Server"

typedef struct {
    int sockfd;
    char name[NAME_LEN];
    int active;
} Client;

Client clients[MAX_CLIENTS];
pthread_mutex_t clients_mutex = PTHREAD_MUTEX_INITIALIZER;
int server_fd;
volatile int running = 1;

void *handle_client(void *arg);
void *server_input_handler(void *arg);
void broadcast_message(char *message, int sender_fd);
void broadcast_to_all(char *message);
void print_time(char *buffer, size_t size);
int add_client(int sockfd);
void remove_client(int sockfd);
void set_client_name(int sockfd, const char *name);
char *get_client_name(int sockfd);
void print_prompt();
void handle_signal(int sig);
void list_clients(int client_fd);
void send_help(int client_fd);
int get_client_count();

void handle_signal(int sig) {
    printf("\nShutting down server...\n");
    running = 0;
    close(server_fd);
    exit(0);
}

int main(int argc, char *argv[]) {
    struct sockaddr_in server_addr, client_addr;
    socklen_t client_len = sizeof(client_addr);
    int opt = 1;
    
    char *ip = DEFAULT_IP;
    int port = DEFAULT_PORT;
    
    if (argc >= 2) {
        port = atoi(argv[1]);
        if (port <= 0 || port > 65535) {
            fprintf(stderr, "Invalid port. Using default %d\n", DEFAULT_PORT);
            port = DEFAULT_PORT;
        }
    }
    if (argc >= 3) {
        ip = argv[2];
    }

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    for (int i = 0; i < MAX_CLIENTS; i++) {
        clients[i].sockfd = -1;
        clients[i].active = 0;
        memset(clients[i].name, 0, NAME_LEN);
    }

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_port = htons(port);
    server_addr.sin_addr.s_addr = inet_addr(ip);

    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, BACKLOG) < 0) {
        perror("listen");
        close(server_fd);
        exit(EXIT_FAILURE);
    }

    printf("Server started on %s:%d\n", ip, port);

    pthread_t input_tid;
    if (pthread_create(&input_tid, NULL, server_input_handler, NULL) != 0) {
        perror("pthread_create for input");
    } else {
        pthread_detach(input_tid);
    }

    while (running) {
        int client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &client_len);
        if (client_fd < 0) {
            if (running) perror("accept");
            continue;
        }

        if (add_client(client_fd) < 0) {
            printf("Max clients reached.\n");
            close(client_fd);
            continue;
        }

        pthread_t tid;
        int *pclient = malloc(sizeof(int));
        *pclient = client_fd;
        
        if (pthread_create(&tid, NULL, handle_client, pclient) != 0) {
            perror("pthread_create");
            remove_client(client_fd);
            close(client_fd);
            free(pclient);
            continue;
        }
        
        pthread_detach(tid);
    }

    close(server_fd);
    return 0;
}

void print_time(char *buffer, size_t size) {
    time_t current_time = time(NULL);
    struct tm *tm_info = localtime(&current_time);
    snprintf(buffer, size, "%02d/%02d/%04d-%02d:%02d:%02d",
             tm_info->tm_mon + 1, tm_info->tm_mday, tm_info->tm_year + 1900,
             tm_info->tm_hour, tm_info->tm_min, tm_info->tm_sec);
}

int add_client(int sockfd) {
    pthread_mutex_lock(&clients_mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].active == 0) {
            clients[i].sockfd = sockfd;
            clients[i].active = 1;
            strcpy(clients[i].name, "Anonymous");
            pthread_mutex_unlock(&clients_mutex);
            return i;
        }
    }
    pthread_mutex_unlock(&clients_mutex);
    return -1;
}

void remove_client(int sockfd) {
    pthread_mutex_lock(&clients_mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].sockfd == sockfd) {
            clients[i].sockfd = -1;
            clients[i].active = 0;
            memset(clients[i].name, 0, NAME_LEN);
            break;
        }
    }
    pthread_mutex_unlock(&clients_mutex);
}

void set_client_name(int sockfd, const char *name) {
    pthread_mutex_lock(&clients_mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].sockfd == sockfd) {
            strncpy(clients[i].name, name, NAME_LEN - 1);
            clients[i].name[NAME_LEN - 1] = '\0';
            break;
        }
    }
    pthread_mutex_unlock(&clients_mutex);
}

char *get_client_name(int sockfd) {
    static char name[NAME_LEN];
    pthread_mutex_lock(&clients_mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].sockfd == sockfd) {
            strncpy(name, clients[i].name, NAME_LEN);
            pthread_mutex_unlock(&clients_mutex);
            return name;
        }
    }
    pthread_mutex_unlock(&clients_mutex);
    strcpy(name, "Unknown");
    return name;
}

int get_client_count() {
    int count = 0;
    pthread_mutex_lock(&clients_mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].active) count++;
    }
    pthread_mutex_unlock(&clients_mutex);
    return count;
}

void list_clients(int client_fd) {
    char list_msg[BUFFER_SIZE] = "Online users: ";
    pthread_mutex_lock(&clients_mutex);
    int first = 1;
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].active) {
            if (!first) strcat(list_msg, ", ");
            strcat(list_msg, clients[i].name);
            first = 0;
        }
    }
    strcat(list_msg, "\n");
    pthread_mutex_unlock(&clients_mutex);
    send(client_fd, list_msg, strlen(list_msg), 0);
}

void send_help(int client_fd) {
    char *help = "Commands: /nick <name>, /list, /help, /quit\n";
    send(client_fd, help, strlen(help), 0);
}

void broadcast_message(char *message, int sender_fd) {
    pthread_mutex_lock(&clients_mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].active && clients[i].sockfd != sender_fd) {
            send(clients[i].sockfd, message, strlen(message), 0);
        }
    }
    pthread_mutex_unlock(&clients_mutex);
}

void broadcast_to_all(char *message) {
    pthread_mutex_lock(&clients_mutex);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients[i].active) {
            send(clients[i].sockfd, message, strlen(message), 0);
        }
    }
    pthread_mutex_unlock(&clients_mutex);
}

void print_prompt() {
    printf("\r\033[K> ");
    fflush(stdout);
}

void *server_input_handler(void *arg) {
    char buffer[BUFFER_SIZE];
    char message[BUFFER_SIZE + NAME_LEN + 64];
    char time_str[32];
    
    while (running) {
        print_prompt();
        if (fgets(buffer, BUFFER_SIZE, stdin) == NULL) break;
        
        char *newline = strchr(buffer, '\n');
        if (newline) *newline = '\0';
        if (strlen(buffer) == 0) continue;
        
        if (strcmp(buffer, "/quit") == 0) {
            handle_signal(SIGINT);
        }
        if (strcmp(buffer, "/list") == 0) {
            printf("Online users (%d):\n", get_client_count());
            pthread_mutex_lock(&clients_mutex);
            for (int i = 0; i < MAX_CLIENTS; i++) {
                if (clients[i].active) printf("  - %s\n", clients[i].name);
            }
            pthread_mutex_unlock(&clients_mutex);
            continue;
        }
        if (strcmp(buffer, "/help") == 0) {
            printf("Commands: /list, /quit, /help, or type message to broadcast\n");
            continue;
        }
        
        print_time(time_str, sizeof(time_str));
        printf("\r\033[K%s [%s]: %s\n", time_str, SERVER_NAME, buffer);
        snprintf(message, sizeof(message), "%s [%s]: %s\n", time_str, SERVER_NAME, buffer);
        broadcast_to_all(message);
    }
    return NULL;
}

void *handle_client(void *arg) {
    int client_fd = *((int *)arg);
    free(arg);
    
    char buffer[BUFFER_SIZE];
    char message[BUFFER_SIZE + NAME_LEN + 64];
    char time_str[32];
    int bytes_received;
    int named = 0;
    
    char *welcome = "Enter name: ";
    send(client_fd, welcome, strlen(welcome), 0);
    
    while ((bytes_received = recv(client_fd, buffer, BUFFER_SIZE - 1, 0)) > 0) {
        buffer[bytes_received] = '\0';
        
        char *newline = strchr(buffer, '\n');
        if (newline) *newline = '\0';
        newline = strchr(buffer, '\r');
        if (newline) *newline = '\0';
        
        if (strlen(buffer) == 0) continue;
        
        if (!named) {
            set_client_name(client_fd, buffer);
            named = 1;
            print_time(time_str, sizeof(time_str));
            printf("%s %s joined\n", time_str, buffer);
            snprintf(message, sizeof(message), "%s joined\n", buffer);
            broadcast_message(message, -1);
            continue;
        }
        
        if (buffer[0] == '/') {
            if (strcmp(buffer, "/quit") == 0) break;
            if (strcmp(buffer, "/list") == 0) { list_clients(client_fd); continue; }
            if (strcmp(buffer, "/help") == 0) { send_help(client_fd); continue; }
            if (strncmp(buffer, "/nick ", 6) == 0) {
                char *new_name = buffer + 6;
                if (strlen(new_name) > 0) {
                    char *old_name = get_client_name(client_fd);
                    print_time(time_str, sizeof(time_str));
                    printf("%s %s -> %s\n", time_str, old_name, new_name);
                    snprintf(message, sizeof(message), "%s is now %s\n", old_name, new_name);
                    broadcast_message(message, -1);
                    set_client_name(client_fd, new_name);
                }
                continue;
            }
            char *unknown = "Unknown command. /help for commands.\n";
            send(client_fd, unknown, strlen(unknown), 0);
            continue;
        }
        
        print_time(time_str, sizeof(time_str));
        char *sender_name = get_client_name(client_fd);
        printf("%s [%s]: %s\n", time_str, sender_name, buffer);
        snprintf(message, sizeof(message), "%s [%s]: %s\n", time_str, sender_name, buffer);
        broadcast_message(message, client_fd);
    }
    
    print_time(time_str, sizeof(time_str));
    char *client_name = get_client_name(client_fd);
    printf("%s %s left\n", time_str, client_name);
    snprintf(message, sizeof(message), "%s left\n", client_name);
    broadcast_message(message, client_fd);
    
    remove_client(client_fd);
    close(client_fd);
    return NULL;
}
