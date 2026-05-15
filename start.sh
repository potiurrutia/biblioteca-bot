#!/bin/bash
set -e

mkdir -p ~/.config/rclone
cat > ~/.config/rclone/rclone.conf << 'EOF'
[gdrive]
type = drive
scope = drive.readonly
token = TOKEN_PLACEHOLDER
root_folder_id = 
EOF

sed -i "s|TOKEN_PLACEHOLDER|$RCLONE_TOKEN|" ~/.config/rclone/rclone.conf

exec python app.py
