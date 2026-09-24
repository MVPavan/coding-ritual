#!/bin/sh
# Private archive defaults for every application command, including future services.
umask 077
exec "$@"
