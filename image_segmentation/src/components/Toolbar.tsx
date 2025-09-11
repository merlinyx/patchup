import React, { useState } from "react";
import axios from 'axios';

import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid";
import TextField from '@mui/material/TextField';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import Select, { SelectChangeEvent } from '@mui/material/Select';
import DeleteIcon from '@mui/icons-material/Delete';
import IconButton from '@mui/material/IconButton';

import { useUndoRedo, useGetPolygons, PolygonStyleProps } from "../lib/index.ts";

import "./Toolbar.css";

const Toolbar = ({
  bgImage,
  maxPolygons,
  setMaxPolygons,
  config,
  setConfig,
  isFabric,
}: {
  bgImage: string;
  maxPolygons: number;
  config: PolygonStyleProps;
  setMaxPolygons: (maxPolygons: number) => void;
  setConfig: (config: PolygonStyleProps) => void;
  isFabric: boolean;
}) => {
  const { undo, redo, canUndo, canRedo } = useUndoRedo();
  const { polygons, updateLabel, updateSize, deletePolygon, deletePolygons } = useGetPolygons();
  const [ sizeValue, setSizeValue ] = useState('');

  const handleSegmentClick = async (event) => {
    event.preventDefault();
    let polygonPoints = polygons.map((polygon) => [polygon.label, polygon.flattenedPoints]);
    let polygonDict = {};
    for (let pi = 0; pi < polygonPoints.length; pi++) {
      const label = polygonPoints[pi][0];
      const points = polygonPoints[pi][1];
      polygonDict[label] = points;
    }
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/segment_image',
        { polygons: polygonDict, bgImageSrc: bgImage, bgScaleRatio: config.bgScaleRatio },
        { responseType: 'json' });
      // Persist polygons to backend with sizes
      axios.post('http://127.0.0.1:5000/api/save_polygons',
        { polygons: polygons, image_name: bgImage, is_fabric: isFabric, segmented_images: response.data['segmented_images'] });
    } catch (error) {
      console.error('Error fetching image:', error);
    }
  };

  return (
    <Grid container columns={5} className="toolbar-wrapper">
      <TextField
        id={`maxPolygons-${config.propId}`}
        label="Max Polygon Number"
        size="small"
        margin="normal"
        defaultValue={maxPolygons}
        helperText="Enter max number of polygons"
        onChange={(e) => setMaxPolygons(+e.target.value)}
      />
      <TextField
        id={`vertexRad-${config.propId}`}
        label="Vertex Radius"
        size="small"
        margin="normal"
        defaultValue={config.vertexRadius}
        helperText="Enter a value"
        onChange={(e) => setConfig({ ...config, vertexRadius: +e.target.value })}
      />
      <TextField
        id={`vertexStroke-${config.propId}`}
        label="Vertex Stroke Width"
        size="small"
        margin="normal"
        defaultValue={config.vertexStrokeWidth}
        helperText="Enter a value"
        onChange={(e) => setConfig({ ...config, vertexStrokeWidth: +e.target.value })}
      />
      <TextField
        id={`lineColor-${config.propId}`}
        label="Polygon Line Color"
        size="small"
        margin="normal"
        type="color"
        defaultValue={config.lineColor}
        helperText="Enter polygon line color"
        onChange={(e) => setConfig({ ...config, lineColor: e.target.value })}
      />
      <TextField
        id={`vertexColor-${config.propId}`}
        label="Vertex Fill Color"
        size="small"
        margin="normal"
        type="color"
        defaultValue={config.lineColor}
        helperText="Enter polygon vertex color"
        onChange={(e) => setConfig({ ...config, vertexColor: e.target.value })}
      />
      <TextField
        id={`fillColor-${config.propId}`}
        label="Polygon Fill Color"
        size="small"
        margin="normal"
        type="color"
        defaultValue={config.fillColor}
        helperText="Enter polygon fill color"
        onChange={(e) => setConfig({ ...config, fillColor: e.target.value })}
      />
      <div>
        <Button variant="contained" onClick={undo} disabled={!canUndo}>Undo</Button>
        <Button variant="contained" onClick={redo} disabled={!canRedo}>Redo</Button>
        <Button variant="contained" onClick={() => deletePolygons(isFabric)} disabled={!canUndo}>Reset</Button>
        <Button variant="contained" onClick={handleSegmentClick}>Segment Image with Current Polygons</Button>
      </div>
      <div className="points-wrapper">
         {polygons.map((polygon) => (
          <div key={polygon.id}>
            <TextField
              id={`label-${polygon.id}`}
              label="Polygon Label"
              type="text"
              size="small"
              margin="normal"
              defaultValue={polygon.label}
              onChange={(e) => {
                updateLabel({ id: polygon.id, label: e.target.value });
              }}
            />
            <IconButton
              aria-label="delete"
              onClick={() => deletePolygon({index: polygon.index, isFabric: isFabric})}
            >
              <DeleteIcon />
            </IconButton>
            {isFabric && (
            <>
              <FormControl sx={{ m: 2, minWidth: 200 }} size="small">
                <InputLabel id={`polygon-size-select-label-${polygon.id}`}>Scrap Piece Size</InputLabel>
                <Select
                  labelId={`polygon-size-select-label-${polygon.id}`}
                  id={`polygon-size-select-${polygon.id}`}
                  value={""}
                  label="Preset Scrap Piece Size"
                  onChange={(e: SelectChangeEvent) => {
                    updateSize({ id: polygon.id, size: e.target.value });
                    if (e.target.value === '2.5"') {
                      setSizeValue('2.5" x ? "');
                    }
                    let size_pre = document.getElementById(`polygon-size-pre-${polygon.id}`);
                    if (size_pre) {
                      size_pre.innerText = `size: ${e.target.value}`;
                    }
                  }}
                >
                  <MenuItem value={'9" x 21"'}>Fat Eighth (9" x 21")</MenuItem>
                  <MenuItem value={'18" x 22"'}>Fat Quarter (18" x 22")</MenuItem>
                  <MenuItem value={'10" x 10"'}>Cake Layers (10" x 10")</MenuItem>
                  <MenuItem value={'2.5"'}>Jelly Roll (2.5" strips)</MenuItem>
                  <MenuItem value={'6.5" x 6.5"'}>Coins (6.5" squares)</MenuItem>
                  <MenuItem value={'5" x 5"'}>Charm Pack (5" squares)</MenuItem>
                </Select>
              </FormControl>
              <TextField
                id={`size-${polygon.id}`}
                label="Custom Scrap Piece Size"
                type="text"
                helperText="Enter the exact size in width x height format (e.g. 10 x 10), unit is inches."
                size="small"
                margin="normal"
                value={sizeValue}
                onChange={(e) => {
                  setSizeValue(e.target.value);
                  updateSize({ id: polygon.id, size: e.target.value });
                  let size_pre = document.getElementById(`polygon-size-pre-${polygon.id}`);
                  if (size_pre) {
                    size_pre.innerText = `size: ${e.target.value}`;
                  }
                }}
              />
            </>)}
            <pre style={{ whiteSpace: "pre-wrap" }}>
              points:{JSON.stringify(polygon.points)}
            </pre>
            {polygon.isFabric && <pre id={`polygon-size-pre-${polygon.id}`} style={{ whiteSpace: "pre-wrap" }}>
              size:{JSON.stringify(polygon.size)}
            </pre>}
          </div>
        ))}
      </div>
    </Grid>
  );
};

export default Toolbar;
