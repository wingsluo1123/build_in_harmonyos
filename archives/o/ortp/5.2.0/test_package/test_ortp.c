#include <stdio.h>
#include <ortp/ortp.h>
#include <ortp/rtpsession.h>

int main(void)
{
    RtpSession *session;

    ortp_init();
    ortp_scheduler_init();
    printf("ok: ortp_init\n");

    session = rtp_session_new(RTP_SESSION_RECVONLY);
    if (!session) {
        printf("FAIL: rtp_session_new\n");
        return 1;
    }
    printf("ok: rtp_session_new(RECVONLY)\n");

    rtp_session_set_scheduling_mode(session, TRUE);
    rtp_session_set_blocking_mode(session, FALSE);
    printf("ok: set_scheduling/blocking_mode\n");

    if (rtp_session_set_local_addr(session, "127.0.0.1", 0, 0) != 0) {
        printf("FAIL: set_local_addr(127.0.0.1)\n");
        rtp_session_destroy(session);
        ortp_exit();
        return 1;
    } else {
        printf("ok: set_local_addr(127.0.0.1)\n");
    }

    rtp_session_destroy(session);
    ortp_exit();
    printf("ok: rtp_session_destroy\n");

    printf("consumer test: PASS\n");
    return 0;
}
