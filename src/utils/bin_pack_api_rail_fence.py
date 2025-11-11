from src.utils.pack import *
from src.utils.bins import Fabric, FabricBins, ColorFabricBins
from src.utils.config import *
from src.utils.filters import *
from src.utils.plot import pil_image_to_base64
import dill as pickle
import threading

file_operation_lock = threading.Lock()

def compute_thickness_constraints(iter, config):
    # we should use high_res lengths for thickness constraints
    thickness_min = None
    thickness_max = None
    if config.strategy == 'rail-fence':
        if iter == 10:
            # For iter 10, limit thickness to be at most the top length
            thickness_max = config.target_L_high_res['top']
            print(f"Applying thickness constraint for iter 10: max={thickness_max}")
        elif iter == 11:
            # For iter 11, limit thickness to be at most the difference between top+bottom and current block34 height
            if hasattr(config, 'block34_high_res_size') and config.block34_high_res_size is not None:
                thickness_max = config.target_L_high_res['top'] + config.target_L_high_res['bottom'] - config.block34_high_res_size[0]
                print(f"Applying thickness constraint for iter 11: max={thickness_max}")
        elif iter == 12:
            # For iter 12, limit thickness to be between a minimum value and the top length
            if hasattr(config, 'block34_high_res_size') and config.block34_high_res_size is not None:
                thickness_min = config.target_L_high_res['top'] + config.target_L_high_res['bottom'] - config.block34_high_res_size[0]
                thickness_max = config.target_L_high_res['top']
                print(f"Applying thickness constraint for iter 12: min={thickness_min}, max={thickness_max}")
    return thickness_min, thickness_max

