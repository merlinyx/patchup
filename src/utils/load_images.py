from PIL import Image
import numpy as np
import os
import json

from scripts.utils.test_set import generate_bordered_test_fabric
from scripts.utils.plot import base64_to_pil_image

def open_image(image_path):
    if image_path is None:
        return None
    try:
        # Open the image and immediately copy it to ensure the file handle is closed
        with Image.open(image_path) as img:
            # Create a copy to ensure we have our own memory
            image_copy = img.copy()
            
            # Convert to RGBA based on the original mode
            if image_copy.mode == 'RGBA':
                return image_copy
            elif image_copy.mode == 'RGB':
                return image_copy.convert('RGBA')
            elif image_copy.mode == 'P':
                return image_copy.convert('RGBA')
            elif image_copy.mode == 'L':
                return image_copy.convert('RGB').convert('RGBA')
            else:
                raise ValueError(f"Unsupported image mode: {image_copy.mode}")
    except Exception as e:
        print(f"Error opening image {image_path}: {str(e)}")
        return None

def is_image_file(file):
    return file.endswith('.png') or file.endswith('.jpg') or file.endswith('.jpeg')

def load_fabrics_for_binning(public_folder, image_folder, available_fabrics=[],
                             should_include_image=False, images_only=False, exclude_ids=[]):
    """
    Load fabric images from a folder and return in the following format:
        {id: i,
        image: imagePath,
        img: PIL.Image object (if should_include_image is True),
        width: dimensions.width,
        height: dimensions.height,
        size: [dimensions.width, dimensions.height]}
    if images_only is True, then return a list of images only
    
    Parameters:
        public_folder: the public folder path
        image_folder: the image folder path relative to public_folder
        available_fabrics: list of available fabrics to load, if empty, load all fabrics from folder
        should_include_image: if True, include the PIL.Image object in the output
        images_only: if True, return a list of PIL.Image objects only
        exclude_ids: list of fabric IDs to exclude from loading
    """
    files = os.listdir(os.path.join(public_folder, image_folder))
    image_files = [f for f in files if is_image_file(f)]
    json_files = [f for f in files if f.endswith('.json')]
    fabrics = []
    if len(available_fabrics) > 0:
        for fabric in available_fabrics:
            # Skip fabrics with IDs in exclude_ids
            if fabric['id'] in exclude_ids:
                continue
                
            if images_only:
                fabrics.append(open_image(os.path.join(public_folder, fabric['image'])))
                continue
            if 'img' not in fabric:
                fabric['img'] = open_image(os.path.join(public_folder, fabric['image']))
            else:
                if isinstance(fabric['img'], str):
                    fabric['img'] = base64_to_pil_image(fabric['img'])
            if 'size' not in fabric:
                fabric['size'] = fabric['img'].size
            if 'width' not in fabric:
                fabric['width'] = fabric['size'][0]
            if 'height' not in fabric:
                fabric['height'] = fabric['size'][1]
            if should_include_image:
                if 'img' not in fabric:
                    fabric['img'] = open_image(os.path.join(public_folder, fabric['image']))
                fabrics.append(fabric)
            else:
                fabrics.append(
                    {"id": fabric['id'], "image": fabric['image'],
                     "width": fabric['width'], "height": fabric['height'],
                     "size": fabric['size']})
    else:
        if len(json_files) == 0: # this is a folder of images
            for id, file in enumerate(image_files):
                # Skip fabrics with IDs in exclude_ids
                if id in exclude_ids:
                    continue
                    
                file_path = os.path.join(public_folder, image_folder, file)
                try:
                    img = open_image(file_path)
                    if images_only:
                        fabrics.append(img)
                        continue
                    fabrics.append(
                        {"id": id, "image": os.path.join(image_folder, file),
                        "width": img.size[0], "height": img.size[1],
                        "size": img.size})
                    if should_include_image:
                        fabrics[-1]['img'] = img
                except Exception as e:
                    print(f"Error loading image {file}: {e}")
        else:
            json_file = None
            if len(json_files) > 1:
                for file in json_files:
                    with open(os.path.join(public_folder, image_folder, file), 'r') as f:
                        json_data = json.load(f)
                    if 'border_color' in json_data: # this is the json file we want
                        json_file = file
                        break
            else: # just one json file
                json_file = json_files[0]
            with open(os.path.join(public_folder, image_folder, json_file), 'r') as f:
                json_data = json.load(f)
            border_color = tuple(json_data['border_color'])
            for i, fabric in enumerate(json_data['test_fabrics']):
                # Skip fabrics with IDs in exclude_ids
                if i in exclude_ids:
                    continue
                    
                if 'path' in fabric:
                    # this is a test set generated from texture images
                    if images_only:
                        fabrics.append(open_image(os.path.join(public_folder, fabric['path'])))
                        continue
                    fabrics.append(
                        {"id": i, "image": fabric['path'],
                        "width": fabric['width'], "height": fabric['height'],
                        "size": [fabric['width'], fabric['height']]})
                    if should_include_image:
                        fabrics[-1]['img'] = open_image(os.path.join(public_folder, fabric['path']))
                else:
                    # this is a test set generated from random colors from a color palette
                    img = generate_bordered_test_fabric(
                        tuple(fabric['color']), fabric['width'], fabric['height'],
                        border_color, json_data['border_width'],
                        json_data['seam_allowance'], should_draw_seam=False)
                    if images_only:
                        fabrics.append(img)
                        continue
                    if not os.path.exists(os.path.join(public_folder, image_folder, f'{i}.png')):
                        img.save(os.path.join(public_folder, image_folder, f'{i}.png'))
                    fabrics.append(
                        {"id": i, "image": os.path.join(image_folder, f'{i}.png'),
                        "width": fabric['width'], "height": fabric['height'],
                        "size": [fabric['width'], fabric['height']]})
                    if should_include_image:
                        fabrics[-1]['img'] = img
    return fabrics

