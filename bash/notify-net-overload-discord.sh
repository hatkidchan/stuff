#!/bin/bash
WEBHOOK="https://discordapp/api/webhooks/12345/CHANGEME";
USERNAME="PKPS panic";
MESSAGE_RX="Too many RX packets (%d)";
MESSAGE_TX="Too many TX packets (%d)";
INTERVAL=1;
THRESHOLD_RX=10000;  # in packets per interval, not second
THRESHOLD_TX=-1;  # -1 means ignore
INTERFACES=(eth0 wlan0);



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

get_packets() {
    local rx_packets=0;
    local tx_packets=0;
    for iface in "${INTERFACES[@]}"; do
        if [[ -d "/sys/class/net/$iface" ]]; then
            rx_cur=$(cat "/sys/class/net/$iface/statistics/rx_packets");
            tx_cur=$(cat "/sys/class/net/$iface/statistics/tx_packets");
            rx_packets=$(($rx_packets + $rx_cur));
            tx_packets=$(($tx_packets + $tx_cur));
        fi;
    done;
    echo $rx_packets $tx_packets;
}

read last_packets_rx last_packets_tx <<< "$(get_packets)";
while sleep $INTERVAL; do
    read packets_rx packets_tx <<< "$(get_packets)";
    delta_prx=$(($packets_rx - $last_packets_rx));
    delta_ptx=$(($packets_tx - $last_packets_tx));
    echo "$delta_prx $delta_ptx";
    
    [ "$delta_prx" -ge "$THRESHOLD_RX" ] \
        && [ "$THRESHOLD_RX" -gt 0 ] \
        && notify "$(printf "$MESSAGE_RX" $delta_prx)";

    [ "$delta_ptx" -ge "$THRESHOLD_TX" ] \
        && [ "$THRESHOLD_TX" -gt 0 ] \
        && notify "$(printf "$MESSAGE_TX" $delta_ptx)";

    last_packets_rx=$packets_rx;
    last_packets_tx=$packets_tx;
done;
