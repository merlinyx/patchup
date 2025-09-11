import React from 'react';
import { Layer, Line } from 'react-konva';

export type ClipPatternProps = {
  src: string,
  // x: number,
  // y: number,
  // rotation: number,
  // sx: number,
  // sy: number,
  patternPath: number[],
  clipPath: number[],
};

const ClipPattern = ({
  src,
  // x, y, rotation, sx, sy, 
  patternPath, clipPath
} : ClipPatternProps) => {

  return (
    <Layer key={src+'-layer'} >
      <Line
        points={clipPath}
        closed
        stroke="blue"
        strokeWidth={2}
      />
      <Line
        points={patternPath}
        closed
        stroke="red"
        strokeWidth={2}
      />
    </Layer>
  );
};

export default ClipPattern;
