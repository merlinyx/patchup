import React, { useRef } from 'react';
import { Image, Layer, Line } from 'react-konva';
import useImage from 'use-image';

export type ClipImageProps = {
  src: string,
  x: number,
  y: number,
  rotation: number,
  sx: number,
  sy: number,
  clipPath: number[],
};

// Using Pattern Polygon as clip path for Fabric Images
const ClipImage = ({
  src, x, y, rotation, sx, sy, clipPath
} : ClipImageProps) => {

  const [image] = useImage(src);
  const imageRef = useRef(null);

  return (
    <Layer
      key={src+'-layer'}
    >
      <Line
        points={clipPath}
        closed
        stroke="red"
        strokeWidth={2}
      />
      {image && <Image
        key={src+'-image'}
        image={image}
        ref={imageRef}
        sceneFunc={(context, shape) => {
          context.beginPath();
          context.moveTo(clipPath[0], clipPath[1]);
          for (let i = 2; i < clipPath.length; i += 2) {
            context.lineTo(clipPath[i], clipPath[i + 1]);
          }
          context.closePath();
          context.clip();

          // Translate context to the center of the image
          context.save();
          context.translate(x, y);
          context.translate(shape.x() + shape.width() / 2, shape.y() + shape.height() / 2);
          context.rotate((rotation * Math.PI) / 180);
          // Draw the image rotated
          context.drawImage(image, -shape.width() / 2, -shape.height() / 2, shape.width() * sx, shape.height() * sy);
          // Restore context
          context.restore();
        }}
      />}
    </Layer>
  );
};

export default ClipImage;
