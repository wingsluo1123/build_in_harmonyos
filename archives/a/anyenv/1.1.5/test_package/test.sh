#!/usr/bin/env bash
set -e
anyenv -v
anyenv commands | grep '^version$'
anyenv help version | grep 'Usage: anyenv version'
anyenv root
