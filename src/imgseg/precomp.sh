#!/bin/bash

# input_image=$1
# scrap_image=$2
# num_scraps=$3
scrap_image=$1
num_scraps=$2

# if [ "$#" -ne 3 ]; then
if [ "$#" -ne 2 ]; then
    # echo "Usage: bash scripts/precomp.sh <input_image> <scrap_image> <num_scraps>"
    echo "Usage: bash scripts/precomp.sh <scrap_image> <num_scraps>"
    exit 1
fi

num_scraps_plus_one=$((num_scraps + 1))

# echo "python scripts/compute_input_overlay.py clean_ui/public/images/"$input_image
# python scripts/compute_input_overlay.py clean_ui/public/images/$input_image

echo "python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/"$scrap_image $num_scraps_plus_one
python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/$scrap_image $num_scraps_plus_one

# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap1.jpg 8
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap2.jpg 9
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap3.jpg 7
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap4.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap5.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap6.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap7.jpg 8
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap8.jpg 10
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap9.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/scraps_bag/scrap10.jpg 32

# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap1.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap2.jpg 5
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap3.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap4.jpg 6
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap5.jpg 6
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap6.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap7.jpg 6
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap8.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap9.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag1/scrap10.jpg 3

# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap1.jpg 3
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap2.jpg 2
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap3.jpg 13
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap4.jpg 2
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap5.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap6.jpg 6
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap7.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap8.jpg 1
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/bag4/scrap9.jpg 2

# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/linen/scrap1-1.jpg 6
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/linen/scrap1-2.jpg 4
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/linen/scrap2-1.jpg 11
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/linen/scrap2-2.jpg 8
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/linen/scrap2-3.jpg 5
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/linen/scrap3-1.jpg 7
# python scripts/sc/compute_scrap_overlay.py clean_ui/public/images/linen/scrap3-2.jpg 5