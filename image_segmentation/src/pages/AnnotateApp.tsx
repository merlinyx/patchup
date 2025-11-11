import React, { useState } from "react";

import { PolygonAnnotation, PolygonStyleProps } from "../lib/index.ts";

import "./App.css";

const AnnotateApp = ({
  initialData,
  scrapsSource
}: {
  initialData: any[];
  annotateWidth: number;
  imageSource: string;
  scrapsSource: string;
}) => {

  const [maxPolygons, setMaxPolygons] = useState<number>(30);
  const [polygonStyle, setPolygonStyle] = useState<PolygonStyleProps>({
    vertexRadius: 3,
    lineColor: "#73fdff",
    fillColor: "#c0c0c0",
    vertexColor: "#d4fb78",
    vertexStrokeWidth: 1,
    propId: "PolyAnno",
    bgScaleRatio: 1,
  });

  return (
    <div className="App">
      <header className="App-header">
        <h2>Fabric Image Extraction for PatchUp</h2>
      </header>
      <p>Click to add points to construct the polygons for the fabric pieces. Make sure to manually change the calibration square's label to "calib".</p>
      <div className="annotation-container">
        <div className="ScrapAnno">
          <PolygonAnnotation
            bgImage={scrapsSource}
            maxPolygons={maxPolygons}
            setMaxPolygons={setMaxPolygons}
            polygonStyle={polygonStyle}
            setPolygonStyle={setPolygonStyle}
            initialPolygons={initialData}
            annotateWidth={Math.round(window.innerWidth * 0.6)}
            isFabric={true} />
        </div>
      </div>
    </div>
  );
};

export default AnnotateApp;
