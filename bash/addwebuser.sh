#!/bin/bash
# I think getopts is a little overkill for this small script..
# Created by @hatkidchan
# https://github.com/hatkidchan/stuff/tree/master/bash/addwebuser.sh

usage() {
    echo "Usage: $0 [-h] [-u <username>] [-p password] [-b base]  [-f mode:path]
Options:
  -h             show this help
  -b <homepath>  set default home (default: $homepath)
  -u <username>  set username (by default from stdin)
  -p <password>  set password (by default from stdin)
  -f <mode:path> add folder with <mode>

Examples:
  $0 -u tester -p 0000 -f 644:www/assets
    Will create user 'tester' with password '0000', default folders set and
    folder at '\$HOME/www/assets' with permissions 644 (rw-r--r--)

  $0 -u secret -f 700:www/public_html -f 700:www/logs -f 700:www/tmp
    Will create user 'secret', password from stdin, all default folders
    permissions will be (rwx------)

Default folders:
  ${!folders[@]}
  ${folders[@]}
" 1>&2;
    exit 1;
}

fail() {
    echo $* 1>&2; exit 2;
}

username="";
password="";
homepath="/home";
declare -A folders=(
    [www/public_html]=755
    [www/logs]=777
    [www/tmp]=777
)

while getopts "hb:u:p:f:" k; do
    case "$k" in
        h) usage;;
        b) homepath="${OPTARG}";;
        u) username="${OPTARG}";;
        p) password="${OPTARG}";;
        f) IFS=':' read mode path <<<"${OPTARG}";
           folders["${path}"]="$mode";;
        *) usage;;
    esac;
done;

while [[ "$username" == "" ]]; do
    read -p "Username: " username;
done;

while [[ "$password" == "" ]]; do
    read -sp "Password: " password;
done;

useradd "$username" -p "$password" -b "$homepath" -mUs /bin/false \
    || fail "Failed to create user";

for path in "${!folders[@]}"; do
    mkdir -pm "${folders[$path]}" "$homepath/$username/$path";
done;
chown -R $username:$username "$homepath/$username";

