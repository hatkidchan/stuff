#!/bin/bash
# Simple script for downloading albums from downloads.khinsider.com
# Requirements: wget and grep

albums_url=();
separate_folders="no";

usage() {
    echo "Usage: $0 -h -s -a <url> [-a <url> ...]

Parameters:
  -h        show this help
  -s        download in separate folders
  -a <url>  add album

Accepted URL formats:
  https://downloads.khinsider.com/<series>/album/<album>
  <series>/<album>

    " >&2; exit 1;
}

while getopts "hsa:" key; do
    case "$key" in
        h) usage;;
        s) separate_folders="yes";;
        a) 
            url="${OPTARG}";
            if echo "$url" | grep -P 'https\:\/\/' >/dev/null; then
                albums_url+=("${OPTARG}");
            else
                IFS='/' read series album <<< "${OPTARG}";
                url="https://downloads.khinsider.com/$series/album/$album";
                albums_url+=("${url}");
            fi;;
        *) usage;;
    esac;
done;

[[ "${#albums_url[@]}" -eq 0 ]] && usage;

main_pwd="$PWD";
for i in "${!albums_url[@]}"; do
    url="${albums_url[$i]}";
    IFS='/' read _ _ _ series _ album <<< "${url}";
    if [[ "$separate_folders" == "yes" ]]; then
        mkdir -p "$main_pwd/${series}_${album}";
        cd "$main_pwd/${series}_${album}";
        echo -e "\e[35m# Created folder \e[36m$main_pwd/${series}_$album\e[0m";
    fi;
    echo -e "\e[35m# Downloading \e[36m${series}\e[33m/\e[34m${album}\e[33m...";
    printf "\r\e[2K\e[33m(\e[35mrequesting tracklist...\e[33m)\e[0m";
    wget -qO- "$url" \
        | grep "a href=" \
        | grep -oP "/${series}/album/${album}/([^\"]+)" \
        | sort -u | while read track_path; do
        filename="$(echo ${track_path} | cut -d '/' -f 5)";
        printf "\r\e[2K\e[33m(\e[35mfound \e[36m%s\e[35m, " "$filename"
        printf "requesting info...\e[33m)\e[0m";
        info_url="https://downloads.khinsider.com${track_path}";
        real_url="$(wget -qO- "$info_url" | grep 'id="audio"' \
                    | grep -oP 'https://([^"]+)';)"
        printf "\r\e[2K\e[33m(\e[35mgot track info, ";
        printf "starting download...\e[33m)\e[0m";
        wget -q --show-progress "$real_url";
    done
    cd "$main_pwd";
done;
