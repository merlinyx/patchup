import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import Grid from '@mui/material/Grid2';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import InputAdornment from '@mui/material/InputAdornment';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import Stack from '@mui/material/Stack';

const RectpackPage = () => {
  const [binAlgo, setBinAlgo] = useState('BNF');
  const [sortAlgo, setSortAlgo] = useState('AREA');
  const [binWidth, setBinWidth] = useState(3200);
  const [binHeight, setBinHeight] = useState(2500);
  const [packedImage, setPackedImage] = useState(null);
  const [fabricFolder, setFabricFolder] = useState('/ui_test1/');
  const [dpi, setDpi] = useState(100);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const logUserAction = async (action, details) => {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      action,
      details,
      binAlgo,
      sortAlgo,
      binWidth,
      binHeight,
      fabricFolder,
      dpi,
    };

    try {
      await axios.post('http://127.0.0.1:5000/api/log_action', logEntry);
    } catch (error) {
      console.error('Error logging action:', error);
    }
  };

  useEffect(() => {
    let folder = localStorage.getItem('fabricFolder');
    if (folder) {
      folder = folder.replace(/"/g, '');
      setFabricFolder(folder);
    }
  }, []);

  const estimatePackingWH = async () => {
    logUserAction('ESTIMATE_PACKING_WH');
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/estimate_packing_wh', {
        fabric_folder: fabricFolder,
        bin_algo: binAlgo,
        sort_algo: sortAlgo,
        dpi: dpi,
      });
      setBinWidth(response.data.width);
      setBinHeight(response.data.height);
      setSuccess(response.data.message);
    } catch (error) {
      console.error('Estimation error:', error);
    }
  }

  const handleFolderSelect = (event) => {
    event.preventDefault();
    const files = event.target.files;
    if (files.length > 0) {
      const folderPath = files[0].webkitRelativePath.split("/")[0];
      setFabricFolder(folderPath);
      localStorage.setItem("fabricFolder", JSON.stringify(folderPath));
    }
  };

  const handlePacking = async () => {
    setLoading(true);
    setError(null);
    setSuccess(null);
    setPackedImage(null);

    logUserAction('RUN_RECTPACK');
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/rectpack', {
        fabric_folder: fabricFolder,
        bin_algo: binAlgo,
        sort_algo: sortAlgo,
        dpi: dpi,
        width: binWidth,
        height: binHeight
      });

      if (response.data.success) {
        setPackedImage(response.data.final_image);
        setSuccess(response.data.message);
      } else {
        setError(response.data.error || 'Unknown error occurred');
      }
    } catch (error) {
      console.error('Packing error:', error);
      setError(error.response?.data?.error || 'Error occurred during packing');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <Grid container spacing={1} sx={{ width: window.innerWidth }} >
        <Grid size={12} sx={{ backgroundColor: '#dbf1ff' }}>
          <Stack direction="row" spacing={2} sx={{ padding: 1 }}>
            <Link to="/">
              <Button sx={{ textTransform: 'none' }}>Back to Fabric Bins</Button>
            </Link>
            <Link to="/packing">
              <Button sx={{ textTransform: 'none' }}>Back to Packing</Button>
            </Link>
          </Stack>
        </Grid>
      </Grid>
      <form onSubmit={(e) => e.preventDefault()}>
        <Grid container spacing={1} sx={{ width: window.innerWidth, marginTop: 1 }} >
          <Grid size={4}>
            <Tooltip title="Select the folder containing your fabric images">
              <Button variant="contained" size="small" component="label" sx={{ textTransform: 'none' }}>
                Select Folder
                <input
                  type="file"
                  webkitdirectory="true"
                  directory="true"
                  multiple
                  hidden
                  onChange={handleFolderSelect}
                />
              </Button>
              <Typography id="fabric-folder" variant="button" gutterBottom>{fabricFolder}</Typography>
            </Tooltip>
          </Grid>
          <Grid size={2}>
            <Tooltip title="How many pixels correspond to one inch. For high-resolution images, dpi=100 but for resized low-res images, dpi=10.">
              <TextField
                label="Pixels per Inch"
                id="outlined-end-adornment"
                value={dpi}
                onChange={(e) => {
                  setDpi(e.target.value);
                  localStorage.setItem('dpi', JSON.stringify(e.target.value));
                }}
                size="small"
                slotProps={{
                  input: {
                    endAdornment: <InputAdornment position="end">dpi</InputAdornment>,
                  },
                }}
              />
            </Tooltip>
          </Grid>
          <Grid size={12}></Grid>
        </Grid>
        <Grid container spacing={1} sx={{ width: window.innerWidth, marginLeft: 2 }} >
          <Grid size={2}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FormControl fullWidth>
                <InputLabel>Bin Algorithm</InputLabel>
                <Select
                  value={binAlgo}
                  onChange={(e) => setBinAlgo(e.target.value)}
                  label="Bin Algorithm"
                  size="small"
                >
                  <MenuItem value="BBF">Best Bin First</MenuItem>
                  <MenuItem value="BNF">Best Node First</MenuItem>
                  <MenuItem value="Global">Global</MenuItem>
                  <MenuItem value="BFF">Best Fit First</MenuItem>
                </Select>
              </FormControl>
              <Tooltip title={
                <div>
                  <p><strong>Best Bin First:</strong> Places fabric in the bin with the best fit</p>
                  <p><strong>Best Node First:</strong> Places fabric at the best available position</p>
                  <p><strong>Global:</strong> Optimizes placement considering all fabrics</p>
                  <p><strong>Best Fit First:</strong> Places fabric where it fits most snugly</p>
                </div>
              }>
                <IconButton size="small">
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </div>
          </Grid>
          <Grid size={2}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FormControl fullWidth>
                <InputLabel>Sort Algorithm</InputLabel>
                <Select
                  value={sortAlgo}
                  label="Sort Algorithm"
                  onChange={(e) => setSortAlgo(e.target.value)}
                  size="small"
                >
                  <MenuItem value="NONE">None</MenuItem>
                  <MenuItem value="AREA">Area</MenuItem>
                  <MenuItem value="DIFF">Difference</MenuItem>
                  <MenuItem value="RATIO">Ratio</MenuItem>
                  <MenuItem value="SSIDE">Short Side</MenuItem>
                  <MenuItem value="LSIDE">Long Side</MenuItem>
                  <MenuItem value="PERI">Perimeter</MenuItem>
                </Select>
              </FormControl>
              <Tooltip title={
                <div>
                  <p><strong>None:</strong> No sorting, use original order</p>
                  <p><strong>Area:</strong> Sort by total fabric area</p>
                  <p><strong>Difference:</strong> Sort by difference between width and height</p>
                  <p><strong>Ratio:</strong> Sort by width to height ratio</p>
                  <p><strong>Short Side:</strong> Sort by shortest side length</p>
                  <p><strong>Long Side:</strong> Sort by longest side length</p>
                  <p><strong>Perimeter:</strong> Sort by total perimeter</p>
                </div>
              }>
                <IconButton size="small">
                  <HelpOutlineIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </div>
          </Grid>
          <Grid size={1}>
            <Tooltip title="Width of the packing area in pixels">
              <TextField
                fullWidth
                type="number"
                label="Bin Width"
                value={binWidth}
                onChange={(e) => setBinWidth(Number(e.target.value))}
                size="small"
              />
            </Tooltip>
          </Grid>
          <Grid size={1}>
            <Tooltip title="Height of the packing area in pixels">
              <TextField
                fullWidth
                type="number"
                label="Bin Height"
                value={binHeight}
                onChange={(e) => setBinHeight(Number(e.target.value))}
                size="small"
              />
            </Tooltip>
          </Grid>
          <Grid size={3}>
            <Stack direction="row" spacing={2}>
              <Tooltip title="Start packing fabrics using current settings">
                <span>
                  <Button 
                    variant="contained" 
                    onClick={handlePacking}
                    disabled={loading}
                    size="small"
                    sx={{ textTransform: 'none' }}
                  >
                    {loading ? <CircularProgress size={24} /> : 'Pack Rectangles'}
                  </Button>
                </span>
              </Tooltip>
              <Tooltip title="Automatically determine optimal packing area dimensions">
                <span>
                  <Button 
                    variant="contained" 
                    onClick={estimatePackingWH}
                    size="small"
                    sx={{ textTransform: 'none' }}
                  >
                    Estimate Packing Sizes
                  </Button>
                </span>
              </Tooltip>
            </Stack>
          </Grid>
          {error && (
            <Grid size={12}>
              <Alert severity="error">{error}</Alert>
            </Grid>
          )}
          {success && (
            <Grid size={12}>
              <Alert severity="success">{success}</Alert>
            </Grid>
          )}
          {packedImage && (
            <Grid size={12} style={{ marginTop: 20 }}>
              <img 
                src={packedImage}
                alt="Packed Result"
                style={{ 
                  maxWidth: '100%',
                  border: '1px solid #ccc',
                  borderRadius: 4,
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                }}
              />
            </Grid>
          )}
        </Grid>
      </form>
    </div>
  );
};

export default RectpackPage;
