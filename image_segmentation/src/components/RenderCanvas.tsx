import React, { useEffect, useState, useRef } from 'react';
import { Layer, Image, Stage } from "react-konva";
import axios from 'axios';
import useImage from 'use-image';

import Grid from '@mui/material/Grid';
import Button from '@mui/material/Button';
import Snackbar from '@mui/material/Snackbar';
import IconButton from '@mui/material/IconButton';
import CloseIcon from '@mui/icons-material/Close';

import ClipImage from './ClipImage.tsx';
import ClipPattern from './ClipPattern.tsx';

const RenderCanvas = ({
  stageWidth,
  stageHeight,
  annotateWidth,
  imageSource,
  scrapsSource,
  layerScale,
  patternToScrapScaling,
  assignments,
  imageTransforms
} : {
  stageWidth: number,
  stageHeight: number,
  annotateWidth: number,
  imageSource: string,
  scrapsSource: string,
  patternToScrapScaling: number,
  layerScale: number,
  assignments: { string: string[] },
  imageTransforms: {},
}) => {
  const [image] = useImage(imageSource);
  const imageRef = useRef(null);
  const [scraps] = useImage(scrapsSource);
  const scrapsRef = useRef(null);

  const [imageScaleRatio, setImageScaleRatio] = useState(1);
  const [scrapsScaleRatio, setScrapsScaleRatio] = useState(1);

  const [open, setOpen] = React.useState(false);
  const [message, setMessage] = React.useState('');

  useEffect(() => {
    if (!image) return;

    const onload = () => {
      const ratio1 = stageWidth / image.width;
      const ratio2 = stageHeight / image.height;
      setImageScaleRatio(Math.min(ratio1, ratio2));
    };

    if (image.complete) {
      onload();
    } else {
      image.addEventListener('load', onload);
      return () => {
        image.removeEventListener('load', onload);
      };
    }
  }, [image, stageWidth, stageHeight]);

  useEffect(() => {
    if (!scraps) return;

    const onload = () => {
      const ratio1 = stageWidth / scraps.width;
      const ratio2 = stageHeight / scraps.height;
      setScrapsScaleRatio(Math.min(ratio1, ratio2));
    };

    if (scraps.complete) {
      onload();
    } else {
      scraps.addEventListener('load', onload);
      return () => {
        scraps.removeEventListener('load', onload);
      };
    }
  }, [scraps, stageWidth, stageHeight]);

  const [patternClipImages, setPatternClipImages] = useState([]);
  const [patternOnScraps, setPatternOnScraps] = useState([]);

  const initializeRender = async () => {
    const response = await axios.post('http://127.0.0.1:5000/api/compute_render_transforms', { 
      imageName: imageSource,
      imageScaleRatio: imageScaleRatio,
      scrapsName: scrapsSource,
      scrapsScaleRatio: scrapsScaleRatio,
      layerScale: layerScale,
      patternToScrapScaling: patternToScrapScaling,
      assignments: assignments,
      imageTransforms: imageTransforms,
    });
    setPatternClipImages(response.data['pattern_clip_images']);
    setPatternOnScraps(response.data['pattern_on_scraps']);
  };

  const saveSVG = async () => {
    const response = await axios.post('http://127.0.0.1:5000/api/save_polygon_as_svg', {
      patternName: imageSource,
      scrapsName: scrapsSource,
      annotateWidth: annotateWidth,
      patterns: patternOnScraps
    });
    if (response.status === 200) {
      setOpen(true);
      setMessage('Pattern saved as SVG. ' + response.data['message']);
      console.log(response.data['message']);
    } else {
      setOpen(true);
      setMessage('Error saving pattern as SVG');
    }
  }

  const handleClose = (event: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') {
      return;
    }

    setOpen(false);
  };

  const action = (
    <React.Fragment>
      <Button color="secondary" size="small" onClick={handleClose}>
        UNDO
      </Button>
      <IconButton
        size="small"
        aria-label="close"
        color="inherit"
        onClick={handleClose}
      >
        <CloseIcon fontSize="small" />
      </IconButton>
    </React.Fragment>
  );

  return (
    <>
      <Grid container spacing={2}>
        <Grid item xs={4} md={6}>
          <Stage width={stageWidth / 2} height={stageHeight}>
            <Layer key={imageSource}>
              <Image
                image={image} ref={imageRef}
                x={0} y={0}
                // scaleX={1} scaleY={1}/>
                scaleX={imageScaleRatio} scaleY={imageScaleRatio}/>
            </Layer>
            {patternClipImages.map((clipImage) => {
              return (
                <ClipImage
                  key={clipImage['src']}
                  src={clipImage['src']}
                  x={clipImage['x']}
                  y={clipImage['y']}
                  rotation={clipImage['rotation']}
                  sx={1/patternToScrapScaling * imageScaleRatio}
                  sy={1/patternToScrapScaling * imageScaleRatio}
                  clipPath={clipImage['clipPath']}
                />
              );
            })}
          </Stage>
          <Button size="small" variant="contained" onClick={initializeRender}>Preview Pattern</Button>
        </Grid>
        <Grid item xs={4} md={6}>
          <Stage width={stageWidth / 2} height={stageHeight}>
            <Layer key={scrapsSource}>
              <Image
                image={scraps} ref={scrapsRef}
                x={0} y={0}
                scaleX={scrapsScaleRatio} scaleY={scrapsScaleRatio}/>
            </Layer>
            {patternOnScraps.map((pattern) => {
              return (
                <ClipPattern
                  key={pattern['src']}
                  src={pattern['src']}
                  patternPath={pattern['patternPath']}
                  clipPath={pattern['clipPath']}
                />
              );
            })}
          </Stage>
          <Button size="small" variant="contained" onClick={saveSVG}>Save Pattern</Button>
          <Snackbar
            open={open}
            onClose={handleClose}
            message={message}
            action={action}
          />
        </Grid>
      </Grid>
    </>
  );
};

export default RenderCanvas;
