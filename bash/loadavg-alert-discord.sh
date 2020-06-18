#!/bin/bash
WEBHOOK="https://discordapp/api/webhooks/12345/CHANGEME";
USERNAME="LoadAVG panic";
THRESHOLD_WARN="5.0";
THRESHOLD_IDLE="4.9";
MESSAGE_WARN="Server load (%s) above threshold.";
MESSAGE_CALM="Server load (%s) is fine now.";
INTERVAL=1;

notify() {
    if echo "$WEBHOOK" | grep CHANGEME >/dev/null; then
        echo "[!] webhook is not set correctly";
    else
        curl -H "Content-Type: application/json" \
             -X POST \
            -d "{\"username\": \"$USERNAME\", \"content\": \"$1\"}" \
            "$WEBHOOK";
    fi;
}

threshold_passed=0;
while sleep $INTERVAL; do
    IFS=' ' read LAVG_1 LAVG_5 LAVG_15 KSCH LASTPID </proc/loadavg;
    if (( $(echo "$LAVG_1 > $THRESHOLD_WARN" | bc -l) )); then
        MESSAGE=$(printf "$MESSAGE_WARN" "$LAVG_1");
        echo $MESSAGE;
        if [ "$threshold_passed" -eq 0 ]; then
            notify "$MESSAGE";
            threshold_passed=1;
        fi
    fi;
    if (( $(echo "$LAVG_1 < $THRESHOLD_IDLE" | bc -l) )); then
        MESSAGE=$(printf "$MESSAGE_CALM" "$LAVG_1");
        echo $MESSAGE;
        if [ "$threshold_passed" -eq 1 ]; then
            notify "$MESSAGE";
            threshold_passed=0;
        fi;
    fi;
done;
