import React, { useMemo, useState, useEffect, useCallback, useRef } from "react";
import { useSelector, useDispatch, shallowEqual } from "react-redux";
import { Layer, Image, Stage } from "react-konva";
import { KonvaEventObject } from "konva/lib/Node";
import { v4 as uuidv4 } from "uuid";

import { setActivePolygonIndex, setPolygons } from "../store/slices/polygonSlice.ts";
import { RootState } from "../store/index.ts";
import { CanvasProps } from "./types.ts";
import { isInsidePoly } from "../utils/index.ts";
import Polygon from "./Polygon.tsx";

import Toolbar from '../components/Toolbar.tsx';

import Button from "@mui/material/Button";
import { styled } from '@mui/material/styles';

import "./Canvas.css";

const MarginButton = styled(Button)({
  margin: '6px 12px',
});

export const Canvas = ({
  annotateWidth,
  imageSource,
  maxPolygons,
  setMaxPolygons,
  polygonStyle,
  setPolygonStyle,
  imageSize,
  isFabric,
}: CanvasProps) => {
  const dispatch = useDispatch();
  const [image, setImage] = useState<HTMLImageElement>();
  const [overlayImage, setOverlayImage] = useState<HTMLImageElement>();
  const [showOverlay, setShowOverlay] = useState<boolean>(false);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [isMouseOverPoint, setIsMouseOverPoint] = useState(false);
  const { polygons, activePolygonIndex } = useSelector(
    (state: RootState) => state.polygon.present,
    shallowEqual,
  );

  const imageElement = useMemo(() => {
    const element = new window.Image();
    element.src = imageSource;
    return element;
  }, [imageSource]);

  const overlayImageElement = useMemo(() => {
    const element = new window.Image();
    element.src = imageSource.slice(0, imageSource.lastIndexOf("."))  + "_overlay.png";
    return element;
  }, [imageSource]);

  useEffect(() => {
    const onload = function () {
      if (imageSize?.width && imageSize?.height) {
        if (imageSize.width > annotateWidth) {
          const ratio = annotateWidth / imageSize.width;
          const width = annotateWidth;
          const height = imageSize.height * ratio;
          setSize({ width, height });
          setPolygonStyle({ ...polygonStyle, bgScaleRatio: ratio});
        } else {
          setSize({
            width: imageSize.width,
            height: imageSize.height,
          });
        }
      } else {
        if (imageElement.width > annotateWidth) {
          const ratio = annotateWidth / imageElement.width;
          const width = annotateWidth;
          const height = imageElement.height * ratio;
          setSize({ width, height });
          setPolygonStyle({ ...polygonStyle, bgScaleRatio: ratio});
        } else {
          setSize({
            width: imageElement.width,
            height: imageElement.height,
          });
        }
      }
      setImage(imageElement);
      setOverlayImage(overlayImageElement);
    };
    imageElement.addEventListener("load", onload);
    return () => {
      imageElement.removeEventListener("load", onload);
    };

  }, [annotateWidth, imageElement, overlayImageElement, imageSize?.height, imageSize?.width, imageSource, setPolygonStyle, polygonStyle]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const getMousePos = (stage: any): number[] => {
    return [stage.getPointerPosition()?.x ?? 0, stage.getPointerPosition()?.y ?? 0];
  };

  const handleMouseClick = useCallback(
    (e: KonvaEventObject<MouseEvent>) => {
      // prevent adding new polygon if maxPolygons is reached
      if (polygons.length >= maxPolygons) return;

      // prevent adding new point on vertex or existing polygons if it is not mouse over
      if (e.target.name() === "vertex" && !isMouseOverPoint) {
        return;
      }

      const stage = e.target.getStage();
      const mousePos = getMousePos(stage);
      // check if mousePos is inside existing polygons
      if (isInsidePoly(mousePos, polygons.map((p) => p.points))) {
        // console.log("inside polygon");
        return;
      }

      let activeKey = activePolygonIndex;
      if (activeKey === -1) {
        // create the first polygon with a single starting point
        let polygon = {
          id: uuidv4(),
          index: 0,
          points: [mousePos],
          flattenedPoints: [],
          isFinished: false,
          isFabric: isFabric,
          label: `Polygon-${polygons.length + 1}`,
        };
        setIsMouseOverPoint(false);
        activeKey += 1;
        dispatch(setActivePolygonIndex(activeKey));
        dispatch(setPolygons({ polygons: [polygon], shouldUpdateHistory: true }));
      } else {
        const copy = [...polygons];
        let polygon = copy[activePolygonIndex];
        const { isFinished } = polygon;
        if (isFinished) {
          // create new polygon
          polygon = {
            id: uuidv4(),
            index: copy.length,
            points: [],
            flattenedPoints: [],
            isFinished: false,
            isFabric: isFabric,
            label: `Polygon-${copy.length + 1}`,
          };
          setIsMouseOverPoint(false);
          activeKey += 1;
          dispatch(setActivePolygonIndex(activeKey));
        }
        const { points } = polygon;
        const stage = e.target.getStage();
        const mousePos = getMousePos(stage);
        if (isMouseOverPoint && points.length >= 3) {
          polygon = {
            ...polygon,
            isFinished: true,
          };
        } else {
          polygon = {
            ...polygon,
            points: [...points, mousePos],
          };
        }
        copy[activeKey] = polygon;
        dispatch(setPolygons({ polygons: copy, shouldUpdateHistory: true }));
      }
    },
    [activePolygonIndex, dispatch, isMouseOverPoint, maxPolygons, polygons, isFabric],
  );


  const polygonsRef = useRef(polygons);
  useEffect(() => {
    polygonsRef.current = polygons;
  }, [polygons]);
  
  const handleMouseMove = useCallback(
    (e: KonvaEventObject<MouseEvent>) => {
      const stage = e.target.getStage();
      if (!stage) {
        return;
      }
      const mousePos = getMousePos(stage);
      const copy = [...polygonsRef.current];
      let polygon = copy[activePolygonIndex];
      if (!polygon || polygon.isFinished) {
        return;
      }
      const _flattenedPoints = polygon.points.concat(mousePos).reduce((a, b) => a.concat(b), []);
      polygon = {
        ...polygon,
        flattenedPoints: _flattenedPoints,
      };
      copy[activePolygonIndex] = polygon;
      dispatch(setPolygons({ polygons: copy, shouldUpdateHistory: false }));
    },
    [activePolygonIndex, dispatch]
  );

  const handleMouseOverStartPoint = useCallback(
    (e: KonvaEventObject<MouseEvent>, polygonKey: number) => {
      const polygon = polygons[polygonKey];
      const { points, isFinished } = polygon;
      if (isFinished || points.length < 3) {
        return;
      }
      e.target.scale({ x: 2, y: 2 });
      setIsMouseOverPoint(true);
    },
    [polygons],
  );

  const handleMouseOutStartPoint = useCallback((e: KonvaEventObject<MouseEvent>) => {
    e.target.scale({ x: 1, y: 1 });
    setIsMouseOverPoint(false);
  }, []);

  const handlePointDragMove = useCallback(
    (e: KonvaEventObject<DragEvent>, polygonKey: number) => {
      const copy = [...polygons];
      let polygon = copy[polygonKey];
      const { isFinished } = polygon;
      if (!isFinished) {
        // prevent drag:
        e.target.stopDrag();
        return;
      }
      const stage = e.target.getStage();
      const index = e.target.index - 1;
      const pos = [e.target.x(), e.target.y()];
      if (stage) {
        if (pos[0] < 0) pos[0] = 0;
        if (pos[1] < 0) pos[1] = 0;
        if (pos[0] > stage.width()) pos[0] = stage.width();
        if (pos[1] > stage.height()) pos[1] = stage.height();
      }

      const { points } = polygon;
      const newPoints = [...points.slice(0, index), pos, ...points.slice(index + 1)];
      const flattenedPoints = newPoints.reduce((a, b) => a.concat(b), []);
      polygon = {
        ...polygon,
        points: newPoints,
        flattenedPoints,
      };
      copy[polygonKey] = polygon;
      dispatch(setPolygons({ polygons: copy, shouldUpdateHistory: false }));
    },
    [dispatch, polygons],
  );

  const handlePointDragEnd = useCallback(
    (e: KonvaEventObject<DragEvent>, polygonKey: number) => {
      const index = e.target.index - 1;
      const pos = [e.target.x(), e.target.y()];
      const copy = [...polygons];
      let polygon = copy[polygonKey];
      const { points } = polygon;
      const newPoints = [...points.slice(0, index), pos, ...points.slice(index + 1)];
      const flattenedPoints = newPoints.reduce((a, b) => a.concat(b), []);
      polygon = {
        ...polygon,
        points: newPoints,
        flattenedPoints,
      };
      copy[polygonKey] = polygon;
      dispatch(setPolygons({ polygons: copy, shouldUpdateHistory: true }));
    },
    [dispatch, polygons],
  );

  const handleGroupDragEnd = useCallback(
    (e: KonvaEventObject<DragEvent>, polygonKey: number) => {
      //drag end listens other children circles" drag end event
      //...for this "name" attr is added
      const copy = [...polygons];
      let polygon = copy[polygonKey];
      const { points } = polygon;
      if (e.target.name() === "polygon") {
        const result: number[][] = [];
        const copyPoints = [...points];
        copyPoints.forEach((point) =>
          result.push([point[0] + e.target.x(), point[1] + e.target.y()]),
        );
        e.target.position({ x: 0, y: 0 }); //reset group position
        polygon = {
          ...polygon,
          points: result,
          flattenedPoints: result.reduce((a, b) => a.concat(b), []),
        };
        copy[polygonKey] = polygon;
        dispatch(setPolygons({ polygons: copy, shouldUpdateHistory: true }));
      }
    },
    [dispatch, polygons],
  );

  return (
    <div>
      <Stage
        width={size.width}
        height={size.height}
        onMouseMove={handleMouseMove}
        onMouseDown={handleMouseClick}
      >
        {showOverlay && <Layer>
          <Image image={overlayImage} x={0} y={0} width={size.width} height={size.height} />
        </Layer>}
        {!showOverlay && <Layer>
          <Image image={image} x={0} y={0} width={size.width} height={size.height} />
        </Layer>}
        <Layer>
          {polygons?.map((polygon, index) => (
            <Polygon
              key={polygon.id}
              isFinished={polygon.isFinished}
              points={polygon.points}
              flattenedPoints={polygon.flattenedPoints}
              handlePointDragMove={(e) => handlePointDragMove(e, index)}
              handlePointDragEnd={(e) => handlePointDragEnd(e, index)}
              handleMouseOverStartPoint={(e) => handleMouseOverStartPoint(e, index)}
              handleMouseOutStartPoint={handleMouseOutStartPoint}
              handleGroupDragEnd={(e) => handleGroupDragEnd(e, index)}
              polygonStyle={polygonStyle}
              label={polygon.label}
            />
          ))}
        </Layer>
      </Stage>
      <MarginButton
        variant="contained"
        onClick={() => {setShowOverlay(!showOverlay);}}>
          Toggle Auto-Segmentation Overlay
      </MarginButton>
      <Toolbar
        bgImage={imageSource}
        maxPolygons={maxPolygons}
        setMaxPolygons={setMaxPolygons}
        config={polygonStyle}
        setConfig={setPolygonStyle}
        isFabric={isFabric} />
    </div>
  );
};