def next_packing_options(packed_fabric, fabrics, iter,
                         bin_filter=None, option_filter=None, option_rank=None,
                         bins=None, config=PackingConfig(),
                         thickness_min=None, thickness_max=None,
                         fabric_count_min=None, fabric_count_max=None):
    """
    Given a list of remaining scrap fabrics, return the next packing options.

    The first three arguments should be stored locally in the server session using flask.
        packed_fabric: the current packing result as an image
        fabrics: the remaining scrap fabrics as a list of images (or potentially other identifiers)
        iter: the current iteration (needed to generate the right options w.r.t. the strategy)
    The other arguments should come from front-end user preferences.
        bin_filter: a filter to select bins (e.g., must have a certain fabric, etc.)
        option_filter: a filter to select options (e.g., a range of desired strip thickness, etc.)
        option_rank: a ranking method to sort the options (e.g., by thickness, wasted area, etc.)
        config: the packing configuration (user selects the packing strategy)
        thickness_min: minimum thickness constraint for the strip
        thickness_max: maximum thickness constraint for the strip
        fabric_count_min: minimum number of fabrics to use
        fabric_count_max: maximum number of fabrics to use
    """

    if fabrics is None or (len(fabrics) == 0 and bins is None):
        print("No more fabrics")
        return []

    if config.strategy == 'rail-fence' and iter == 12:
        print('Rail-fence strategy is done after 12 iterations. Exiting...')
        return []

    fb = bins
    if fb is None:
        Fabric.id = 0
        fb = ColorFabricBins(fabrics, sa=config.sa) if config.use_color_bins else FabricBins(fabrics, sa=config.sa)

    # always use high-res target sum for bin selection and edge set generation
    _, target_L = get_fabric_shape(packed_fabric, iter, config)
    _, target_L_high_res = get_fabric_shape(packed_fabric, iter, config, is_high_res=True)
    target_sum_high_res = target_L_high_res - 50

    # select bins based on filters and target length
    selected_bins = None
    if config.use_color_bins:
        selected_bins = fb.select_bins(target_sum_high_res, config.threshold, config.desired_color, bin_filter)
    else:
        selected_bins = fb.select_bins(target_sum_high_res, config.threshold, bin_filter)
    if selected_bins is None:
        print('No valid bins found. Exiting...')
        return []

    max_time_limit = min(30, int(60 / len(selected_bins)))

    # Define thickness constraints for rail-fence iterations 10, 11, 12
    if thickness_min is None or thickness_max is None:
        thickness_min, thickness_max = compute_thickness_constraints(iter, config)

    # Pass thickness and fabric count constraints to find_best_subsets
    best_sum_subsets = [res for bin in selected_bins 
                            for res in bin.find_best_subsets(target_sum_high_res, 100, sa=25,
                                                             time_limit=max_time_limit,
                                                             thickness_min=thickness_min,
                                                             thickness_max=thickness_max,
                                                             fabric_count_min=fabric_count_min,
                                                             fabric_count_max=fabric_count_max)]
    best_sum_subsets.sort(key=lambda item: abs(item[0] - target_sum_high_res))
    all_edge_subsets = [edge_subset for (best_sum, best_sum_subset) in best_sum_subsets 
                        for edge_subset in best_sum_subset 
                        if best_sum >= target_sum_high_res]

    # If no valid subsets found, use any available subsets
    if len(all_edge_subsets) == 0:
        print("No target length satisfying edge subsets found")
        if config.strategy == 'rail-fence':
            all_edge_subsets = [edge_subset for (_, best_sum_subset) in best_sum_subsets for edge_subset in best_sum_subset]
        if len(all_edge_subsets) == 0:
            print('No valid subsets found. Exiting...')
            return []

    # use the filter to filter and the ranking method to rank the edge_subsets
    # the options here are not high res for display purposes
    no_filter = option_filter is None
    all_options = []
    grouped_check_dups = {}
    for i, edge_subset in enumerate(all_edge_subsets):
        the_other_dimensions = [edge.get_other_dim(use_high_res=False) - 2 * config.sa for edge in edge_subset]
        shortest_side = min(the_other_dimensions)
        filter_passed = (not no_filter) and option_filter.validates(shortest_side)
        if shortest_side not in grouped_check_dups:
            grouped_check_dups[shortest_side] = set()
        edge_lengths = frozenset([edge.length(use_high_res=False) for edge in edge_subset])
        if (no_filter or filter_passed) and edge_lengths not in grouped_check_dups[shortest_side]:
            wasted_area = 0
            for edge, other_dim in zip(edge_subset, the_other_dimensions):
                remaining_length = other_dim - shortest_side
                if remaining_length < config.min_scrap_size or edge.length(use_high_res=False) < config.min_scrap_size:
                    wasted_area += remaining_length * (edge.length(use_high_res=False) + 2 * config.sa)
            sum_edge_lengths_diff = sum([edge.length(use_high_res=False) for edge in edge_subset]) - target_L + 2 * config.sa
            if sum_edge_lengths_diff > 0:
                wasted_area += sum_edge_lengths_diff * (shortest_side + 4 * config.sa)
            elif sum_edge_lengths_diff < 0:
                print(f"[Wasted Area Debug] Iteration {iter}")
                print(f"sum_edge_lengths_diff (low res) negative: {sum_edge_lengths_diff}")
                print(f"edge_subset: {edge_subset}")
                print(f"target_L: {target_L}")
                print(f"edge_lengths: {edge_lengths}")
                print(f"shortest_side: {shortest_side}")
                print(f"wasted_area: {wasted_area}")
                print(f"[END]")
            total_area = sum([(edge.length(use_high_res=False) + 2 * config.sa) * (edge.s.length(use_high_res=False) + 2 * config.sa) for edge in edge_subset])
            the_other_dimensions_high_res_px = [edge.get_other_dim() for edge in edge_subset]
            shortest_side_px = min(the_other_dimensions_high_res_px)
            all_options.append(PackingOption(i, edge_subset, the_other_dimensions, shortest_side, total_area, wasted_area, shortest_side_px=shortest_side_px))
            grouped_check_dups[shortest_side].add(edge_lengths)
    if option_rank is None: # default to wasted area rank
        option_rank = WastedAreaRank()
    ranked_options = sorted(all_options, key=lambda option: option_rank.compute_rank(option))
    return ranked_options

