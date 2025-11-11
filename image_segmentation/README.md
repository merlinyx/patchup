# Image Segmentation

This is the UI for segmenting the fabric pieces from photos semi-manually in PatchUp. It is included for documenting purposes and there's a less manual, SAM-based UI available here: [patchup-fabric-segmenter](https://patchup-fabric-segmenter.netlify.app/).

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app). Code largely adapted from [polygon-annotation](https://github.com/definite2/polygon-annotation/tree/main).

## Precomputation

Use the following scripts to compute the overlay of the bounding polygons before turning on the optional overlay or it will give an error.
`python src/imgseg/compute_scrap_overlay.py <path/to/image> <number of images to segment>`

The `number of images to segment` arguments count the calibration square as well so you would input the number of fabric pieces in the image plus 1.

## Quick Start

Run
`npm install`

`npm run start-api`

`npm run start`

to start the webapp in the development mode. Open [http://localhost:3000](http://localhost:3000) to view it in your browser.
