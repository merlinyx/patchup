import React from "react";
import { useLocation, useNavigate } from 'react-router-dom';
import Button from '@mui/material/Button';

import FabricPatternCanvas from "../components/ImageCanvas.tsx";

import "./App.css";

const PlacingApp = ({
  annotateWidth,
  imageSource,
  scrapsSource
}: {
  annotateWidth: number;
  imageSource: string;
  scrapsSource: string;
}) => {

  const navigate = useNavigate();
  const navigateToAnnotate = () => {
    navigate('/');
  };
  const navigateToAssign = () => {
    navigate('/assign', { state: { fabricAssignments } });
  };

  const location = useLocation();
  const { patternImages, fabricAssignments, patternScaling } = location.state;

  return (
    <div className="App">
      <header className="App-header">
        <h2>Scrappy Collage Design</h2>
      </header>
      <FabricPatternCanvas
        stageWidth={window.innerWidth / 2}
        stageHeight={400}
        annotateWidth={annotateWidth}
        imageSource={imageSource}
        scrapsSource={scrapsSource}
        patterns={patternImages}
        assignments={fabricAssignments}
        patternScaling={patternScaling} />
      <Button variant="contained" onClick={navigateToAnnotate}>Back to Annotate</Button>
      <Button variant="contained" onClick={navigateToAssign}>Back to Assign</Button>
    </div>
  );
};

export default PlacingApp;
