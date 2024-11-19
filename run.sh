#!/bin/bash

# Source the .env file
if [ -f .env ]; then
  export $(cat .env | xargs)
else
  echo
  echo
  echo "######################################################"
  echo "# .env file not found. Probably nothing will work :) #"
  echo "######################################################"
  echo
  echo
fi

# Run docker compose up
docker compose up $*
