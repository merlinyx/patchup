from PIL import Image, ImageDraw
import json
import seaborn as sns
import random
import os
import shutil
random.seed(42)

def generate_random_color():
    """Generate a random RGBA color."""
    return tuple(random.randint(0, 255) for _ in range(3)) + (255,)

def get_random_texture(texture_folder):
    texture_dir = os.path.abspath(texture_folder)
    textures = [f for f in os.listdir(texture_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
    return Image.open(os.path.join(texture_dir, random.choice(textures)))

def generate_test_fabric(min_size=50, max_size=300, square_probability=0.5):
    """Generate a rectangle or square with random dimensions and a random color."""
    if random.random() < square_probability:
        size = random.randint(min_size, max_size)
        width, height = size, size
    else:
        width = random.randint(min_size, max_size)
        height = random.randint(min_size, max_size)
    
    img = Image.new("RGBA", (width, height), generate_random_color())
    return img

def generate_test_fabric_with_texture(texture, width, height):
    texture_width, texture_height = texture.size
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0)) 

    if width <= texture_width and height <= texture_height:
        x = random.randint(0, texture_width - width)
        y = random.randint(0, texture_height - height)
        img.paste(texture.crop((x, y, x + width, y + height)), (0, 0))
    else:
        for x in range(0, width, texture_width):
            for y in range(0, height, texture_height):
                img.paste(texture, (x, y))

        if width > texture_width:
            if width % texture_width != 0:
                img.paste(texture.crop((0, 0, width % texture_width, texture_height)), (width - (width % texture_width), 0))

        if height > texture_height:
            if height % texture_height != 0:
                img.paste(texture.crop((0, 0, texture_width, height % texture_height)), (0, height - (height % texture_height)))

    return img

def generate_test_fabric_with_all_textures(texture_folder, min_size=100, max_size=700, square_probability=0.5):
    """ Generate a set of randomly texture rectangles and squares."""
    test_set = []
    for texture_path in os.listdir(texture_folder):
        texture = Image.open(os.path.join(texture_folder, texture_path))
        if random.random() < square_probability:
            size = random.randint(min_size, max_size)
            width, height = size, size
        else:
            width = random.randint(min_size, max_size)
            height = random.randint(min_size, max_size)
        img = generate_test_fabric_with_texture(texture, width, height)
        test_set.append(img)
    return test_set

def generate_test_fabric_with_random_texture(texture_folder, min_size=100, max_size=700, square_probability=0.5):
    """Generate a rectangle or square with random dimensions and a random texture."""
    if random.random() < square_probability:
        size = random.randint(min_size, max_size)
        width, height = size, size
    else:
        width = random.randint(min_size, max_size)
        height = random.randint(min_size, max_size)
    
    texture = get_random_texture(texture_folder)
    texture_path = os.path.join(texture_folder, os.path.basename(texture.filename))  
    img = generate_test_fabric_with_texture(texture, width, height)

    return texture_path, img

def generate_test_set(num_images, min_size=50, max_size=300, square_probability=0.5):
    """
    Generate a set of randomly colored rectangles and squares.
    
    Parameters:
    - num_images: Number of images in the test set.
    - min_size: Minimum dimension size for generated shapes.
    - max_size: Maximum dimension size for generated shapes.
    - square_probability: Probability of generating a square (between 0 and 1).
    
    Returns:
    - List of PIL Image objects.
    """
    test_set = []
    for _ in range(num_images):
        img = generate_test_fabric(min_size, max_size, square_probability)
        test_set.append(img)
    return test_set

def generate_test_set_with_random_texture(num_images, texture_folder, min_size=100, max_size=700, square_probability=0.5):
    """ Generate a set of randomly texture rectangles and squares."""
    test_set = []
    for _ in range(num_images):
        _, img = generate_test_fabric_with_random_texture(texture_folder, min_size, max_size, square_probability)
        test_set.append(img)
    return test_set

