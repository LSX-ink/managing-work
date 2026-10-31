#!/bin/sh
# ship.sh videos/NN-slug : push phone copy + contact sheet, copy phone copy + caption to Desktop\lowkey-lore-videos
V=$1; S=$(basename $V | cut -d- -f2-); D=/c/Users/Thato/OneDrive/Desktop/lowkey-lore-videos
.venv/Scripts/python.exe pipeline/make.py $V push 2>&1 | grep pushed
cp $V/out/lowkey-lore-$S-phone.mp4 $D/ && cp $V/caption.txt $D/$S-caption.txt
FF=$(.venv/Scripts/python.exe -c "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())")
"$FF" -hide_banner -i $V/out/lowkey-lore-$S-phone.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "Duration|^\s+(I:|Peak:)" | tr -s ' '
