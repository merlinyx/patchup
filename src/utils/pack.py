from src.utils.gif import *
from src.utils.image_shape import *
from src.utils.load_images import *
from src.utils.plot import *
import sys

#####################################################################
# Core Dimension and Target Length Calculation Functions
#####################################################################

def target_length(curr_image_shape, iter, strategy):
    target_L = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0 or iter % 4 == 1:
            target_L = curr_image_shape.w
        else:
            target_L = curr_image_shape.h
    elif strategy == 'log-cabin':
        if iter % 4 == 0 or iter % 4 == 2:
            target_L = curr_image_shape.h
        else:
            target_L = curr_image_shape.w
    elif strategy == 'rail-fence':
        if (iter // 3) % 2 == 0:
            target_L = curr_image_shape.w
        else:
            target_L = curr_image_shape.h
    else:
        raise ValueError("Invalid strategy")
    return target_L

def high_res_packed_fabric_size(curr_packed_fabric_high_res_size, shortest_side_high_res, iter, strategy, sa=0):
    packed_fabric_size_high_res = None
    w, h = curr_packed_fabric_high_res_size.w, curr_packed_fabric_high_res_size.h
    shortest_side_high_res += 2 * sa
    if strategy == 'log-cabin':
        if iter % 4 == 0 or iter % 4 == 2: # left or right
            packed_fabric_size_high_res = (w + shortest_side_high_res, h)
        else: # iter % 4 == 2 or 3 # top or bottom
            packed_fabric_size_high_res = (w, h + shortest_side_high_res)
    elif strategy == 'courthouse-steps':
        if iter % 4 == 0 or iter % 4 == 1: # top or bottom
            packed_fabric_size_high_res = (w, h + shortest_side_high_res)
        else: # iter % 4 == 2 or 3 # left or right
            packed_fabric_size_high_res = (w + shortest_side_high_res, h)
    elif strategy == 'rail-fence':
        if (iter // 3) % 2 == 0: # top or bottom
            packed_fabric_size_high_res = (w, h + shortest_side_high_res)
        else: # (iter // 3) % 2 == 1 # left or right
            packed_fabric_size_high_res = (w + shortest_side_high_res, h)
    else:
        raise ValueError("Invalid strategy")
    return packed_fabric_size_high_res

def update_rail_fence_packed_fabric_high_res_size(config):
    assert config.strategy == 'rail-fence'
    if config.block12_high_res_size is None or config.block34_high_res_size is None:
        return
    config.packed_fabric_high_res_size = (min(config.block12_high_res_size[0], config.block34_high_res_size[0]), config.block12_high_res_size[1] + config.block34_high_res_size[1])

#####################################################################
# Image Shape and Fabric Shape Management Functions
#####################################################################

def _create_image_shape(size_tuple, sa=0):
    """Helper function to create ImageShape objects with consistent initialization"""
    if not size_tuple:
        return None
    if isinstance(size_tuple, tuple):
        return ImageShape(0, 0, size_tuple[0], size_tuple[1])
    else:
        return ImageShape(0, 0, size_tuple, 2 * sa)

def get_curr_image_shape(packed_fabric_size, iter, config, is_high_res=False):
    if not packed_fabric_size:
        if config.strategy != 'rail-fence':
            raise ValueError(f"packed_fabric must be provided for strategy {config.strategy}")
        if iter == 0:
            if is_high_res:
                return _create_image_shape(config.target_L_high_res['top'], 25)
            else:
                return _create_image_shape(config.target_L['top'], config.sa)
        elif iter == 6:
            if is_high_res:
                return _create_image_shape(config.target_L_high_res['bottom'], 25)
            else:
                return _create_image_shape(config.target_L['bottom'], config.sa)
        raise ValueError(f"this must be the 1st or 7th iteration instead of {iter + 1}")
    return _create_image_shape(packed_fabric_size)

def _get_packed_fabric_rail_fence(packed_fabric, iter, config, is_high_res=False):
    """Helper function to determine the fabric source information"""
    if iter == 6:
        return None
    elif iter > 6:
        if is_high_res:
            return config.block34_high_res_size
        return config.block34.size
    else:
        if is_high_res:
            return config.packed_fabric_high_res_size
        return packed_fabric.size if packed_fabric else None

def get_fabric_shape(packed_fabric, iter, config, is_high_res=False):
    packed_fabric_size = packed_fabric.size if packed_fabric else None
    if config.strategy == 'rail-fence':
        packed_fabric_size = _get_packed_fabric_rail_fence(packed_fabric, iter, config, is_high_res=is_high_res)
    else:
        if is_high_res:
            packed_fabric_size = config.packed_fabric_high_res_size
    curr_fabric_shape = get_curr_image_shape(packed_fabric_size, iter, config, is_high_res=is_high_res)
    target_L = target_length(curr_fabric_shape, iter, config.strategy)
    return curr_fabric_shape, target_L

#####################################################################
# Fabric Attachment and Positioning Functions
#####################################################################

def get_attach_instruction(iter, strategy):
    attach_instruction = None
    if strategy == 'log-cabin':
        if iter % 4 == 0:
            attach_instruction = "Attach the strip to the left side of the packed fabric"
        elif iter % 4 == 1:
            attach_instruction = "Attach the strip to the top of the packed fabric"
        elif iter % 4 == 2:
            attach_instruction = "Attach the strip to the right side of the packed fabric"
        else: # iter % 4 == 3
            attach_instruction = "Attach the strip to the bottom of the packed fabric"
    elif strategy == 'courthouse-steps':
        if iter % 4 == 0:
            attach_instruction = "Attach the strip to the top of the packed fabric"
        elif iter % 4 == 1:
            attach_instruction = "Attach the strip to the bottom of the packed fabric"
        elif iter % 4 == 2:
            attach_instruction = "Attach the strip to the left side of the packed fabric"
        else: # iter % 4 == 3
            attach_instruction = "Attach the strip to the right side of the packed fabric"
    elif strategy == 'rail-fence':
        if iter % 12 == 0 or iter % 12 == 1 or iter % 12 == 2:
            attach_instruction = "Attach the strip to the top of the packed fabric"
        elif iter % 12 == 3 or iter % 12 == 4 or iter % 12 == 5:
            attach_instruction = "Attach the strip to the right side of the packed fabric"
        elif iter % 12 == 6 or iter % 12 == 7 or iter % 12 == 8:
            attach_instruction = "Attach the strip to the bottom of the packed fabric"
        else: # iter % 12 == 9 or iter % 12 == 10 or iter % 12 == 11
            attach_instruction = "Attach the strip to the left side of the packed fabric"
    attach_instruction += " with quarter inch seam allowance and press seams open."
    return attach_instruction

def top_left(curr_image_shape, iter, strategy, best_shortest_side, sa=0):
    pos = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0: # top
            pos = (0, -best_shortest_side - 2 * sa)
        elif iter % 4 == 1: # bottom
            pos = (0, curr_image_shape.h - sa)
        elif iter % 4 == 2: # left
            pos = (-best_shortest_side - 2 * sa, 0)
        else: # right
            pos = (curr_image_shape.w - sa, 0)
    elif strategy == 'log-cabin':
        if iter % 4 == 0: # left
            pos = (-best_shortest_side - 2 * sa, 0)
        elif iter % 4 == 1: # top
            pos = (0, -best_shortest_side - 2 * sa)
        elif iter % 4 == 2: # right
            pos = (curr_image_shape.w - sa, 0)
        else: # bottom
            pos = (0, curr_image_shape.h - sa)
    elif strategy == 'rail-fence':
        if iter % 12 == 0 or iter % 12 == 1 or iter % 12 == 2: # top
            pos = (0, -best_shortest_side - 2 * sa)
        elif iter % 12 == 3 or iter % 12 == 4 or iter % 12 == 5: # right
            pos = (curr_image_shape.w - sa, 0)
        elif iter % 12 == 6 or iter % 12 == 7 or iter % 12 == 8: # bottom
            pos = (0, curr_image_shape.h - sa)
        else: # left
            pos = (-best_shortest_side - 2 * sa, 0)
    else:
        raise ValueError("Invalid strategy")
    return pos

def shifted_top_left(top_left_corner, best_shortest_side, other_dim, w, h, iter, strategy, sa=0):
    image_shape = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0: # top
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1], w, h)
        elif iter % 4 == 2: # left
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1], w, h)
        elif iter % 4 == 1: # bottom
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1] - (other_dim - best_shortest_side) - sa, w, h)
        else: # iter % 4 == 3 # right
            image_shape = ImageShape(top_left_corner[0] - (other_dim - best_shortest_side) - sa, top_left_corner[1], w, h)
    elif strategy == 'log-cabin':
        if iter % 4 == 0:
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1], w, h)
        elif iter % 4 == 1:
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1], w, h)
        elif iter % 4 == 2:
            image_shape = ImageShape(top_left_corner[0] - (other_dim - best_shortest_side) - sa, top_left_corner[1], w, h)
        else: # iter % 4 == 3
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1] - (other_dim - best_shortest_side) - sa, w, h)
    elif strategy == 'rail-fence':
        if iter % 12 == 0 or iter % 12 == 1 or iter % 12 == 2: # top
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1], w, h)
        elif iter % 12 == 3 or iter % 12 == 4 or iter % 12 == 5: # right
            image_shape = ImageShape(top_left_corner[0] - (other_dim - best_shortest_side) - sa, top_left_corner[1], w, h)
        elif iter % 12 == 6 or iter % 12 == 7 or iter % 12 == 8: # bottom
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1] - (other_dim - best_shortest_side) - sa, w, h)
        else: # left
            image_shape = ImageShape(top_left_corner[0], top_left_corner[1], w, h)
    else:
        raise ValueError("Invalid strategy")
    return image_shape

