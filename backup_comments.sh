#!/bin/bash
# This program requires gist: https://github.com/defunkt/gist
# Usage: backup_comments.sh [comments file] [file for storing URL] [wait time in between backups]

comments_file = CHECKED_COMMENTS.txt
backup_log = BACKUP_LOCATIONS.txt
sleep_time = 3600

if [ -z "$1" ]
  then
    comments_file = $1
    echo "Using specified comments file: " $(comments_file)
  else
    echo "Using default comments file: " $(comments_file)
fi

if [ -z "$2" ]
  then
    backup_log = $2
    echo "Storing backup locations in specified file: " $(backup_log)
  else
    echo "Storing backup locations in default file: " $(backup_log)
fi

if [ -z "$3" ]
  then
    sleep_time = $3
    echo "Using specified sleep time: " $(sleep_time)
  else
    echo "Using default sleep time: " $(sleep_time)
fi

  
while true
do
  echo "$(date): Backing up..."
  echo -n $(date) - $(gist $(comments_file)) >> $(backup_log)
  echo "$(date): Sleeping for " $(sleep_time) "seconds..."
  sleep $(sleep_time)
done
