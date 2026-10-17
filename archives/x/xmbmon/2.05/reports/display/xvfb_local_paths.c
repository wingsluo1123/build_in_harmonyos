/* Process-local deployment adapter for the unmodified official Xvfb binary.
 * Redirect its known xkbcomp command and restrict display 205 to loopback.
 * This file belongs to the display harness, not the xmbmon source recipe. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <netinet/in.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int execl(const char *path, const char *arg, ...) {
    char *args[32]; size_t n=0; va_list ap;
    args[n++]=(char *)arg; va_start(ap,arg);
    while(n<31 && (args[n]=va_arg(ap,char *)) != NULL) n++;
    va_end(ap);
    if(n==31) {errno=E2BIG;return -1;}
    const char *old="\"/storage/Users/currentUser/usr/local/bin/xkbcomp\"";
    const char *replacement=getenv("X205_XKBCOMP");
    if(n==3 && !strcmp(path,"/bin/sh") && !strcmp(args[1],"-c") &&
       replacement && strncmp(args[2],old,strlen(old))==0) {
        char *cmd=NULL;
        if(asprintf(&cmd,"\"%s\"%s",replacement,args[2]+strlen(old))<0)return -1;
        fprintf(stderr,"X205 xkb command: %s\n",cmd);
        args[2]=cmd;
        execv(path,args);int e=errno;free(cmd);errno=e;return -1;
    }
    return execv(path,args);
}

int bind(int fd,const struct sockaddr *address,socklen_t length) {
    int (*real_bind)(int,const struct sockaddr *,socklen_t)=dlsym(RTLD_NEXT,"bind");
    if(address->sa_family==AF_INET && length>=sizeof(struct sockaddr_in)) {
        struct sockaddr_in local=*(const struct sockaddr_in *)address;
        if(ntohs(local.sin_port)==6205) {
            local.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
            return real_bind(fd,(const struct sockaddr *)&local,sizeof(local));
        }
    }
    if(address->sa_family==AF_INET6 && length>=sizeof(struct sockaddr_in6)) {
        struct sockaddr_in6 local=*(const struct sockaddr_in6 *)address;
        if(ntohs(local.sin6_port)==6205) {
            local.sin6_addr=in6addr_loopback;
            return real_bind(fd,(const struct sockaddr *)&local,sizeof(local));
        }
    }
    return real_bind(fd,address,length);
}
