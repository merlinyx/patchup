import colorsys
import numpy as np
import os
from scripts.utils.binning import *
from scripts.utils.config import PackingOption
from scripts.utils.filters import *
from scripts.utils.plot import base64_to_pil_image, pil_image_to_base64
from scripts.utils.load_images import open_image
from gurobipy import *
import copy

def has_gurobi():
    # uncomment to disable gurobi
    # return False
    try:
        # Create a test model
        m = Model("test")
        
        # Add a variable
        m.addVar(name="x")
        
        # Update model
        m.update()
        
        return True
    except GurobiError:
        return False

M = 1e6

class Edge:
    def __init__(self, length, parent_fabric, sibling_edge, is_e1, high_res_length=None):
        self._length = length
        self._high_res_length = high_res_length
        self.p = parent_fabric
        self.s = sibling_edge
        self.is_e1 = is_e1
        if self.s is not None and self.s.s is None:
            self.s.s = self

    def length(self, use_high_res=True):
        if use_high_res and self._high_res_length is not None:
            return self._high_res_length
        return self._length

    def get_other_dim(self, use_high_res=True):
        if self.s is None:
            return self.length(use_high_res)
        return self.s.length(use_high_res)

    def update_edge(self, length, high_res_length=None):
        """Update the edge's length values while maintaining its relationships.

        Args:
            length: New length value
            high_res_length: New high-resolution length value (optional)
        """
        self._length = length
        if high_res_length is not None:
            self._high_res_length = high_res_length

    def __repr__(self):
        return f"Edge({self._length}/{self._high_res_length}, Fabric {self.p.id})"

class Fabric:

    id = 0

    def __init__(self, image, sa=0, fid=None, image_path=None, high_res_image_path=None):
        # Use high-res image for edge dimensions if available
        self.high_res_image_size = None
        if high_res_image_path:
            high_res_image = open_image(high_res_image_path)
            self.high_res_image_size = high_res_image.size
            self.e1 = Edge(image.size[0] - 2 * sa, self, None, True, high_res_length=(high_res_image.size[0] - 50))
            self.e2 = Edge(image.size[1] - 2 * sa, self, self.e1, False, high_res_length=(high_res_image.size[1] - 50))
        else:
            self.e1 = Edge(image.size[0] - 2 * sa, self, None, True)
            self.e2 = Edge(image.size[1] - 2 * sa, self, self.e1, False)
        self.image_path = image_path
        self.image = image
        self.image_updated = False
        # average color of the fabric
        self.color = np.mean(np.mean(np.array(image)[:, :, :3], axis=0), axis=0)
        self.dominant_color = get_mode_color(image, mode='dominant')
        # autoincrement id or use user-supplied id
        if fid is None:
            self.id = Fabric.id
            Fabric.id += 1
        else:
            self.id = fid

    def __repr__(self):
        return f"Fabric({self.id}, {self.image_path}, e1={self.e1}, e2={self.e2})"

    def __hash__(self):
        return self.id

    def to_json(self):
        if self.image_updated:
            return {'id': self.id, 'image': self.image_path, 'img': pil_image_to_base64(self.image)}
        return {'id': self.id, 'image': self.image_path}

    def update_after_trimming(self, trimmed_image, sa=0, high_res_image_size=None):
        # return # hack for result generation for p3 & p4's task2
        # Update image
        self.image = trimmed_image
        self.color = np.mean(np.mean(np.array(self.image)[:, :, :3], axis=0), axis=0)
        # Update edges with new dimensions while maintaining relationships
        if high_res_image_size is not None:
            self.high_res_image_size = high_res_image_size
            self.e1.update_edge(trimmed_image.size[0] - 2 * sa, high_res_length=(high_res_image_size[0] - 50))
            self.e2.update_edge(trimmed_image.size[1] - 2 * sa, high_res_length=(high_res_image_size[1] - 50))
        else:
            self.e1.update_edge(trimmed_image.size[0] - 2 * sa)
            self.e2.update_edge(trimmed_image.size[1] - 2 * sa)
        self.image_updated = True

    def reload(self, sa=0):
        self.image = open_image(self.image_path)
        self.color = np.mean(np.mean(np.array(self.image)[:, :, :3], axis=0), axis=0)
        self.dominant_color = get_mode_color(self.image, mode='dominant')
        self.e1.update_edge(self.image.size[0] - 2 * sa)
        self.e2.update_edge(self.image.size[1] - 2 * sa)

