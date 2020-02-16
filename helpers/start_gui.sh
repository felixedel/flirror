#!/usr/bin/env sh

# Make the connected display available from command line
export DISPLAY=:0.0

# Deactivate screensaver
xset s off
# Disable DPMS (Energy Star) features
xset -dpms

# Don't blank the vide device
xset s noblank

# NOTE (felix): List of chromium command line switches/options can be found here:
# https://peter.sh/experiments/chromium-command-line-switches/

# Launch chrome in full-screen mode
chromium-browser --app --kiosk "http://localhost:8000"
