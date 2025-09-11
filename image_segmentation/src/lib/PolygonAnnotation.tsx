import React, { useMemo, ReactNode } from "react";
import { Provider } from "react-redux";
import { initStore } from "../store/index.ts";
import { PolygonStyleProps, PolygonInputProps } from "./types.ts";

import { Canvas } from "./Canvas.tsx";

export const PolygonAnnotation = ({
  bgImage,
  maxPolygons,
  setMaxPolygons,
  initialPolygons,
  polygonStyle,
  setPolygonStyle,
  imageSize,
  isFabric = false,
  annotateWidth,
  children,
}: {
  bgImage: string;
  maxPolygons: number;
  setMaxPolygons: (maxPolygons: number) => void;
  initialPolygons?: PolygonInputProps[];
  polygonStyle: PolygonStyleProps;
  setPolygonStyle: (polygonStyle: PolygonStyleProps) => void;
  imageSize?: { width: number; height: number };
  isFabric?: boolean;
  annotateWidth: number;
  children?: ReactNode;
  }) => {
  const store = useMemo(() => {
    return initStore(initialPolygons);
  }, [initialPolygons]);

  return (
    <Provider store={store}>
    <Canvas
      annotateWidth={annotateWidth}
      imageSource={bgImage}
      maxPolygons={maxPolygons}
      setMaxPolygons={setMaxPolygons}
      polygonStyle={polygonStyle}
      setPolygonStyle={setPolygonStyle}
      imageSize={imageSize}
      isFabric={isFabric}
    />
    {children}
    </Provider>
  );
};