def option_to_strip(packed_fabric, sorted_fabrics, option, iter, bins, config, option_display=False, use_high_res=False):
    """
    Helper function to process each strip. (Rail Fence version)
    """
    new_edge_images = []
    new_edge_shapes = []
    trimmed_images = []
    trimming_records = []
    fabric_details = []

    # reset option's wasted area if it's high res because we'll need to recompute
    if use_high_res:
        option.wasted_area = 0
        option.total_area = sum([(edge.length(use_high_res=False) + 50) * (edge.s.length(use_high_res=False) + 50) for edge in option.edge_subset])

    curr_fabric_shape, target_L = get_fabric_shape(packed_fabric, iter, config)
    curr_fabric_shape_high_res, target_L_high_res = get_fabric_shape(packed_fabric, iter, config, is_high_res=True)
    # these two also the same in the high_res reconstruction case
    other_dim_high_res = [(edge.get_other_dim() - 50) for edge in option.edge_subset]
    shortest_side_high_res = min(other_dim_high_res)
    # if not option_display:
    #     print(f"\n[High-Res Debug] Iteration {iter}")
    #     print(f"Current fabric shape: {curr_fabric_shape}")
    #     print(f"Current fabric shape high-res: {curr_fabric_shape_high_res}")
    #     print(f"Target L high-res: {target_L_high_res}")
    #     print(f"Shortest side high-res: {shortest_side_high_res}")
    other_dims = other_dim_high_res if use_high_res else option.other_dims
    shortest_side = shortest_side_high_res if use_high_res else option.shortest_side
    if use_high_res:
        target_L = target_L_high_res

    top_left_corner = top_left(curr_fabric_shape, iter, config.strategy, shortest_side, sa=config.sa)
    strip_shape = ImageShape(top_left_corner[0], top_left_corner[1], 0, 0)
    length_to_keep_high_res = shortest_side_high_res + 50
    length_to_keep = shortest_side + 2 * config.sa

    # then pick out these images and set the image shapes and rotations accordingly
    fabric_mapping = {} if bins is None else bins.to_id_fabric_map()
    total_length = 0
    for op_index, (edge, other_dim) in enumerate(zip(option.edge_subset, other_dims)):
        fabric_image = sorted_fabrics[edge.p.id] if bins is None else fabric_mapping[edge.p.id]
        w, h = fabric_image.size
        fabric_detail = {
            'order': op_index + 1,
            'fabric_id': edge.p.id,
            'image': fabric_image,
            'original_size': (w, h),
            'length': edge.length(use_high_res=use_high_res),
            'other_dim': other_dim,
            'needs_trimming': other_dim - shortest_side > config.min_scrap_size
        }
        total_length += fabric_detail['length']
        image_shape = shifted_top_left(top_left_corner, shortest_side, other_dim, w, h, iter, config.strategy, sa=config.sa)
        # Use high-res dimensions for rotation check if available
        high_res_w, high_res_h = edge.p.high_res_image_size if edge.p.high_res_image_size is not None else (w, h)
        rotated = rotate_image_shape(high_res_w, high_res_h, image_shape, edge.length(), iter, config.strategy, sa=config.sa, use_high_res=True)
        fabric_detail['rotated'] = rotated
        # we actually need to trim the fabrics to correctly display seams
        image_to_append = trim_image_in_strip(fabric_image.copy(), op_index, len(option.edge_subset),
                                              rotated, iter, config.strategy, sa=config.sa)
        image_shape.w = image_to_append.size[0]
        image_shape.h = image_to_append.size[1]
        new_edge_images.append(image_to_append)
        new_edge_shapes.append(image_shape)
        top_left_corner = next_top_left(op_index, top_left_corner, edge.length(use_high_res=use_high_res), iter, config.strategy, sa=config.sa)
        # and make the trimmed off parts as the new images
        if fabric_detail['needs_trimming']:
            trimmed_image, _ = trim_image(fabric_image.copy(), length_to_keep + 2 * config.sa, rotated, w, h, iter, config.strategy)
            high_res_image_size = fabric_image.size if edge.p.high_res_image_size is None else edge.p.high_res_image_size
            trimmed_image_high_res_size = trim_image_high_res(high_res_image_size, length_to_keep_high_res + 50, rotated, iter, config.strategy)
            # if not option_display:
            #     print(f'{edge} needs trimming - ')
            #     print(f'\tTrimmed fabric size: {trimmed_image.size if trimmed_image else None}')
            #     print(f'\tHigh res trimmed size: {trimmed_image_high_res_size}')
            #     print(f'\tOriginal fabric size: {fabric_detail["original_size"]}')
            if trimmed_image is not None:
                fabric_detail['trimmed_image'] = pil_image_to_base64(trimmed_image)
                fabric_detail['trim_line'] = shortest_side
                trimming_records.append({
                    'original_image': pil_image_to_base64(fabric_image),
                    'trimmed_image': pil_image_to_base64(trimmed_image),
                    'fabric_id': edge.p.id,
                    'trimmed_image_high_res_size': trimmed_image_high_res_size
                })
                trimmed_images.append(trimmed_image)
        if use_high_res:
            if other_dim - shortest_side <= config.min_scrap_size:
                option.wasted_area += (fabric_detail['length'] + 50) * (other_dim - shortest_side)
        fabric_details.append(fabric_detail)

    # check current strip image
    homed_image_shapes = home_image_shapes(new_edge_shapes)
    curr_strip = composite_images(new_edge_images, homed_image_shapes, suppress_output=True, alpha=128)

    strip_image = None
    # need to keep additional seam allowance for rail-fence iter 0 and iter 6
    if packed_fabric is None or (iter in [0, 6] and config.strategy == 'rail-fence'):
        strip_image = crop_curr_strip(length_to_keep + config.sa, curr_strip, iter, config.strategy, sa=config.sa)
    else:
        strip_image = crop_curr_strip(length_to_keep, curr_strip, iter, config.strategy, sa=config.sa)

    trimmed_strip = trim_curr_image(target_L, strip_image, iter, config.strategy, sa=config.sa) # +2 * sa needed or no?
    if trimmed_strip is not None:
        if trimmed_strip.size[0] > config.min_scrap_size and trimmed_strip.size[1] > config.min_scrap_size:
            trimmed_images.append(trimmed_strip)
            last_edge = option.edge_subset[-1]
            fid = last_edge.p.id
            original_image = sorted_fabrics[fid] if bins is None else fabric_mapping[fid]
            high_res_image_size = original_image.size if last_edge.p.high_res_image_size is None else last_edge.p.high_res_image_size
            trimmed_image_high_res_size = trim_curr_image_high_res(high_res_image_size, target_L, fabric_details[-1]['rotated'], iter, config.strategy)
            # if not option_display:
            #     print(f'{last_edge} needs trimming - ')
            #     print(f'\tOriginal fabric size: {original_image.size}')
            #     print(f'\tTrimmed strip size: {trimmed_strip.size}')
            #     print(f'\tlength to keep in the strip: {target_L}')
            #     print(f'\tHigh res trimmed size: {trimmed_image_high_res_size}')
            trimming_records.append({
                'original_image': pil_image_to_base64(original_image),
                'trimmed_image': pil_image_to_base64(trimmed_strip),
                'fabric_id': fid,
                'trimmed_image_high_res_size': trimmed_image_high_res_size
            })
        else:
            if use_high_res:
                option.wasted_area += (total_length + 50 - target_L) * (shortest_side + 100)

    if option_display: # for front-end display
        return new_edge_images, homed_image_shapes, strip_image
    else: # for actual packing with this strip option
        after_crop, before_crop = None, None
        if len(option.edge_subset) > 1:
            after_crop, before_crop = crop_curr_strip(length_to_keep + config.sa, curr_strip, iter, config.strategy, sa=config.sa, should_draw_crop_line=True)
            if before_crop and after_crop.size == before_crop.size: before_crop = None
        else:
            after_crop = crop_curr_strip(length_to_keep + config.sa, curr_strip, iter, config.strategy, sa=config.sa)
        after_crop = draw_seam_lines(after_crop, seam_allowance=config.sa)
        return trimmed_images, trimming_records, fabric_details, strip_image, before_crop, after_crop, strip_shape, curr_fabric_shape, target_L

