import React, { useEffect, useRef, useState } from 'react';
import { Stage, Layer } from 'react-konva';

import Slider from '@mui/material/Slider';
import Grid from '@mui/material/Grid';

import FabricImage from './FabricImage.tsx';
import PatternImage from './PatternImage.tsx';
import RenderCanvas from './RenderCanvas.tsx';

const FabricPatternCanvas = ({
    stageWidth,
    stageHeight,
    annotateWidth,
    imageSource,
    scrapsSource,
    patterns,
    assignments,
    patternScaling,
} : {
    stageWidth: number,
    stageHeight: number,
    annotateWidth: number,
    imageSource: string,
    scrapsSource: string,
    patterns: string[],
    assignments: { string: string[] },
    patternScaling: number,
}) => {
  const [selectedId, setSelectedId] = useState<string>("");
  const [layerScale, setLayerScale] = useState<number>(50);
  const [imageTransforms, setImageTransforms] = useState({});
  const stageRef = useRef();

  const itemSize = 100 * patternScaling; // Assuming each item has a base size of 100

  const calculatePosition = (index: number, total: number, itemSize: number, stageSize: number) => {
    const spacing = stageSize / total;
    const offset = (spacing - itemSize) / 2;
    return index * spacing + offset;
  };

  useEffect(() => {
    let initTransforms = {};
    patterns.forEach((patternPiece, index) => {
      const xPos = calculatePosition(index, patterns.length, itemSize, stageWidth);
      initTransforms[patternPiece] = { x: xPos, y: 0, rotation: 0 };
      assignments[patternPiece].forEach((fabric) => {
        initTransforms[fabric] = { x: xPos, y: 0, rotation: 0 };
      });
    });
    setImageTransforms(initTransforms);
  }, [patterns, assignments, itemSize, stageWidth]);

  const handleTransformEnd = (node, src) => {
    if (node === null) {
      console.log("Node is null");
      return;
    }
    const position = node.position();
    const rotation = node.rotation();
    const newTransforms = { ...imageTransforms };
    newTransforms[src] = { x: position.x, y: position.y, rotation: rotation };
    setImageTransforms(newTransforms);
    // console.log(newTransforms);
  };

  const handleSliderChange = (event: Event, newValue: number | number[]) => {
    setLayerScale(newValue as number);
  };

  const marks = [
    {
      value: 5,
      label: '5%',
    },
    {
      value: 50,
      label: '50%',
    },
    {
      value: 100,
      label: '100%',
    },
  ];

  function valuetext(value: number) {
    return `${value}%`;
  }

  return (
    <>
      <Grid container spacing={2} sx={{ width: window.innerWidth }}>
        <Grid item xs={12} md={6}>
          <Stage
            width={stageWidth}
            height={stageHeight}
            ref={stageRef}
            onMouseDown={(e) => {
              if (e.target === e.target.getStage()) {
                setSelectedId("");
              }}}
          >
            {patterns.map((patternPiece, index) => {
              const xPos = calculatePosition(index, patterns.length, itemSize, stageWidth);
              return (
                <Layer
                  key={`Layer-${patternPiece}`} >
                  {assignments[patternPiece].map((fabric) => {
                    return (
                      <FabricImage
                        src={fabric}
                        key={fabric}
                        id={fabric}
                        x={xPos}
                        y={0}
                        onChange={handleTransformEnd}
                        imageScaling={layerScale / 100.}
                      />
                    );
                  })}
                  <PatternImage
                    src={patternPiece}
                    key={patternPiece}
                    id={patternPiece}
                    x={xPos}
                    y={0}
                    isSelected={selectedId === patternPiece}
                    onSelect={() => {
                      setSelectedId(patternPiece);
                    }}
                    onChange={handleTransformEnd}
                    stageRef={stageRef}
                    imageScaling={patternScaling * layerScale / 100.}
                  />
                </Layer>
              );
            })}
          </Stage>
          <Grid container spacing={2} sx={{ width: window.innerWidth / 2 }}>
            <Grid item xs={2} md={6}>
              <Slider
                aria-label="Custom marks"
                defaultValue={50}
                getAriaValueText={valuetext}
                step={1}
                onChange={handleSliderChange}
                valueLabelDisplay="auto"
                marks={marks}
              />
            </Grid>
          </Grid>
        </Grid>
        <Grid item xs={12} md={6}>
          <RenderCanvas
            stageWidth={stageWidth}
            stageHeight={stageHeight}
            annotateWidth={annotateWidth}
            imageSource={imageSource}
            scrapsSource={scrapsSource}
            layerScale={layerScale}
            patternToScrapScaling={patternScaling}
            assignments={assignments}
            imageTransforms={imageTransforms} />
        </Grid>
      </Grid>
    </>
  );
};

export default FabricPatternCanvas;
