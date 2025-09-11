import React, { useState } from "react";
import Konva from "konva";
import { Line, Circle, Group, Text } from "react-konva";
import { KonvaEventObject } from "konva/lib/Node";
import { Vector2d } from "konva/lib/types";

import { minMax, getMiddlePoint } from "../utils/index.ts";
import { PolygonProps } from "./types.ts";

// default values
const LineColor = "#73fdff";
const FillColor = "#c0c0c0";
const VertexColor = "#FF019A";
const VertexRadius = 3;
const VertexStrokeWidth = 1;

const Polygon = ({
  points,
  flattenedPoints,
  isFinished,
  label = "Polygon",
  polygonStyle = {
    vertexRadius: VertexRadius,
    lineColor: LineColor,
    fillColor: FillColor,
    vertexColor: VertexColor,
    vertexStrokeWidth: VertexStrokeWidth,
  },
  handlePointDragMove,
  handlePointDragEnd,
  // handleGroupDragStart,
  handleGroupDragEnd,
  handleMouseOverStartPoint,
  handleMouseOutStartPoint,
}: PolygonProps) => {
  const { vertexRadius, lineColor, fillColor, vertexColor, vertexStrokeWidth } = polygonStyle;
  const [stageObject, setStageObject] = useState<Konva.Stage | null>(null);
  const [minMaxX, setMinMaxX] = useState([0, 0]); //min and max in x axis
  const [minMaxY, setMinMaxY] = useState([0, 0]); //min and max in y axis

  const textRef = React.useRef<Konva.Text>(null);
  const handleGroupMouseOver = (e: KonvaEventObject<MouseEvent>) => {
    const stage = e.target.getStage();
    if (!isFinished || !stage) return;
    stage.container().style.cursor = "pointer";
    setStageObject(stage);
  };

  const handleGroupMouseOut = (e: KonvaEventObject<MouseEvent>) => {
    const stage = e.target.getStage();
    if (!stage) return;
    stage.container().style.cursor = "default";
  };

  const handleGroupDragStart = () => {
    const arrX = points.map((p) => p[0]);
    const arrY = points.map((p) => p[1]);
    setMinMaxX(minMax(arrX));
    setMinMaxY(minMax(arrY));
  };

  const groupDragBoundFunc = (pos: Vector2d) => {
    let { x, y } = pos;
    if (!stageObject) return { x, y };
    const sw = stageObject.width();
    const sh = stageObject.height();
    if (minMaxY[0] + y < 0) y = -1 * minMaxY[0];
    if (minMaxX[0] + x < 0) x = -1 * minMaxX[0];
    if (minMaxY[1] + y > sh) y = sh - minMaxY[1];
    if (minMaxX[1] + x > sw) x = sw - minMaxX[1];
    return { x, y };
  };

  const vertexDragBoundFunc = (pos: Vector2d) => {
    let { x, y } = pos;
    if (!stageObject) return { x, y };
    const sw = stageObject.width();
    const sh = stageObject.height();
    if (x > sw) x = sw;
    if (x < 0) x = 0;
    if (y > sh) y = sh;
    if (y < 0) y = 0;
    return { x, y };
  };

  return (
    <Group
      name="polygon"
      draggable={isFinished}
      onDragStart={handleGroupDragStart}
      onDragEnd={handleGroupDragEnd}
      dragBoundFunc={groupDragBoundFunc}
      onMouseOver={handleGroupMouseOver}
      onMouseOut={handleGroupMouseOut}
    >
      <Line
        name="line"
        opacity={0.7}
        points={flattenedPoints}
        stroke={lineColor}
        strokeWidth={2}
        closed={isFinished}
        fill={fillColor}
      />
      {points.map((point, index) => {
        const x = point[0];
        const y = point[1];
        const startPointAttr =
          index === 0
            ? {
                onMouseOver: handleMouseOverStartPoint,
                onMouseOut: handleMouseOutStartPoint,
              }
            : null;
        return (
          <Circle
            name="vertex"
            key={index}
            x={x}
            y={y}
            radius={vertexRadius}
            fill={vertexColor}
            stroke={lineColor}
            strokeWidth={vertexStrokeWidth}
            draggable
            onDragMove={handlePointDragMove}
            onDragEnd={handlePointDragEnd}
            dragBoundFunc={vertexDragBoundFunc}
            {...startPointAttr}
          />
        );
      })}
      {isFinished && label && (
        <>
          <Text
            name={`Text-${label}`}
            ref={textRef}
            text={label}
            fontSize={12}
            x={minMax(points.map((p) => p[0]))[0]}
            y={getMiddlePoint(points).y}
            fill="white"
          />
        </>
      )}
    </Group>
  );
};

export default Polygon;