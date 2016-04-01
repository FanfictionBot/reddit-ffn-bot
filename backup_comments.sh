#!/bin/bash
# This program requires gist: https://github.com/defunkt/gist

usage() { echo "Usage: $0 [-i <comment file in>] [-o <log file out>] [-s <seconds to sleep>]" 1>&2; exit 1; }
comments_file=CHECKED_COMMENTS.txt
backup_log=BACKUP_LOCATIONS.txt
sleep_time=3600

while getopts ":i:o:s:" o; do
    case "${o}" in
        i)
            comments_file=${OPTARG}
            ;;
        o)
            backup_log=${OPTARG}
            ;;
        s)
            sleep_time=${OPTARG}
            ;;        
        *)
            usage
            ;;
    esac
done

echo "Using comments file: " $comments_file
echo "Storing backup locations in file: " $backup_log
echo "Using sleep time: " $sleep_time

  
while true
do
  echo "$(date): Backing up..."
  echo -n $(date) - $(gist $comments_file) >> $backup_log
  echo "$(date): Sleeping for " $sleep_time "seconds..."
  sleep $sleep_time
done
