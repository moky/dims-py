#!/usr/bin/bash

ps -fe | grep "\/srv\/dims\/station\/start.py" | grep -v grep
if [ $? -ne 0 ]
then
    time=`date +%Y%m%d-%H%M%S`
    stdbuf -oL /srv/dims/station/start.py >> /tmp/dims-${time}.log 2>&1 &
else
    echo "Station is running..."
fi
