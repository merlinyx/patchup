import math
from copy import deepcopy

class Points:
    def __init__(self, points):
        self.points = deepcopy(points)
        self.npoints = len(points)
        top_left = [self.min_x(), self.min_y()]
        self.points.append(top_left)

    def __len__(self):
        return self.npoints

    def flattened(self):
        flattened_points = []
        for point in self.points[:self.npoints]:
            flattened_points.extend(point)
        return flattened_points

    def closed_polygon(self):
        closed_points = self.points[:self.npoints] + [self.points[0]]
        closed_points_int = [(int(point[0]), int(point[1])) for point in closed_points]
        return closed_points_int

    def mid_x(self):
        x = [point[0] for point in self.points[:self.npoints]]
        return (min(x) + max(x)) / 2

    def mid_y(self):
        y = [point[1] for point in self.points[:self.npoints]]
        return (max(y) + min(y)) / 2

    def top_left(self):
        return self.points[-1]

    def x(self):
        return [point[0] for point in self.points]

    def y(self):
        return [point[1] for point in self.points]

    def px(self):
        return [point[0] for point in self.points[:self.npoints]]

    def py(self):
        return [-point[1] for point in self.points[:self.npoints]]

    def min_x(self):
        return min(self.x())

    def max_x(self):
        return max(self.x())

    def min_y(self):
        return min(self.y())

    def max_y(self):
        return max(self.y())

    def min(self):
        return self.min_x(), self.min_y()

    def mid(self):
        return self.mid_x(), self.mid_y()

    def translate(self, dx, dy):
        x = [point[0] + dx for point in self.points]
        y = [point[1] + dy for point in self.points]
        self.points = list(zip(x, y))
        # print("translate by", dx, dy)
        return self

    def scale(self, scale, anchor=(0, 0)):
        x = [anchor[0] + (point[0] - anchor[0]) * scale for point in self.points]
        y = [anchor[1] + (point[1] - anchor[1]) * scale for point in self.points]
        self.points = list(zip(x, y))
        # print("scale by", scale, "with anchor", anchor)
        return self

    def rotate(self, angle, anchor=None):
        # by default rotation anchor is the midpoint
        if anchor is None:
            anchor = self.mid_x(), self.mid_y()
        angle = math.radians(angle)
        x = [anchor[0] + math.cos(angle) * (point[0] - anchor[0]) - math.sin(angle) * (point[1] - anchor[1]) for point in self.points]
        y = [anchor[1] + math.sin(angle) * (point[0] - anchor[0]) + math.cos(angle) * (point[1] - anchor[1]) for point in self.points]
        self.points = list(zip(x, y))
        # print("rotate by", angle, "with anchor", anchor)
        return self

    def bbox(self):
        return self.min_x(), self.min_y(), self.max_x(), self.max_y()

    def wh(self):
        return self.max_x() - self.min_x(), self.max_y() - self.min_y()