class FabricBin:

    id = 0

    def __init__(self, edges, fbid=None, name=None):
        self.edges = edges
        self.sibling_edges = [e.s for e in self.edges]
        fabrics = set([e.p for e in self.edges])
        self.nfabrics = len(fabrics)
        self.max_length = sum([max(f.e1.length(), f.e2.length()) for f in fabrics])
        self.min_length = min([min(f.e1.length(), f.e2.length()) for f in fabrics])
        self.length_range = (self.min_length, self.max_length)
        # autoincrement id or use user-supplied id
        if fbid is None:
            self.id = FabricBin.id
            FabricBin.id += 1
        else:
            self.id = fbid
        if name is None:
            self.name = f"Bin {self.id + 1}"
        else:
            self.name = name
        # add Wij matrix to precompute which edge is smaller than the other in length
        self.Wmat = {}
        for i in range(len(self.edges)):
            for j in range(len(self.edges)):
                self.Wmat[i, j] = 1 if self.edges[i].length() <= self.edges[j].length() else 0
                
        # Precompute color differences for all edge pairs
        self.edge_pairs = []
        self.color_diffs = {}
        self.value_diffs = {}
        self.hue_diffs = {}
        for i, edge_i in enumerate(self.edges):
            for j, edge_j in enumerate(self.edges[i+1:], i+1):
                if edge_i.p != edge_j.p:  # Don't compute for edges from same fabric
                    self.edge_pairs.append((edge_i, edge_j))
                    # Compute color differences (CIE1994)
                    self.color_diffs[(edge_i, edge_j)] = color_distance(edge_i.p.color, edge_j.p.color, "CIE1994")
                    # Value differences
                    self.value_diffs[(edge_i, edge_j)] = color_distance(edge_i.p.dominant_color, edge_j.p.dominant_color, "value")
                    # Hue differences
                    self.hue_diffs[(edge_i, edge_j)] = color_distance(edge_i.p.dominant_color, edge_j.p.dominant_color, "hue")
                else:
                    self.color_diffs[(edge_i, edge_j)] = 0
                    self.value_diffs[(edge_i, edge_j)] = 0
                    self.hue_diffs[(edge_i, edge_j)] = 0

    def __repr__(self):
        return f"FabricBin({self.length_range}) with {len(self.edges)} edges"

    def to_json(self):
        fabrics = set([e.p for e in self.edges])
        return {'id': self.id, 'name': self.name, 'fabrics': [fabric.to_json() for fabric in fabrics]}

    def can_afford(self, target_length, threshold):
        return self.min_length - threshold // 2 <= target_length <= self.max_length + threshold // 2

    def affordable_ranges(self): # this is the range of the sibling edges
        return (self.min_length, self.max_length)

    def find_best_subsets_dp(self, target_L, threshold, suppress_output=True):
        """
        Dynamic programming implementation of the subset sum problem (slow as #edges grows)
        """
        print('bin size:', len(self.edges))
        # dp dictionary to hold the best subsets for each possible sum
        dp = {0: set([frozenset()])}

        for edge in self.sibling_edges:
            # Create a new state dictionary to avoid modifying the dictionary during iteration
            new_dp = dp.copy()
            
            for current_sum in dp:
                if current_sum > target_L:
                    continue
                new_sum = current_sum + edge.length()
                # Only consider new sums that are within the target threshold
                for curr_subset in dp[current_sum].copy():
                    # Ensure the new edge isn't from the same rectangle as any edge in the current subset
                    if edge.p.id not in set([edge.p.id for edge in curr_subset]):
                        if new_sum not in new_dp:
                            new_dp[new_sum] = set()
                        # check for duplicates
                        new_subset = set(curr_subset)
                        new_subset.add(edge)
                        if frozenset(new_subset) not in new_dp[new_sum]:
                            new_dp[new_sum].add(frozenset(new_subset))

            dp = new_dp

        # Filter out subsets that are out of the threshold range
        best_sums = [sum_ for sum_ in dp.keys() if target_L <= sum_ <= target_L + threshold]

        # If no valid sums are found, return an empty list
        if not best_sums:
            minimum = min(dp.keys(), key=lambda x: abs(target_L - x))
            if not suppress_output: print(f"No valid sums found within the threshold. Closest sum: {minimum}")
            if minimum == 0:
                return []
            return minimum, dp[minimum]

        # Get the best subsets (closest to L)
        best_sum = min(best_sums, key=lambda x: abs(target_L - x))
        if not suppress_output: print(f"Best sum: {best_sum}; Target length: {target_L}")
        if target_L == best_sum:
            if not suppress_output: print(f"Found {len(dp[best_sum])} edge subsets with the exact length")
        return best_sum, dp[best_sum]

    def find_best_subsets_gurobi(self, target_L, threshold, sa=0, time_limit=30, solution_limit=10,
                          option_rank=None, mip_gap=10, suppress_output=True, thickness_min=None, thickness_max=None):
        """
        Gurobi implementation of the subset sum problem.
        
        Args:
            target_L: Target length for the subset sum
            threshold: Acceptable deviation from target length
            sa: Seam allowance
            time_limit: Maximum time for Gurobi to run (seconds)
            solution_limit: Maximum number of solutions to return
            option_rank: Ranking method for solutions
            mip_gap: MIP gap tolerance (%)
            suppress_output: Whether to suppress Gurobi output
            thickness_min: Minimum thickness constraint (optional)
            thickness_max: Maximum thickness constraint (optional)
        """
        if not has_gurobi():
            print("Gurobi license not found. Falling back to dynamic programming implementation.")
            return self.find_best_subsets_dp(target_L, threshold, suppress_output)

        print('bin size:', len(self.edges))

        # Create a new model
        m = Model("edge_selection")
        m.Params.OutputFlag = 0 if suppress_output else 1
        m.Params.TimeLimit = time_limit
        if mip_gap > 0:
            m.Params.MIPGap = mip_gap
        m.Params.SolutionLimit = solution_limit

        # Create binary variables for each edge
        edge_vars = {}
        edges_by_var = {}  # Reverse lookup dictionary
        for edge in self.edges:
            var = m.addVar(vtype=GRB.BINARY, name=f"edge_{edge.p.id}_{edge.length()}")
            edge_vars[edge] = var
        # Update model to finalize variable creation
        m.update()
        for edge, var in edge_vars.items():
            edges_by_var[var] = edge

        total_length = quicksum(edge.length() * edge_vars[edge] for edge in self.sibling_edges)

        # Create min_thickness variable
        min_thickness = m.addVar(name="min_thickness", lb=self.length_range[0], ub=self.length_range[1])

        # Ensure min_thickness is less than or equal to all selected edges
        for edge in self.edges:
            m.addConstr(min_thickness <= edge.get_other_dim() + M * (1 - edge_vars[edge]))

        # For each edge, check if it's the minimum using Wmat
        is_min_vars = []
        for i, edge_i in enumerate(self.edges):
            # Binary variable indicating if edge_i is the minimum
            is_min_i = m.addVar(vtype=GRB.BINARY, name=f"is_min_{i}")
            is_min_vars.append(is_min_i)

            # If edge_i is selected and is the minimum, min_thickness should equal its length
            m.addConstr(min_thickness >= edge_i.get_other_dim() - M * (1 - is_min_i))
            m.addConstr(min_thickness <= edge_i.get_other_dim() + M * (1 - is_min_i))

            # Edge can only be minimum if it's selected
            m.addConstr(is_min_i <= edge_vars[edge_i])

            # If edge_i is minimum, it must be <= all other selected edges
            for j, edge_j in enumerate(self.edges):
                if i != j:
                    # If edge_i is minimum and edge_j is selected, then edge_i <= edge_j must be true
                    m.addConstr(self.Wmat[i,j] >= is_min_i + edge_vars[edge_j] - 1)

        # Exactly one selected edge must be the minimum
        m.addConstr(quicksum(is_min_vars) == 1)

        # Add thickness constraints if provided
        if thickness_min is not None:
            m.addConstr(min_thickness >= thickness_min)
        if thickness_max is not None:
            m.addConstr(min_thickness <= thickness_max)

        # Create option rank objective
        if isinstance(option_rank, WastedAreaRank) or isinstance(option_rank, LargeThicknessRank) or isinstance(option_rank, SmallThicknessRank):
            if isinstance(option_rank, WastedAreaRank):
                wasted_area = quicksum((edge.get_other_dim() - 2 * sa - min_thickness) * edge.length() * edge_vars[edge] for edge in self.edges)
                # Add absolute deviation and constraints
                abs_deviation = m.addVar(name="abs_deviation", lb=0, ub=threshold)
                m.addConstr(abs_deviation >= total_length - target_L)
                m.addConstr(abs_deviation >= target_L - total_length)
                m.setObjective(wasted_area + abs_deviation * min_thickness, GRB.MINIMIZE)
            elif isinstance(option_rank, LargeThicknessRank):
                m.setObjective(-min_thickness, GRB.MINIMIZE)
            elif isinstance(option_rank, SmallThicknessRank):
                m.setObjective(min_thickness, GRB.MINIMIZE)

        elif isinstance(option_rank, HighFabricCountRank) or isinstance(option_rank, LowFabricCountRank):
            fabric_count = m.addVar(name="fabric_count", lb=0, ub=self.nfabrics) # lb=1 is somehow wrong         
            m.addConstr(fabric_count == quicksum(edge_vars[edge] for edge in self.edges))
            if isinstance(option_rank, HighFabricCountRank):
                m.setObjective(-fabric_count, GRB.MINIMIZE)
            elif isinstance(option_rank, LowFabricCountRank):
                m.setObjective(fabric_count, GRB.MINIMIZE)

        else:
            # Create variables for each pair being selected
            pair_vars = {}
            for edge_i, edge_j in self.edge_pairs:
                pair_vars[(edge_i, edge_j)] = m.addVar(vtype=GRB.BINARY, name=f"pair_{edge_i.p.id}_{edge_j.p.id}")

            # Pair variable should be 1 only if both edges are selected
            for (edge_i, edge_j), pair_var in pair_vars.items():
                m.addConstr(pair_var <= edge_vars[edge_i])
                m.addConstr(pair_var <= edge_vars[edge_j])
                m.addConstr(pair_var >= edge_vars[edge_i] + edge_vars[edge_j] - 1)

            # Calculate total number of pairs
            total_pairs = quicksum(pair_vars.values())

            # Add constraint to ensure we have at least one pair if we have at least 2 edges
            total_edges = quicksum(edge_vars.values())
            m.addConstr(total_pairs >= (total_edges * (total_edges - 1)) / 2 - M * (2 - total_edges))

            # Set objective based on the specific rank type
            if isinstance(option_rank, LowContrastRank) or isinstance(option_rank, HighContrastRank):
                total_diff = quicksum(self.color_diffs[(edge_i, edge_j)] * pair_vars[(edge_i, edge_j)] 
                                    for (edge_i, edge_j) in self.edge_pairs)
                                    
                if isinstance(option_rank, LowContrastRank):
                    m.setObjective(total_diff, GRB.MINIMIZE)
                else:  # HighContrastRank
                    m.setObjective(-total_diff, GRB.MINIMIZE)

            elif isinstance(option_rank, LowValueContrastRank) or isinstance(option_rank, HighValueContrastRank):
                total_diff = quicksum(self.value_diffs[(edge_i, edge_j)] * pair_vars[(edge_i, edge_j)]
                                    for (edge_i, edge_j) in self.edge_pairs)
                                    
                if isinstance(option_rank, LowValueContrastRank):
                    m.setObjective(total_diff, GRB.MINIMIZE)
                else:  # HighValueContrastRank
                    m.setObjective(-total_diff, GRB.MINIMIZE)

            elif isinstance(option_rank, LowHueContrastRank) or isinstance(option_rank, HighHueContrastRank):
                total_diff = quicksum(self.hue_diffs[(edge_i, edge_j)] * pair_vars[(edge_i, edge_j)]
                                    for (edge_i, edge_j) in self.edge_pairs)

                if isinstance(option_rank, LowHueContrastRank):
                    m.setObjective(total_diff, GRB.MINIMIZE)
                else:  # HighHueContrastRank
                    m.setObjective(-total_diff, GRB.MINIMIZE)

        # Add constraints
        # 1. Total length should be within threshold
        m.addConstr(total_length >= target_L)
        m.addConstr(total_length <= target_L + threshold)

        # 2. Can't use multiple edges from same rectangle
        for fabric in set([edge.p for edge in self.edges]):
            m.addConstr(edge_vars[fabric.e1] + edge_vars[fabric.e2] <= 1)

        # Print out the gurobi model for debugging
        if not suppress_output:
            print("Gurobi model:")
            print(m.getConstrs())
            print(m.getVars())
            print(m.getObjective())
            print("target_L:", target_L)
            print("threshold:", threshold)

        # Collection to store solutions by their sums
        solution_sums = {}

        # Callback function to collect solutions
        def solution_callback(model, where):
            if where == GRB.Callback.MIPSOL:
                # Get current solution - this works in callbacks even if model status is LOADED
                var_values = model.cbGetSolution(list(edge_vars.values()))
                vars_list = list(edge_vars.values())

                # Build solution set and calculate sum
                solution = set()
                sol_sum = 0
                for var, val in zip(vars_list, var_values):
                    if val > 0.5:  # Binary variable is 1
                        edge = edges_by_var[var]
                        solution.add(edge)
                        sol_sum += edge.length()

                # if min_thickness is wrong, don't add the solution
                if min_thickness is not None:
                    min_thickness_val = model.cbGetSolution(min_thickness)
                    shortest_side = min([edge.get_other_dim() for edge in solution])
                    if round(min_thickness_val) != (shortest_side):
                        print(f"warning: min thickness is wrong for sol#{sum([len(sol) for sol in solution_sums.values()])}")
                        print(f"min thickness: {min_thickness_val}")
                        print(f"shortest side: {shortest_side}")
                        # Add constraint to find different solutions
                        # model.cbLazy(quicksum(edge_vars[edge] for edge in solution) <= len(solution) - 1)
                        return

                # Add to solution_sums if not already present
                solution_frozen = frozenset(solution)
                if sol_sum not in solution_sums:
                    solution_sums[sol_sum] = set()
                if solution_frozen not in solution_sums[sol_sum]:
                    solution_sums[sol_sum].add(solution_frozen)
                    if not suppress_output:
                        print(f"Found solution with sum {sol_sum}")
                # Check if we've found enough solutions
                best_sum = min(solution_sums.keys(), key=lambda x: abs(target_L - x))
                total_solutions = len(solution_sums[best_sum])
                if total_solutions >= solution_limit:
                    if not suppress_output:
                        print(f"Found {total_solutions} solutions at {best_sum}, terminating")
                    model.terminate()

                # Add constraint to ensure at least one edge is different from this solution
                # For each edge in the solution, we need at least one to be 0
                # For each edge not in the solution, we need at least one to be 1
                model.cbLazy(quicksum(1 - edge_vars[edge] for edge in solution) + 
                            quicksum(edge_vars[edge] for edge in set(self.edges) - solution) >= 1)

        # Set the callback
        m.setParam(GRB.Param.LazyConstraints, 1)

        # Optimize
        m.optimize(solution_callback)

        # Find the best sum (closest to target_L)
        if len(solution_sums) > 0:
            # return up to solution_limit solutions sorted by key
            nsolutions = 0
            solutions_to_return = []
            for best_sum in sorted(solution_sums.keys(), key=lambda x: abs(target_L - x)):
                best_sum_subset = solution_sums[best_sum]
                if nsolutions + len(best_sum_subset) < solution_limit:
                    solutions_to_return.append((best_sum, best_sum_subset))
                    nsolutions += len(best_sum_subset)
                elif solution_limit - nsolutions > 0:
                    solutions_to_return.append((best_sum, list(best_sum_subset)[:solution_limit - nsolutions]))
                    break
            if not suppress_output:
                print(f"returning {len(solutions_to_return)} sum-solutions")
            return solutions_to_return

        if not suppress_output:
            print("No solutions found")
        return [(0, [])]

    def find_best_subsets(self, target_L, threshold, sa=0, time_limit=30, mip_gap=10,
                          thickness_min=None, thickness_max=None,
                          fabric_count_min=None, fabric_count_max=None,
                          solution_limit=20, suppress_output=True):
        """
        Gurobi implementation of the subset sum problem with more constraints and fixed waste area objective.

        Args:
            target_L: Target length for the subset sum
            threshold: Acceptable deviation from target length
            sa: Seam allowance
            time_limit: Maximum time for Gurobi to run (seconds)
            mip_gap: MIP gap tolerance (%)
            suppress_output: Whether to suppress Gurobi output
            thickness_min: Minimum thickness constraint (optional)
            thickness_max: Maximum thickness constraint (optional)
            fabric_count_min: Minimum fabric count constraint (optional)
            fabric_count_max: Maximum fabric count constraint (optional)
        """
        if not has_gurobi():
            print("Gurobi license not found. Falling back to dynamic programming implementation.")
            return self.find_best_subsets_dp(target_L, threshold, suppress_output)

        print('bin size:', len(self.edges))

        # Create a new model
        m = Model("edge_selection")
        m.Params.OutputFlag = 0 if suppress_output else 1
        m.Params.TimeLimit = time_limit
        m.Params.SolutionLimit = solution_limit # still give a solution limit but much larger
        if mip_gap > 0:
            m.Params.MIPGap = mip_gap

        # Create binary variables for each edge
        edge_vars = {}
        edges_by_var = {}  # Reverse lookup dictionary
        for edge in self.edges:
            var = m.addVar(vtype=GRB.BINARY, name=f"edge_{edge.p.id}_{edge.length()}")
            edge_vars[edge] = var
        # Update model to finalize variable creation
        m.update()
        for edge, var in edge_vars.items():
            edges_by_var[var] = edge

        total_length = quicksum(edge.length() * edge_vars[edge] for edge in self.sibling_edges)

        ########## Create min_thickness variable ##########
        min_thickness = m.addVar(name="min_thickness", lb=self.length_range[0], ub=self.length_range[1])
        # Add thickness constraints if provided
        if thickness_min is not None:
            m.addConstr(min_thickness >= thickness_min)
        if thickness_max is not None:
            m.addConstr(min_thickness <= thickness_max)

        # Ensure min_thickness is less than or equal to all selected edges
        for edge in self.edges:
            m.addConstr(min_thickness <= edge.get_other_dim() + M * (1 - edge_vars[edge]))

        # For each edge, check if it's the minimum using Wmat
        is_min_vars = []
        for i, edge_i in enumerate(self.edges):
            # Binary variable indicating if edge_i is the minimum
            is_min_i = m.addVar(vtype=GRB.BINARY, name=f"is_min_{i}")
            is_min_vars.append(is_min_i)

            # If edge_i is selected and is the minimum, min_thickness should equal its length
            m.addConstr(min_thickness >= edge_i.get_other_dim() - M * (1 - is_min_i))
            m.addConstr(min_thickness <= edge_i.get_other_dim() + M * (1 - is_min_i))

            # Edge can only be minimum if it's selected
            m.addConstr(is_min_i <= edge_vars[edge_i])

            # If edge_i is minimum, it must be <= all other selected edges
            for j, edge_j in enumerate(self.edges):
                if i != j:
                    # If edge_i is minimum and edge_j is selected, then edge_i <= edge_j must be true
                    m.addConstr(self.Wmat[i,j] >= is_min_i + edge_vars[edge_j] - 1)

        # Exactly one selected edge must be the minimum
        m.addConstr(quicksum(is_min_vars) == 1)

        ########## Create fabric count constraints ##########
        if fabric_count_min is not None or fabric_count_max is not None:
            fabric_count = m.addVar(name="fabric_count", lb=0, ub=self.nfabrics) # lb=1 is somehow wrong
            m.addConstr(fabric_count == quicksum(edge_vars[edge] for edge in self.edges))
            if fabric_count_min is not None:
                m.addConstr(fabric_count >= fabric_count_min)
            if fabric_count_max is not None:
                m.addConstr(fabric_count <= fabric_count_max)

        ########## Create common constraints ##########
        # 1. Total length should be within threshold
        m.addConstr(total_length >= target_L)
        m.addConstr(total_length <= target_L + threshold) # TODO: maybe this constraint is not necessary
        # 2. Can't use multiple edges from same rectangle
        for fabric in set([edge.p for edge in self.edges]):
            m.addConstr(edge_vars[fabric.e1] + edge_vars[fabric.e2] <= 1)

        ########## Create wasted area objective ##########
        wasted_area = quicksum((edge.get_other_dim() - 2 * sa - min_thickness) * edge.length() * edge_vars[edge] for edge in self.edges)
        # Add absolute deviation and constraints
        abs_deviation = m.addVar(name="abs_deviation", lb=0, ub=threshold)
        m.addConstr(abs_deviation >= total_length - target_L)
        m.addConstr(abs_deviation >= target_L - total_length)
        m.setObjective(wasted_area + abs_deviation * min_thickness, GRB.MINIMIZE)

        # Print out the gurobi model for debugging
        if not suppress_output:
            print("Gurobi model:")
            print(m.getConstrs())
            print(m.getVars())
            print(m.getObjective())
            print("target_L:", target_L)
            print("threshold:", threshold)

        # Collection to store solutions by their sums
        solution_sums = {}

        # Callback function to collect solutions
        def solution_callback(model, where):
            if where == GRB.Callback.MIPSOL:
                # Get current solution - this works in callbacks even if model status is LOADED
                var_values = model.cbGetSolution(list(edge_vars.values()))
                vars_list = list(edge_vars.values())

                # Build solution set and calculate sum
                solution = set()
                sol_sum = 0
                for var, val in zip(vars_list, var_values):
                    if val > 0.5:  # Binary variable is 1
                        edge = edges_by_var[var]
                        solution.add(edge)
                        sol_sum += edge.length()

                # if min_thickness is wrong, don't add the solution
                if min_thickness is not None:
                    min_thickness_val = model.cbGetSolution(min_thickness)
                    shortest_side = min([edge.get_other_dim() for edge in solution])
                    if round(min_thickness_val) != (shortest_side):
                        print(f"warning: min thickness is wrong for sol#{sum([len(sol) for sol in solution_sums.values()])}")
                        print(f"min thickness: {min_thickness_val}")
                        print(f"shortest side: {shortest_side}")
                        # Add constraint to find different solutions
                        # model.cbLazy(quicksum(edge_vars[edge] for edge in solution) <= len(solution) - 1)
                        return

                # Add to solution_sums if not already present
                solution_frozen = frozenset(solution)
                if sol_sum not in solution_sums:
                    solution_sums[sol_sum] = set()
                if solution_frozen not in solution_sums[sol_sum]:
                    solution_sums[sol_sum].add(solution_frozen)
                    if not suppress_output:
                        print(f"Found solution with sum {sol_sum}")
                # Check if we've found enough solutions
                total_solutions = sum([len(sol) for sol in solution_sums.values()])
                if total_solutions >= solution_limit:
                    if not suppress_output:
                        print(f"Found {total_solutions} solutions, terminating")
                    model.terminate()

                # Add constraint to ensure at least one edge is different from this solution
                # For each edge in the solution, we need at least one to be 0
                # For each edge not in the solution, we need at least one to be 1
                model.cbLazy(quicksum(1 - edge_vars[edge] for edge in solution) + 
                             quicksum(edge_vars[edge] for edge in set(self.edges) - solution) >= 1)

        # Set the callback
        m.setParam(GRB.Param.LazyConstraints, 1)

        # Optimize
        m.optimize(solution_callback)

        # Return all solutions found
        if len(solution_sums) > 0:
            nsolutions = 0
            solutions_to_return = []
            for best_sum in sorted(solution_sums.keys(), key=lambda x: abs(target_L - x)):
                best_sum_subset = solution_sums[best_sum]
                solutions_to_return.append((best_sum, best_sum_subset))
                nsolutions += len(best_sum_subset)
            if not suppress_output:
                print(f"returning {nsolutions} total #solutions")
            return solutions_to_return

        if not suppress_output:
            print("No solutions found")
        return [(0, [])]

    def update_precomputed(self):
        """Update all precomputed values based on the current edges in the bin."""
        # Update sibling edges
        self.sibling_edges = [e.s for e in self.edges]

        # Update fabric count and length ranges
        fabrics = set([e.p for e in self.edges])
        self.nfabrics = len(fabrics)
        if fabrics:
            self.max_length = sum([max(f.e1.length(), f.e2.length()) for f in fabrics])
            self.min_length = min([min(f.e1.length(), f.e2.length()) for f in fabrics])
        else:
            self.max_length = 0
            self.min_length = 0

        # Update Wij matrix
        self.Wmat = {}
        for i in range(len(self.edges)):
            for j in range(len(self.edges)):
                self.Wmat[i, j] = 1 if self.edges[i].length() <= self.edges[j].length() else 0

        # Update edge pairs and color differences
        self.edge_pairs = []
        self.color_diffs = {}
        self.value_diffs = {}
        self.hue_diffs = {}
        for i, edge_i in enumerate(self.edges):
            for j, edge_j in enumerate(self.edges[i+1:], i+1):
                if edge_i.p != edge_j.p:  # Don't compute for edges from same fabric
                    self.edge_pairs.append((edge_i, edge_j))
                    # Compute color differences (CIE1994)
                    self.color_diffs[(edge_i, edge_j)] = color_distance(edge_i.p.color, edge_j.p.color, "CIE1994")
                    # Value differences
                    self.value_diffs[(edge_i, edge_j)] = color_distance(edge_i.p.dominant_color, edge_j.p.dominant_color, "value")
                    # Hue differences
                    self.hue_diffs[(edge_i, edge_j)] = color_distance(edge_i.p.dominant_color, edge_j.p.dominant_color, "hue")
                else:
                    self.color_diffs[(edge_i, edge_j)] = 0
                    self.value_diffs[(edge_i, edge_j)] = 0
                    self.hue_diffs[(edge_i, edge_j)] = 0

