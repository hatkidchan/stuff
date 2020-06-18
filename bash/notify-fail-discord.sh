#!/bin/bash
# Usage: bash notify-fail-discord.sh 1.2.3.4 https://discord-webhook
HOST_IP="$1";
WEBHOOK="$2";
MAX_ATTEMPTS="${3:-8}";
TIMEOUT=1;
INTERVAL=1;
USERNAME="Server panic";
PANIC="panik";
CALM="kalm";
panic() {
    curl -H "Content-Type: application/json" \
         -X POST \
         -d "{\"username\": \"$USERNAME\", \"content\": \"$PANIC\"}" \
         "$WEBHOOK";
}
calm() {
    curl -H "Content-Type: application/json" \
         -X POST \
         -d "{\"username\": \"$USERNAME\", \"content\": \"$CALM\"}" \
         "$WEBHOOK";
}

failed=0;
locked=0;
while true; do
    if ! ping=$(ping -n -c 1 -W $TIMEOUT $HOST_IP 2>/dev/null); then
        failed=$(($failed + 1));
        printf "[%3d] connection failed\n" $failed;
        if [ "$failed" -ge "$MAX_ATTEMPTS" ]; then
            if [ "$locked" -eq 0 ]; then
                locked=1;
                echo $PANIC;
                panic;
            fi;
        fi;
    else
        echo '[---] Ping OK';
        if [ "$locked" -eq 1 ]; then
            echo $CALM;
            calm;
        fi;
        locked=0;
        failed=0;
    fi;
    sleep $INTERVAL;
done;
