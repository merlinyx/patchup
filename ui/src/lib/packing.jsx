import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Link } from 'react-router-dom';
import { Stage, Layer, Image, Rect } from 'react-konva';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import update from 'immutability-helper';
import axios from 'axios';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

import Grid from '@mui/material/Grid2';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import { styled } from '@mui/material/styles';
import Paper from '@mui/material/Paper';
import TextField from '@mui/material/TextField';
import InputAdornment from '@mui/material/InputAdornment';
import Typography from '@mui/material/Typography';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Checkbox from '@mui/material/Checkbox';
import ListItemText from '@mui/material/ListItemText';
import CircularProgress from '@mui/material/CircularProgress';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import Stack from '@mui/material/Stack';
import UndoIcon from '@mui/icons-material/Undo';

import PackingConstraints from '../components/PackingConstraints';
import SortOptions from '../components/SortOptions';
import { StepByStepInstructions, StripFirstInstructions } from '../components/Instructions';

import './packing.css';
import './instructions.css';

const Item = styled(Paper)(({ theme }) => ({
  backgroundColor: '#fff',
  ...theme.typography.body2,
  margin: theme.spacing(1),
  padding: theme.spacing(1),
  textAlign: 'center',
  color: theme.palette.text.secondary,
  ...theme.applyStyles('dark', {
    backgroundColor: '#1A2027',
  }),
}));

const addCacheBuster = (url) => {
  if (!url) return url;
  const cacheBuster = `cache=${Date.now()}`;
  return url.includes('?') ? `${url}&${cacheBuster}` : `${url}?${cacheBuster}`;
};

// Create a draggable fabric element
const DraggableFabric = ({ id, width, height, index, moveCard, fabricImageSrc, rotated }) => {
  const ref = useRef(null);
  const [, drop] = useDrop({
    accept: 'fabric',
    hover(item, monitor) {
      if (!ref.current) {
        return;
      }
      const dragIndex = item.index;
      const hoverIndex = index;
      if (dragIndex === hoverIndex) {
        return;
      }
      // If index changes, move the fabric order
      moveCard(dragIndex, hoverIndex);
      item.index = hoverIndex;
    },
  });

  const [{ isDragging }, drag] = useDrag({
    type: 'fabric',
    item: () => ({ id, index }),
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const opacity = isDragging ? 0.4 : 1;
  drag(drop(ref));

  // Create a rotated version of the image when needed
  const [displayImageSrc, setDisplayImageSrc] = useState(fabricImageSrc);

  if (rotated) {
    // Create an image object to check dimensions
    const img = new window.Image();
    img.src = fabricImageSrc;
    img.onload = () => {
      // Create canvas to rotate image
      const canvas = document.createElement('canvas');
      canvas.width = img.height;
      canvas.height = img.width;
      const ctx = canvas.getContext('2d');
      // Translate and rotate
      ctx.translate(canvas.width/2, canvas.height/2);
      ctx.rotate(Math.PI/2);
      ctx.drawImage(img, -img.width/2, -img.height/2);
      // Set the rotated image source
      setDisplayImageSrc(canvas.toDataURL());
    };
  }

  return (
    <div 
      ref={ref}
      className="draggable-fabric"
      style={{ 
        opacity, 
        width: `${rotated ? height : width}px`,
        height: `${rotated ? width : height}px`,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        overflow: 'hidden'
      }}
    >
      {displayImageSrc && (
        <img 
          src={displayImageSrc}
          alt={`Fabric ${id}`}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover'
          }}
        />
      )}
    </div>
  );
};

// Reorder the fabrics
const ReorderModal = ({ option, onClose, onConfirm, isVertical }) => {
  const currentBins = JSON.parse(localStorage.getItem('currentBins'));
  // Find the fabric image from currentBins
  const getFabricImage = (id) => {
    if (!currentBins || !Array.isArray(currentBins)) return null;
    // Search through all bins for a fabric with matching id
    for (const bin of currentBins) {
      const fabric = bin.fabrics.find(fabric => fabric.id === id);
      if (fabric) {
        // Return the image src - using img (base64) if available, otherwise use image path
        return fabric.img ? `data:image/png;base64,${fabric.img}` : fabric.image;
      }
    }
    return null;
  };

  const [fabrics, setFabrics] = useState(option.images_data);
  const [indices, setIndices] = useState(fabrics.map((_, index) => index));
  const [scalingFactor, setScalingFactor] = useState(1);

  // Consider making them parameters
  const modalMaxWidthPercentage = 95;
  const containerMaxWidth = 600;
  const modalMaxWidth = containerMaxWidth * modalMaxWidthPercentage / 100;
  const modalMaxHeight = 400;

  useEffect(() => {
    let totalWidth = 0;
    let totalHeight = 0;

    if (isVertical()) {
      // For vertical orientation
      totalWidth = option.thickness;
      
      // Calculate total height accounting for rotation
      totalHeight = fabrics.reduce((sum, fabric) => {
        // If rotated, use width as height, otherwise use height
        const fabricHeight = fabric.rotated ? fabric.width : fabric.height;
        return sum + fabricHeight;
      }, 0);
      
      setScalingFactor(Math.min(modalMaxHeight / totalHeight, modalMaxWidth / totalWidth));
    } else {
      // For horizontal orientation
      
      // Calculate total width accounting for rotation
      totalWidth = fabrics.reduce((sum, fabric) => {
        // If rotated, use height as width, otherwise use width
        const fabricWidth = fabric.rotated ? fabric.height : fabric.width;
        return sum + fabricWidth;
      }, 0);
      
      // Calculate maximum height accounting for rotation
      totalHeight = Math.max(...fabrics.map(fabric => 
        fabric.rotated ? fabric.width : fabric.height
      ));
      
      setScalingFactor(Math.min(modalMaxHeight / totalHeight, modalMaxWidth / totalWidth));
    }
  }, [isVertical, option.thickness, fabrics, modalMaxWidth, modalMaxHeight]);

  // Move the fabric
  const moveCard = useCallback((dragIndex, hoverIndex) => {
    setFabrics((prevCards) =>
      update(prevCards, {
        $splice: [
          [dragIndex, 1],
          [hoverIndex, 0, prevCards[dragIndex]],
        ],
      }),
    );
    setIndices((prevIndices) => {
      const newIndices = [...prevIndices];
      newIndices.splice(hoverIndex, 0, newIndices.splice(dragIndex, 1)[0]);
      return newIndices;
    });
  }, []);

  return (
    <div className="modal">
      <div className="modal-content" style={{ width: '90%', maxWidth: containerMaxWidth + 'px' }}>
        <h3>Reorder the fabric</h3>
        <div 
          className="fabric-container"
          style={{
            display: 'flex',
            flexDirection: isVertical() ? 'column' : 'row',
            width: modalMaxWidthPercentage + '%',
            height: modalMaxHeight + 'px',
            overflowX: isVertical() ? 'hidden' : 'auto',
            overflowY: isVertical() ? 'auto' : 'hidden',
          }}
        >
          {fabrics.map((fabric, index) => (
            <DraggableFabric
              key={fabric.id}
              id={fabric.id}
              width={fabric.width * scalingFactor}
              height={fabric.height * scalingFactor}
              index={index}
              moveCard={moveCard}
              fabricImageSrc={getFabricImage(fabric.id)}
              rotated={fabric.rotated}
            />
          ))}
        </div>
        <form onSubmit={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }} className="modal-buttons">
          <Button 
            variant="contained" 
            sx={{ textTransform: 'none' }}
            onClick={() => onConfirm({ option_key: option.option_key, indices: indices })}
          >
            Add to Block
          </Button>
          <Button
            variant="contained"
            sx={{ textTransform: 'none' }}
            onClick={onClose}
          >
            Cancel
          </Button>
        </form>
      </div>
    </div>
  );
};

