from copy import deepcopy
import numpy as np

class Segment:
    def __init__(self, edge_start, edge_end, orientation=None):
        self.s = edge_start
        self.e = edge_end
        self.dir = np.array(self.e) - np.array(self.s)
        self.length = np.linalg.norm(self.dir)
        self.angle = np.arctan2(self.dir[1], self.dir[0])
        self.is_horizontal = self.s[1] == self.e[1]
        self.orientation = orientation

    def __repr__(self):
        return f'Segment({self.s}, {self.e})'

class ImageShape:
    def __init__(self, x, y, w, h, rotations=None):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        # the rotation to be applied to the image itself
        self.rotations = []
        if rotations is not None:
            self.rotations = rotations

    def rotated(self):
        return sum(self.rotations) % 180 != 0

    def copy_from(self, other):
        self.x = other.x
        self.y = other.y
        self.w = other.w
        self.h = other.h
        self.rotations = deepcopy(other.rotations)

    def box(self):
        if self.rotated():
            return (self.x, self.y, self.h, self.w)
        else:
            return (self.x, self.y, self.w, self.h)

    def points(self):
        return [(self.x, self.y), (self.x + self.w, self.y), (self.x + self.w, self.y + self.h), (self.x, self.y + self.h)]

    def edges(self):
        return [Segment((self.x, self.y), (self.x + self.w, self.y), 'downward'),
                Segment((self.x + self.w, self.y), (self.x + self.w, self.y + self.h), 'right'),
                Segment((self.x + self.w, self.y + self.h), (self.x, self.y + self.h), 'upward'),
                Segment((self.x, self.y + self.h), (self.x, self.y), 'left')]

    def rotate(self, angle):
        self.rotations.append(angle)

    def overlaps_with(self, other_boxes, margin=0):
        self_x, self_y, self_w, self_h = self.box()
        for other in other_boxes:
            other_x, other_y, other_w, other_h = other
            if not (self_x + self_w <= other_x + margin or 
                    self_x + margin >= other_x + other_w or 
                    self_y + self_h <= other_y + margin or 
                    self_y + margin >= other_y + other_h):
                return True
        return False

    def overlap_area(self, other_boxes, margin=0):
        self_x, self_y, self_w, self_h = self.box()
        overlap_area = 0
        for other in other_boxes:
            other_x, other_y, other_w, other_h = other
            if not (self_x + self_w <= other_x + margin or 
                    self_x + margin >= other_x + other_w or 
                    self_y + self_h <= other_y + margin or 
                    self_y + margin >= other_y + other_h):
                overlap_area += (min(self_x + self_w, other_x + other_w) - max(self_x, other_x)) * (min(self_y + self_h, other_y + other_h) - max(self_y, other_y))
        return overlap_area

    def __repr__(self):
        return f'ImageShape({self.x}, {self.y}, {self.w}, {self.h})'

# translate everything such that the bottom left corner is at (0, 0)
def home_image_shapes(image_shapes):
    min_x = min([image_shape.x for image_shape in image_shapes])
    min_y = min([image_shape.y for image_shape in image_shapes])
    homed_image_shapes = []
    for image_shape in image_shapes:
        homed_image_shapes.append(ImageShape(image_shape.x - min_x, image_shape.y - min_y, image_shape.w, image_shape.h, image_shape.rotations))
    return homed_image_shapes