def option_to_strip_image(packed_fabric, sorted_fabrics, option, iter, bins=None, config=PackingConfig(),
                          should_save=False, session_id=None, save_folder=None, pickle_folder=None, use_high_res=False):
    """
    Convert a packing option to a strip image for display.

    Args:
        packed_fabric: Current packed fabric
        sorted_fabrics: List of fabrics to pack
        option: Selected packing option
        iter: Current iteration
        bins: Optional bins for fabric selection
        config: Packing configuration
        should_save: Whether to save the result
        session_id: Session ID for saving
        save_folder: Folder to save results
        pickle_folder: Folder to save pickle files
        use_high_res: Whether to use high-res images
    """
    # Always use low-res for display but compute high-res dimensions for storage
    new_edge_images, homed_image_shapes, curr_strip = option_to_strip(
        packed_fabric, sorted_fabrics, option, iter, bins, config, option_display=True, use_high_res=use_high_res)

    if should_save:
        assert save_folder
        images_data = [{
            'color': [int(number) for number in list(np.array(im).mean(axis=(0, 1)))],
            'box_xywh': imshape.box(),
            'id': edge.p.id
        } for im, imshape, edge in zip(new_edge_images, homed_image_shapes, option.edge_subset)]
        strip_image_path = f'iter_{iter}_strip_{option.index}.png'
        with file_operation_lock:
            with open(os.path.join(save_folder, strip_image_path), 'wb') as f:
                curr_strip.save(f, format='PNG')
        strip_data = {
            'strip_image': os.path.join(session_id[:10], strip_image_path),
            'wasted_area': option.wasted_area / config.dpi ** 2,
            'thickness': option.shortest_side,
            'thickness_px': option.shortest_side_px,
            'images_data': images_data,
        }
        if session_id is not None and pickle_folder is not None:
            assert session_id and pickle_folder
            option_pickle_path = f'iter_{iter}_option_{option.index}.pkl'
            with file_operation_lock:
                with open(os.path.join(pickle_folder, option_pickle_path), 'wb') as f:
                    pickle.dump(option, f)
            strip_data['pickle_path'] = option_pickle_path
        return strip_data

    return curr_strip

