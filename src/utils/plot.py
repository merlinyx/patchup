from PIL import Image, ImageDraw
from io import BytesIO
import base64
import cv2
import matplotlib.pyplot as plt
import math

def pil_image_to_base64(img):
    if img is None:
        return None
    buffered = BytesIO()
    img.save(buffered, format="PNG")  # Save the image to buffer in PNG format (or another format)
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')  # Encode the image as base64
    return img_str

def base64_to_pil_image(img_str):
    # Decode the base64 string
    image_data = base64.b64decode(img_str)
    # Convert the binary data into an image
    image = Image.open(BytesIO(image_data))
    return image

def plot_images_in_grid(images, titles=None, grid_width=None, should_cvt_color=True):
    """
    Plots an arbitrarily long list of images in a grid.
    
    Parameters:
    - images: List of images as numpy arrays.
    - titles: Optional list of titles for each image.
    - grid_width: Optional width of the grid. If None, a square layout is attempted.
    - should_cvt_color: If True, converts BGR images to RGB.
    """

    num_images = len(images)
    if num_images == 0: return
    if grid_width is None:
        grid_width = math.ceil(math.sqrt(num_images))
    grid_height = math.ceil(num_images / grid_width)
    
    _, axs = plt.subplots(grid_height, grid_width, figsize=(grid_width * 4, grid_height * 4))
    if len(images) == 1:
        axs = [axs]
    else:
        axs = axs.flatten()
    
    for i in range(grid_width * grid_height):
        axs[i].axis('off')  # Turn off axis for empty subplots

    import matplotlib as mpl
    mpl.rcParams['axes.facecolor'] = (1,1,1,0)
    mpl.rcParams['figure.facecolor'] = (1,1,1,0)

    for i, image in enumerate(images):
        ax = axs[i]
        if should_cvt_color:
            ax.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        else:
            ax.imshow(image)
        
        if titles and i < len(titles):
            ax.set_title(titles[i])
    
    plt.tight_layout()
    plt.show()

def draw_seam_lines(img, img_before=None, seam_width=1, seam_allowance=25):
    width, height = img.size
    draw = ImageDraw.Draw(img)
    sa_color = (100, 100, 100)
    draw.line([0, seam_allowance, width, seam_allowance], fill=sa_color, width=seam_width)
    draw.line([seam_allowance, 0, seam_allowance, height], fill=sa_color, width=seam_width)
    draw.line([0, height - seam_allowance, width, height - seam_allowance], fill=sa_color, width=seam_width)
    draw.line([width - seam_allowance, 0, width - seam_allowance, height], fill=sa_color, width=seam_width)

    if img_before:
        draw = ImageDraw.Draw(img_before)
        w_offset = img_before.size[0] - width
        h_offset = img_before.size[1] - height
        draw.line([-w_offset, seam_allowance, width-w_offset, seam_allowance], fill=sa_color, width=seam_width)
        draw.line([seam_allowance, -h_offset, seam_allowance, height-h_offset], fill=sa_color, width=seam_width)
        draw.line([-w_offset, height-h_offset - seam_allowance, width-w_offset, height-h_offset - seam_allowance], fill=sa_color, width=seam_width)
        draw.line([width-w_offset - seam_allowance, -h_offset, width-w_offset - seam_allowance, height-h_offset], fill=sa_color, width=seam_width)
        return img, img_before
    return img

def draw_border(img, border_width=1, border_color=(0, 0, 0)):
    width, height = img.size
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, width, border_width], fill=border_color)
    draw.rectangle([0, 0, border_width, height], fill=border_color)
    draw.rectangle([0, height - border_width, width, height], fill=border_color)
    draw.rectangle([width - border_width, 0, width, height], fill=border_color)
    return img

def trans_paste(bg_img,fg_img,box=(0,0)):
    fg_img_trans = Image.new("RGBA",bg_img.size)
    fg_img_trans.paste(fg_img,box,mask=fg_img)
    new_img = Image.alpha_composite(bg_img,fg_img_trans)
    return new_img

def rail_fence_compose_incomplete(block12, partial_block34, sa=0, suppress_output=False, alpha=0):
    packing_width = block12.size[0]
    top_height = block12.size[1] - sa
    bottom_height = partial_block34.size[1] - sa
    packing_height = top_height + bottom_height
    final_image = Image.new('RGBA', (packing_width, packing_height), (255, 255, 255, alpha))
    partial_block34 = partial_block34.crop((0, sa, partial_block34.size[0], partial_block34.size[1]))
    final_image = trans_paste(final_image, partial_block34, box=(packing_width - partial_block34.size[0], packing_height - partial_block34.size[1], packing_width, packing_height))
    block12 = block12.crop((0, 0, block12.size[0], top_height))
    final_image = trans_paste(final_image, block12, box=(0, 0, block12.size[0], block12.size[1]))
    # Display the result
    if not suppress_output:
        plt.figure(figsize=(4, 4))
        plt.imshow(final_image)
        plt.axis('off')
        plt.axis('equal')
        plt.show()
    return final_image

def rail_fence_compose(block12, block34, sa=0, suppress_output=False, alpha=0):
    assert block12.size[0] == block34.size[0], "The two sets of blocks must have the same width"
    packing_width = block12.size[0]
    top_height = block12.size[1] - sa
    bottom_height = block34.size[1] - sa
    packing_height = top_height + bottom_height
    final_image = Image.new('RGBA', (packing_width, packing_height), (255, 255, 255, alpha))
    block34 = block34.crop((0, sa, block34.size[0], block34.size[1]))
    final_image = trans_paste(final_image, block34, box=(0, packing_height - block34.size[1], block34.size[0], packing_height))
    block12 = block12.crop((0, 0, block12.size[0], top_height))
    final_image = trans_paste(final_image, block12, box=(0, 0, block12.size[0], block12.size[1]))
    # Display the result
    if not suppress_output:
        plt.figure(figsize=(4, 4))
        plt.imshow(final_image)
        plt.axis('off')
        plt.axis('equal')
        plt.show()
    return final_image

def composite_images(list_of_images, image_shapes, suppress_output=False, alpha=0):
    boxes = [image_shape.box() for image_shape in image_shapes] # this considers rotated images
    packing_width = max([x + w for x, y, w, h in boxes])
    packing_height = max([y + h for x, y, w, h in boxes])
    final_image = Image.new('RGBA', (int(packing_width), int(packing_height)), (255, 255, 255, alpha))
    if not suppress_output: print(f"final image size: {final_image.size}")
    for i, image_shape in enumerate(image_shapes):
        img = list_of_images[i]
        x, y, w, h = image_shape.box()
        x = int(x)
        y = int(y)
        w = int(w)
        h = int(h)
        # print(f"image {i}", w, h, img.size)
        image_to_paste = img
        if len(image_shape.rotations) > 0:
            angle_to_rotate = sum(image_shape.rotations)
            image_to_paste = img.rotate(angle_to_rotate, expand=True)
            # print(f"image {i} rotated by {angle_to_rotate} degrees", image_to_paste.size)
        final_image = trans_paste(final_image, image_to_paste, box=(x, y, x+w, y+h))
    # Display the result
    if not suppress_output:
        plt.figure(figsize=(4, 4))
        plt.imshow(final_image)
        plt.axis('off')
        plt.axis('equal')
        plt.show()
    return final_image
