import React, { useState, useEffect, useRef, useMemo } from 'react';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import { Link } from 'react-router-dom';
import { ImageList, ImageListItem } from '@mui/material';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';

import axios from 'axios';

import Grid from '@mui/material/Grid2';
import Button from '@mui/material/Button';
import FormControl from '@mui/material/FormControl';
import TextField from '@mui/material/TextField';
// import Typography from '@mui/material/Typography';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Tooltip from '@mui/material/Tooltip';
import IconButton from '@mui/material/IconButton';
import { KeyboardArrowLeft, KeyboardArrowRight, KeyboardArrowDown } from '@mui/icons-material';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import Stack from '@mui/material/Stack';
import DeleteIcon from '@mui/icons-material/Delete';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';
import LockIcon from '@mui/icons-material/Lock';
import LockOpenIcon from '@mui/icons-material/LockOpen';
import UnfoldMoreIcon from '@mui/icons-material/UnfoldMore';
import UnfoldLessIcon from '@mui/icons-material/UnfoldLess';
import ListSubheader from '@mui/material/ListSubheader';

import './binning.css';

const DraggableBinFabric = ({ id, image, img, currentBin, onDelete }) => {
  const [{ isDragging }, drag] = useDrag({
    type: 'binFabric',
    item: { id, currentBin },
    collect: (monitor) => ({
      isDragging: monitor.isDragging()
    })
  });

  // Use img (base64 data) if it exists, otherwise use image path
  const imageSrc = img ? 'data:image/png;base64,' + img : image;
  const [rotatedSrc, setRotatedSrc] = useState(imageSrc);
  const [showDeleteButton, setShowDeleteButton] = useState(false);

  useEffect(() => {
    // Create an image object to check dimensions
    const img = new Image();
    img.src = imageSrc;
    img.onload = () => {
      if (img.width < img.height * 1.1) {
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
        setRotatedSrc(canvas.toDataURL());
      } else {
        setRotatedSrc(imageSrc);
      }
    };
  }, [imageSrc]);

  const handleDelete = (e) => {
    e.stopPropagation(); // Prevent drag event from firing
    onDelete(id, currentBin);
  };

  return (
    <ImageListItem
      ref={drag}
      className="bin-fabric"
      onMouseEnter={() => setShowDeleteButton(true)}
      onMouseLeave={() => setShowDeleteButton(false)}
      style={{
        opacity: isDragging ? 0.4 : 1,
        cursor: 'move',
        position: 'relative'
      }}
    >
      <img 
        src={rotatedSrc}
        alt={`Fabric ${id}`}
        loading="lazy"
        style={{ objectFit: 'cover' }}
      />
      {showDeleteButton && !isDragging && (
        <IconButton
          size="small"
          onClick={handleDelete}
          sx={{
            position: 'absolute',
            top: 4,
            right: 4,
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            '&:hover': {
              backgroundColor: 'rgba(255, 255, 255, 0.9)',
            },
            padding: '4px',
            zIndex: 1, // Ensure button is above the image
          }}
        >
          <DeleteIcon fontSize="small" />
        </IconButton>
      )}
    </ImageListItem>
  );
};

const Bin = ({
  id,
  name,
  fabrics,
  onDrop,
  onDelete,
  onRemove,
  isFixed,
  onToggleFix,
  isChecked,
  onToggleCheck,
  onRename,
  allBinsCollapsed
}) => {
  const [{ isOver }, drop] = useDrop({
    accept: 'binFabric',
    drop: (item) => {
      if (item.currentBin === id) return; 
      onDrop(item.id, id, item.currentBin);
    },
    collect: monitor => ({
      isOver: !!monitor.isOver(),
    }),
  });

  const [isEditing, setIsEditing] = useState(false);
  const [editedName, setEditedName] = useState(name);
  const [localCollapsed, setLocalCollapsed] = useState(allBinsCollapsed);
  
  useEffect(() => {
    setLocalCollapsed(allBinsCollapsed);
  }, [allBinsCollapsed]);

  // Toggle just the local collapsed state
  const toggleCollapse = () => {
    setLocalCollapsed(!localCollapsed);
  };

  const handleNameClick = () => {
    setIsEditing(true);
  };

  const handleNameChange = (e) => {
    setEditedName(e.target.value);
  };

  const handleNameBlur = () => {
    setIsEditing(false);
    if (editedName.trim() !== name) {
      onRename(id - 1, editedName.trim());
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      e.target.blur();
    }
  };

  return (
    <div className="bin-container">
      <div className="bin-header" style={{ display: 'flex', alignItems: 'center' }}>
        <Tooltip title="Drag to reorder bins">
          <DragIndicatorIcon sx={{ mr: 1, color: 'rgba(0, 0, 0, 0.5)', cursor: 'grab' }} />
        </Tooltip>
        <Checkbox 
          checked={isChecked}
          onChange={(e) => onToggleCheck(id - 1, e.target.checked)}
          size="small"
          sx={{ mr: 1 }}
        />
        {isEditing ? (
          <TextField
            value={editedName}
            onChange={handleNameChange}
            onBlur={handleNameBlur}
            onKeyDown={handleKeyPress}
            size="small"
            autoFocus
            sx={{ 
              width: '150px',
              '& .MuiInputBase-root': {
                height: '28px',
                fontSize: '0.875rem'
              },
              padding: '10px'
            }}
          />
        ) : (
          <h4 onClick={handleNameClick} style={{ cursor: 'pointer', margin: '15px' }}>{name}</h4>
        )}
        <Stack direction="row" spacing={1} sx={{ marginLeft: 'auto' }}>
          <Tooltip title={localCollapsed ? "Expand bin" : "Collapse bin"}>
            <IconButton
              size="small"
              onClick={toggleCollapse}
            >
              {localCollapsed ? <KeyboardArrowRight /> : <KeyboardArrowDown />}
            </IconButton>
          </Tooltip>
          <Tooltip title={isFixed ? "Unlock this bin (it will be changed during grouping)" : "Lock this bin (it won't be changed during grouping)"}>
            <IconButton
              size="small"
              onClick={() => onToggleFix(id - 1)}
              color={isFixed ? "primary" : "default"}
            >
              {isFixed ? <LockIcon /> : <LockOpenIcon />}
            </IconButton>
          </Tooltip>
          <Tooltip title="Remove this bin and return its fabrics to available fabrics">
            <Button 
              size="small" 
              variant="outlined"
              sx={{ textTransform: 'none' }}
              onClick={() => onRemove(id - 1)}
            >
              Remove Bin
            </Button>
          </Tooltip>
        </Stack>
      </div>
      {/* Show bin content only when not collapsed */}
      {!localCollapsed && (
        <div
          ref={drop}
          className={`bin ${isOver ? 'bin-hover' : ''} ${isFixed ? 'bin-fixed' : ''} ${isChecked ? 'bin-selected' : ''}`}
        >
          <ImageList variant="masonry" cols={10} gap={5} className="bin-content">
            {fabrics.map((fabric) => (
              <DraggableBinFabric
                key={fabric.id}
                {...fabric}
                currentBin={id}
                onDelete={onDelete}
              />
            ))}
          </ImageList>
        </div>
      )}
      {/* Display the fabric count when collapsed */}
      {localCollapsed && (
        <div 
          className={`bin-collapsed ${isFixed ? 'bin-fixed' : ''} ${isChecked ? 'bin-selected' : ''}`} 
          style={{ 
            padding: '10px', 
            borderBottom: '1px solid #e0e0e0',
            backgroundColor: '#f5f5f5',
            color: '#666',
            fontSize: '0.875rem'
          }}
        >
          {fabrics.length} fabric{fabrics.length !== 1 ? 's' : ''} in this bin
        </div>
      )}
    </div>
  );
};

