#!/bin/bash
# This script requires gist: https://github.com/defunkt/gist

usage() { echo "Usage: $0 [-i <comment file in>] [-o <log file out>] [-s <seconds to sleep>] [-a <Login to GitHub? TRUE|FALSE>] [-e <existing Gist id (requires login)>]" 1>&2; exit 1; }
comments_file=CHECKED_COMMENTS.txt
backup_log=BACKUP_LOCATIONS.txt
sleep_time=3600
existing_gist=""

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
        a)
            gist --login
            ;;
        e)
            existing_gist=${OPTARG}
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
  if [ "$existing_gist" != "" ]
    then
      echo "Using existing gist ID: $existing_gist"
      echo $(date) - $(gist -p -u $existing_gist -d "FanfictionBot Comment Backup: $date" $comments_file)\ >> $backup_log
    else
      echo $(date) - $(gist -d "FanfictionBot Comment Backup: $date" $comments_file)\ >> $backup_log
  fi
  echo "$(date): Sleeping for " $sleep_time "seconds..."
  sleep $sleep_time
done
