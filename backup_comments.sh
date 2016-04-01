#!/bin/bash
# This program requires gist: https://github.com/defunkt/gist
# Usage: Pass in the file you'd like to back up

while true
do
  if [ -z "$1" ]
    then
      gist $1 > backup_location.txt
    else
      gist ./CHECKED_COMMENTS.txt > backup_location.txt
  fi
  sleep 3600
done