def generate_palette_colors(num_colors):
    """
    Generate a palette of distinct colors.
    You can modify this to use any specific color palette or algorithm.
    """
    # Generate base colors from different palettes and combine them
    palette = []

    # Get colors from different seaborn palettes
    palette.extend(sns.color_palette("husl", n_colors=num_colors//4))
    palette.extend(sns.color_palette("Set2", n_colors=num_colors//4))
    palette.extend(sns.color_palette("Paired", n_colors=num_colors//4))
    palette.extend(sns.color_palette("hls", n_colors=num_colors - len(palette)))

    # Convert to RGBA format (0-255 range)
    palette = [(int(r * 255), int(g * 255), int(b * 255), 255) for r, g, b in palette]
    return palette

def generate_bordered_test_fabric(color, width, height, border_color=(0, 0, 0), border_width=1,
                                  seam_allowance=25, should_draw_seam=True):
    """Generate a rectangle or square with random dimensions, a color from the palette, a black border and grey seam lines."""

    # Create an image with a black border
    img = Image.new("RGBA", (width, height), border_color)
    draw = ImageDraw.Draw(img)
    
    # Draw the colored rectangle/square inside the black border
    draw.rectangle(
        [border_width, border_width, width - 1 - border_width, height - 1 - border_width],
        # fill=(color[0], color[1], color[2], 240) # <- this enables transparency in packing results
        fill=color
    )

    # Draw the seam allowance lines
    if should_draw_seam:
        sa_color = (100, 100, 100)
        draw.line([0, seam_allowance, width, seam_allowance], fill=sa_color, width=border_width)
        draw.line([seam_allowance, 0, seam_allowance, height], fill=sa_color, width=border_width)
        draw.line([0, height - seam_allowance, width, height - seam_allowance], fill=sa_color, width=border_width)
        draw.line([width - seam_allowance, 0, width - seam_allowance, height], fill=sa_color, width=border_width)

    return img

def generate_bordered_test_set(num_images, min_size=50, max_size=300, square_probability=0.5,
                               border_color=(0, 0, 0), border_width=1, seam_allowance=25,
                               should_draw_seam=True, save_json=False, filename=None):
    """
    Generate a set of rectangles and squares with a border using colors from a palette.
    
    Parameters:
    - num_images: Number of images in the test set.
    - min_size: Minimum dimension size for generated shapes.
    - max_size: Maximum dimension size for generated shapes.
    - square_probability: Probability of generating a square (between 0 and 1).
    - border_color: Color of the border.
    - border_width: Width of the border (default is 1 pixel).
    - seam_allowance: Width of the seam allowance lines.
    - save_json: If True, saves the color information in a JSON file.
    - filename: Name of the JSON file to save.
    
    Returns:
    - List of PIL Image objects.
    """
    color_palette = generate_palette_colors(num_images)
    test_set = []
    test_data_json = {
        'border_color': border_color,
        'border_width': border_width,
        'seam_allowance': seam_allowance,
        'test_fabrics': []
    }
    for _ in range(num_images):
        color = random.choice(color_palette)
        if random.random() < square_probability:
            size = random.randint(min_size, max_size)
            width, height = size, size
        else:
            width = random.randint(min_size, max_size)
            height = random.randint(min_size, max_size)
        img = generate_bordered_test_fabric(color, width, height, border_color, border_width,
                                            seam_allowance, should_draw_seam)
        test_set.append(img)
        if save_json:
            test_data_json['test_fabrics'].append({'color': color, 'width': width, 'height': height})
    if save_json:
        assert filename is not None, 'Please provide a filename to save the JSON data.'
        with open(f'fabric_data/{filename}.json', 'w') as f:
            json.dump(test_data_json, f)
    return test_set

def generate_bordered_test_set_with_texture(num_images, texture_folder, min_size=100, max_size=700, 
                                            square_probability=0.5, border_color=(0, 0, 0), 
                                            border_width=1, seam_allowance=25, save_json=False, 
                                            json_filename=None, output_dir='output_fabrics'):
    """ Generate a set of rectangles and squares with a border using textures from a folder. """
    test_set = []
    test_data_json = {
        'border_color': border_color,
        'border_width': border_width,
        'seam_allowance': seam_allowance,
        'test_fabrics': []
    }
    os.makedirs(os.path.join('fabric_data', output_dir), exist_ok=True)
    for i in range(num_images):
        texture_path, img = generate_test_fabric_with_random_texture(texture_folder, min_size, max_size, square_probability)
        test_set.append(img)
        output_path = os.path.join(output_dir, f'fabric_{i+1}.png')
        img.save(output_path)
        if save_json:
            test_data_json['test_fabrics'].append(
                {'texture': texture_path, 'width': img.width, 'height': img.height, 'path': output_path})
    if save_json:
        assert json_filename is not None, 'Please provide a filename to save the JSON data.'
        with open(os.path.join('fabric_data', output_dir, f'{json_filename}.json'), 'w') as f:
            json.dump(test_data_json, f)
    return test_set

def load_bordered_test_set(test_data_path, should_draw_seam=True, should_save_img=False):
    """Load the test set from saved json file."""
    with open(test_data_path, 'r') as f:
        test_data_json = json.load(f)
    test_set = []
    border_color = tuple(test_data_json['border_color'])
    test_data_folder = os.path.dirname(test_data_path)
    for i, fabric in enumerate(test_data_json['test_fabrics']):
        img = generate_bordered_test_fabric(
            tuple(fabric['color']), fabric['width'], fabric['height'],
            border_color, test_data_json['border_width'],
            test_data_json['seam_allowance'], should_draw_seam)
        test_set.append(img)
        if should_save_img and not os.path.exists(os.path.join(test_data_folder, f'{i}.png')):
            img.save(os.path.join(test_data_folder, f'{i}.png'))
    return test_set

def load_bordered_test_set_with_texture(test_data_path):
    """Load the test set with texture from saved json file."""
    with open(test_data_path, 'r') as f:
        test_data_json = json.load(f)
    test_set = []
    for fabric in test_data_json['test_fabrics']:
        img = Image.open(fabric['path']).convert("RGBA")
        test_set.append(img)
    return test_set

# TEST
def main():
    # TEXTURE_DIR = 'fabric_data/inner_images'
    TEXTURE_DIR = 'fabric_data/textures'

    generate_bordered_test_set_with_texture(
        num_images=40, 
        texture_folder=TEXTURE_DIR, 
        min_size=200, 
        max_size=600, 
        square_probability=0.5,
        border_color=(0, 0, 0), 
        border_width=1, 
        seam_allowance=25,
        save_json=True,
        json_filename='test_fabrics_with_textures2',
        output_dir='output_fabrics2')

def generate_textured_image_set():
    images1 = generate_test_fabric_with_all_textures(
        texture_folder='fabric_data/adobe_stock_textures',
        min_size=500,
        max_size=2000,
        square_probability=0.5
    )
    images3 = generate_test_fabric_with_all_textures(
        texture_folder='fabric_data/adobe_stock_textures',
        min_size=600,
        max_size=1500,
        square_probability=0.2
    )
    images2 = generate_test_fabric_with_all_textures(
        texture_folder='fabric_data/tiling',
        min_size=300,
        max_size=1800,
        square_probability=0.5
    )
    return images1 + images2 + images3

if __name__ == '__main__':
    # main()
    images = generate_textured_image_set()
    if not os.path.exists('fabric_data/textured_images'):
        os.makedirs('fabric_data/textured_images')
    else:
        shutil.rmtree('fabric_data/textured_images')
        os.makedirs('fabric_data/textured_images')
    for i, img in enumerate(images):
        img.save(f'fabric_data/textured_images/{i}.png')
