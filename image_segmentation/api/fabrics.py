import cv2
import numpy as np

# https://stackoverflow.com/a/63638091/5403217
# ray-casting algorithm based on
# https://wrfranklin.org/Research/Short_Notes/pnpoly.html
def is_inside(pos, polygon):
    x, y = pos
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
        p1x, p1y = p2x, p2y
    return inside

class Pattern:
    def __init__(self, pattern_pieces):
        self.pieces = pattern_pieces

class PatternPiece:
    def __init__(self, image, contour):
        self.image = cv2.imread(image)
        self.wh = (self.image.shape[1], self.image.shape[0])
        self.contour = np.array(contour, dtype=np.int32)
        self.min_bbox = cv2.minAreaRect(self.contour)
        self.seamed_contour = []

    def add_seam_allowance(self, seam_allowance):
        """
        The seam allowance should be 0.25 inch in pixels.
        """
        self.seamed_contour = []
        for i in range(len(self.contour) - 1):
            edge = np.array(self.contour[i]) - np.array(self.contour[i-1])
            perp = np.array([-edge[1], edge[0]])
            perp = perp / np.linalg.norm(perp)
            seam_allowance_vector = perp * seam_allowance
            if is_inside(self.contour[i] + seam_allowance_vector, self.contour):
                seam_allowance_vector = -seam_allowance_vector
            self.seamed_contour.append(self.contour[i-1])
            self.seamed_contour.append(self.contour[i-1] + seam_allowance_vector)
            self.seamed_contour.append(self.contour[i] + seam_allowance_vector)
        self.seamed_contour = np.array(self.seamed_contour, dtype=np.int32)
        self.min_bbox = cv2.minAreaRect(self.seamed_contour)
        self.export_svg() # for debugging

    def min_wh(self):
        return self.wh
        # return self.min_bbox[1]

    def export_svg(self):
        with open("pattern_piece.svg", "w") as f:
            f.write("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>")
            f.write("<path d='M")
            for point in self.seamed_contour:
                f.write(f"{point[0]},{point[1]} ")
            f.write("Z' fill='none' stroke='black' stroke-width='1' />")
            f.write("</svg>")

class FabricScrap:
    def __init__(self, image, contour):
        self.image = cv2.imread(image)
        self.wh = (self.image.shape[1], self.image.shape[0])
        self.contour = np.array(contour, dtype=np.int32)
        self.min_bbox = cv2.minAreaRect(self.contour)
        self.assigned_pattern_pieces = []

    def min_wh(self):
        return self.wh
        # return self.min_bbox[1]

    def pack(self, matched_pattern_piece):
        pass
