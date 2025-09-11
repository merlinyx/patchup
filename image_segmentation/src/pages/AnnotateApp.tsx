import React, { useState } from "react";
import { useNavigate } from 'react-router-dom';
import Button from '@mui/material/Button';

import { PolygonAnnotation, PolygonStyleProps } from "../lib/index.ts";

import "./App.css";

const AnnotateApp = ({
  initialData1,
  initialData2,
  annotateWidth,
  imageSource,
  scrapsSource
}: {
  initialData1: any[];
  initialData2: any[];
  annotateWidth: number;
  imageSource: string;
  scrapsSource: string;
}) => {

  const navigate = useNavigate();
  const navigateToNewPage = () => {
    navigate('/assign');
  };

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
  const [maxPolygons2, setMaxPolygons2] = useState<number>(30);
  const [polygonStyle2, setPolygonStyle2] = useState<PolygonStyleProps>({
    vertexRadius: 3,
    lineColor: "#73fdff",
    fillColor: "#c0c0c0",
    vertexColor: "#d4fb78",
    vertexStrokeWidth: 1,
    propId: "ScrapAnno",
    bgScaleRatio: 1,
  });

  return (
    <div className="App">
      <header className="App-header">
        <h2>Scrappy Collage Design</h2>
      </header>
      <div className="annotation-container">
        {/* <div className="PolyAnno">
          <PolygonAnnotation
            bgImage={imageSource}
            maxPolygons={maxPolygons}
            setMaxPolygons={setMaxPolygons}
            polygonStyle={polygonStyle}
            setPolygonStyle={setPolygonStyle}
            initialPolygons={initialData1}
            annotateWidth={annotateWidth}
            isFabric={false} />
        </div> */}
        <div className="ScrapAnno">
          <PolygonAnnotation
            bgImage={scrapsSource}
            maxPolygons={maxPolygons2}
            setMaxPolygons={setMaxPolygons2}
            polygonStyle={polygonStyle2}
            setPolygonStyle={setPolygonStyle2}
            initialPolygons={initialData2}
            annotateWidth={Math.round(window.innerWidth * 0.6)}
            isFabric={true} />
        </div>
      </div>
      <Button variant="contained" onClick={navigateToNewPage}>Go to Design Page</Button>
    </div>
  );
};

export default AnnotateApp;
