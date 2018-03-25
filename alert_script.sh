#!/bin/bash

echo "$1" >> /tmp/alert.txt
echo "$2" >> /tmp/alert.txt
echo "$3" >> /tmp/alert.txt

/usr/bin/curl -d '{"subject":"'"$2"'","message":"'"$3"'"}' -H "Content-Type:application/json" -X POST 'http://'$1
