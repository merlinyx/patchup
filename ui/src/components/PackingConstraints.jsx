import React, { useState, useEffect } from 'react';
import { Slider, Checkbox, FormControlLabel, Tooltip, IconButton, Stack } from '@mui/material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import Grid from '@mui/material/Grid2';

// Convert decimal to fraction (nearest 1/4th)
const decimalToFraction = (decimal) => {
  const wholePart = Math.floor(decimal);
  const decimalPart = decimal - wholePart;
  
  // If it's a whole number, just return it
  if (decimalPart === 0) {
    return `${wholePart}"`;
  }

  // Convert to nearest 1/4th
  const quarters = Math.round(decimalPart * 4);
  
  // Simplify fraction if possible
  const fractions = {
    1: '1/4',
    2: '1/2',
    3: '3/4',
    4: '1' // This would actually make it a whole number
  };

  if (quarters === 4) {
    return `${wholePart + 1}"`;
  }

  if (quarters === 0) {
    return `${wholePart}"`;
  }

  return wholePart > 0 ? `${wholePart} ${fractions[quarters]}"` : `${fractions[quarters]}"`;
};

const PackingConstraints = ({
  thicknessMin,
  thicknessMax,
  fabricCountMin,
  fabricCountMax,
  onThicknessChange,
  onFabricCountChange,
  maxThickness = 1500,
  maxFabricCount = 10,
  onThicknessToggle,
  onFabricCountToggle
}) => {
  const [isThicknessEnabled, setIsThicknessEnabled] = useState(true);
  const [isFabricCountEnabled, setIsFabricCountEnabled] = useState(true);
  const [lastThicknessValues, setLastThicknessValues] = useState([
    thicknessMin ? thicknessMin / 100 : 0,
    thicknessMax ? thicknessMax / 100 : maxThickness / 100
  ]);
  const [lastFabricCountValues, setLastFabricCountValues] = useState([fabricCountMin || 0, fabricCountMax || maxFabricCount]);

  // Reset the saved values when props change to null
  useEffect(() => {
    setLastThicknessValues([
      thicknessMin ? thicknessMin / 100 : 0,
      thicknessMax ? thicknessMax / 100 : maxThickness / 100
    ]);
  }, [thicknessMin, thicknessMax, maxThickness]);

  useEffect(() => {
    setLastFabricCountValues([fabricCountMin || 0, fabricCountMax || maxFabricCount]);
  }, [fabricCountMin, fabricCountMax, maxFabricCount]);

  useEffect(() => {
    if (localStorage.getItem('isThicknessEnabled')) {
      setIsThicknessEnabled(JSON.parse(localStorage.getItem('isThicknessEnabled')));
    }
    if (localStorage.getItem('isFabricCountEnabled')) {
      setIsFabricCountEnabled(JSON.parse(localStorage.getItem('isFabricCountEnabled')));
    }
  }, []);

  const handleThicknessChange = (event, newValue) => {
    event.preventDefault();
    setLastThicknessValues(newValue);
    // Convert back to pixels when sending to parent
    onThicknessChange(Math.round(newValue[0] * 100), Math.round(newValue[1] * 100));
  };

  const handleFabricCountChange = (event, newValue) => {
    event.preventDefault();
    setLastFabricCountValues(newValue);
    onFabricCountChange(newValue[0], newValue[1]);
  };

  const handleThicknessToggle = (event) => {
    event.preventDefault();
    const newState = event.target.checked;
    setIsThicknessEnabled(newState);
    localStorage.setItem('isThicknessEnabled', newState);
    
    // Call the callback if provided
    if (onThicknessToggle) {
      onThicknessToggle(newState);
    }
    
    if (!newState) {
      onThicknessChange(null, null);
    } else {
      onThicknessChange(Math.round(lastThicknessValues[0] * 100), Math.round(lastThicknessValues[1] * 100));
    }
  };

  const handleFabricCountToggle = (event) => {
    event.preventDefault();
    const newState = event.target.checked;
    setIsFabricCountEnabled(newState);
    localStorage.setItem('isFabricCountEnabled', newState);
    
    // Call the callback if provided
    if (onFabricCountToggle) {
      onFabricCountToggle(newState);
    }
    
    if (!newState) {
      onFabricCountChange(null, null);
    } else {
      onFabricCountChange(lastFabricCountValues[0], lastFabricCountValues[1]);
    }
  };

  return (
    <>
      <Stack spacing={2}>
        <Grid container spacing={1} alignItems="center">
          <Grid size={4}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={isThicknessEnabled}
                    onChange={handleThicknessToggle}
                  />
                }
                label="Strip Thickness (in)"
              />
              <Tooltip title="Set the minimum and maximum thickness (in inches) for the next strip to be attached. Uncheck the checkbox to disable this constraint.">
                <IconButton size="small">
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
          </Grid>
          <Grid size={7}>
            <Slider
              getAriaLabel={() => 'Strip Width Range'}
              value={isThicknessEnabled ? lastThicknessValues : [0, maxThickness / 100]}
              onChange={handleThicknessChange}
              valueLabelDisplay="on"
              valueLabelFormat={(value) => decimalToFraction(value)}
              min={0}
              max={maxThickness / 100}
              step={0.25}
              disabled={!isThicknessEnabled}
            />
          </Grid>
        </Grid>

        <Grid container spacing={1} alignItems="center">
          <Grid size={4}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <FormControlLabel
                control={
                  <Checkbox
                    checked={isFabricCountEnabled}
                    onChange={handleFabricCountToggle}
                  />
                }
                label="Fabric Count"
              />
              <Tooltip title="Set the minimum and maximum number of fabrics the next strip should have. Uncheck the checkbox to disable this constraint.">
                <IconButton size="small">
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Stack>
          </Grid>
          <Grid size={7}>
            <Slider
              value={isFabricCountEnabled ? lastFabricCountValues : [0, maxFabricCount]}
              onChange={handleFabricCountChange}
              valueLabelDisplay="on"
              min={0}
              max={maxFabricCount}
              step={1}
              disabled={!isFabricCountEnabled}
            />
          </Grid>
        </Grid>
      </Stack>
    </>
  );
};

export default PackingConstraints; 
