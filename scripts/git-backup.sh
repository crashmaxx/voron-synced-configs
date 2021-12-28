#!/bin/bash

#####################################################################
### Please set the paths accordingly. In case you don't have all  ###
### the listed folders, just keep that line commented out.        ###
#####################################################################
### Path to your config folder you want to backup
config_folder=/home/pi/klipper_config/voron-synced-configs

### Path to your Klipper folder, by default that is '~/klipper'
klipper_folder=/home/pi/klipper

### Path to your Moonraker folder, by default that is '~/moonraker'
moonraker_folder=/home/pi/moonraker

### Path to your Mainsail folder, by default that is '~/mainsail'
mainsail_folder=/home/pi/mainsail

### Path to your Fluidd folder, by default that is '~/fluidd'
#fluidd_folder=~/fluidd

#####################################################################
#####################################################################


#####################################################################
################ !!! DO NOT EDIT BELOW THIS LINE !!! ################
#####################################################################
grab_version(){
  if [ ! -z "$klipper_folder" ]; then
    cd "$klipper_folder"
    klipper_commit=$(git rev-parse --short=7 HEAD)
    m1="Klipper on commit: $klipper_commit"
    cd ..
  fi
  if [ ! -z "$moonraker_folder" ]; then
    cd "$moonraker_folder"
    moonraker_commit=$(git rev-parse --short=7 HEAD)
    m2="Moonraker on commit: $moonraker_commit"
    cd ..
  fi
  if [ ! -z "$mainsail_folder" ]; then
    mainsail_ver=$(head -n 1 $mainsail_folder/.version)
    m3="Mainsail version: $mainsail_ver"
  fi
  if [ ! -z "$fluidd_folder" ]; then
    fluidd_ver=$(head -n 1 $fluidd_folder/.version)
    m4="Fluidd version: $fluidd_ver"
  fi
}

push_config(){
  cd $config_folder
  if ! git fetch --all --quiet
  then
    if ! git diff --quiet
    then
      echo "Dirty, changes will be stashed."
      git stash
    fi
    git pull
  else
      git pull
      git add .
    if ! git diff origin/main..HEAD --quiet
    then
      echo "Clean, commiting changes."
      current_date=$(date +"%Y-%m-%d %T")
      git commit -m "Autocommit from $current_date" -m "$m1" -m "$m2" -m "$m3" -m "$m4"
      git remote update
      tag=$(git describe --tags --abbrev=0)
      n_tag=$(./scripts/next-tag.sh $tag build)
      git tag -a $n_tag -m "$HOSTNAME"
      git push --follow-tags
    else
      echo "No changes to commit. Already up to date."
    fi
  fi
}

grab_version
push_config
