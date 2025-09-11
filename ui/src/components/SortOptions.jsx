import React, { useState, useEffect } from 'react';
import { FormControl, InputLabel, Select, MenuItem, IconButton, Box, Typography, Tooltip } from '@mui/material';
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward';
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';

const SortOptions = ({ value, onChange, onDirectionToggle, onCriteriaChange }) => {
  const [selectedCriteria, setSelectedCriteria] = useState('none');
  const [isAscending, setIsAscending] = useState(true);

  // Reset internal state when value is 'none'
  useEffect(() => {
    if (value === 'none') {
      setSelectedCriteria('none');
      setIsAscending(true);
      return;
    }
    
    // Parse the current value to set initial state
    if (value && value !== 'none') {
      const criteria = value.replace('Inc', '').replace('Dec', '');
      const ascending = value.endsWith('Inc');
      setSelectedCriteria(criteria);
      setIsAscending(ascending);
    }
  }, [value]);

  const handleCriteriaChange = (event) => {
    const criteria = event.target.value;
    setSelectedCriteria(criteria);
    
    // Call the callback if provided
    if (onCriteriaChange) {
      onCriteriaChange(criteria, selectedCriteria);
    }
    
    if (criteria === 'none') {
      onChange('none');
    } else {
      onChange(criteria + (isAscending ? 'Inc' : 'Dec'));
    }
  };

  const toggleDirection = () => {
    const newIsAscending = !isAscending;
    setIsAscending(newIsAscending);
    
    // Call the callback if provided
    if (onDirectionToggle) {
      onDirectionToggle(newIsAscending, selectedCriteria);
    }
    
    if (selectedCriteria !== 'none') {
      onChange(selectedCriteria + (newIsAscending ? 'Inc' : 'Dec'));
    }
  };

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', marginLeft: 2 }}>
      <FormControl size="small" sx={{ minWidth: 120 }}>
        <InputLabel>Rank Options By</InputLabel>
        <Select
          value={selectedCriteria}
          label="Rank Options By"
          onChange={handleCriteriaChange}
        >
          <MenuItem value="none">
            Wasted Area (Least)
            <Tooltip title="Default sorting (least wasted area first)">
              <span>
                <IconButton size="small" sx={{ padding: '2px' }}>
                  <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                </IconButton>
              </span>
            </Tooltip>
          </MenuItem>
          <MenuItem value="hue">
            Color Tone
            <Tooltip title="Sort options by their color tone similarity">
              <span>
                <IconButton size="small" sx={{ padding: '2px' }}>
                  <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                </IconButton>
              </span>
            </Tooltip>
          </MenuItem>
          <MenuItem value="value">
            Color Brightness
            <Tooltip title="Sort options by their brightness similarity">
              <span>
                <IconButton size="small" sx={{ padding: '2px' }}>
                  <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                </IconButton>
              </span>
            </Tooltip>
          </MenuItem>
          <MenuItem value="color">
            Color Tone + Brightness
            <Tooltip title="Sort options by their color tone and brightness similarity">
              <span>
                <IconButton size="small" sx={{ padding: '2px' }}>
                  <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                </IconButton>
              </span>
            </Tooltip>
          </MenuItem>
        </Select>
      </FormControl>
      {selectedCriteria !== 'none' && (
        <Tooltip title={isAscending ? 
          "Low Contrast: Fabrics within the strip option will have similar color tones and/or brightness" : 
          "High Contrast: Fabrics within the strip option will have different color tones and/or brightness"}>
          <span>
            <IconButton
              onClick={toggleDirection}
              size="small"
            >
            {isAscending ? <ArrowUpwardIcon /> : <ArrowDownwardIcon />}
            </IconButton>
            <Typography variant="caption">{isAscending ? "Low Contrast" : "High Contrast"}</Typography>
          </span>
        </Tooltip>
      )}
    </Box>
  );
};

export default SortOptions;
