#!/bin/bash

# Configuration
LOCAL_DIR="/Users/mike/escrow-gigs-bot/"
REMOTE_USER="ubuntu"
REMOTE_HOST="52.59.238.26"
REMOTE_DIR="/home/ubuntu/escrow-gigs-bot/escrow-gigs-bot"
SSH_KEY="/Users/mike/.ssh/escrow-bot-key.pem"

# Check if the SSH key exists
if [ ! -f "$SSH_KEY" ]; then
    echo "Error: SSH key not found at $SSH_KEY"
    exit 1
fi

# rsync command
rsync -avz -e "ssh -i $SSH_KEY" --rsync-path="mkdir -p $REMOTE_DIR && rsync" --exclude='.git' --exclude='*.pyc' --exclude='__pycache__' --exclude='venv' "$LOCAL_DIR" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"

echo "Sync complete."