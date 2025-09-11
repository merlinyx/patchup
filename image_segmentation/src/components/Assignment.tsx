import React, { useState } from 'react';
import axios from 'axios';

import { Tabs, Tab, Chip, Paper, Box, Typography, Button } from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import ToggleButton from '@mui/material/ToggleButton';

const FabricPatternSelector = ({
    fabricPieces,
    patternPieces,
    fabricAssignments,
    setFabricAssignments,
    setPatternScaling,
}: {
    fabricPieces: string[];
    patternPieces: string[];
    fabricAssignments: {};
    setFabricAssignments: (fabricAssignments: {}) => void;
    setPatternScaling: (patternScaling: number) => void;
}) => {

  const [selectedTab, setSelectedTab] = useState(0);
  const [turnedEdge, setTurnedEdge] = useState(false);

  const getLabel = (patternPiece) => {
    let paths = patternPiece.split('/');
    return paths[paths.length - 1].split('.')[0];
  };

  const fitPattern = (fabricAssignments, turnedEdge) => async () => {
    const response = await axios.post('http://127.0.0.1:5000/api/fit_pattern', { assignment: fabricAssignments, turnedEdge: turnedEdge }, { responseType: 'json' });
    setPatternScaling(response.data['pattern_scaling']);
  };

  return (
    <div className="PatternAssignment">
      <Tabs
        value={selectedTab}
        onChange={(e, newValue) => setSelectedTab(newValue)}
        indicatorColor="primary"
        textColor="primary"
        variant="fullWidth">
        {patternPieces.map((patternPiece) => (
          <Tab label={getLabel(patternPiece)} key={patternPiece} />
        ))}
      </Tabs>
      <Box p={2}>
        {patternPieces.map((patternPiece, index) => (
          <TabPanel value={selectedTab} index={index} key={patternPiece}>
            <Paper style={{ minHeight: 50, padding: 2 }} >
              {fabricAssignments[patternPiece].map((fabric) => (
                <Chip
                  label={getLabel(fabric)}
                  key={fabric}
                  style={{ margin: 4 }}
                  onDelete={() => {
                    const newAssignments = { ...fabricAssignments };
                    newAssignments[patternPiece] = fabricAssignments[patternPiece].filter((f) => f !== fabric);
                    setFabricAssignments(newAssignments);}}
                />
              ))}
            </Paper>
          </TabPanel>
        ))}
      </Box>
      <Box p={2}>
        <Typography variant="h6">Available Fabrics</Typography>
        <Paper style={{ minHeight: 50, padding: 2 }} >
          {fabricPieces
            .filter((fabric) => !Object.values(fabricAssignments).flat().includes(fabric))
            .map((fabric) => (
            <Chip
              key={fabric}
              label={getLabel(fabric)}
              style={{ margin: 4 }}
              onClick={() => {
                const newAssignments = { ...fabricAssignments };
                newAssignments[patternPieces[selectedTab]].push(fabric);
                setFabricAssignments(newAssignments);}}
            />
          ))}
        </Paper>
      </Box>
      <ToggleButton
        size="small"
        value="check"
        selected={turnedEdge}
        onChange={() => {
          setTurnedEdge(!turnedEdge);
        }}
      >
        <CheckIcon /> Use Turned Edge
      </ToggleButton>
      <Button variant="contained" onClick={fitPattern(fabricAssignments, turnedEdge)}>
        Fit Patterns onto Fabric
      </Button>
    </div>
  );
};

const TabPanel = ({ children, value, index }) => {
  return (
    <div role="tabpanel" hidden={value !== index}>
      {value === index && <Box p={3}>{children}</Box>}
    </div>
  );
};

export default FabricPatternSelector;
