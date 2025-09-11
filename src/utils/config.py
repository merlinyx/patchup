class PackingConfig:
    def __init__(self, dpi=100, threshold=100, min_scrap_size=100,
                 seam_allowance=25, strategy='log-cabin', color_bin=False,
                 start_length=None, max_options=20):
        self.dpi = dpi # how many pixels per inch
        self.scale_factor = 1
        self.threshold = threshold # threshold for allowable packing target length difference
        self.min_scrap_size = min_scrap_size # minimum size of scrap to keep
        self.sa = seam_allowance # seam allowance
        self.strategy = strategy
        self.use_color_bins = color_bin
        self.desired_color = None
        self.max_options = max_options
        # useful when the strategy is rail-fence
        self.start_length = start_length
        self.block12 = None
        self.block34 = None
        self.target_L = {
            'top': 0,
            'right': 0,
            'bottom': 0,
            'left': 0,
        }
        # properties for high-res packing
        self.packed_fabric_high_res_size = None
        self.block12_high_res_size = None
        self.block34_high_res_size = None
        self.target_L_high_res = {
            'top': 0,
            'right': 0,
            'bottom': 0,
            'left': 0,
        }

    def update_dpi(self, dpi):
        if dpi != self.dpi:
            self.sa = int(self.sa / self.dpi * dpi)
            self.threshold = int(self.threshold / self.dpi * dpi)
            self.min_scrap_size = int(self.min_scrap_size / self.dpi * dpi)
            self.scale_factor = dpi / self.dpi
            self.dpi = dpi

    def reset_dpi(self):
        self.dpi = 100
        self.sa = 25
        self.threshold = 100
        self.min_scrap_size = 100
        self.scale_factor = 1

class PackingOption:
    """
    A container class for packing options.

    i: the index of the option
    edge_subset: a list of Edges used to pack this strip
    other_dims: a list of the other dimensions of the used edges
    wasted_area: the fabric area wasted by selecting this strip
    shortest_side: the shortest side of the strip (min of other_dims)
    """
    def __init__(self, i, edge_subset, other_dims, shortest_side, total_area, wasted_area, shortest_side_px=None):
        self.index = i
        self.edge_subset = list(edge_subset)
        self.other_dims = other_dims
        self.shortest_side = shortest_side
        self.total_area = total_area
        self.wasted_area = wasted_area
        self.shortest_side_px = shortest_side_px

    def update_order(self, order):
        self.edge_subset = [self.edge_subset[i] for i in order]
        self.other_dims = [self.other_dims[i] for i in order]

    def __repr__(self):
        return f"<Option Edges ({self.index}): {self.edge_subset}\nOther dimensions: {self.other_dims}\nWasted area: {self.wasted_area}\nTotal area: {self.total_area}\nThickness: {self.shortest_side}>\n"
