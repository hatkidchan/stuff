#!/usr/bin/env python3
# Simple https://github.com/mcRPW/rpw projects exporter
# Ignores all setting files (for now), but still does the job
# Contributions are welcome
from zipfile import ZipFile
from pathlib import Path
from sys import argv
from os import walk
from json import dumps

if len(argv) != 3:
    print("Usage: {} [project root] [output.zip]".format(argv[0]))
    exit(2)

project_root = Path(argv[1])
project_files = project_root / "project_files"
extras_directory = project_root / "extra_files"
custom_sounds = project_root / "custom_sounds"
custom_languages = project_root / "custom_languages"

pack_description = ""
pack_version = 6

def add_tree(zipf, path_from, path_to=""):
    for (dpath, _, fnames) in walk(path_from):
        for fname in fnames:
            realpath = Path(dpath, fname)
            relpath = realpath.relative_to(path_from)
            zipf.write(realpath, Path(path_to, relpath))
            print(" + {}".format(relpath))


with ZipFile(argv[2], "w") as zipf:
    add_tree(zipf, extras_directory)
    add_tree(zipf, custom_sounds, "assets/minecraft/sounds")
    add_tree(zipf, custom_languages, "assets/minecraft/lang")
    zipf.write(project_root / "sounds.json", "assets/minecraft/sounds.json")
    zipf.writestr("pack.mcmeta", dumps({
        "pack": {
            "pack_format": pack_version,
            "description": pack_description
        }
    }, indent=2))
    add_tree(zipf, project_files)
    zipf.write(project_root / "pack.png", "pack.png")
