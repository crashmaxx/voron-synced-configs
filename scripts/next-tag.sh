#!/bin/bash

version="$1"
major=0
minor=0
build=0

# break down the version number into it's components
regex="v([0-9]+).([0-9]+).([0-9]+)"
if [[ $version =~ $regex ]]; then
  major="${BASH_REMATCH[1]}"
  minor="${BASH_REMATCH[2]}"
  build="${BASH_REMATCH[3]}"
fi

# check paramater to see which number to increment
if [[ "$2" == "major" ]]; then
  major=$((major + 1))
elif [[ "$2" == "minor" ]]; then
  minor=$((minor + 1))
elif [[ "$2" == "build" ]]; then
  build=$((build + 1))
else
  echo "usage: ./next-tag.sh version_number [major/minor/build]"
  exit -1
fi

# echo the new version number
echo "v${major}.${minor}.${build}"
