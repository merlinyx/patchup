import React, { useRef, useEffect } from 'react';
import { Image, Transformer } from 'react-konva';
import useImage from 'use-image';

// PatternImages can be transformed (translation + rotation)
const PatternImage = ({ 
  src, id, x, y,
  isSelected, onSelect, onChange,
  stageRef,
  imageScaling = 1,
}) => {
    const [image] = useImage(src);
    const shapeRef = useRef();
    const trRef = useRef();

    useEffect(() => {
      if (isSelected && trRef.current && shapeRef.current) {
        trRef.current.nodes([shapeRef.current]);
        trRef.current.getLayer().batchDraw();
      }
    }, [isSelected]);

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

    const getClientRect = (box) => {
      const { x, y, width, height } = box;
      const rotation = box.rotation || 0;
      const radians = (rotation * Math.PI) / 180;
  
      const x1 = x;
      const y1 = y;
      const x2 = x + width * Math.cos(radians);
      const y2 = y + width * Math.sin(radians);
      const x3 = x + width * Math.cos(radians) - height * Math.sin(radians);
      const y3 = y + width * Math.sin(radians) + height * Math.cos(radians);
      const x4 = x - height * Math.sin(radians);
      const y4 = y + height * Math.cos(radians);
  
      const minX = Math.min(x1, x2, x3, x4);
      const minY = Math.min(y1, y2, y3, y4);
      const maxX = Math.max(x1, x2, x3, x4);
      const maxY = Math.max(y1, y2, y3, y4);
  
      return {
        x: minX,
        y: minY,
        width: maxX - minX,
        height: maxY - minY,
      };
    };
  
    const boundBoxCallback = (oldBox, newBox) => {
      const box = getClientRect(newBox);
      const isOut =
        box.x < 0 ||
        box.y < 0 ||
        box.x + box.width > stageRef.width ||
        box.y + box.height > stageRef.height;

      // if new bounding box is out of visible viewport, let's just skip transforming
      // this logic can be improved by still allow some transforming if we have small available space
      if (isOut) {
        return oldBox;
      }
      return newBox;
    };

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
          onClick={onSelect}
          onTap={onSelect}
          onDragEnd={(e) => {
            const node = e.target;
            onChange(node, src);
          }}
          onTransformEnd={(e) => {
            const node = shapeRef.current;
            // Reset the scale
            node.scaleX(imageScaling);
            node.scaleY(imageScaling);
            onChange(node, src);
          }}
        />
        {isSelected &&
          <Transformer
            ref={trRef}
            boundBoxFunc={boundBoxCallback} />}
      </>
    );
};

export default PatternImage;