const DraggableBin = ({
  id,
  index,
  name,
  fabrics,
  onDrop,
  onDelete,
  onRemove,
  moveBin,
  isFixed,
  onToggleFix,
  isChecked,
  onToggleCheck,
  onRename,
  allBinsCollapsed
}) => {
  const ref = useRef(null);
  const [{ isDragging }, drag] = useDrag({
    type: 'bin',
    item: { id, index },
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    })
  });

  const [, drop] = useDrop({
    accept: 'bin',
    hover(item, monitor) {
      if (!ref.current) {
        return;
      }
      const dragIndex = item.index;
      const hoverIndex = index;
      
      // Don't replace items with themselves
      if (dragIndex === hoverIndex) {
        return;
      }
      
      // Move the bin
      moveBin(dragIndex, hoverIndex);
      
      // Update the item's index for the next hover
      item.index = hoverIndex;
    },
  });

  // Connect the drag and drop refs to the same element
  drag(drop(ref));

  return (
    <div 
      ref={ref}
      className={`draggable-bin ${isDragging ? 'dragging' : ''}`}
    >
      <Bin 
        id={id}
        name={name}
        fabrics={fabrics}
        onDrop={onDrop}
        onDelete={onDelete}
        onRemove={onRemove}
        isFixed={isFixed}
        onToggleFix={onToggleFix}
        isChecked={isChecked}
        onToggleCheck={onToggleCheck}
        onRename={onRename}
        allBinsCollapsed={allBinsCollapsed}
      />
    </div>
  );
};