def load_from_folder(image_folder, dpi):
    list_of_images = []
    image_files = os.listdir(image_folder)
    image_to_segmented = {}
    image_to_calib = {}
    for file in image_files:
        filename = file.split('.')[0].split('_')[0]
        if file.endswith('.png'):
            if filename not in image_to_segmented:
                image_to_segmented[filename] = []
            image_to_segmented[filename].append(file)
            if 'calib' in file:
                image_to_calib[filename] = file
    for scrap_image, segmented_images in image_to_segmented.items():
        calib_image = Image.open(os.path.join(image_folder, image_to_calib[scrap_image]))
        calib_size = max(calib_image.size)
        for segmented_image in segmented_images:
            if segmented_image == image_to_calib[scrap_image]:
                continue
            segmented_img = Image.open(os.path.join(image_folder, segmented_image))
            new_size = int(segmented_img.size[0] / calib_size * dpi), int(segmented_img.size[1] / calib_size * dpi)
            resized_img = segmented_img.resize(new_size)
            list_of_images.append(resized_img)
    return list_of_images

def load_images_from_folder(image_folder):
    """ Load images only. """
    list_of_images = []
    image_files = os.listdir(image_folder)
    for file in image_files:
        file_path = os.path.join(image_folder, file)
        try:
            img = Image.open(file_path)
            list_of_images.append(img)
        except Exception as e:
            print(f"Error loading image {file}: {e}")
    return list_of_images

def find_inner_bbox(image):
    w, h = image.size
    image = np.array(image)

    init_ratio = 0.05
    inc_ratio = 0.01
    while inc_ratio <= 1 - init_ratio:
        xi = int(w * (1 - init_ratio - inc_ratio) / 2)
        xj = w - xi
        yi = int(h * (1 - init_ratio - inc_ratio) / 2)
        yj = h - yi
        curr_block = image[yi:yj, xi:xj, :]
        num_zeros = ((curr_block[:, :, 0] == 0) & (curr_block[:, :, 1] == 0) & (curr_block[:, :, 2] == 0) & (curr_block[:, :, 3] == 0)).sum()
        if num_zeros < 0.01 * w * h:
            # expand the bounding box
            inc_ratio += 0.01
        else:
            # shrink the bounding box
            print(num_zeros, w * h)
            break
    xi = int(w * (1 - init_ratio - inc_ratio) / 2)
    xj = w - xi
    yi = int(h * (1 - init_ratio - inc_ratio) / 2)
    yj = h - yi
    return Image.fromarray(image[yi:yj, xi:xj]).convert('RGBA')
