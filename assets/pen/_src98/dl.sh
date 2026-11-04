#!/bin/sh
# uso: dl.sh nome object_id
curl -sSL -o "$1.png" "https://api.pixellab.ai/mcp/objects/$2/download"
python -c "from PIL import Image;i=Image.open('$1.png');print(i.size,i.mode)"