// Convert decimal to fraction string
const decimalToFraction = (decimal) => {
  const wholePart = Math.floor(decimal);
  const decimalPart = decimal - wholePart;
  
  // If it's a whole number, just return it
  if (decimalPart === 0) {
    return `${wholePart}`;
  }

  // Convert to nearest 1/8th
  const eighths = Math.round(decimalPart * 8);
  
  // Simplify fraction if possible
  const fractions = {
    1: '1/8',
    2: '1/4',
    3: '3/8',
    4: '1/2',
    5: '5/8',
    6: '3/4',
    7: '7/8',
    8: '1'
  };

  if (eighths === 8) {
    return `${wholePart + 1}`;
  }

  if (eighths === 0) {
    return `${wholePart}`;
  }

  return wholePart > 0 ? `${wholePart} ${fractions[eighths]}` : fractions[eighths];
};

// Parse fraction string to decimal
const parseFraction = (value) => {
  // Handle empty input
  if (!value) return 0;

  // Try parsing as a simple number first
  const numValue = Number(value);
  if (!isNaN(numValue)) return numValue;

  // Handle mixed numbers and fractions
  const parts = value.trim().split(' ');
  let result = 0;

  // Parse whole number part if it exists
  if (parts.length > 1) {
    result = Number(parts[0]);
    if (isNaN(result)) return 0;
  }

  // Parse fraction part
  const fractionPart = parts[parts.length - 1];
  if (fractionPart.includes('/')) {
    const [num, denom] = fractionPart.split('/').map(Number);
    if (!isNaN(num) && !isNaN(denom) && denom !== 0) {
      result += num / denom;
    }
  }

  return result;
};

