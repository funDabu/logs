#! /usr/bin/bash

CONFIG_PATH="/home/xbus/Documents/nlp/config_bots"

echo "Content-Type:text/html"
echo 

IP_ADDRESS=$( echo $QUERY_STRING | sed "s/^ip_address=\(.*\)$/\1/" )
echo $IP_ADDRESS >> $CONFIG_PATH

echo "<html><head></head><body><p>Address $IP_ADDRESS was added.</p></body></html>"