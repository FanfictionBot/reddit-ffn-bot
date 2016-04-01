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
      echo "Using existing gist: $existing_gist"
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


# If there are differences between the current comments_file and the last backup (comments_file~),
# then we create a gist (or use an existing_gist ID, if specified (this requires logging into git using gist)).
# We store the location of our new gist in backup_log (or simply echo it if we're updating an existing gist.)
# Then, we replace comments_file~ with comments_file to reflect our changes. 
# Finally, we sleep for sleep_time.
  
while true
do
  if ! cmp "$comments_file" "${comments_file}~" >/dev/null 2>&1
    then
      echo "$(date): Differences found! Backing up..."
      if [ "$existing_gist" != "" ]
        then
          echo $(date) - $(gist -p -u $existing_gist -d "FanfictionBot Comment Backup: $date" "$comments_file")
        else
          echo $(date) - $(gist -d "FanfictionBot Comment Backup: $date" "$comments_file")\ >> "$backup_log"
      fi
      cp "$comments_file" "${comments_file}~"
    else
      echo "$(date): No differences found since last backup."
  fi
  echo "$(date): Sleeping for " $sleep_time "seconds..."
  sleep $sleep_time
done
