import numpy as np
from scripts.utils.binning import color_distance

class BinFilter:
    def __init__(self, filter_parameters):
        pass

    def validates(self, bin):
        pass

class FabricFilter(BinFilter):
    def __init__(self, filter_parameters):
        self.must_have_fabric = filter_parameters['must_have_fabric']
        assert isinstance(self.must_have_fabric, int), "must_have_fabric must be an integer that represents fabric id"

    def validates(self, bin):
        return any([edge.p.id == self.must_have_fabric for edge in bin.edges])

class UserBinFilter(BinFilter):
    def __init__(self, filter_parameters):
        self.user_selected_bins = filter_parameters.get('user_selected_bins', [])

    def __repr__(self):
        return f"Filtering bins with bin IDs [{self.user_selected_bins}]"

    def validates(self, bin):
        return bin.id in self.user_selected_bins

class OptionFilter:
    def __init__(self, filter_parameters):
        pass

    def validates(self, option):
        pass

class ThicknessFilter(OptionFilter):
    def __init__(self, filter_parameters):
        self.thickness_min = filter_parameters['thickness_min']
        self.thickness_max = filter_parameters['thickness_max']

    def __repr__(self):
        return f"Filtering options with thickness between {self.thickness_min} and {self.thickness_max}"

    def validates(self, thickness):
        return self.thickness_min <= thickness <= self.thickness_max

class OptionRank:
    def __init__(self):
        pass

    def compute_rank(self):
        pass

class HighFabricCountRank(OptionRank):
    # more fabrics = better
    def compute_rank(self, option):
        return len(option.edge_subset)

class LowFabricCountRank(HighFabricCountRank):
    # less fabrics = better
    def compute_rank(self, option):
        return -super().compute_rank(option)

class LargeThicknessRank(OptionRank):
    # thicker = better
    def compute_rank(self, option):
        return option.shortest_side

class SmallThicknessRank(LargeThicknessRank):
    # thinner = better
    def compute_rank(self, option):
        return -super().compute_rank(option)

class WastedAreaRank(OptionRank):
    # less wasted area = better
    def compute_rank(self, option):
        return option.wasted_area

class LowContrastRank(OptionRank):
    # less color difference = better
    def compute_rank(self, option):
        fabric_images = [edge.p.image for edge in option.edge_subset]
        average_colors = [np.mean(np.mean(np.array(im)[:, :, :3], axis=0), axis=0) for im in fabric_images]
        
        n = len(average_colors)
        if n < 2:
            return 0

        # Calculate average pairwise color differences using CIE2000
        total_diff = sum(
            color_distance(average_colors[i], average_colors[j], "CIE2000")
            for i in range(n)
            for j in range(i + 1, n)
        )

        return total_diff / (n * (n - 1) / 2)

class LowValueContrastRank(OptionRank):
    # less value difference = better
    def compute_rank(self, option):
        fabric_images = [edge.p.image for edge in option.edge_subset]
        hsv_images = [image.convert('HSV') for image in fabric_images]
        average_values = [np.mean(np.mean(np.array(hsv_image)[:, :, 2])) for hsv_image in hsv_images]

        n = len(average_values)
        if n < 2:
            return 0

        total_diff = sum(
            color_distance([0, 0, average_values[i]], [0, 0, average_values[j]], "value")
            for i in range(n)
            for j in range(i + 1, n)
        )

        return total_diff / (n * (n - 1) / 2)

class LowHueContrastRank(OptionRank):
    # less hue difference = better
    def compute_rank(self, option):
        fabric_images = [edge.p.image for edge in option.edge_subset]
        hsv_images = [image.convert('HSV') for image in fabric_images]
        average_hues = [np.mean(np.mean(np.array(hsv_image)[:, :, 0])) for hsv_image in hsv_images]

        n = len(average_hues)
        if n < 2:
            return 0

        total_diff = sum(
            color_distance([average_hues[i], 0, 0], [average_hues[j], 0, 0], "hue")
            for i in range(n)
            for j in range(i + 1, n)
        )

        return total_diff / (n * (n - 1) / 2)

class HighContrastRank(LowContrastRank):
    # more color difference = better
    def compute_rank(self, option):
        return -super().compute_rank(option)

class HighValueContrastRank(LowValueContrastRank):
    # more value difference = better
    def compute_rank(self, option):
        return -super().compute_rank(option)

class HighHueContrastRank(LowHueContrastRank):
    # more hue difference = better
    def compute_rank(self, option):
        return -super().compute_rank(option)