class FabricBins:
    def __init__(self, fabric_images, n=10, min_size=None, max_size=None, sa=None):
        self.fabric_list = [Fabric(image, sa=sa) for image in fabric_images]
        self.create_bins(n=n, min_size=min_size, max_size=max_size)

    def to_json(self):
        return [{
            'id': bin.id,
            'name': bin.name,
            'nfabrics': len(set([e.p for e in bin.edges]))
        } for bin in self.bins]

    def to_bins_data(self):
        return [bin.to_json() for bin in self.bins]

    def can_merge(self):
        # default to merge if more than 3 bins (used to be 1)
        return len(self.bins) > 3

    def merge_bins(self):
        new_bins = []
        FabricBin.id = 0
        for i in range(len(self.bins)):
            if i % 2 == 0:
                if len(self.bins) > i + 1:
                    new_edges = self.bins[i].edges + self.bins[i+1].edges
                    new_bins.append(FabricBin(new_edges))
                else:
                    new_bins.append(self.bins[i])
        print(f"Merged {len(self.bins)} bins into {len(new_bins)} bins")
        self.bins = new_bins

    def create_bins(self, n=10, min_size=None, max_size=None):
        edges = [f.e1 for f in self.fabric_list] + [f.e2 for f in self.fabric_list]
        edge_lengths = [e.length() for e in edges]
        min_len = min(edge_lengths)
        if min_size is not None:
            min_len = min_size
        max_len = max(edge_lengths)
        if max_size is not None:
            max_len = max_size
        length_ranges = np.linspace(min_len, max_len, n + 1)
        bins = {i : [] for i in range(n)}
        for edge in edges:
            for i in range(n):
                if length_ranges[i] <= edge.length() <= length_ranges[i+1]:
                    bins[i].append(edge)
                    break
        self.bins = [FabricBin(bins[i]) for i in range(n) if len(bins[i]) > 0]

    def select_bins(self, target_L, threshold, bin_filter=None):
        valid_bins = [bin for bin in self.bins if bin.can_afford(target_L, threshold)]
        if not isinstance(self, UserFabricBins): # user fabric bins only allow users to manually merge
            while not valid_bins and self.can_merge():
                self.merge_bins()
                valid_bins = [bin for bin in self.bins if bin.can_afford(target_L, threshold)]
        if not valid_bins:
            print("No bins valid for the target length found")
            return None
        selected_bins = None
        if bin_filter is not None:
            selected_bins = [bin for bin in valid_bins if bin_filter.validates(bin)]
        else:
            selected_bins = valid_bins
        if not selected_bins:
            print("No bins found that satisfy the filter")
            return None
        return selected_bins

