import React, { useEffect, useState } from "react";
import axios from "axios";

import Box from '@mui/material/Box';
import ImageList from "@mui/material/ImageList";
import ImageListItem from "@mui/material/ImageListItem";
import ImageListItemBar from "@mui/material/ImageListItemBar";
import { Typography } from "@mui/material";

const Assignable = ({
    imageSource,
    isFabric,
    images,
    setImages,
  }: {
    imageSource: string;
    isFabric: boolean;
    images: string[];
    setImages: (images: string[]) => void;
  }) => {
  
    const [imageLabels, setImageLabels] = useState<string[]>([]);

    useEffect(() => {
      // Function to fetch segmented images
      const fetchSegmentedImages = async () => {
        try {
          const response = await axios.post('http://127.0.0.1:5000/api/get_segmented_images', { imageName: imageSource });
          setImages(response.data['segmented_images']);
          setImageLabels(response.data['segmented_image_labels']);
        } catch (error) {
          console.error('Error fetching segmented images:', error);
        }
      };
      if (images.length === 0) {
        fetchSegmentedImages();
      }
    }, [imageSource, imageLabels, setImageLabels, images, setImages]);

    return (
      <div>
        <Box sx={{ width: 500, height: 300, overflowY: 'scroll',
          boxShadow: 2, borderRadius: 5, p: 2, }}>
        <Typography variant="h6">
          {isFabric ? 'Fabric Scraps' : 'Pattern Pieces'}
        </Typography>
        <ImageList variant="masonry" cols={3} gap={8}>
          {images.map((image, index) => (
            <ImageListItem key={index}>
              <img
                srcSet={`${image}?h=164&fit=crop&auto=format&dpr=2 2x`}
                src={`${image}?h=164&fit=crop&auto=format`}
                alt={isFabric ? `Fabric Scrap ${index}` : `Pattern Piece ${index}`}
                loading="lazy"
                style={{ height: '164px', width: 'auto', objectFit: 'cover' }}
              />
              <ImageListItemBar position="below" title={imageLabels[index]} />
            </ImageListItem>
          ))}
        </ImageList>
        </Box>
      </div>
    );
  };

export default Assignable;