def pack_with_option(packed_fabric, sorted_fabrics, iter, wasted, used, option,
                     bins=None, config=PackingConfig(), use_high_res=False, include_instruction=True):
    """
    Given the selected packing option, pack the fabrics accordingly.
    ! After the packing, update packed_fabric, fabrics, and iter stored in the server session. !

    The first three arguments should be stored locally in the server session using flask.
        packed_fabric: the current packing result as an image
        sorterd_fabrics: the sorted remaining scrap fabrics from the previous step as a list of images
                         (or potentially other identifiers)
        iter: the current iteration (needed to pack according to the strategy)
        wasted: trimmed off materials that cannot be used again
        used: fabrics used in the design
    The last two arguments should come from front-end user preferences.
        option: the user-selected and potentially reordered packing option
        config: the packing configuration (user selects strategy)
    """
    trimmed_images, trimming_records, fabric_details, curr_strip, before_crop, after_crop, strip_shape, curr_fabric_shape, target_L = option_to_strip(
        packed_fabric, sorted_fabrics, option, iter, bins, config, use_high_res=use_high_res)

    wasted += option.wasted_area
    used += option.total_area

    # keep track of high-res fabric shape and target length for reconstruction purposes
    curr_fabric_shape_high_res, _ = get_fabric_shape(packed_fabric, iter, config, is_high_res=True)
    other_dimensions_high_res = [(edge.get_other_dim() - 2 * config.sa) for edge in option.edge_subset]
    shortest_side_high_res = min(other_dimensions_high_res)

    new_packing_shapes = []
    new_packing_images = []
    # add the first image the first so that in the final image it will be below
    if packed_fabric is not None:
        if config.strategy != 'rail-fence':
            packed_fabric = draw_seam_lines(packed_fabric, seam_allowance=config.sa)
        if config.strategy == 'rail-fence' and iter > 6:
            new_packing_images.append(config.block34)
            new_packing_shapes.append(curr_fabric_shape)
        elif not (config.strategy == 'rail-fence' and iter == 6):
            new_packing_images.append(packed_fabric)
            new_packing_shapes.append(curr_fabric_shape)
    new_packing_images.append(curr_strip)
    strip_shape.w = curr_strip.size[0]
    strip_shape.h = curr_strip.size[1]
    new_packing_shapes.append(strip_shape)

    # prepare for the next iteration
    new_curr_image = composite_images(new_packing_images, home_image_shapes(new_packing_shapes), suppress_output=True, alpha=128)
    cropped_new_curr_image = crop_curr_image(target_L, new_curr_image, iter, config.strategy)
    new_packed_fabric = draw_seam_lines(cropped_new_curr_image, seam_allowance=config.sa)
    config.packed_fabric_high_res_size = high_res_packed_fabric_size(curr_fabric_shape_high_res, shortest_side_high_res, iter, config.strategy, sa=config.sa)

    # print(f"Projected packed fabric high-res size: {config.packed_fabric_high_res_size}")
    # print(f"Current packed fabric size: {new_packed_fabric.size}")
    if use_high_res: # this is hopefully not cheating any more because I added 2 * sa init to _create_image_shape()
        config.packed_fabric_high_res_size = new_packed_fabric.size

    if config.strategy == 'rail-fence':
        if iter == 5: # save block12 results after packing with the option
            config.block12 = new_packed_fabric
            config.block12_high_res_size = config.packed_fabric_high_res_size
            print(f"Block12 high-res size: {config.block12_high_res_size}")
        elif iter > 5 and iter < 11:
            config.block34 = new_packed_fabric
            config.block34_high_res_size = config.packed_fabric_high_res_size
            print(f"Block34 high-res size: {config.block34_high_res_size}")
            # Compose blocks 1-2 and incomplete 3-4 for final result
            new_packed_fabric = rail_fence_compose_incomplete(config.block12, config.block34, sa=config.sa, suppress_output=True)
            composed_packed_fabric_high_res_size = (min(config.block12_high_res_size[0], config.block34_high_res_size[0]), config.block12_high_res_size[1] + config.block34_high_res_size[1])
            print(f"Final composed high-res size: {composed_packed_fabric_high_res_size}")
        elif iter == 11:
            config.block34 = new_packed_fabric
            config.block34_high_res_size = config.packed_fabric_high_res_size
            print(f"Block34 high-res size: {config.block34_high_res_size}")
            # Compose blocks 1-2 and 3-4 for final result
            if config.block12.size[0] < config.block34.size[0]:
                config.block34 = config.block34.crop((config.block34.size[0] - config.block12.size[0], 0, config.block34.size[0], config.block34.size[1]))
            else:
                config.block12 = config.block12.crop((config.block12.size[0] - config.block34.size[0], 0, config.block12.size[0], config.block12.size[1]))
            new_packed_fabric = rail_fence_compose(config.block12, config.block34, sa=config.sa, suppress_output=True)
            update_rail_fence_packed_fabric_high_res_size(config)
            print(f"Final composed high-res size: {config.packed_fabric_high_res_size}")
    used_fabrics = set([edge.p.id for edge in option.edge_subset])
    remaining_fabrics = [img for i, img in enumerate(sorted_fabrics) if i not in used_fabrics] + trimmed_images
    if bins is not None:
        bins.update_fabrics(option, trimming_records, sa=config.sa)
    attach_instr = get_attach_instruction(iter, config.strategy)
    iter += 1

    if include_instruction:
        trimming_instructions = [
            f"For fabric {detail['fabric_id'] + 1} (in order {detail['order']}): "
            f"Cut at {detail['trim_line']} pixels from the edge to create a strip of width {option.shortest_side} pixels."
            for detail in fabric_details if detail.get('needs_trimming')
        ]
        instruction = {
            'step': iter,
            'used_fabrics': [{
                'image': pil_image_to_base64(draw_seam_lines(detail['image'], seam_allowance=config.sa)),
                'size': detail['original_size'],
                'rotated': detail['rotated'],
                'order': i
            } for i, detail in enumerate(fabric_details)],
            'packed_fabric': pil_image_to_base64(packed_fabric),
            'packed_fabric_size': packed_fabric.size if packed_fabric is not None else None,
            'strip_images': {
                'after_crop': pil_image_to_base64(after_crop),
                'after_crop_size': after_crop.size
            },
            'trimming_records': trimming_records,
            'trimming_instructions': trimming_instructions,
            'attachment_instruction': attach_instr,
            'final_result': pil_image_to_base64(new_packed_fabric),
            'final_result_size': new_packed_fabric.size
        }
        if before_crop is not None:
            instruction['strip_images']['before_crop'] = pil_image_to_base64(before_crop)
        if cropped_new_curr_image.size != new_curr_image.size:
            instruction['final_before_crop'] = pil_image_to_base64(new_curr_image)
        return new_packed_fabric, remaining_fabrics, bins, iter, wasted, used, instruction
    return new_packed_fabric, remaining_fabrics, bins, iter, wasted, used