# Supporting ColorBin class for storing the color range
class ColorFabricBin(FabricBin):
    def __init__(self, edges, hue_range, fbid=None):
        super().__init__(edges, fbid=fbid)
        self.hue_range = hue_range

    def contains_color(self, color):
        # color is a tuple of RGB values
        hue, _, _ = colorsys.rgb_to_hsv(*color)
        return self.hue_range[0] <= hue < self.hue_range[1]

class ColorFabricBins(FabricBins):
    def __init__(self, fabric_images, n=10, min_hue=None, max_hue=None, sa=None):
        self.fabric_list = [Fabric(image, sa=sa) for image in fabric_images]
        self.create_bins(n=n, min_hue=min_hue, max_hue=max_hue)

    def merge_bins(self):
        new_bins = []
        FabricBin.id = 0
        for i in range(len(self.bins)):
            if i % 2 == 0:
                if len(self.bins) > i + 1:
                    new_edges = self.bins[i].edges + self.bins[i+1].edges
                    new_hue_range = (self.bins[i].hue_range[0], self.bins[i+1].hue_range[1])
                    new_bins.append(ColorFabricBin(new_edges, new_hue_range))
                else:
                    new_bins.append(self.bins[i])
        self.bins = new_bins

    def create_bins(self, n=10, min_hue=None, max_hue=None):
        # Set up hue ranges based on the color wheel
        hues = [colorsys.rgb_to_hsv(*f.color)[0] for f in self.fabric_list]
        if min_hue is None:
            min_hue = min(hues)
        if max_hue is None:
            max_hue = max(hues)
        hue_ranges = np.linspace(min_hue, max_hue, n + 1)
        bins = {i: [] for i in range(n)}
        for f, hue in zip(self.fabric_list, hues):
            for i in range(n):
                if hue_ranges[i] <= hue <= hue_ranges[i + 1]:
                    bins[i].append(f.e1)
                    bins[i].append(f.e2)
                    break
        FabricBin.id = 0
        self.bins = [ColorFabricBin(bins[i], (hue_ranges[i], hue_ranges[i + 1])) for i in range(n) if bins[i]]

    def select_bins(self, target_L, threshold, desired_color=None, bin_filter=None):
        valid_bins = [bin for bin in self.bins if bin.can_afford(target_L, threshold)]
        while not valid_bins and self.can_merge():
            self.merge_bins()
            valid_bins = [bin for bin in self.bins if bin.can_afford(target_L, threshold)]
        if not valid_bins:
            print("No bins valid for the target length found")
            return None
        selected_bins = None
        if bin_filter is not None:
            selected_bins = [bin for bin in valid_bins if bin_filter.validates(bin)]
        else:
            selected_bins = valid_bins
        if not selected_bins:
            print("No bins found that satisfy the filter")
            return None
        if desired_color is not None:
            selected_bins = [bin for bin in selected_bins if bin.contains_color(desired_color)]
        if not selected_bins:
            print("No bins found that contain the desired color")
            return None
        return selected_bins