const PackingPage = () => {
  // Helper function to safely parse localStorage items
  const getStorageItem = (key, defaultValue) => {
    const item = localStorage.getItem(key);
    if (!item || item === 'undefined') return defaultValue;
    try {
      return JSON.parse(item);
    } catch (e) {
      return defaultValue;
    }
  };

  // Get fabric folder first as DPI depends on it
  const fabricFolder = getStorageItem('fabricFolder', '/ui_test1/');
  const shouldUseLowDpi = fabricFolder.toLowerCase && fabricFolder.toLowerCase().includes('resized');
  const dpi = shouldUseLowDpi ? 10 : getStorageItem('dpi', 100);

  const [currentStep, setCurrentStep] = useState(getStorageItem('currentStep', 0));
  const [currentImage, setCurrentImage] = useState(null);
  const [showReorderModal, setShowReorderModal] = useState(false);
  const [selectedOption, setSelectedOption] = useState(null);
  const [showOptions, setShowOptions] = useState(getStorageItem('showOptions', false));
  const [packingStrategy, setPackingStrategy] = useState(getStorageItem('packingStrategy', 'log-cabin'));
  const [startLength, setStartLength] = useState(getStorageItem('startLength', 800));
  const [sortBy, setSortBy] = useState(getStorageItem('sortBy', 'none'));
  const [packedFabricSize, setPackedFabricSize] = useState(getStorageItem('packedFabricSize', null));
  const [utilization, setUtilization] = useState(getStorageItem('utilization', null));
  const [backendResponse, setBackendResponse] = useState(getStorageItem('backendResponse', null));
  const [backendMessage, setBackendMessage] = useState(getStorageItem('backendMessage', ''));
  const [loading, setLoading] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [packingResults, setPackingResults] = useState(null);
  const [availableBins, setAvailableBins] = useState([]);
  const [selectedBins, setSelectedBins] = useState(getStorageItem('selectedBins', []));
  const [thicknessMin, setThicknessMin] = useState(getStorageItem('thicknessMin', null));
  const [thicknessMax, setThicknessMax] = useState(getStorageItem('thicknessMax', null));
  const [fabricCountMin, setFabricCountMin] = useState(getStorageItem('fabricCountMin', null));
  const [fabricCountMax, setFabricCountMax] = useState(getStorageItem('fabricCountMax', null));
  const [isExporting, setIsExporting] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [saveLoading, setSaveLoading] = useState(false);
  const [undoPerformed, setUndoPerformed] = useState(getStorageItem('undoPerformed', false));
  const [isResetting, setIsResetting] = useState(false);
  const [stepByStep, setStepByStep] = useState(true);
  const [inputValue, setInputValue] = useState('');

  const logUserAction = async (action, details) => {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      action,
      details,
      fabricFolder,
      packingStrategy,
      dpi,
      startLength,
      sortBy,
      currentStep
    };

    try {
      await axios.post('http://127.0.0.1:5000/api/log_action', logEntry);
    } catch (error) {
      console.error('Error logging action:', error);
    }
  };

  const handleFinishPacking = async () => {
    logUserAction('FINISH_PACKING');
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/finish_packing');
      setPackingResults(response.data);
      setShowResults(true);
      setBackendMessage('Packing completed');
      localStorage.setItem('backendMessage', JSON.stringify('Packing completed'));
    } catch (error) {
      console.error('Error:', error);
      setBackendMessage(error.message);
      localStorage.setItem('backendMessage', JSON.stringify(error.message));
    }
  };

  const saveHighResResults = async () => {
    setSaveLoading(true);
    logUserAction('SAVE_HIGH_RES_RESULTS');
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/finish_packing_high_res', {
        fabricFolder: fabricFolder,
        stepByStep: stepByStep,
      });
      setBackendMessage(response.data.message);
      localStorage.setItem('backendMessage', JSON.stringify(response.data.message));
    } catch (error) {
      console.error('Error:', error);
      setBackendMessage(error.message);
      localStorage.setItem('backendMessage', JSON.stringify(error.message));
    } finally {
      setSaveLoading(false);
    }
  }

  // Load saved image on component mount
  useEffect(() => {
    const savedResponse = getStorageItem('backendResponse', null);
    if (savedResponse && savedResponse.packed_fabric_path) {
      const img = new window.Image();
      img.src = addCacheBuster(savedResponse.packed_fabric_path);
      if (!img.src.includes('undefined')) {
        img.onload = () => {
          setCurrentImage(img);
        };
      }
    }
  }, []);

  const loadBinOptions = async () => {
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/load_bin_options', { isBinning: false });
      if (response.data.bins) {
        if (response.data.bins.length !== availableBins.length) {
          clearBins();
        }
        setAvailableBins(response.data.bins);
      }
    } catch (error) {
      console.error('Error loading bins:', error);
    }
  };

  // Load available bins on component mount
  useEffect(() => {
    const loadBins = async () => {
      try {
        const response = await axios.post('http://127.0.0.1:5000/api/load_bin_options', { isBinning: false });
        if (response.data.bins) {
          setAvailableBins(response.data.bins);
        }
      } catch (error) {
        console.error('Error loading bins:', error);
      }
    };

    loadBins();
  }, []);

  // Handle bin selection change
  const handleBinSelectionChange = async (event) => {
    const selectedBinIds = event.target.value;
    logUserAction('SELECT_BINS', {
      fromBins: selectedBins,
      toBins: selectedBinIds
    });
    setSelectedBins(selectedBinIds);
    localStorage.setItem('selectedBins', JSON.stringify(selectedBinIds));
  };

  const handleOptionSelect = (option) => {
    logUserAction('SELECT_OPTION', {
      optionKey: option.option_key
    });
    setSelectedOption(option);
    setShowReorderModal(true);
  };

  const handleReorderConfirm = (newOption) => {
    logUserAction('REORDER_CONFIRM', {
      optionKey: newOption.option_key,
      optionOrder: newOption.indices
    });
    setShowReorderModal(false);
    updateCurrentImageWithStrip(newOption);
  };

  const isVertical = useCallback(() => {
    if (packingStrategy === 'courthouse-steps') {
      return Math.floor(currentStep / 2) % 2 === 1;
    } else if (packingStrategy === 'log-cabin') {
      return currentStep % 2 === 0;
    } else if (packingStrategy === 'rail-fence') {
      return Math.floor(currentStep / 3) % 2 === 1;
    }
  }, [currentStep, packingStrategy]);

  const handleThicknessChange = (min, max) => {
    logUserAction('CHANGE_THICKNESS_CONSTRAINT', {
      fromMin: thicknessMin,
      fromMax: thicknessMax,
      toMin: min,
      toMax: max
    });
    setThicknessMin(min);
    setThicknessMax(max);
    localStorage.setItem('thicknessMin', JSON.stringify(min));
    localStorage.setItem('thicknessMax', JSON.stringify(max));
  };

  const handleFabricCountChange = (min, max) => {
    logUserAction('CHANGE_FABRIC_COUNT_CONSTRAINT', {
      fromMin: fabricCountMin,
      fromMax: fabricCountMax,
      toMin: min,
      toMax: max
    });
    setFabricCountMin(min);
    setFabricCountMax(max);
    localStorage.setItem('fabricCountMin', JSON.stringify(min));
    localStorage.setItem('fabricCountMax', JSON.stringify(max));
  };

  const handleGenerateOptionsResponse = (data) => {
    if (data.packed_fabric_path) {
      const img = new window.Image();
      if (!data.packed_fabric_path.includes('undefined')) {
        img.src = addCacheBuster(data.packed_fabric_path);
        img.onload = () => {
          setCurrentImage(img);
        };
      }
    }

    // Update the packed fabric size if it's included in the response
    if (data.packed_fabric_size) {
      setPackedFabricSize(data.packed_fabric_size);
      localStorage.setItem('packedFabricSize', JSON.stringify(data.packed_fabric_size));
    }
    if (data.utilization) {
      setUtilization(data.utilization);
      localStorage.setItem('utilization', JSON.stringify(data.utilization));
    }
    localStorage.setItem('showOptions', JSON.stringify(true));
    localStorage.setItem('backendResponse', JSON.stringify(data));
    setShowOptions(true);
    setBackendResponse(data);

    if ('bins_merged' in data && data.bins_merged) {
      console.log('bins_merged in response.data');
      setBackendMessage('cannot find options with current bins; automatically merged neighboring bins');
      localStorage.setItem('backendMessage', JSON.stringify('cannot find options with current bins; automatically merged neighboring bins'));
      loadBinOptions();
      clearBins();
    } else {
      setBackendMessage(data.message);
      localStorage.setItem('backendMessage', JSON.stringify(data.message));
    }
  };

  const retrieveLastResponse = () => {
    logUserAction('RETRIEVE_LAST_RESPONSE');
    fetch('http://127.0.0.1:5000/api/retrieve_last_response', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    })
    .then(response => response.json())
    .then(data => {
      handleGenerateOptionsResponse(data);
    })
    .catch(error => {
      console.log(error);
      setBackendMessage('Error retrieving last response');
      localStorage.setItem('backendMessage', JSON.stringify('Error retrieving last response'));
    });
  };

  const generateNextOptions = async (stepOverride = null) => {
    setLoading(true);
    logUserAction('GENERATE_OPTIONS');
    let packedFabricPath = null;
    if (backendResponse && backendResponse.packed_fabric_path) {
      packedFabricPath = backendResponse.packed_fabric_path;
    }

    try {
      const response = await fetch('http://127.0.0.1:5000/api/generate_options', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          currentStep: stepOverride !== null ? stepOverride : currentStep,
          dataFolder: fabricFolder,
          packedFabric: packedFabricPath,
          packingStrategy: packingStrategy,
          selectedBins: selectedBins,
          dpi: dpi,
          startLength: startLength,
          sortBy: sortBy,
          thicknessMin: thicknessMin,
          thicknessMax: thicknessMax,
          fabricCountMin: fabricCountMin,
          fabricCountMax: fabricCountMax,
        }),
      });
      const data = await response.json();
      if (data.message === 'Options generated successfully!') {
        await retrieveLastResponse();
      }
    } catch (error) {
      console.log(error);
      setBackendMessage('Error generating next options');
      localStorage.setItem('backendMessage', JSON.stringify('Error generating next options'));
    } finally {
      setLoading(false);
      setShowResults(false);
    }
  };

  const updateCurrentImageWithStrip = (option) => {
    logUserAction('PACK_WITH_OPTION', {
      optionKey: option.option_key,
      optionOrder: option.indices,
    });

    // Reset undo state when packing with a new option
    setUndoPerformed(false);
    localStorage.setItem('undoPerformed', JSON.stringify(false));

    fetch('http://127.0.0.1:5000/api/pack_with_selected_option', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        currentStep: currentStep,
        packingStrategy: packingStrategy,
        optionKey: option.option_key,
        optionOrder: option.indices,
      }),
    })
    .then(response => response.json())
    .then(data => {
      localStorage.setItem('backendMessage', JSON.stringify(data.message));
      localStorage.setItem('currentStep', JSON.stringify(data.iter));
      localStorage.setItem('packedArea', JSON.stringify(data.used_area));
      localStorage.setItem('packedFabricSize', JSON.stringify(data.packed_fabric_size));
      localStorage.setItem('utilization', JSON.stringify(data.utilization));
      setBackendResponse(data);
      setBackendMessage(data.message);
      setCurrentStep(data.iter);
      setPackedFabricSize(data.packed_fabric_size);
      setUtilization(data.utilization);

      if (data.packed_fabric_path) {
        const img = new window.Image();
        if (!data.packed_fabric_path.includes('undefined')) {
          img.src = addCacheBuster(data.packed_fabric_path);
          img.onload = () => {
            setCurrentImage(img);
          };
        }
      }
      localStorage.setItem('showOptions', JSON.stringify(false));
      setShowOptions(false);
    })
    .catch(error => {
      console.log(error);
      setBackendMessage('Error updating current image with strip');
      localStorage.setItem('backendMessage', JSON.stringify('Error updating current image with strip'));
    })
    .finally(() => {
      loadBinOptions();
    });
  };

  const stageSize = 550;
  const scalingFactor = useCallback(() => {
    if (!currentImage) return 1;
    if (currentImage.width < stageSize && currentImage.height < stageSize) return 1;
    return stageSize / Math.max(currentImage.width, currentImage.height);
  }, [currentImage]);

  const options = useMemo(() => {
    if (showOptions) {
      if (backendResponse && backendResponse['options']) {
        return backendResponse['options'];
      } else {
        console.log('No backend response; checking localStorage');
        const savedResponse = localStorage.getItem('backendResponse');
        if (savedResponse) {
          if (JSON.parse(savedResponse))
            return JSON.parse(savedResponse)['options'];
        } else {
          console.log('No saved response');
        }
      }
    }
    return [];
  }, [showOptions, backendResponse]);

  const onSelectPackingStrategy = (e) => {
    logUserAction('SELECT_PACKING_STRATEGY', {
      fromStrategy: packingStrategy,
      toStrategy: e.target.value
    });
    setPackingStrategy(e.target.value);
    localStorage.setItem('packingStrategy', JSON.stringify(e.target.value));
    setShowOptions(false);
    localStorage.setItem('showOptions', JSON.stringify(false));
  };

  const clearBins = () => {
    logUserAction('CLEAR_BINS');
    localStorage.setItem('selectedBins', JSON.stringify([]));
    setSelectedBins([]);
  };

  const resetPacking = async () => {
    logUserAction('RESET_PACKING');
    setIsResetting(true);
    try {
      // reset everything on the frontend
      clearBins();
      handleThicknessChange(null, null);
      handleFabricCountChange(null, null);
      localStorage.setItem('sortBy', JSON.stringify('none'));
      localStorage.removeItem('backendResponse');
      localStorage.removeItem('backendMessage');
      localStorage.removeItem('packedFabricSize');
      localStorage.removeItem('utilization');
      localStorage.setItem('currentStep', JSON.stringify(0));
      localStorage.setItem('showOptions', JSON.stringify(false));
      setSortBy('none');
      setBackendResponse(null);
      setBackendMessage('');
      setPackedFabricSize(null);
      setUtilization(null);
      setPackingResults(null);
      setShowResults(false);
      setCurrentStep(0);
      setShowOptions(false);
      setCurrentImage(null);
      // reset everything on the backend
      const response = await axios.post('http://127.0.0.1:5000/api/reset_session');
      localStorage.setItem('backendMessage', JSON.stringify(response.data.message));
      // load bins from local storage so that there's no need to go back to binning page
      const localBins = localStorage.getItem('bins');
      if (localBins) {
        const saveBinsResponse = await axios.post('http://127.0.0.1:5000/api/save_bins', {
          bins: JSON.parse(localBins),
          dpi: dpi,
          isModify: false
        });
        if (saveBinsResponse.status !== 200) {
          console.error('Error saving bins:', saveBinsResponse);
        } else {
          loadBinOptions();
        }
      }
      setBackendMessage(response.data.message);
    } catch (error) {
      console.error('Error during reset:', error);
      setBackendMessage(`Reset failed: ${error.message}`);
      localStorage.setItem('backendMessage', JSON.stringify(`Reset failed: ${error.message}`));
    } finally {
      setIsResetting(false);
    }
  };

  const getAttachmentSide = useCallback(() => {    
    if (packingStrategy === 'log-cabin') {
      if (currentStep % 4 === 0) return " (attaching from left)";
      if (currentStep % 4 === 1) return " (attaching from top)";
      if (currentStep % 4 === 2) return " (attaching from right)";
      return " (attaching from bottom)";
    } else if (packingStrategy === 'courthouse-steps') {
      if (currentStep % 4 === 0) return " (attaching from top)";
      if (currentStep % 4 === 1) return " (attaching from bottom)";
      if (currentStep % 4 === 2) return " (attaching from left)";
      return " (attaching from right)";
    } else if (packingStrategy === 'rail-fence') {
      if (currentStep % 12 >= 0 && currentStep % 12 <= 2) return " (attaching from top)";
      if (currentStep % 12 >= 3 && currentStep % 12 <= 5) return " (attaching from right)";
      if (currentStep % 12 >= 6 && currentStep % 12 <= 8) return " (attaching from bottom)";
      return " (attaching from left)";
    }
    return "";
  }, [currentStep, packingStrategy]);

  const exportToPDF = async () => {
    setIsExporting(true);
    try {
      const element = document.getElementById('instructions-container');
      if (!element) {
        console.error('Instructions container not found');
        throw new Error('Instructions container not found');
      }
      
      // Wait for a short delay to ensure content is rendered
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Wait for all images to load
      const images = element.getElementsByTagName('img');
      const imagePromises = Array.from(images).map(img => {
        if (img.complete) {
          return Promise.resolve();
        }
        return new Promise((resolve, reject) => {
          img.onload = resolve;
          img.onerror = reject;
        });
      });

      await Promise.all(imagePromises);

      const canvas = await html2canvas(element, {
        scale: 1,
        useCORS: true,
        logging: false,
        allowTaint: true,
        backgroundColor: '#ffffff',
        scrollY: 0,
        windowWidth: element.scrollWidth,
        windowHeight: element.scrollHeight
      });

      // Page dimensions (in inches)
      const pageWidth = 8.5;
      const pageHeight = 11;
      const margin = 0.5;
      const contentWidth = pageWidth;
      const contentHeight = pageHeight - (2 * margin);

      // Convert page dimensions to pixels
      const pagedpi = 192;
      const contentWidthPx = contentWidth * pagedpi;
      const contentHeightPx = contentHeight * pagedpi;

      // Calculate number of pages needed
      const numPagesX = Math.ceil(canvas.width / contentWidthPx);
      const numPagesY = Math.ceil(canvas.height / contentHeightPx);

      // Create PDF
      const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'in',
        format: 'letter'
      });

      let pageCount = 0;
      // Add each page
      for (let y = 0; y < numPagesY; y++) {
        for (let x = 0; x < numPagesX; x++) {
          // Calculate the portion of the canvas to capture
          const sourceX = x * contentWidthPx;
          const sourceY = y * contentHeightPx;
          const sourceWidth = Math.min(contentWidthPx, canvas.width - sourceX);
          const sourceHeight = Math.min(contentHeightPx, canvas.height - sourceY);

          // Skip if this section would be empty
          if (sourceWidth <= 0 || sourceHeight <= 0) {
            continue;
          }

          // Create a temporary canvas for this page
          const tempCanvas = document.createElement('canvas');
          tempCanvas.width = sourceWidth;
          tempCanvas.height = sourceHeight;
          const tempCtx = tempCanvas.getContext('2d');

          // Draw the portion of the main canvas to the temporary canvas
          tempCtx.drawImage(
            canvas,
            sourceX, sourceY, sourceWidth, sourceHeight,
            0, 0, sourceWidth, sourceHeight
          );

          // Check if the temporary canvas has any non-white pixels
          const imageData = tempCtx.getImageData(0, 0, sourceWidth, sourceHeight);
          const hasContent = imageData.data.some(pixel => pixel !== 255);

          if (hasContent) {
            pageCount++;
            // Convert to image data
            const imgData = tempCanvas.toDataURL('image/jpeg', 0.95);

            // Only add a new page if this isn't the first page
            if (pageCount > 1) {
              pdf.addPage();
            }

            pdf.addImage(
              imgData,
              'JPEG',
              margin,
              margin,
              sourceWidth / pagedpi,
              sourceHeight / pagedpi
            );
          }
        }
      }
      
      pdf.save('quilt_instructions.pdf');
      logUserAction('EXPORT_TO_PDF');
    } catch (error) {
      console.error('Error exporting to PDF:', error);
      setBackendMessage('Error exporting to PDF: ' + error.message);
      localStorage.setItem('backendMessage', JSON.stringify('Error exporting to PDF: ' + error.message));
    } finally {
      setIsExporting(false);
    }
  };

  // Add handler for undo functionality
  const handleUndo = async () => {
    if (currentStep <= 0 || undoPerformed) {
      return; // Can't undo if at first step or already performed an undo
    }

    logUserAction('UNDO_STEP', {
      currentStep: currentStep,
    });

    setIsLoading(true);

    try {
      const response = await fetch('http://127.0.0.1:5000/api/undo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('Undo failed:', errorData.error);
        setBackendMessage(errorData.error || 'Failed to undo the last action');
        localStorage.setItem('backendMessage', JSON.stringify(errorData.error || 'Failed to undo the last action'));
        return;
      }

      const data = await response.json();
      
      // Update state with the previous state data
      setCurrentStep(data.iter);
      localStorage.setItem('currentStep', data.iter);
      
      if (data.packed_fabric_path) {
        const img = new window.Image();
        img.src = addCacheBuster(data.packed_fabric_path);
        img.onload = () => {
          setCurrentImage(img);
        };
        // Update backendResponse with the new data
        setBackendResponse({
          ...backendResponse,
          packed_fabric_path: data.packed_fabric_path
        });
        localStorage.setItem('backendResponse', JSON.stringify({
          ...backendResponse,
          packed_fabric_path: data.packed_fabric_path
        }));
      }
      
      setPackedFabricSize(data.packed_fabric_size || [0, 0]);
      setUtilization(data.utilization);
      setShowOptions(false);
      localStorage.setItem('packedFabricSize', JSON.stringify(data.packed_fabric_size));
      localStorage.setItem('utilization', JSON.stringify(data.utilization));
      localStorage.setItem('showOptions', JSON.stringify(false));
      
      // Mark that we've performed an undo
      setUndoPerformed(true);
      localStorage.setItem('undoPerformed', JSON.stringify(true));
      
      // Generate new options for the previous step
      // Pass the step from the server to avoid using the old value due to React's async state updates
      await generateNextOptions(data.iter);
    } catch (error) {
      console.error('Error during undo:', error);
      setBackendMessage('Failed to undo the last action: ' + error.message);
      localStorage.setItem('backendMessage', JSON.stringify('Failed to undo the last action: ' + error.message));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <DndProvider backend={HTML5Backend}>
      <Grid container sx={{ width: window.innerWidth }} >
        <Grid size={7} sx={{ backgroundColor: '#dbf1ff', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', padding: '0 10px' }}>
          <Link to="/" onClick={(e) => {
            e.preventDefault();
            logUserAction('NAVIGATE_TO_FABRIC_BINS');
            window.location.href = '/';
          }}>
            <Button size="large" sx={{ textTransform: 'none' }}>Back to Fabric Bins</Button>
          </Link>
          {/* <Link to="/rectpack">
            <Button sx={{ textTransform: 'none' }}>RectPack</Button>
          </Link> */}
        </Grid>
        <Grid size={5} sx={{ backgroundColor: '#dbf1ff', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', padding: '0 10px' }}>
          <Button
            size="small"
            sx={{ textTransform: 'none', color: 'rgba(0,0,0,0)' }}
            onClick={() => {
              if (currentStep === 0 || isResetting) {
                return;
              }
              saveHighResResults();
            }}
            disabled={saveLoading}
          >
            {saveLoading ? <CircularProgress size={24} /> : 'SHR'}
          </Button>
        </Grid>
        <Grid size={5}>
          <Item elevation={0}>
            <h2 className="packing-step-title">Step {currentStep}{getAttachmentSide()}</h2>
            <div className="packing-step-image">
              <Tooltip title={
                <div>
                  <p>Packing visualization showing the current state of the quilt.</p>
                  {currentStep > 0 && <p>White areas indicate where the next strip will be attached.</p>}
                  <p>The image is automatically scaled to fit the display area while maintaining proportions.</p>
                </div>
              }>
                <div> {/* Wrapper div needed for Tooltip to work with Stage */}
                  <Stage width={stageSize} height={stageSize}>
                    <Layer>
                      <Rect
                        x={0}
                        y={0}
                        width={stageSize}
                        height={stageSize}
                        fill="white"
                        stroke="black"
                        strokeWidth={2}
                      />
                      {currentImage && (
                        <Image
                          image={currentImage}
                          x={(stageSize - currentImage.width * scalingFactor()) / 2}
                          y={(stageSize - currentImage.height * scalingFactor()) / 2}
                          scaleX={scalingFactor()}
                          scaleY={scalingFactor()}
                        />
                      )}
                    </Layer>
                  </Stage>
                </div>
              </Tooltip>
            </div>
          </Item>
        </Grid>
        <Grid size={7}>
          <Item elevation={0}>
            <form onSubmit={(e) => {
              e.preventDefault();
              e.stopPropagation();
            }}>
              <Grid container spacing={1} alignItems="center">
                <Grid size={2}>
                  <Typography sx={{ fontSize: '16px' }}>1. Set packing strategy</Typography>
                </Grid>
                <Grid size={10}>
                  <Stack direction="row" spacing={2} alignItems="center">
                    <FormControl sx={{ marginRight: '10px' }}>
                      <InputLabel id="packing-strategy">Packing Strategy</InputLabel>
                      <Select
                        value={packingStrategy}
                        label="Packing Strategy"
                        onChange={onSelectPackingStrategy}
                        size="small">
                        <MenuItem value="log-cabin">
                          Log Cabin
                          <Tooltip title="Builds the quilt by attaching strips in a clockwise spiral pattern.">
                            <span>
                              <IconButton size="small" sx={{ padding: '2px' }}>
                                <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                              </IconButton>
                            </span>
                          </Tooltip>
                        </MenuItem>
                        <MenuItem value="courthouse-steps">
                          Courthouse Steps
                          <Tooltip title="Builds the quilt by attaching strips from the top/bottom and then the left/right.">
                            <span>
                              <IconButton size="small" sx={{ padding: '2px' }}>
                                <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                              </IconButton>
                            </span>
                          </Tooltip>
                        </MenuItem>
                        <MenuItem value="rail-fence">
                          Rail Fence
                          <Tooltip title="Builds by attaching three strips in the same direction before changing direction, rotating clockwise.">
                            <span>
                              <IconButton size="small" sx={{ padding: '2px' }}>
                                <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                              </IconButton>
                            </span>
                          </Tooltip>
                        </MenuItem>
                      </Select>
                    </FormControl>
                    {packingStrategy === 'rail-fence' && (
                      <Tooltip title="Initial length of the first strip for the Rail Fence strategy in pixels. Subsequent strips will be sized relative to this.">
                        <TextField
                          type="text"
                          label="Rail Fence Start Length"
                          value={inputValue} // Use a local state variable for the input text
                          onChange={(e) => {
                            // Just update the local input state without parsing
                            setInputValue(e.target.value);
                          }}
                          onBlur={() => {
                            // Parse and update the actual value only when the field loses focus
                            const newValue = parseFraction(inputValue);
                            logUserAction('CHANGE_START_LENGTH', {
                              fromStartLength: startLength,
                              toStartLength: newValue
                            });
                            setStartLength(Math.round(newValue * 100));
                            localStorage.setItem('startLength', JSON.stringify(Math.round(newValue * 100)));
                            
                            // Optional: format the display value after blur for consistency
                            setInputValue(decimalToFraction(Math.round(newValue * 100) / 100));
                          }}
                          size="small"
                          slotProps={{
                            input: {
                              endAdornment: <InputAdornment position="end">inch</InputAdornment>,
                            }
                          }}
                          helperText="e.g., '1 1/2', '3 1/4', or '8'"
                        />
                      </Tooltip>
                    )}
                    <Tooltip title="Reset the packing process and start over">
                      <span>
                        <Button variant="contained" sx={{ textTransform: 'none' }} onClick={() => resetPacking()}>Reset Packing</Button>
                      </span>
                    </Tooltip>
                  </Stack>
                </Grid>
              </Grid>
              <Grid size={12}>
                <hr style={{ marginBottom: '10px', border: 'none', borderTop: '1px solid rgba(0, 0, 0, 0.12)' }} />
              </Grid>
              <Grid container spacing={1} alignItems="center" sx={{ marginTop: 4, marginBottom: 1 }}>
                <Grid size={2}>
                  <Typography sx={{ fontSize: '16px' }}>2. Generate strip options</Typography>
                </Grid>
                <Grid size={10}>
                  <PackingConstraints
                    thicknessMin={thicknessMin}
                    thicknessMax={thicknessMax}
                    fabricCountMin={fabricCountMin}
                    fabricCountMax={fabricCountMax}
                    onThicknessChange={handleThicknessChange}
                    onFabricCountChange={handleFabricCountChange}
                    onThicknessToggle={(enabled) => {
                      logUserAction('TOGGLE_THICKNESS_CONSTRAINT', {
                        enabled: enabled,
                        values: enabled ? [thicknessMin, thicknessMax] : [null, null]
                      });
                    }}
                    onFabricCountToggle={(enabled) => {
                      logUserAction('TOGGLE_FABRIC_COUNT_CONSTRAINT', {
                        enabled: enabled,
                        values: enabled ? [fabricCountMin, fabricCountMax] : [null, null]
                      });
                    }}
                  />
                </Grid>
              </Grid>
              <Grid container size={12} spacing={1} alignItems="center">
                <Grid size={2}>
                  <Tooltip 
                    title="Generate options for the next strip to be attached based on current settings"
                    placement="right"
                    slotProps={{
                      popper: {
                        sx: { marginLeft: '10px' }
                      }
                    }}
                  >
                    <span>
                      <Button 
                        variant="contained" 
                        size="small"
                        disabled={loading || isResetting}
                        sx={{ textTransform: 'none' }}
                        onClick={() => generateNextOptions()}
                      >
                        {loading ? <CircularProgress size={24} /> : 'Generate Next Options'}
                      </Button>
                    </span>
                  </Tooltip>
                  {/* <Button
                    size="small"
                    sx={{ textTransform: 'none', color: 'rgba(0,0,0,0.5)' }}
                    onClick={retrieveLastResponse}>
                      Retrieve Last Response
                  </Button> */}
                  {backendMessage && <p>{backendMessage}</p>}
                </Grid>
                <Grid size={5} alignItems="center">
                  <FormControl size="small" sx={{ width: '50%', marginBottom: '10px' }}>
                    <InputLabel id="bin-select-label">Select Bins</InputLabel>
                    <Select
                      label="Select Bins"
                      multiple
                      value={selectedBins}
                      onChange={handleBinSelectionChange}
                      size="small"
                      disabled={isResetting}
                      renderValue={(selected) => {
                        if (selected.length === 0) {
                          return 'Select bins';
                        }
                        return `Selected ${selected.length} bin${selected.length > 1 ? 's' : ''}`;
                      }}
                    >
                      {availableBins.map((bin) => (
                        <MenuItem key={bin.id} value={bin.id}>
                          <Checkbox checked={selectedBins.indexOf(bin.id) > -1} />
                          <ListItemText
                            primary={bin.name}
                            secondary={`${bin.nfabrics} fabrics`}
                          />
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Tooltip title="Select bins to generate strip options from. Multiple bins can be selected to get strip options from multiple groups.">
                    <IconButton >
                      <HelpOutlineIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Clear all selected bins (this defaults to all bins)">
                    <span>
                      <Button variant="outlined" size="small" sx={{ textTransform: 'none' }} onClick={() => clearBins()} disabled={isResetting}>Clear Selection</Button>
                    </span>
                  </Tooltip>
                </Grid>
                <Grid size={5}>
                  <SortOptions
                    value={sortBy}
                    onChange={(newValue) => {
                      logUserAction('CHANGE_SORT_BY', {
                        fromSortBy: sortBy,
                        toSortBy: newValue
                      });
                      setSortBy(newValue);
                      localStorage.setItem('sortBy', JSON.stringify(newValue));
                    }}
                    onCriteriaChange={(newCriteria, oldCriteria) => {
                      logUserAction('CHANGE_SORT_CRITERIA', {
                        fromCriteria: oldCriteria,
                        toCriteria: newCriteria
                      });
                    }}
                    onDirectionToggle={(isAscending, criteria) => {
                      logUserAction('TOGGLE_SORT_DIRECTION', {
                        criteria: criteria,
                        direction: isAscending ? 'ascending' : 'descending',
                        contrast: isAscending ? 'low' : 'high'
                      });
                    }}
                  />
                </Grid>
              </Grid>
            </form>
            <Grid container spacing={1} alignItems="center" sx={{ marginTop: 1, marginBottom: 1 }}>
              <Grid size={2}>
                <Typography sx={{ fontSize: '16px' }}>3. Select from generated strip options</Typography>
                </Grid>
                {packedFabricSize && (
                  <Grid size={8}>
                    <Typography id="packing-info" gutterBottom>
                      Current Packed Fabric Size: {packedFabricSize[0] / dpi} x {packedFabricSize[1] / dpi} in; Scrap utilization Rate: {utilization}%
                    </Typography>
                  </Grid>
                )}
                {currentStep > 0 && (
                  <Grid size={2}>
                    <Tooltip title="Undo the previous packing step and go back to the previous state. Can only be used once per step.">
                      <span>
                        <Button
                          variant="outlined"
                          size="small"
                          color="primary"
                          startIcon={<UndoIcon />}
                          sx={{ textTransform: 'none' }}
                          onClick={handleUndo}
                          disabled={isLoading || undoPerformed || isResetting}
                        >
                          Undo Last Step
                        </Button>
                      </span>
                    </Tooltip>
                  </Grid>
                )}
            </Grid>
            { options.length > 0 && <div className="packing-options-grid"> 
              {options.map((option, index) => (
                option.strip_image &&
                <Tooltip
                  key={index}
                  placement="top"
                  title="Click to reorder fabrics in this strip and confirm the strip to attach next"
                >
                  <div className="packing-option-card" onClick={() => handleOptionSelect(option)}>
                    <div className="packing-option-content">
                      <div className="packing-option-image-wrapper">
                        <img 
                          src={`${addCacheBuster(option.strip_image)}`} 
                          alt={`strip ${index + 1} of ${options.length}`} 
                          className={`packing-option-image ${isVertical() ? 'vertical' : 'horizontal'}`}
                        />
                      </div>
                      <div className="packing-option-info">
                        <div style={{ 
                          display: 'grid',
                          gridTemplateColumns: 'auto 1px 125px',
                          alignItems: 'center'
                        }}>
                          <span>Strip Thickness</span> <span>:</span>
                          <span>{(option.thickness_px / 100).toFixed(2)} in.</span>
                          <span>Wasted Area</span> <span>:</span>
                          <span>{Number(option.wasted_area).toFixed(2)} sq. in.</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </Tooltip>
              ))}
            </div>}
            <Grid size={12}>
              {showReorderModal && selectedOption && (
                <ReorderModal
                  option={selectedOption}
                  onClose={() => setShowReorderModal(false)}
                  onConfirm={handleReorderConfirm}
                  isVertical={isVertical}
                />
              )}
            </Grid>
          </Item>
        </Grid>
      </Grid>
      <Grid size={4}>
        <Stack direction="row" spacing={2} justifyContent="center" sx={{ margin: '20px 0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Checkbox
              checked={stepByStep}
              onChange={(e) => {
                setStepByStep(e.target.checked);
                localStorage.setItem('stepByStep', JSON.stringify(e.target.checked));
              }}
            />
            <Typography sx={{ fontSize: '16px' }}>Use Step-by-Step Instructions</Typography>
            <Tooltip title="If checked, will show step-by-step instructions to guide you through the packing process. This will show you the fabrics you need to prepare for each step and the final result after each step. If unchecked, will use a strip-first format which shows how to prepare all strips first and then put them together.">
              <HelpOutlineIcon />
            </Tooltip>
          </div>
          <Tooltip title="Complete the packing process and generate final instructions">
            <span>
              <Button 
                variant="contained" 
                sx={{ textTransform: 'none' }}
                onClick={() => handleFinishPacking()}
                disabled={currentStep === 0 || isResetting}
              >
                Finish Packing
              </Button>
            </span>
          </Tooltip>
          <Tooltip title="Export instructions to PDF">
            <span>
              <Button
                variant="contained"
                sx={{ textTransform: 'none' }}
                onClick={exportToPDF}
                disabled={!showResults || isExporting || isResetting}
              >
                {isExporting ? <CircularProgress size={24} /> : 'Export Instructions to PDF'}
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Grid>
      {showResults && packingResults && (
        stepByStep ?
        <div id="instructions-container">
          <StepByStepInstructions instructions={packingResults.instructions} dpi={dpi} />
        </div>
        :
        <div id="instructions-container">
          <StripFirstInstructions instructions={packingResults.instructions} dpi={dpi} />
        </div>
      )}
    </DndProvider>
  );
};

export default PackingPage;
