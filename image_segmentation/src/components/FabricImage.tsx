import React, { useRef, useEffect } from 'react';
import { Image } from 'react-konva';
import useImage from 'use-image';

// FabricImages can only be translated
const FabricImage = ({ 
  src, id, x, y,
  onChange,
  imageScaling = 1,
}) => {
    const [image] = useImage(src);
    const shapeRef = useRef();

    useEffect(() => {
      if (image) {
        const baseWidth = image.width;
        const baseHeight = image.height;
        if (shapeRef.current) {
          shapeRef.current.width(baseWidth * imageScaling);
          shapeRef.current.height(baseHeight * imageScaling);
          shapeRef.current.getLayer().batchDraw();
        }
      }
    }, [image, imageScaling]);

    return (
      <>
        <Image
          image={image}
          ref={shapeRef}
          id={id}
          x={x}
          y={y}
          scaleX={ imageScaling }
          scaleY={ imageScaling }
          draggable
          onDragEnd={(e) => {
            const node = e.target;
            onChange(node, src);
          }}
        />
      </>
    );
};

export default FabricImage;