# Supporting UserBin class for storing user-created bins
class UserFabricBins(FabricBins):
    def __init__(self, public_folder, bins, sa=None, high_res_fabrics=None):
        if high_res_fabrics is not None:
            self.create_bins_for_high_res(bins, sa, high_res_fabrics)
        else:
            self.create_bins(public_folder, bins, sa)
        self.bins_merged = False
        # HACK: this is a hack for fabrics that are completely removed from the bin
        # self.removed_fabrics = {}

    def create_bin_from_fabrics(self, fabric_in_bin, name=None):
        if len(fabric_in_bin) == 0:
            print("No fabrics to create bin from")
            return
        if has_gurobi():
            edges = [f.e1 for f in fabric_in_bin] + [f.e2 for f in fabric_in_bin]
            self.bins.append(FabricBin(edges, name=name))
        else:
            nbins = 1
            nfabrics = len(fabric_in_bin)
            while nbins * 10 < nfabrics:
                nbins += 1
            for i in range(nbins):
                start_idx = i * (nfabrics // nbins)
                end_idx = (i + 1) * (nfabrics // nbins)
                if i == nbins - 1:
                    end_idx = nfabrics
                edges = [f.e1 for f in fabric_in_bin[start_idx:end_idx]] + [f.e2 for f in fabric_in_bin[start_idx:end_idx]]
                self.bins.append(FabricBin(edges, name=f"{name} - {i+1}" if name else None))

    def create_bins_for_high_res(self, input_bins, sa, high_res_fabrics):
        FabricBin.id = 0
        self.bins = []
        high_res_fabric_map = {f['id']: f for f in high_res_fabrics}
        for bin in input_bins:
            # newer version: bin is {id: .., name: .., fabrics: [...]}
            if 'fabrics' in bin:
                fabricjson_in_bin = [high_res_fabric_map[f['id']] for f in bin['fabrics']]
                fabric_in_bin = [Fabric(f['img'], sa=sa, fid=f['id'], image_path=f['image']) for f in fabricjson_in_bin]
                self.create_bin_from_fabrics(fabric_in_bin, name=bin['name'])
            # the bin is a list of dictionaries each representing a fabric
            else:
                fabricjson_in_bin = [high_res_fabric_map[f['id']] for f in bin]
                fabric_in_bin = [Fabric(f['img'], sa=sa, fid=f['id'], image_path=f['image']) for f in fabricjson_in_bin]
                self.create_bin_from_fabrics(fabric_in_bin)

    def create_bins(self, public_folder, bins, sa=None):
        FabricBin.id = 0
        self.bins = []
        for bin in bins:
            # the bin is a list of dictionaries each representing a fabric
            fabric_in_bin = []
            if 'fabrics' in bin:
                fabrics = bin['fabrics']
                name = bin['name']
            else:
                fabrics = bin
                name = None
            for f in fabrics:
                img = None
                image_path = os.path.join(public_folder, f['image'])
                high_res_image_path = image_path.replace('_resized', '').replace('_tiny', '')
                if not os.path.exists(high_res_image_path):
                    print(f"High res image {high_res_image_path} does not exist!")
                    high_res_image_path = None
                if 'img' not in f:
                    if os.path.exists(image_path):
                        img = open_image(image_path)
                    else:
                        print(f"Image {image_path} does not exist!")
                else:
                    img = f['img']
                fabric_in_bin.append(Fabric(img, sa=sa, fid=f['id'], image_path=f['image'], high_res_image_path=high_res_image_path))
            self.create_bin_from_fabrics(fabric_in_bin, name=name)

    def merge_bins(self):
        new_bins = []
        FabricBin.id = 0
        for i in range(len(self.bins)):
            if i % 2 == 0:
                if len(self.bins) > i + 1:
                    new_edges = self.bins[i].edges + self.bins[i+1].edges
                    new_bins.append(FabricBin(new_edges, name=f"{self.bins[i].name} + {self.bins[i+1].name}"))
                else:
                    new_bins.append(self.bins[i])
        print(f"Merged {len(self.bins)} bins into {len(new_bins)} bins")
        self.bins = new_bins
        self.bins_merged = True

    def create_from_option(self, option):
        # this method creates a new option using the mapped edges instead of old edges that might be low-res
        fabric_map = self.to_fabric_map()
        mapped_edges = []
        for edge in option.edge_subset:
            mapped_fabric = None
            try:
                mapped_fabric = fabric_map[edge.p.id]
            except Exception as e:
                print(f"edge not in fabric_map: {edge}")
                print(f"Error creating new option from option {option.index}: {e}")
                print(f"Edge subset: {option.edge_subset}")
                print(f"Fabric map: {fabric_map}")
                raise e
                # HACK: this is a hack for fabrics that are completely removed from the bin
                # mapped_fabric = self.removed_fabrics[edge.p.id]
                # print("HACKING BY REUSING USED FABRICS")
            if edge.is_e1:
                mapped_edges.append(mapped_fabric.e1)
            else:
                mapped_edges.append(mapped_fabric.e2)
        other_dims = [(edge.get_other_dim() - 50) for edge in mapped_edges]
        shortest_side = min(other_dims)
        total_area = sum([(edge.length() + 50) * (edge.s.length() + 50) for edge in mapped_edges])
        wasted_area = sum([(edge.length() * (edge.s.length() - shortest_side)) for edge in mapped_edges])
        return PackingOption(option.index, mapped_edges, other_dims, shortest_side, total_area, wasted_area, shortest_side_px=shortest_side+50)

    def remove_fabric(self, removed_fabric_id):
        removed = False
        removed_fabric = None
        new_bins = []
        for bin in self.bins:
            new_edges = [edge for edge in bin.edges if edge.p.id != removed_fabric_id]
            if len(new_edges) < len(bin.edges):
                removed = True
                removed_fabric = [edge.p for edge in bin.edges if edge.p.id == removed_fabric_id][0]
            if new_edges:
                new_bins.append(FabricBin(new_edges, fbid=bin.id, name=bin.name))
        self.bins = new_bins
        if not removed:
            return removed, None
        if removed_fabric.high_res_image_size is not None:
            return removed, removed_fabric.high_res_image_size
        else:
            return removed, removed_fabric.image.size

    def update_fabrics(self, used_option, trimming_records, sa=0):
        """
        Update fabrics that were used in a packing option and process trimmed fabrics.
        
        Args:
            used_option (PackingOption): The packing option containing the used edges
            trimming_records (list): List of dicts containing trimming information
                Each record has:
                - fabric_id: ID of the trimmed fabric
                - original_image: Original PIL Image
                - trimmed_image: Trimmed PIL Image
            sa (int): Seam allowance to apply
        """
        # Get the set of fabric IDs that were used
        used_fabric_ids = {edge.p.id for edge in used_option.edge_subset}
        # HACK: this is a hack for fabrics that are completely removed from the bin
        # current_fabric_map = self.to_fabric_map()
        # for removed_fabric_id in used_fabric_ids:
        #     if removed_fabric_id in current_fabric_map:
        #         self.removed_fabrics[removed_fabric_id] = current_fabric_map[removed_fabric_id]

        # Create a map of trimming records by fabric ID
        trimming_map = {}
        for record in trimming_records:
            if record['fabric_id'] not in trimming_map:
                trimming_map[record['fabric_id']] = [record]
            else:
                trimming_map[record['fabric_id']].append(record)

        max_fabric_id = max(list(self.to_fabric_map().keys()))
        Fabric.id = max_fabric_id + 1

        # Update the fabric and the bin
        for bin in self.bins:
            bin.edges = [edge for edge in bin.edges if (edge.p.id not in used_fabric_ids or edge.p.id in trimming_map)]
            # Get unique fabrics from the bin's edges
            fabrics_in_bin = {edge.p for edge in bin.edges}
            for fabric in fabrics_in_bin:
                # If fabric was trimmed, update it
                if fabric.id in trimming_map:
                    records = trimming_map[fabric.id]
                    # Update the fabric with trimmed image
                    fabric.update_after_trimming(
                        base64_to_pil_image(records[0]['trimmed_image']),
                        sa=sa,
                        high_res_image_size=records[0]['trimmed_image_high_res_size'])
                    if len(records) > 1:
                        print(f"Warning: multiple trimming records for fabric {fabric.id}")
                        for record in records[1:]:
                            new_fabric = copy.deepcopy(fabric)
                            new_fabric.id = Fabric.id
                            Fabric.id += 1
                            new_fabric.update_after_trimming(
                                base64_to_pil_image(record['trimmed_image']),
                                sa=sa,
                                high_res_image_size=record['trimmed_image_high_res_size'])
                            bin.edges.append(new_fabric.e1)
                            bin.edges.append(new_fabric.e2)
            bin.update_precomputed()

    def to_id_fabric_map(self, bin_filter=None):
        # construct the mapping from fabric ids to fabric images
        fabric_map = {}
        for bin in self.bins:
            if bin_filter is not None and not bin_filter.validates(bin):
                continue
            for edge in bin.edges:
                fabric_map[edge.p.id] = edge.p.image
        return fabric_map

    def to_fabric_map(self, bin_filter=None):
        fabric_map = {}
        for bin in self.bins:
            if bin_filter is not None and not bin_filter.validates(bin):
                continue
            for edge in bin.edges:
                fabric_map[edge.p.id] = edge.p
        return fabric_map

    def update_bins(self, new_bins):
        """
        Update the bins with new binning data while preserving trimmed fabrics.
        
        Args:
            new_bins (list): List of new bin configurations
        """
        # Create new bins with updated fabrics
        FabricBin.id = 0
        current_fabrics = self.to_fabric_map()
        self.bins = []
        for bin in new_bins:
            fabric_in_bin = []
            for f in bin['fabrics']:
                fabric_id = f['id']
                # HACK: this is a hack for fabrics that are completely removed from the bin
                # if fabric_id not in current_fabrics:
                #     print('the new bins should be existing fabrics shifted around, not introducing any new fabrics')
                #     print(f)
                #     if fabric_id in self.removed_fabrics:
                #         print('HACKING BY REUSING USED FABRICS')
                #         fabric_in_bin.append(self.removed_fabrics[fabric_id])
                #     continue
                assert fabric_id in current_fabrics, 'the new bins should be existing fabrics shifted around, not introducing any new fabrics'
                fabric_in_bin.append(current_fabrics[fabric_id])
            self.create_bin_from_fabrics(fabric_in_bin, name=bin['name'])
