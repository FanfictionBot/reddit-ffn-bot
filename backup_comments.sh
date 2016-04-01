#!/bin/bash
# This script requires gist: https://github.com/defunkt/gist

usage() { 
  echo "Usage: $0 [-i <comments_file>] [-o <backup_log>] [-s <sleep_time>] [-a <github_auth>] [-e <existing_gist>]" 1>&2 
  echo "  -i: checked_comments input; defaults to 'CHECKED_COMMENTS.txt' (this is the file containing checked comments)"
  echo "  -o: backup_locations output; defaults to 'BACKUP_LOCATIONS.txt' (this is where your gist ID/urls will be stored)"
  echo "  -s: sleep_time; defaults to 3600 (this is how long we'll wait before backing up)"
  echo "  -a: github_auth; use this if you want to authenticate gist with GitHub - this is required to modify an existing gist"
  echo "  -e: existing_gist; this is the full ID of the gist you want to modify or update"
  exit 1
}

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
      echo "$(date) - Using existing gist: $existing_gist"\ >> "$backup_log"
      ;;
    *)
      usage
      ;;
  esac
done

echo "(INIT) Using existing_gist:   $existing_gist"
echo "(INIT) Using comments_file:   $comments_file"
echo "(INIT) Logging in backup_log: $backup_log"
echo "(INIT) Using sleep_time:      $sleep_time"

# If it doesn't exist, create comments_file~ to check if comments_file has changed since our last backup.
if [ ! -e "${comments_file}~" ] ; then
  echo "(INIT) Creating a local backup of the comments file..."
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
      echo "(BACKUP) $(date): Differences found! Backing up..."
      if [ "$existing_gist" != "" ]
        then
          echo (BACKUP) $(date) - $(gist -p -u $existing_gist -d "FanfictionBot Comment Backup: $date" "$comments_file")
        else
          echo $(date) - $(gist -d "FanfictionBot Comment Backup: $date" "$comments_file")\ >> "$backup_log"
      fi
      cp "$comments_file" "${comments_file}~"
    else
      echo "(BACKUP) $(date): No differences found since last backup."
  fi
  echo "(SLEEP) $(date): Sleeping for $sleep_time seconds..."
  sleep $sleep_time
done
