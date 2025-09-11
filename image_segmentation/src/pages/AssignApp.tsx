import React, { useEffect, useState } from "react";
import { useNavigate } from 'react-router-dom';
import Button from '@mui/material/Button';

import Assignable from "../components/Assignable.tsx";
import FabricPatternSelector from "../components/Assignment.tsx";

import "./App.css";

const AssignApp = ({
  imageSource,
  scrapsSource
}: {
  imageSource: string;
  scrapsSource: string;
}) => {

  const [patternImages, setPatternImages] = useState<string[]>([]);
  const [scrapImages, setScrapImages] = useState<string[]>([]);
  const [patternScaling, setPatternScaling] = useState<number | null>(null);
  const [fabricAssignments, setFabricAssignments] = useState({});

  useEffect(() => {
    let emptyAssignments = {};
    patternImages.forEach((patternPiece) => { emptyAssignments[patternPiece] = []; });
    setFabricAssignments(emptyAssignments);
  }, [patternImages]);

  const navigate = useNavigate();
  const navigateBack = () => {
    navigate('/');
  };
  const navigateForward = () => {
    navigate('/placing', { state: { patternImages, fabricAssignments, patternScaling } });
  };

  return (
    <div className="App">
      <header className="App-header">
        <h2>Scrappy Collage Design</h2>
      </header>
      <div className="assignable-container">
        <Assignable
          imageSource={imageSource}
          isFabric={false}
          images={patternImages}
          setImages={setPatternImages} />
        <Assignable
          imageSource={scrapsSource}
          isFabric={true}
          images={scrapImages}
          setImages={setScrapImages} />
      </div>
      {scrapImages.length > 0 && patternImages.length > 0 &&
        <FabricPatternSelector
          fabricPieces={scrapImages}
          patternPieces={patternImages}
          fabricAssignments={fabricAssignments}
          setFabricAssignments={setFabricAssignments}
          setPatternScaling={setPatternScaling} />
      }
      {patternScaling && <Button variant="contained" onClick={navigateForward}>Go to Placing</Button>}
      {!patternScaling && <Button variant="contained" disabled onClick={navigateForward}>Go to Placing</Button>}
      <Button variant="contained" onClick={navigateBack}>Back to Annotate</Button>
    </div>
  );
};

export default AssignApp;
