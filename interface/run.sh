#!/bin/bash

case "$1" in
    "build")
        docker-compose build
        ;;
    "remove")
        docker-compose down -v
        ;;
    "down")
        docker-compose down
        ;;
    *)
        docker-compose build
        docker-compose down
        docker-compose up -d
        ;;
esac