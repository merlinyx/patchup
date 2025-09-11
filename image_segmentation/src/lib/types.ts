import { KonvaEventObject } from "konva/lib/Node";

export type Polygon = {
  id: string;
  index: number;
  points: number[][];
  flattenedPoints: number[];
  isFinished: boolean;
  isFabric: boolean;
  label?: string;
  size?: string;
};

export type PolygonStyleProps = {
  lineColor?: string;
  fillColor?: string;
  vertexColor?: string;
  vertexRadius?: number;
  vertexStrokeWidth?: number;
  propId?: string;
  bgScaleRatio?: number;
};

export type CanvasProps = {
  annotateWidth: number;
  imageSource: string;
  maxPolygons: number;
  setMaxPolygons: (maxPolygons: number) => void;
  polygonStyle: PolygonStyleProps;
  setPolygonStyle: (polygonStyle: PolygonStyleProps) => void;
  imageSize?: {
    width: number;
    height: number;
  };
  isFabric: boolean;
};

export type PolygonInputProps = {
  id?: string;
  label?: string;
  points: number[][];
};

export type PolygonProps = {
  points: number[][];
  flattenedPoints: number[] | undefined;
  isFinished: boolean;
  label?: string;
  polygonStyle?: PolygonStyleProps;
  handlePointDragMove: (e: KonvaEventObject<DragEvent>) => void;
  handlePointDragEnd: (e: KonvaEventObject<DragEvent>) => void;
  handleGroupDragEnd: (e: KonvaEventObject<DragEvent>) => void;
  handleMouseOverStartPoint: (e: KonvaEventObject<MouseEvent>) => void;
  handleMouseOutStartPoint: (e: KonvaEventObject<MouseEvent>) => void;
};