const BinningPage = () => {
  const [fabricFolder, setFabricFolder] = useState('/studyset_resized/');
  const [packingStrategy, setPackingStrategy] = useState('log-cabin');
  const [groupCriterion, setGroupCriterion] = useState(() => {
    const savedGroupCriterion = localStorage.getItem('groupCriterion');
    return (savedGroupCriterion && savedGroupCriterion !== 'undefined') ? JSON.parse(savedGroupCriterion) : 'hue';
  });
  const [mode, setMode] = useState(() => {
    const savedMode = localStorage.getItem('mode');
    return (savedMode && savedMode !== 'undefined') ? JSON.parse(savedMode) : 'dominant';
  });
  const [availableFabrics, setAvailableFabrics] = useState([]);
  const [removedFabrics, setRemovedFabrics] = useState([]);
  const [showRemovedFabrics, setShowRemovedFabrics] = useState(() => {
    const savedShowRemovedFabrics = localStorage.getItem('showRemovedFabrics');
    return (savedShowRemovedFabrics && savedShowRemovedFabrics !== 'undefined') ? JSON.parse(savedShowRemovedFabrics) : false;
  });
  const [useAllFabrics, setUseAllFabrics] = useState(() => {
    const savedUseAllFabrics = localStorage.getItem('useAllFabrics');
    return (savedUseAllFabrics && savedUseAllFabrics !== 'undefined') ? JSON.parse(savedUseAllFabrics) : true;
  });
  const [nFabricBins, setNFabricBins] = useState(() => {
    const savedNFabricBins = localStorage.getItem('nFabricBins');
    return (savedNFabricBins && savedNFabricBins !== 'undefined') ? JSON.parse(savedNFabricBins) : 3;
  });
  const [bins, setBins] = useState([
      { id: 1, name: 'Bin 1', fabrics: [] },
      { id: 2, name: 'Bin 2', fabrics: [] },
      { id: 3, name: 'Bin 3', fabrics: [] }
    ]);
  const [fixedBins, setFixedBins] = useState([]);
  const [binsChanged, setBinsChanged] = useState(false);
  const [modifyBins, setModifyBins] = useState(false);
  const [isGroupingFabrics, setIsGroupingFabrics] = useState(false);
  const [dpi, setDpi] = useState(100);
  const [binsFile, setBinsFile] = useState('');
  const [backendMessage, setBackendMessage] = useState('');
  const [messageType, setMessageType] = useState('info'); // 'info', 'error', 'success'
  const [messageVisible, setMessageVisible] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const [confirmDialogConfig, setConfirmDialogConfig] = useState({
    title: '',
    message: '',
    onConfirm: () => {},
    onCancel: () => {}
  });
  const [checkedBins, setCheckedBins] = useState([]);
  const [allBinsCollapsed, setAllBinsCollapsed] = useState(false);

  // Handle collapsing/expanding all bins
  const toggleAllBins = () => {
    setAllBinsCollapsed(!allBinsCollapsed);
    logUserAction('TOGGLE_ALL_BINS', {
      collapsed: !allBinsCollapsed
    });
  };

  // Use useMemo to derive fixedBins array from bins with fixed property
  const fixedBinIndexes = useMemo(() => {
    return bins.reduce((indexes, bin, index) => {
      if (bin.fixed) {
        indexes.push(index);
      }
      return indexes;
    }, []);
  }, [bins]);

  // Add useEffect for availableFabrics persistence
  useEffect(() => {
    localStorage.setItem('availableFabrics', JSON.stringify(availableFabrics));
  }, [availableFabrics]);

  // Add useEffect for mode persistence
  useEffect(() => {
    localStorage.setItem('mode', JSON.stringify(mode));
  }, [mode]);

  // Add useEffect for groupCriterion persistence
  useEffect(() => {
    localStorage.setItem('groupCriterion', JSON.stringify(groupCriterion));
  }, [groupCriterion]);

  // Add useEffect for nFabricBins persistence
  useEffect(() => {
    localStorage.setItem('nFabricBins', JSON.stringify(nFabricBins));
  }, [nFabricBins]);

  // Add useEffect for useAllFabrics persistence
  useEffect(() => {
    localStorage.setItem('useAllFabrics', JSON.stringify(useAllFabrics));
  }, [useAllFabrics]);

  // Add useEffect for removedFabrics persistence
  useEffect(() => {
    localStorage.setItem('removedFabrics', JSON.stringify(removedFabrics));
  }, [removedFabrics]);

  // Add useEffect for showRemovedFabrics persistence
  useEffect(() => {
    localStorage.setItem('showRemovedFabrics', JSON.stringify(showRemovedFabrics));
  }, [showRemovedFabrics]);

  // Add useEffect for fixedBins persistence
  useEffect(() => {
    localStorage.setItem('fixedBins', JSON.stringify(fixedBins));
  }, [fixedBins]);

  // Add useEffect for checkedBins persistence
  useEffect(() => {
    localStorage.setItem('checkedBins', JSON.stringify(checkedBins));
  }, [checkedBins]);

  useEffect(() => {
    const savedDpi = localStorage.getItem('dpi');
    if (savedDpi) {
      setDpi(JSON.parse(savedDpi));
    }
    const savedFolder = localStorage.getItem('fabricFolder');
    if (savedFolder) {
      setFabricFolder(JSON.parse(savedFolder));
    }
    const savedPackingStrategy = localStorage.getItem('packingStrategy');
    if (savedPackingStrategy) {
      setPackingStrategy(JSON.parse(savedPackingStrategy));
    }
  }, []);

  // Enhanced message handling
  const showMessage = (message, type = 'info', isPermanent = false) => {
    setBackendMessage(message);
    setMessageType(type);
    setMessageVisible(true);

    if (!isPermanent) {
      const timer = setTimeout(() => {
        setMessageVisible(false);
        // Clear message after fade-out animation completes
        setTimeout(() => setBackendMessage(''), 300);
      }, 2000);

      return () => clearTimeout(timer);
    }
  };

  // Handle message updates
  useEffect(() => {
    if (backendMessage) {
      setMessageVisible(true);
    }
  }, [backendMessage]);

  const dismissMessage = () => {
    setMessageVisible(false);
    setTimeout(() => setBackendMessage(''), 300); // Clear after fade animation
  };

  // Add message clearing effect
  useEffect(() => {
    if (backendMessage && messageType !== 'error') {
      const timer = setTimeout(() => {
        setMessageVisible(false);
        // Clear message after fade-out animation completes
        setTimeout(() => setBackendMessage(''), 300);
      }, 3000);

      return () => clearTimeout(timer);
    }
  }, [backendMessage, messageType]);

  const logUserAction = async (action, details) => {
    const timestamp = new Date().toISOString();
    const logEntry = {
      timestamp,
      action,
      details,
      fabricFolder,
      packingStrategy,
      groupCriterion,
      mode
    };

    try {
      await axios.post('http://127.0.0.1:5000/api/log_action', logEntry);
    } catch (error) {
      console.error('Error logging action:', error);
    }
  };

  const onSelectPackingStrategy = (e) => {
    logUserAction('SELECT_PACKING_STRATEGY', {
      fromStrategy: packingStrategy,
      toStrategy: e.target.value
    });
    setPackingStrategy(e.target.value);
    localStorage.setItem('packingStrategy', JSON.stringify(e.target.value));
  };

  useEffect(() => {
    if (fabricFolder.toLowerCase().includes('resized')) {
      setDpi(10);
      localStorage.setItem('dpi', JSON.stringify(10));
    } else if (fabricFolder.toLowerCase().includes('tiny')) {
      setDpi(8);
      localStorage.setItem('dpi', JSON.stringify(8));
    } else {
      setDpi(100);
      localStorage.setItem('dpi', JSON.stringify(100));
    }
  }, [fabricFolder]);

  const loadFabrics = async () => {
    logUserAction('LOAD_FABRICS', {
      fabricFolder: fabricFolder
    });
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/load_fabrics', {
        fabric_folder: fabricFolder
      });

      if (response.data.fabrics.length === 0) {
        alert('No fabrics found in the selected folder!');
      } else {
        setAvailableFabrics(response.data.fabrics);
        setBinsChanged(false);
      }
      showMessage('Fabrics loaded successfully', 'success');
    } catch (error) {
      console.error('Error loading images:', error);
      showMessage('Error loading fabrics', 'error', true);
    }
  };

  // const handleFolderSelect = (event) => {
  //   event.preventDefault();
  //   const files = event.target.files;
  //   if (files.length > 0) {
  //     const folderPath = files[0].webkitRelativePath.split("/")[0];
  //     setFabricFolder(folderPath);
  //     localStorage.setItem("fabricFolder", JSON.stringify(folderPath));
  //   }
  // };

  const estimateBinSize = async() => {
    logUserAction('ESTIMATE_BINS', {
      groupCriterion: groupCriterion,
      mode: mode
    });
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/estimate_nbins', {
        fabric_folder: fabricFolder,
        group_criterion: groupCriterion,
        mode: mode
      });
      setNFabricBins(response.data.nbins);
      localStorage.setItem('nFabricBins', JSON.stringify(response.data.n_bins));
      showMessage('Estimated number of bins: ' + response.data.nbins, 'success');
    } catch (error) {
      console.error('Error:', error);
      showMessage('Error estimating bins', 'error', true);
    }
  };

  const addBin = () => {
    logUserAction('ADD_BIN');
    setBins(prevBins => [...prevBins, {
      id: prevBins.length + 1,
      name: `Bin ${prevBins.length + 1}`,
      fabrics: []
    }]);
    setBinsChanged(true);
  };

  const removeBin = (index) => {
    logUserAction('REMOVE_BIN', {
      removedBin: index
    });
    setBins(prevBins => {
      const binToRemove = prevBins[index];
      setAvailableFabrics(prevAvailableFabrics => [...prevAvailableFabrics, ...binToRemove.fabrics]);
      return prevBins.filter((_, binIndex) => binIndex !== index);
    });
    setBinsChanged(true);
  };

  const groupFabrics = async () => {
    setIsGroupingFabrics(true);
    logUserAction('GROUP_FABRICS', {
      nBins: nFabricBins,
      nFabrics: availableFabrics.length,
      useAllFabrics: useAllFabrics,
      fixedBinsCount: fixedBinIndexes.length
    });
    
    try {
      const response = await axios.post('http://127.0.0.1:5000/api/group_fabrics', {
        fabric_folder: fabricFolder,
        available_fabrics: useAllFabrics ? [] : availableFabrics,
        n_bins: nFabricBins - fixedBinIndexes.length, // Reduce number of new bins to create
        group_criterion: groupCriterion,
        mode: mode,
        fixed_bins: fixedBinIndexes.map(binIndex => bins[binIndex].fabrics) // Send fixed bins data to backend
      });

      // Create new bins array with the proper format
      const newBins = Array.from({ length: nFabricBins }, (_, index) => ({
        id: index + 1,
        name: `Bin ${index + 1}`,
        fabrics: []
      }));

      const groupedBins = response.data.bins;
      let groupedBinIndex = 0;

      // First, preserve the fixed bins with their fixed property
      for (let i = 0; i < bins.length && i < newBins.length; i++) {
        if (fixedBinIndexes.includes(i)) {
          // Preserve the fixed property and update the name if it's a default "Bin x" name
          const bin = bins[i];
          const isDefaultName = bin.name.startsWith('Bin ');
          newBins[i] = {
            ...bin,
            id: i + 1,
            name: isDefaultName ? `Bin ${i + 1}` : bin.name,
            fixed: true
          };
        }
      }

      // Then fill non-fixed bins with grouped bins
      for (let i = 0; i < newBins.length; i++) {
        if (!fixedBinIndexes.includes(i)) {
          if (groupedBinIndex < groupedBins.length) {
            newBins[i] = {
              id: i + 1,
              name: `Bin ${i + 1}`,
              fabrics: groupedBins[groupedBinIndex]
            };
            groupedBinIndex++;
          }
        }
      }
      
      // Add any remaining grouped bins as new bins
      while (groupedBinIndex < groupedBins.length) {
        newBins.push({
          id: newBins.length + 1,
          name: `Bin ${newBins.length + 1}`,
          fabrics: groupedBins[groupedBinIndex]
        });
        groupedBinIndex++;
      }

      setBins(newBins);
      setBinsChanged(true);
      
      // Update available fabrics to exclude all fabrics used in bins
      const allBinnedFabricIds = new Set(newBins.flatMap(bin => bin.fabrics.map(fabric => fabric.id)));
      setAvailableFabrics(prevFabrics => 
        prevFabrics.filter(fabric => !allBinnedFabricIds.has(fabric.id))
      );
      
      showMessage('Fabrics grouped successfully', 'success');
    } catch (error) {
      console.error('Error grouping fabrics:', error);
      showMessage('Error grouping fabrics: ' + error.message, 'error', true);
    } finally {
      setIsGroupingFabrics(false);
    }
  };

  const handleGroupFabrics = () => {
    // Check if all bins are fixed
    if (fixedBins.length > 0 && fixedBins.length >= nFabricBins) {
      showMessage('All bins are locked. Unlock some bins to allow grouping.', 'info', true);
      return;
    }

    // Check if we're requesting more bins than available after accounting for fixed bins
    const requiredNewBins = nFabricBins - fixedBins.length;
    if (requiredNewBins <= 0) {
      showMessage('Number of locked bins exceeds or equals the total number of bins requested. Please increase the number of bins or unlock some bins.', 'info', true);
      return;
    }

    if (!useAllFabrics) {
      if (availableFabrics.length === 0) {
        showMessage('No fabrics to group', 'info', true);
        return;
      } else if (availableFabrics.length < requiredNewBins) {
        showMessage(`Not enough available fabrics. Need at least ${requiredNewBins} fabrics to group into ${requiredNewBins} new bins.`, 'info', true);
        return;
      }
    }
    
    if (binsChanged) {
      showConfirmDialogWithConfig(
        "Unsaved Bin Changes",
        "You have unsaved changes to the fabric bins. Grouping fabrics will overwrite your current bin assignments except for locked bins. Would you like to continue?",
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'group_fabrics',
            action: 'continue'
          });
          groupFabrics();
        },
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'group_fabrics',
            action: 'cancel'
          });
        }
      );
    } else {
      groupFabrics();
    }
  };

  const handleDrop = (itemId, targetBinId, sourceBinId) => {    
    const targetIndex = targetBinId - 1;
    const sourceIndex = sourceBinId !== null ? sourceBinId - 1 : null;
    
    logUserAction('DRAG_FABRIC', {
      fabricId: itemId,
      fromBin: sourceBinId !== null ? sourceBinId : 'available',
      toBin: targetBinId
    });

    let fabric;
  
    if (sourceIndex !== null && sourceIndex >= 0 && sourceIndex < bins.length) {
      fabric = bins[sourceIndex].fabrics.find(f => f.id === itemId);
    } else {
      fabric = availableFabrics.find(f => f.id === itemId);
    }
  
    if (!fabric) return;
  
    if (sourceIndex !== null && sourceIndex >= 0 && sourceIndex < bins.length) {
      setBins(prevBins => prevBins.map((bin, index) => {
        if (index !== sourceIndex) return bin;
        return {
          ...bin,
          fabrics: bin.fabrics.filter(f => f.id !== itemId)
        };
      }));
      setBinsChanged(true);
    } else {
      setAvailableFabrics(prevFabrics => prevFabrics.filter(f => f.id !== itemId));
    }

    if (targetIndex !== null && targetIndex >= 0 && targetIndex < bins.length) {
      setBins(prevBins => prevBins.map((bin, index) => {
        if (index !== targetIndex) return bin;
        return {
          ...bin,
          fabrics: [...bin.fabrics, fabric]
        };
      }));
      setBinsChanged(true);
    } else {
      setAvailableFabrics(prevFabrics => [...prevFabrics, fabric]);
    }
  };

  const saveBins = async () => {
    logUserAction('SAVE_BINS', {
      nBins: bins.length,
      binSizes: bins.map(bin => bin.fabrics.length),
      isModify: modifyBins
    });

    if (!modifyBins) {
      localStorage.setItem('bins', JSON.stringify(bins));
    }
    localStorage.setItem('currentBins', JSON.stringify(bins));

    try {
      const response = await axios.post('http://127.0.0.1:5000/api/save_bins', {
        bins: bins,
        dpi: dpi,
        isModify: modifyBins
      });
      setBinsChanged(false);
      setModifyBins(false);
      showMessage(response.data.message, 'success');
    } catch (error) {
      console.error('Error saving bins:', error);
      showMessage('Error saving bins', 'error', true);
    }
  };
  
  const loadBins = async () => {
    logUserAction('LOAD_BINS', {
      binsFile: binsFile
    });
    try {
      if (binsFile) {
        const response = await axios.post('http://127.0.0.1:5000/api/load_bins', { binsFile });
        setBins(response.data.bins);
        showMessage(response.data.message, 'success');
        return;
      }

      const localBins = localStorage.getItem('bins');
      if (localBins) {
        setBins(JSON.parse(localBins));
        showMessage('Bins loaded from local storage', 'success');
        return;
      }

      const storedBinsFile = localStorage.getItem('binsFile');
      if (storedBinsFile) {
        const parsedBinsFile = JSON.parse(storedBinsFile);
        setBinsFile(parsedBinsFile);
        const response = await axios.post('http://127.0.0.1:5000/api/load_bins', { binsFile: parsedBinsFile });
        setBins(response.data.bins);
        showMessage(response.data.message, 'success');
      }
    } catch (error) {
      console.error('Error:', error);
      showMessage('Error loading bins', 'error', true);
    }
  };

  const loadBinOptions = async () => {
    logUserAction('MODIFY_BINS');
    setModifyBins(true);

    try {
      const response = await axios.post('http://127.0.0.1:5000/api/load_bin_options', { isBinning: true });
      if (response.data.bins) {
        setBins(response.data.bins);
        showMessage('Bins loaded successfully', 'success');
      } else {
        showMessage('No bins found', 'info');
      }
    } catch (error) {
      console.error('Error loading bins:', error);
      showMessage('Error loading bins', 'error', true);
    }
  };

  // Clear selected bins when bin count changes
  const numBins = useMemo(() => bins.length, [bins]);
  useEffect(() => {
    localStorage.setItem('selectedBins', JSON.stringify([]));
  }, [numBins]);
  
  const clearBins = () => {
    logUserAction('CLEAR_BINS');
    setAvailableFabrics([]);
    setRemovedFabrics([]);
    setBins([
      { id: 1, name: 'Bin 1', fabrics: [] },
      { id: 2, name: 'Bin 2', fabrics: [] },
      { id: 3, name: 'Bin 3', fabrics: [] }
    ]);
    setFixedBins([]);
    setBinsChanged(true);
    localStorage.setItem('bins', JSON.stringify([
      { id: 1, name: 'Bin 1', fabrics: [] },
      { id: 2, name: 'Bin 2', fabrics: [] },
      { id: 3, name: 'Bin 3', fabrics: [] }
    ]));
    localStorage.setItem('currentBins', JSON.stringify([
      { id: 1, name: 'Bin 1', fabrics: [] },
      { id: 2, name: 'Bin 2', fabrics: [] },
      { id: 3, name: 'Bin 3', fabrics: [] }
    ]));
    localStorage.setItem('availableFabrics', JSON.stringify([]));
    localStorage.setItem('removedFabrics', JSON.stringify([]));
    localStorage.setItem('fixedBins', JSON.stringify([]));
    showMessage('Bins cleared', 'info');
  };

  const handleDelete = (fabricId, currentBin) => {
    logUserAction('DELETE_FABRIC', {
      fabricId,
      currentBin,
      action: 'move_to_removed'
    });

    let fabric;
    if (currentBin === null) {
      // Move from available fabrics to removed fabrics
      fabric = availableFabrics.find(f => f.id === fabricId);
      setAvailableFabrics(prev => prev.filter(f => f.id !== fabricId));
    } else {
      // Move from bin to removed fabrics
      const binIndex = currentBin - 1;
      fabric = bins[binIndex].fabrics.find(f => f.id === fabricId);
      setBins(prevBins => {
        const newBins = [...prevBins];
        newBins[binIndex] = {
          ...newBins[binIndex],
          fabrics: newBins[binIndex].fabrics.filter(f => f.id !== fabricId)
        };
        return newBins;
      });
      setBinsChanged(true);
    }

    if (fabric) {
      setRemovedFabrics(prev => [...prev, { ...fabric, removedAt: new Date().toISOString() }]);
      showMessage('Fabric moved to removed fabrics', 'info');
    }
  };

  const restoreFabric = (fabricId) => {
    const fabric = removedFabrics.find(f => f.id === fabricId);
    if (fabric) {
      setRemovedFabrics(prev => prev.filter(f => f.id !== fabricId));
      setAvailableFabrics(prev => [...prev, fabric]);
      showMessage('Fabric restored to available fabrics', 'success');
    }
  };

  const permanentlyDeleteFabric = (fabricId) => {
    if (binsChanged) {
      showConfirmDialogWithConfig(
        "Unsaved Bin Changes",
        "You have unsaved changes to the fabric bins. Permanently deleting a fabric will mark your changes as unsaved. Would you like to continue?",
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'permanent_delete',
            action: 'continue'
          });
          setRemovedFabrics(prev => prev.filter(f => f.id !== fabricId));
          showMessage('Fabric permanently deleted', 'info');
        },
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'permanent_delete',
            action: 'cancel'
          });
        }
      );
    } else {
      setRemovedFabrics(prev => prev.filter(f => f.id !== fabricId));
      showMessage('Fabric permanently deleted', 'info');
    }
  };

  const showConfirmDialogWithConfig = (title, message, onConfirm, onCancel) => {
    setConfirmDialogConfig({
      title,
      message,
      onConfirm,
      onCancel
    });
    setShowConfirmDialog(true);
  };

  const handleLoadBins = () => {
    if (binsChanged) {
      showConfirmDialogWithConfig(
        "Unsaved Bin Changes",
        "You have unsaved changes to the fabric bins. Loading bins will overwrite your current bin assignments. Would you like to continue?",
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'load_bins',
            action: 'continue'
          });
          loadBins();
        },
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'load_bins',
            action: 'cancel'
          });
        }
      );
    } else {
      loadBins();
    }
  };

  const handleLoadBinOptions = () => {
    if (binsChanged) {
      showConfirmDialogWithConfig(
        "Unsaved Bin Changes",
        "You have unsaved changes to the fabric bins. Loading current bins will overwrite your current bin assignments. Would you like to continue?",
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'load_bin_options',
            action: 'continue'
          });
          loadBinOptions();
        },
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'load_bin_options',
            action: 'cancel'
          });
        }
      );
    } else {
      loadBinOptions();
    }
  };

  const handleClearBins = () => {
    if (binsChanged) {
      showConfirmDialogWithConfig(
        "Unsaved Bin Changes",
        "You have unsaved changes to the fabric bins. Clearing all bins will remove all your current bin assignments. Would you like to continue?",
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'clear_bins',
            action: 'continue'
          });
          clearBins();
        },
        () => {
          logUserAction('CONFIRM_DIALOG_ACTION', {
            dialog: 'clear_bins',
            action: 'cancel'
          });
        }
      );
    } else {
      clearBins();
    }
  };

  // Add a function to log fabric folder selection
  const handleFabricFolderChange = (e) => {
    const newFolder = e.target.value;
    setFabricFolder(newFolder);
    localStorage.setItem('fabricFolder', JSON.stringify(newFolder));
    
    logUserAction('SELECT_FABRIC_FOLDER', {
      fabricFolder: newFolder
    });
  };

  const moveBin = (dragIndex, hoverIndex) => {
    logUserAction('MOVE_BIN', {
      fromIndex: dragIndex,
      toIndex: hoverIndex
    });

    setBins(prevBins => {
      const newBins = [...prevBins];
      // Swap the bins
      const temp = newBins[dragIndex];
      newBins[dragIndex] = newBins[hoverIndex];
      newBins[hoverIndex] = temp;
      return newBins;
    });
    
    setBinsChanged(true);
  };

  const toggleFixBin = (binIndex) => {
    logUserAction('TOGGLE_FIX_BIN', {
      binIndex: binIndex,
      fixed: !bins[binIndex]?.fixed
    });

    setBins(prevBins => {
      const newBins = [...prevBins];
      if (binIndex >= 0 && binIndex < newBins.length) {
        newBins[binIndex] = {
          ...newBins[binIndex],
          fixed: !newBins[binIndex].fixed
        };
      }
      return newBins;
    });
  };

  const handleBinCheck = (binIndex, isChecked) => {
    logUserAction('CHECK_BIN', {
      binIndex,
      isChecked
    });

    setCheckedBins(prev => {
      if (isChecked) {
        return [...prev, binIndex];
      } else {
        return prev.filter(idx => idx !== binIndex);
      }
    });
  };

  const mergeBins = () => {
    if (checkedBins.length < 2) {
      showMessage('Select at least two bins to merge', 'info', true);
      return;
    }

    logUserAction('MERGE_BINS', {
      checkedBins
    });

    const sortedCheckedBins = [...checkedBins].sort((a, b) => a - b);
    const targetBinIndex = sortedCheckedBins[0];
    
    showConfirmDialogWithConfig(
      "Merge Selected Bins",
      `Are you sure you want to merge ${checkedBins.length} bins? All fabrics will be moved to ${bins[targetBinIndex].name}.`,
      () => {
        const fabricsToMerge = [];
        
        for (let i = sortedCheckedBins.length - 1; i >= 0; i--) {
          const binIndex = sortedCheckedBins[i];
          const binFabrics = bins[binIndex].fabrics;
          
          if (binIndex !== targetBinIndex) {
            fabricsToMerge.push(...binFabrics);
          }
        }
        
        const newBins = [...bins];
        
        // Add fabrics to the target bin
        newBins[targetBinIndex] = {
          ...newBins[targetBinIndex],
          fabrics: [...newBins[targetBinIndex].fabrics, ...fabricsToMerge],
          name: sortedCheckedBins.map(binIndex => `${bins[binIndex].name}`).join(', ')
        };

        // Remove other checked bins in reverse order
        for (let i = sortedCheckedBins.length - 1; i > 0; i--) {
          const binIndex = sortedCheckedBins[i];
          newBins.splice(binIndex, 1);
        }

        setBins(newBins);
        setBinsChanged(true);
        setCheckedBins([]);
        showMessage(`Merged ${checkedBins.length} bins successfully`, 'success');
      },
      () => {
        logUserAction('CONFIRM_DIALOG_ACTION', {
          dialog: 'merge_bins',
          action: 'cancel'
        });
      }
    );
  };

  const handleRenameBin = (binIndex, newName) => {
    logUserAction('RENAME_BIN', {
      binIndex,
      oldName: bins[binIndex].name,
      newName
    });

    setBins(prevBins => {
      const newBins = [...prevBins];
      newBins[binIndex] = {
        ...newBins[binIndex],
        name: newName
      };
      return newBins;
    });
    setBinsChanged(true);
  };

  return (
    <DndProvider backend={HTML5Backend}>
      {backendMessage && (
        <div 
          className={`message-toast ${messageType} ${messageVisible ? 'visible' : ''}`}
          onClick={dismissMessage}
          style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '10px 20px',
            borderRadius: '4px',
            backgroundColor: messageType === 'error' ? '#f8cfcb' : 
                           messageType === 'success' ? '#c2decb' : '#d4d7f9',
            color: '#222222',
            zIndex: 1000,
            cursor: 'pointer',
            transition: 'opacity 0.3s ease-in-out',
            opacity: messageVisible ? 1 : 0,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            boxShadow: '0 2px 5px rgba(0,0,0,0.2)',
          }}
        >
          {backendMessage}
          <span style={{ marginLeft: '10px', fontSize: '12px' }}>
            (dismiss)
          </span>
        </div>
      )}
      <Grid container spacing={1}>
        <Grid size={12} sx={{ backgroundColor: '#dbf1ff' }}>
          <Link to="/packing" onClick={(e) => {
            e.preventDefault();
            logUserAction('NAVIGATE_TO_PACKING', {
              binsChanged: binsChanged
            });
            if (binsChanged) {
              saveBins().then(() => {
                window.location.href = '/packing'; // Navigate after saving bins
              });
            } else {
              window.location.href = '/packing';
            }
          }}>
            <Button size="large" sx={{ textTransform: 'none' }}>Proceed to Packing</Button>
          </Link>
          {/* <Link to="/rectpack">
            <Button size="small">RectPack</Button>
          </Link> */}
        </Grid>
        <Grid size={12}></Grid>
        <Grid size={4}>
          <form onSubmit={(e) => e.preventDefault()}>
            <Stack spacing={1} direction="row" justifyContent="center" sx={{ gap: `10px`, marginLeft: `20px` }}>
              {/* <Tooltip title="Select the folder containing your fabric images">
                <span>
                  <Button variant="contained" component="label" size="small" sx={{ textTransform: 'none' }}>
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
                  <Typography id="fabric-folder" variant="button" gutterBottom>  {fabricFolder}  </Typography>
                </span>
              </Tooltip> */}
              <span className='flex-row center-align'>
                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel id="fabric-folder-select-label">Fabric Folder</InputLabel>
                  <Select
                    labelId="fabric-folder-select-label"
                    id="fabric-folder-select"
                    value={fabricFolder}
                    label="Fabric Folder"
                    onChange={handleFabricFolderChange}
                  >
                    <ListSubheader>User Study Sets</ListSubheader>
                    <MenuItem value="/studyset_resized/">Etsy Cotton</MenuItem>
                    <MenuItem value="/linen_pp_resized/">Etsy Linen</MenuItem>
                    <ListSubheader>Fabric Sets</ListSubheader>
                    <MenuItem value="/fabscrap_pp_resized/">FABSCRAP Bag</MenuItem>
                    <MenuItem value="/etsybag_pp_resized/">Etsy Bag</MenuItem>
                    <MenuItem value="/textured_resized/">Textured</MenuItem>
                    <MenuItem value="/adobe_seamless_resized/">Adobe+Tiling</MenuItem>
                    <ListSubheader>Generated Sets</ListSubheader>
                    <MenuItem value="/aspect_ratio/">Aspect Ratio</MenuItem>
                    <MenuItem value="/bimodal/">Bimodal</MenuItem>
                    <MenuItem value="/power_law/">Power Law</MenuItem>
                    <MenuItem value="/uniform/">Uniform</MenuItem>
                    <MenuItem value="/mixed_quilting/">Mixed Quilting</MenuItem>
                    <MenuItem value="/similar_sized/">Similar Sized</MenuItem>
                    <MenuItem value="/square_heavy/">Square Heavy</MenuItem>
                    <MenuItem value="/sequential/">Sequential</MenuItem>
                  </Select>
                </FormControl>
              </span>
              <Tooltip title="Load all fabric images from the selected folder">
                <span>
                  <Button
                    variant="contained"
                    size="small"
                    sx={{ textTransform: 'none' }}
                    onClick={loadFabrics}
                  >
                    Load Fabrics
                  </Button>
                </span>
              </Tooltip>
            </Stack>
          </form>
        </Grid>
        <Grid size={8}>
          <form onSubmit={(e) => e.preventDefault()}>
            <Stack direction="column" spacing={2}>
              <Stack direction="row" justifyContent="center" sx={{ gap: `10px` }}>
                <FormControl>
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
                <Tooltip title="Number of bins to group fabrics into">
                  <TextField
                    label="# Fabric Bins"
                    id="n-fabric-bins-field"
                    value={nFabricBins}
                    onChange={(e) => {
                      const newValue = e.target.value;
                      logUserAction('CHANGE_BIN_COUNT', {
                        fromBinCount: nFabricBins,
                        toBinCount: newValue
                      });
                      setNFabricBins(newValue);
                      localStorage.setItem('nFabricBins', JSON.stringify(newValue));
                    }}
                    size="small"
                  />
                </Tooltip>
                <FormControl>
                  <InputLabel id="grouping-criterion">Group Fabrics By</InputLabel>
                  <Select
                    value={groupCriterion}
                    label="Group Fabrics By"
                    onChange={(e) => {
                      const newValue = e.target.value;
                      logUserAction('CHANGE_GROUP_CRITERION', {
                        fromCriterion: groupCriterion,
                        toCriterion: newValue
                      });
                      setGroupCriterion(newValue);
                      localStorage.setItem('groupCriterion', JSON.stringify(newValue));
                    }}
                    size="small">
                    <MenuItem value="hue">
                      Color Tone
                      <Tooltip title="Group fabrics by their color hue">
                        <span>
                          <IconButton size="small" sx={{ padding: '2px' }}>
                            <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </MenuItem>
                    <MenuItem value="value">
                      Color Brightness
                      <Tooltip title="Group fabrics by how light or dark they are">
                        <span>
                          <IconButton size="small" sx={{ padding: '2px' }}>
                            <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </MenuItem>
                    <MenuItem value="lab">
                      Color Tone + Brightness
                      <Tooltip title="Group fabrics considering both color and brightness">
                        <span>
                          <IconButton size="small" sx={{ padding: '2px' }}>
                            <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </MenuItem>
                  </Select>
                </FormControl>
                <FormControl>
                  <InputLabel id="mode">Color Mode</InputLabel>
                  <Select
                    value={mode}
                    label="Color Mode"
                    onChange={(e) => {
                      const newValue = e.target.value;
                      logUserAction('CHANGE_COLOR_MODE', {
                        fromMode: mode,
                        toMode: newValue
                      });
                      setMode(newValue);
                      localStorage.setItem('mode', JSON.stringify(newValue));
                    }}
                    size="small">
                    <MenuItem value="dominant">
                      Dominant Color
                      <Tooltip title="Use the most common color in each fabric">
                        <span>
                          <IconButton size="small" sx={{ padding: '2px' }}>
                            <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </MenuItem>
                    <MenuItem value="average">
                      Average Color
                      <Tooltip title="Use the average color of each fabric">
                        <span>
                          <IconButton size="small" sx={{ padding: '2px' }}>
                            <HelpOutlineIcon sx={{ fontSize: '15px' }} />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </MenuItem>
                  </Select>
                </FormControl>
              </Stack>
              <Stack direction="row" justifyContent="center" sx={{ gap: `10px` }} alignItems="center">
                <Tooltip title="Automatically determine the optimal number of bins based on fabric colors">
                  <span>
                    <Button variant="contained" size="small" sx={{ textTransform: 'none' }} onClick={estimateBinSize}>Estimate # Bins</Button>
                  </span>
                </Tooltip>
                <Tooltip title={
                  fixedBins.length > 0 
                    ? `Group fabrics into bins based on current settings. ${fixedBins.length} bin${fixedBins.length > 1 ? 's are' : ' is'} locked and will not change.` 
                    : "Group fabrics into bins based on current settings"
                }>
                  <span>
                    <Button
                      variant="contained"
                      size="small"
                      sx={{ textTransform: 'none' }}
                      onClick={handleGroupFabrics}
                      disabled={isGroupingFabrics}
                    >
                      {isGroupingFabrics ? <CircularProgress size={24} /> : 'Group Fabrics'}
                    </Button>
                  </span>
                </Tooltip>
                <FormControl sx={{ display: 'flex', flexDirection: 'row', alignItems: 'center' }}>
                  <Checkbox
                    id="use-all-fabrics-checkbox"
                    checked={!useAllFabrics}
                    onChange={(e) => {
                      setUseAllFabrics(!e.target.checked);
                      logUserAction('TOGGLE_USE_ALL_FABRICS', {
                        useAllFabrics: !e.target.checked
                      });
                      localStorage.setItem('useAllFabrics', JSON.stringify(!e.target.checked));
                    }}
                    size="small"
                  />
                  <Tooltip title="When checked, groups available fabrics only. When unchecked, groups all fabrics from the folder (except for locked bins).">
                    <label htmlFor="use-all-fabrics-checkbox" style={{ fontSize: '0.875rem', cursor: 'pointer' }}>
                      Group Available Fabrics Only
                    </label>
                  </Tooltip>
                </FormControl>
              </Stack>
            </Stack>
          </form>
        </Grid>
        <Grid size={12}></Grid>
      </Grid>
      <div className="bin-assignment-container">
        <div className="available-fabrics-section">
          <h3>Available Fabrics</h3>
          <ImageList variant="masonry" cols={8} gap={5}>
            {availableFabrics.map((fabric) => (
              <DraggableBinFabric
                key={fabric.id}
                {...fabric}
                currentBin={null}
                onDelete={handleDelete}
              />
            ))}
          </ImageList>
          {removedFabrics.length > 0 && (
            <div className="removed-fabrics-section">
              <Stack direction="row" spacing={1} alignItems="center">
                <Button
                  size="small"
                  onClick={() => setShowRemovedFabrics(!showRemovedFabrics)}
                  startIcon={showRemovedFabrics ? <KeyboardArrowLeft /> : <KeyboardArrowRight />}
                  sx={{ textTransform: 'none' }}
                >
                  Removed Fabrics ({removedFabrics.length})
                </Button>
              </Stack>
              {showRemovedFabrics && (
                <div style={{ marginTop: '10px' }}>
                  <ImageList variant="masonry" cols={7} gap={5}>
                    {removedFabrics.map((fabric) => (
                      <ImageListItem key={fabric.id} style={{ position: 'relative' }}>
                        <img 
                          src={fabric.img ? fabric.img : fabric.image}
                          alt={`Fabric ${fabric.id}`}
                          loading="lazy"
                          style={{ objectFit: 'cover' }}
                        />
                        <Stack 
                          direction="row" 
                          spacing={0.5}
                          sx={{
                            position: 'absolute',
                            top: 2,
                            right: 2,
                            backgroundColor: 'rgba(255, 255, 255, 0.8)',
                            padding: '2px',
                            borderRadius: '2px',
                            zIndex: 1,
                            '& .MuiIconButton-root': {
                              padding: '2px',
                              width: '20px',
                              height: '20px',
                              '& .MuiSvgIcon-root': {
                                fontSize: '14px'
                              }
                            }
                          }}
                        >
                          <Tooltip title="Restore fabric to available fabrics">
                            <IconButton
                              size="small"
                              onClick={() => restoreFabric(fabric.id)}
                              sx={{ minWidth: '20px' }}
                            >
                              <KeyboardArrowLeft />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Permanently delete fabric">
                            <IconButton
                              size="small"
                              onClick={() => permanentlyDeleteFabric(fabric.id)}
                              color="error"
                              sx={{ minWidth: '20px' }}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Tooltip>
                        </Stack>
                      </ImageListItem>
                    ))}
                  </ImageList>
                </div>
              )}
            </div>
          )}
        </div> 
        <div className="bins-section">
          <Stack direction="row" spacing={2} marginBottom="10px">
            {/* <FormControl>
              <InputLabel id="bins-file-select-label">Bins File</InputLabel>
              <input
                type="file"
                onChange={(e) => {
                  logUserAction('SELECT_BINS_FILE', {
                    binsFile: e.target.files[0].name
                  });
                  const file = e.target.files[0];
                  setBinsFile(file.name);
                  localStorage.setItem('binsFile', JSON.stringify(file.name));
                }}
              />
            </FormControl> */}
            <Tooltip title="Load bins saved at the start of the packing process">
              <span>
                <Button variant="outlined" size="small" sx={{ textTransform: 'none' }} onClick={handleLoadBins}>Load Bins</Button>
              </span>
            </Tooltip>
            <Tooltip title="Load current bins during the packing process">
              <span>
                <Button variant="outlined" size="small" sx={{ textTransform: 'none' }} onClick={handleLoadBinOptions}>Load Current Bins</Button>
              </span>
            </Tooltip>
            <Tooltip title="Add a new empty bin">
              <span>
                <Button variant="outlined" size="small" sx={{ textTransform: 'none' }} onClick={addBin}>Add Bin</Button>
              </span>
            </Tooltip>
            <Tooltip title="Clear all bins and fabrics">
              <span>
                <Button variant="outlined" size="small" sx={{ textTransform: 'none' }} onClick={handleClearBins}>Clear All</Button>
              </span>
            </Tooltip>
            <Tooltip title={allBinsCollapsed ? "Expand all bins" : "Collapse all bins"}>
              <span>
                <Button 
                  variant="outlined" 
                  size="small" 
                  sx={{ textTransform: 'none' }} 
                  onClick={toggleAllBins}
                  startIcon={allBinsCollapsed ? <UnfoldMoreIcon /> : <UnfoldLessIcon />}
                >
                  {allBinsCollapsed ? "Expand All" : "Collapse All"}
                </Button>
              </span>
            </Tooltip>
            {checkedBins.length >= 2 && (
              <Tooltip title={`Merge ${checkedBins.length} checked bins into one bin`}>
                <span>
                  <Button 
                    variant="contained" 
                    color="primary"
                    size="small" 
                    sx={{ textTransform: 'none' }} 
                    onClick={mergeBins}
                  >
                    Merge Checked Bins
                  </Button>
                </span>
              </Tooltip>
            )}
          </Stack>
          {bins.length > 0 && (
            <>
              {bins.map((bin, index) => {
                // Check if bin is fixed
                const isFixed = bin.fixed || false;
                // Check if bin is checked
                const isChecked = checkedBins.includes(index);
                
                return (
                  <DraggableBin
                    key={index}
                    id={`${index+1}`}
                    index={index}
                    name={bin.name}
                    fabrics={bin.fabrics}
                    onDrop={(itemId, targetBinId, sourceBinId) => handleDrop(itemId, targetBinId, sourceBinId)}
                    onDelete={(fabricId, currentBin) => handleDelete(fabricId, currentBin)}
                    onRemove={() => removeBin(index)}
                    moveBin={moveBin}
                    isFixed={isFixed}
                    onToggleFix={() => toggleFixBin(index)}
                    isChecked={isChecked}
                    onToggleCheck={handleBinCheck}
                    onRename={handleRenameBin}
                    allBinsCollapsed={allBinsCollapsed}
                  />
                );
              })}
            </>
          )}
        </div>
      </div>
      <Dialog
        open={showConfirmDialog}
        onClose={() => setShowConfirmDialog(false)}
        aria-labelledby="alert-dialog-title"
        aria-describedby="alert-dialog-description"
      >
        <DialogTitle id="alert-dialog-title">
          {confirmDialogConfig.title}
        </DialogTitle>
        <DialogContent>
          <DialogContentText id="alert-dialog-description">
            {confirmDialogConfig.message}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            confirmDialogConfig.onConfirm();
            setShowConfirmDialog(false);
          }} 
            color="primary"
            sx={{ textTransform: 'none' }}
          >
            Yes, continue
          </Button>
          <Button onClick={() => {
            confirmDialogConfig.onCancel();
            setShowConfirmDialog(false);
          }} 
            color="primary" 
            autoFocus 
            sx={{ textTransform: 'none' }}
          >
            No, don't continue
          </Button>
        </DialogActions>
      </Dialog>
    </DndProvider>
  );
};

export default BinningPage;

