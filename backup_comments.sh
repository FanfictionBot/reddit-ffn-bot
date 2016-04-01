#!/bin/bash
# This script requires gist: https://github.com/defunkt/gist

usage() { echo "Usage: $0 [-i <comment file in>] [-o <log file out>] [-s <seconds to sleep>] [-a <Login to GitHub? TRUE|FALSE>] [-e <existing Gist id (requires login)>]" 1>&2; exit 1; }
comments_file=CHECKED_COMMENTS.txt
backup_log=BACKUP_LOCATIONS.txt
sleep_time=3600
existing_gist=""

while getopts ":i:o:s:a:e:" o; do
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
      echo "Using existing gist: $existing_gist"\ >> "$backup_log"
      ;;
    *)
      usage
      ;;
  esac
done

echo "Using comments file: " $comments_file
echo "Storing backup locations in file: " $backup_log
echo "Using sleep time: " $sleep_time

if [ ! -e "${comments_file}~" ] ; then
  echo "Creating a local backup of the comments file..."
  touch "${comments_file}~"
fi

  
while true
do
  if ! cmp "$comments_file" "${comments_file}~" >/dev/null 2>&1 # Only update if comment files and last gist are different
    echo "$(date): Differences found! Backing up..."
    if [ "$existing_gist" != "" ] # If we're using an existing gist,
      then # Use the existing gist (requires github login through gist)
        echo $(date) - $(gist -p -u $existing_gist -d "FanfictionBot Comment Backup: $date" "$comments_file")
      else # Else, create a new gist
        echo $(date) - $(gist -d "FanfictionBot Comment Backup: $date" "$comments_file")\ >> "$backup_log"
    fi
    cp "$comments_file" "${comments_file}~" # Update our comparison backup to reflect changes
  fi
  echo "$(date): Sleeping for " $sleep_time "seconds..."
  sleep $sleep_time
done