def next_top_left(op_index, top_left_corner, edge, iter, strategy, sa=0):
    pos = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0 or iter % 4 == 1:
            pos = (top_left_corner[0] + edge, top_left_corner[1])
            if op_index == 0: pos = (pos[0] + sa, pos[1])
        else:
            pos = (top_left_corner[0], top_left_corner[1] + edge)
            if op_index == 0: pos = (pos[0], pos[1] + sa)
    elif strategy == 'log-cabin':
        if iter % 4 == 0 or iter % 4 == 2:
            pos = (top_left_corner[0], top_left_corner[1] + edge)
            if op_index == 0: pos = (pos[0], pos[1] + sa)
        else:
            pos = (top_left_corner[0] + edge, top_left_corner[1])
            if op_index == 0: pos = (pos[0] + sa, pos[1])
    elif strategy == 'rail-fence':
        if (iter // 3) % 2 == 0:
            pos = (top_left_corner[0] + edge, top_left_corner[1])
            if op_index == 0: pos = (pos[0] + sa, pos[1])
        else:
            pos = (top_left_corner[0], top_left_corner[1] + edge)
            if op_index == 0: pos = (pos[0], pos[1] + sa)
    else:
        raise ValueError("Invalid strategy")
    return pos

def rotate_image_shape(w, h, image_shape, edge, iter, strategy, sa=0, use_high_res=False):
    rotated = False
    try:
        # Adjust dimensions based on whether we're using high-res or not
        width = w - (50 if use_high_res else 2 * sa)
        height = h - (50 if use_high_res else 2 * sa)

        if strategy == 'courthouse-steps':
            if iter % 4 == 0 or iter % 4 == 1:
                if height == edge:
                    image_shape.rotate(90)
                    rotated = True
                else:
                    assert width == edge, "dimension mismatch"
            else:
                if width == edge:
                    image_shape.rotate(90)
                    rotated = True
                else:
                    assert height == edge, "dimension mismatch"
        elif strategy == 'log-cabin':
            if iter % 4 == 0 or iter % 4 == 2:
                if width == edge:
                    image_shape.rotate(90)
                    rotated = True
                else:
                    assert height == edge, "dimension mismatch"
            else:
                if height == edge:
                    image_shape.rotate(90)
                    rotated = True
                else:
                    assert width == edge, "dimension mismatch"
        elif strategy == 'rail-fence':
            if (iter // 3) % 2 == 0:
                if height == edge:
                    image_shape.rotate(90)
                    rotated = True
                else:
                    assert width == edge, "dimension mismatch"
            else:
                if width == edge:
                    image_shape.rotate(90)
                    rotated = True
                else:
                    assert height == edge, "dimension mismatch"
        else:
            raise ValueError("Invalid strategy")
    except Exception as e:
        print(e, file=sys.stderr)
        print(iter, strategy, file=sys.stderr)
        print('sa', sa, file=sys.stderr)
        print('edge', edge, file=sys.stderr)
        print('w - 2 * sa', width, file=sys.stderr)
        print('h - 2 * sa', height, file=sys.stderr)
        raise e
    return rotated

#####################################################################
# Image Trimming and Cropping Functions
#####################################################################

def trim_image_in_strip(image, im_index, n_edges, rotated, iter, strategy, sa=0):
    # this is for trimming the fabrics next to each other so that the final image
    # looks clean without extra fabric for seaming
    if n_edges == 1:
        return image
    def trim_horizontal(image, im_index, n_edges, rotated, sa):
        timage = None
        if 0 < im_index < n_edges - 1:
            if rotated:
                timage = image.crop((0, sa, w, h - sa))
            else:
                timage = image.crop((sa, 0, w - sa, h))
        elif im_index == 0:
            if rotated:
                timage = image.crop((0, 0, w, h - sa))
            else:
                timage = image.crop((0, 0, w - sa, h))
        elif im_index == n_edges - 1:
            if rotated:
                timage = image.crop((0, sa, w, h))
            else:
                timage = image.crop((sa, 0, w, h))
        return timage

    def trim_vertical(image, im_index, n_edges, rotated, sa):
        timage = None
        if 0 < im_index < n_edges - 1:
            if rotated:
                timage = image.crop((sa, 0, w - sa, h))
            else:
                timage = image.crop((0, sa, w, h - sa))
        elif im_index == n_edges - 1:
            if rotated:
                timage = image.crop((0, 0, w - sa, h))
            else:
                timage = image.crop((0, 0, w, h - sa))
        elif im_index == 0:
            if rotated:
                timage = image.crop((sa, 0, w, h))
            else:
                timage = image.crop((0, sa, w, h))
        return timage

    w, h = image.size
    timage = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0 or iter % 4 == 1: # horizontal
            timage = trim_horizontal(image, im_index, n_edges, rotated, sa)
        else: # vertical
            timage = trim_vertical(image, im_index, n_edges, rotated, sa)
    elif strategy == 'log-cabin':
        if iter % 4 == 0 or iter % 4 == 2: # vertical
            timage = trim_vertical(image, im_index, n_edges, rotated, sa)
        else: # horizontal
            timage = trim_horizontal(image, im_index, n_edges, rotated, sa)
    elif strategy == 'rail-fence':
        if (iter // 3) % 2 == 0: # horizontal
            timage = trim_horizontal(image, im_index, n_edges, rotated, sa)
        else: # vertical
            timage = trim_vertical(image, im_index, n_edges, rotated, sa)
    return timage

def trim_image(image, best_shortest_side, rotated, w, h, iter, strategy):
    # this is for keeping the trimmed off parts of the fabrics to use
    # again if it is large enough (within the strip)
    cropped_image = None
    try:
        if strategy == 'courthouse-steps':
            if iter % 4 == 0:
                if rotated:
                    cropped_image = image.crop((0, 0, w - best_shortest_side, h))
                else:
                    cropped_image = image.crop((0, best_shortest_side, w, h))
            elif iter % 4 == 1:
                if rotated:
                    cropped_image = image.crop((best_shortest_side, 0, w, h))
                else:
                    cropped_image = image.crop((0, 0, w, h - best_shortest_side))
            elif iter % 4 == 2:
                if rotated:
                    cropped_image = image.crop((0, best_shortest_side, w, h))
                else:
                    cropped_image = image.crop((best_shortest_side, 0, w, h))
            else: # iter % 4 == 3
                if rotated:
                    cropped_image = image.crop((0, 0, w, h - best_shortest_side))
                else:
                    cropped_image = image.crop((0, 0, w - best_shortest_side, h))
        elif strategy == 'log-cabin':
            if iter % 4 == 0:
                if rotated:
                    cropped_image = image.crop((0, best_shortest_side, w, h))
                else:
                    cropped_image = image.crop((best_shortest_side, 0, w, h))
            elif iter % 4 == 1:
                if rotated:
                    cropped_image = image.crop((0, 0, w - best_shortest_side, h))
                else:
                    cropped_image = image.crop((0, best_shortest_side, w, h))
            elif iter % 4 == 2:
                if rotated:
                    cropped_image = image.crop((0, 0, w, h - best_shortest_side))
                else:
                    cropped_image = image.crop((0, 0, w - best_shortest_side, h))
            else: # iter % 4 == 3
                if rotated:
                    cropped_image = image.crop((best_shortest_side, 0, w, h))
                else:
                    cropped_image = image.crop((0, 0, w, h - best_shortest_side))
        elif strategy == 'rail-fence':
            if iter % 12 == 0 or iter % 12 == 1 or iter % 12 == 2:
                if rotated:
                    cropped_image = image.crop((best_shortest_side, 0, w, h))
                else:
                    cropped_image = image.crop((0, best_shortest_side, w, h))
            elif iter % 12 == 3 or iter % 12 == 4 or iter % 12 == 5:
                if rotated:
                    cropped_image = image.crop((0, 0, w, h - best_shortest_side))
                else:
                    cropped_image = image.crop((0, 0, w - best_shortest_side, h))
            elif iter % 12 == 6 or iter % 12 == 7 or iter % 12 == 8:
                if rotated:
                    cropped_image = image.crop((0, 0, w - best_shortest_side, h))
                else:
                    cropped_image = image.crop((0, 0, w, h - best_shortest_side))
            else: # iter % 12 == 9 or iter % 12 == 10 or iter % 12 == 11
                if rotated:
                    cropped_image = image.crop((0, best_shortest_side, w, h))
                else:
                    cropped_image = image.crop((best_shortest_side, 0, w, h))
    except Exception as e:
        print(e, file=sys.stderr)
        print(iter, strategy, file=sys.stderr)
        print(best_shortest_side, w, h, w - best_shortest_side, h - best_shortest_side, file=sys.stderr)
        print('rotated =', rotated, file=sys.stderr)
    if cropped_image is None:
        print("cropped image is None")
        return image, 0
    return cropped_image, image.size[0] * image.size[1] - cropped_image.size[0] * cropped_image.size[1]

def trim_image_high_res(image_size, best_shortest_side, rotated, iter, strategy):
    # this method doesn't actually trim any image and is only for keeping track of
    # the remainder trimmed off part's size (within the strip)
    if image_size is None:
        return None
    w, h = image_size
    trimmed_size = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0 or iter % 4 == 1:
            if rotated:
                trimmed_size = (w - best_shortest_side, h)
            else:
                trimmed_size = (w, h - best_shortest_side)
        else: # iter % 4 == 2 or 3
            if rotated:
                trimmed_size = (w, h - best_shortest_side)
            else:
                trimmed_size = (w - best_shortest_side, h)
    elif strategy == 'log-cabin':
        if iter % 4 == 0 or iter % 4 == 2:
            if rotated:
                trimmed_size = (w, h - best_shortest_side)
            else:
                trimmed_size = (w - best_shortest_side, h)
        else: # iter % 4 == 1 or 3
            if rotated:
                trimmed_size = (w - best_shortest_side, h)
            else:
                trimmed_size = (w, h - best_shortest_side)
    elif strategy == 'rail-fence':
        if (iter // 3) % 2 == 0:
            if rotated:
                trimmed_size = (w - best_shortest_side, h)
            else:
                trimmed_size = (w, h - best_shortest_side)
        else:
            if rotated:
                trimmed_size = (w, h - best_shortest_side)
            else:
                trimmed_size = (w - best_shortest_side, h)
    return trimmed_size

#####################################################################
# Drawing and Visualization Functions
#####################################################################

def draw_dashed_crop_line(image, x=0, y=0, direction=None, sa=0):
    """
    Draw a dashed line on the image to indicate where to crop and seam allowances
    
    Args:
        image: PIL Image to draw on
        x: x-coordinate for vertical line
        y: y-coordinate for horizontal line
        direction: one of 'top', 'right', 'bottom', 'left' indicating where strip attaches
        sa: seam allowance width
    """
    if x == 0 and y == 0:
        print("x and y cannot both be 0, no cropping")
        return None
        
    draw = ImageDraw.Draw(image)
    w, h = image.size
    dash_length = 10
    gap_length = 5
    crop_color = "red"
    seam_color = (100, 100, 100)

    # Draw crop line
    if x == 0:
        assert y != 0, "x and y cannot both be 0"
        x_pos = x
        while x_pos < w:
            end_x = min(x_pos + dash_length, w)
            draw.line([(x_pos, y), (end_x, y)], fill=crop_color, width=2)
            x_pos += dash_length + gap_length
    elif y == 0:
        y_pos = y
        while y_pos < h:
            end_y = min(y_pos + dash_length, h)
            draw.line([(x, y_pos), (x, end_y)], fill=crop_color, width=2)
            y_pos += dash_length + gap_length
    else:
        raise ValueError("One of x and y should be 0")

    # Draw seam lines
    if direction and sa > 0:
        if direction == 'top':
            # Draw two horizontal lines at sa distance from top
            draw.line([(0, sa), (w, sa)], fill=seam_color, width=1)
            draw.line([(0, y-sa), (w, y-sa)], fill=seam_color, width=1)
        elif direction == 'bottom':
            # Draw two horizontal lines at sa distance from bottom
            draw.line([(0, y+sa), (w, y+sa)], fill=seam_color, width=1)
            draw.line([(0, h-sa), (w, h-sa)], fill=seam_color, width=1)
        elif direction == 'left':
            # Draw two vertical lines at sa distance from left
            draw.line([(sa, 0), (sa, h)], fill=seam_color, width=1)
            draw.line([(x-sa, 0), (x-sa, h)], fill=seam_color, width=1)
        elif direction == 'right':
            # Draw two vertical lines at sa distance from right
            draw.line([(x+sa, 0), (x+sa, h)], fill=seam_color, width=1)
            draw.line([(w-sa, 0), (w-sa, h)], fill=seam_color, width=1)

    return image

#####################################################################
# Current Strip Processing Functions
#####################################################################

def crop_curr_strip(shortest_side, curr_image, iter, strategy, sa=0, should_draw_crop_line=False):
    # this crops the strip so that all fabrics have the same width (shortest_side)
    w, h = curr_image.size
    cropped_image = None
    crop_line_image = None
    try:
        if strategy == 'courthouse-steps':
            if iter % 4 == 0:
                cropped_image = curr_image.crop((0, 0, w, shortest_side + sa))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, y=shortest_side + sa, direction='top', sa=sa)
            elif iter % 4 == 1:
                cropped_image = curr_image.crop((0, h - (shortest_side + sa), w, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, y=h-(shortest_side + sa), direction='bottom', sa=sa)
            elif iter % 4 == 2:
                cropped_image = curr_image.crop((0, 0, shortest_side + sa, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, x=shortest_side + sa, direction='left', sa=sa)
            else: # iter % 4 == 3
                cropped_image = curr_image.crop((w - (shortest_side + sa), 0, w, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, x=w-(shortest_side + sa), direction='right', sa=sa)
        elif strategy == 'log-cabin':
            if iter % 4 == 0:
                cropped_image = curr_image.crop((0, 0, shortest_side + sa, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, x=shortest_side + sa, direction='left', sa=sa)
            elif iter % 4 == 1:
                cropped_image = curr_image.crop((0, 0, w, shortest_side + sa))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, y=shortest_side + sa, direction='top', sa=sa)
            elif iter % 4 == 2:
                cropped_image = curr_image.crop((w - (shortest_side + sa), 0, w, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, x=w-(shortest_side + sa), direction='right', sa=sa)
            else: # iter % 4 == 3
                cropped_image = curr_image.crop((0, h - (shortest_side + sa), w, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, y=h-(shortest_side + sa), direction='bottom', sa=sa)
        elif strategy == 'rail-fence':
            if iter % 12 == 0 or iter % 12 == 1 or iter % 12 == 2:
                cropped_image = curr_image.crop((0, 0, w, shortest_side + sa))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, y=shortest_side + sa, direction='top', sa=sa)
            elif iter % 12 == 3 or iter % 12 == 4 or iter % 12 == 5:
                cropped_image = curr_image.crop((w - (shortest_side + sa), 0, w, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, x=w-(shortest_side + sa), direction='right', sa=sa)
            elif iter % 12 == 6 or iter % 12 == 7 or iter % 12 == 8:
                cropped_image = curr_image.crop((0, h - (shortest_side + sa), w, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, y=h-(shortest_side + sa), direction='bottom', sa=sa)
            else:
                cropped_image = curr_image.crop((0, 0, shortest_side + sa, h))
                if should_draw_crop_line: crop_line_image = draw_dashed_crop_line(curr_image, x=shortest_side + sa, direction='left', sa=sa)
    except Exception as e:
        print(e, file=sys.stderr)
        print(iter, strategy, file=sys.stderr)
        print(shortest_side, w, h, w - shortest_side, h - shortest_side, file=sys.stderr)
    if should_draw_crop_line:
        return cropped_image, crop_line_image
    return cropped_image

def crop_curr_image(target_L, curr_image, iter, strategy):
    # this crops the current strip to the target length
    w, h = curr_image.size
    cropped_image = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0 or iter % 4 == 1:
            cropped_image = curr_image.crop((0, 0, target_L, h))
        else: # iter % 4 == 2 or 3
            cropped_image = curr_image.crop((0, 0, w, target_L))
    elif strategy == 'log-cabin':
        if iter % 4 == 0 or iter % 4 == 2:
            cropped_image = curr_image.crop((0, 0, w, target_L))
        else: # iter % 4 == 1 or 3
            cropped_image = curr_image.crop((0, 0, target_L, h))
    elif strategy == 'rail-fence':
        if (iter // 3) % 2 == 0:
            cropped_image = curr_image.crop((0, 0, target_L, h))
        else:
            cropped_image = curr_image.crop((0, 0, w, target_L))
    return cropped_image

def trim_curr_image(target_L, curr_image, iter, strategy, sa=0):
    # this keeps the trimmed off part of the fabric in the current strip
    w, h = curr_image.size
    cropped_image = None
    try:
        if strategy == 'courthouse-steps':
            if iter % 4 == 0 or iter % 4 == 1:
                cropped_image = curr_image.crop((target_L, 0, w, h))
            else: # iter % 4 == 2 or 3
                cropped_image = curr_image.crop((0, target_L, w, h))
        elif strategy == 'log-cabin':
            if iter % 4 == 0 or iter % 4 == 2:
                cropped_image = curr_image.crop((0, target_L, w, h))
            else: # iter % 4 == 1 or 3
                cropped_image = curr_image.crop((target_L, 0, w, h))
        elif strategy == 'rail-fence':
            if (iter // 3) % 2 == 0:
                cropped_image = curr_image.crop((target_L, 0, w, h))
            else:
                cropped_image = curr_image.crop((0, target_L, w, h))
    except Exception as e:
        if w + 2 * sa < target_L or h + 2 * sa < target_L:
            print(target_L, w, h, w - target_L, h - target_L, file=sys.stderr)
            print('curr strip is not trimmed; the original piece should have been trimmed', file=sys.stderr)
    return cropped_image

def trim_curr_image_high_res(image_size, trimmed_length, rotated, iter, strategy):
    # this computes the high res size of the trimmed off part of the fabric in the current strip
    if image_size is None:
        return None
    w, h = image_size
    trimmed_size = None
    if strategy == 'courthouse-steps':
        if iter % 4 == 0 or iter % 4 == 1:
            if rotated:
                trimmed_size = (w, trimmed_length)
            else:
                trimmed_size = (trimmed_length, h)
        else: # iter % 4 == 2 or 3
            if rotated:
                trimmed_size = (trimmed_length, h)
            else:
                trimmed_size = (w, trimmed_length)
    elif strategy == 'log-cabin':
        if iter % 4 == 0 or iter % 4 == 2:
            if rotated:
                trimmed_size = (w, trimmed_length)
            else:
                trimmed_size = (trimmed_length, h)
        else: # iter % 4 == 1 or 3
            if rotated:
                trimmed_size = (trimmed_length, h)
            else:
                trimmed_size = (w, trimmed_length)
    elif strategy == 'rail-fence':
        if (iter // 3) % 2 == 0:
            if rotated:
                trimmed_size = (trimmed_length, h)
            else:
                trimmed_size = (w, trimmed_length)
        else:
            if rotated:
                trimmed_size = (w, trimmed_length)
            else:
                trimmed_size = (trimmed_length, h)
    return trimmed_size
