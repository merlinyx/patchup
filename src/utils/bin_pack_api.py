from src.utils.pack import *
from src.utils.bins import Fabric, FabricBins, ColorFabricBins
from src.utils.config import *
from src.utils.filters import *
from src.utils.plot import pil_image_to_base64
from time import time
import dill as pickle

def next_packing_options(packed_fabric, fabrics, iter,
                         bin_filter=None, option_filter=None, option_rank=None,
                         bins=None, config=PackingConfig()):
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
    """

    if len(fabrics) == 0 and bins is None:
        return []

    # sort the remaining fabrics
    # ! this should be stored in the server session to be accessed later !
    if packed_fabric is None and config.strategy != 'rail-fence':
        sorted_fabrics = sorted(fabrics, key=lambda x: min(x.size) ** 2, reverse=True)
        packed_fabric = sorted_fabrics[0]
        fabrics = sorted_fabrics[1:]

    fb = bins
    if fb is None:
        Fabric.id = 0
        fb = ColorFabricBins(fabrics, sa=config.sa) if config.use_color_bins else FabricBins(fabrics, sa=config.sa)
    curr_fabric_shape = get_curr_image_shape(packed_fabric, config.target_L, iter, config.strategy)
    target_L = target_length(curr_fabric_shape, iter, config.strategy)
    target_sum = target_L - 2 * config.sa

    # select bins based on filters and target length
    selected_bins = None
    if config.use_color_bins:
        selected_bins = fb.select_bins(target_sum, config.threshold, config.desired_color, bin_filter)
    else:
        selected_bins = fb.select_bins(target_sum, config.threshold, bin_filter)
    if selected_bins is None:
        print('No valid bins found. Exiting...')
        return []

    start_time = time.time()
    best_sum_subsets = [bin.find_best_subsets(target_sum, config.threshold) for bin in selected_bins]
    method_time = time.time() - start_time
    print(f'find_best_subsets() took {method_time} seconds')
    best_sum_subsets.sort(key=lambda item: abs(item[0] - target_sum))
    all_edge_subsets = [edge_subset for (best_sum, best_sum_subset) in best_sum_subsets if best_sum >= target_sum for edge_subset in best_sum_subset]
    if len(all_edge_subsets) == 0:
        print("No target length satisfying edge subsets found")
        all_edge_subsets = [edge_subset for (_, best_sum_subset) in best_sum_subsets for edge_subset in best_sum_subset]
        if len(all_edge_subsets) == 0:
            print('No valid subsets found. Exiting...')
            return []

    # use the filter to filter and the ranking method to rank the edge_subsets
    no_filter = option_filter is None
    all_options = []
    grouped_check_dups = {}
    for i, edge_subset in enumerate(all_edge_subsets):
        the_other_dimensions = [edge.get_other_dim() - 2 * config.sa for edge in edge_subset]
        shortest_side = min(the_other_dimensions)
        filter_passed = (not no_filter) and option_filter.validates(shortest_side)
        if shortest_side not in grouped_check_dups:
            grouped_check_dups[shortest_side] = set()
        edge_lengths = frozenset([edge.length() for edge in edge_subset])
        if (no_filter or filter_passed) and edge_lengths not in grouped_check_dups[shortest_side]:
            wasted_area = sum([(edge.get_other_dim() - 2 * config.sa - shortest_side) * edge.length() for edge in edge_subset])
            total_area = sum([(edge.length() + 2 * config.sa) * (edge.s.length() + 2 * config.sa) for edge in edge_subset])
            the_other_dimensions_high_res_px = [edge.get_other_dim() for edge in edge_subset]
            shortest_side_px = min(the_other_dimensions_high_res_px)
            all_options.append(PackingOption(i, edge_subset, the_other_dimensions, shortest_side, total_area, wasted_area, shortest_side_px=shortest_side_px))
            grouped_check_dups[shortest_side].add(edge_lengths)
    if option_rank is not None:
        ranked_options = sorted(all_options, key=lambda option: option_rank.compute_rank(option))
        selected_options = ranked_options[:config.max_options]
    else:
        selected_options = all_options[:config.max_options]
    return selected_options

def option_to_strip(packed_fabric, sorted_fabrics, option, iter, bins, config, option_display=False):
    """
    Helper function to process each strip.
    """
    new_edge_images = []
    new_edge_shapes = []
    trimmed_images = []
    trimming_records = []
    fabric_details = []

    curr_fabric_shape = get_curr_image_shape(packed_fabric, config.target_L, iter, config.strategy)
    top_left_corner = top_left(curr_fabric_shape, iter, config.strategy, option.shortest_side, sa=config.sa)
    strip_shape = ImageShape(top_left_corner[0], top_left_corner[1], 0, 0)
    target_L = target_length(curr_fabric_shape, iter, config.strategy)
    length_to_keep = option.shortest_side + 2 * config.sa # <- this corresponds to having other_dim with -2*sa

    # then pick out these images and set the image shapes and rotations accordingly
    fabric_mapping = {} if bins is None else bins.to_id_fabric_map()
    for op_index, (edge, other_dim) in enumerate(zip(option.edge_subset, option.other_dims)):
        fabric_image = sorted_fabrics[edge.p.id] if bins is None else fabric_mapping[edge.p.id]
        w, h = fabric_image.size
        fabric_detail = {
            'order': op_index + 1,
            'fabric_id': edge.p.id,
            'image': fabric_image,
            'original_size': (w, h),
            'length': edge.length(),
            'other_dim': other_dim,
            'needs_trimming': other_dim - option.shortest_side > config.min_scrap_size
        }
        image_shape = shifted_top_left(top_left_corner, option.shortest_side, other_dim, w, h, iter, config.strategy, sa=config.sa)
        # Use high-res dimensions for rotation check if available
        high_res_w, high_res_h = edge.p.high_res_image_size if edge.p.high_res_image_size is not None else (w, h)
        rotated = rotate_image_shape(high_res_w, high_res_h, image_shape, edge.length(), iter, config.strategy, sa=config.sa, use_high_res=True)
        fabric_detail['rotated'] = rotated
        # we actually need to trim the fabrics to correctly display seams
        image_to_append = trim_image_in_strip(fabric_image, op_index, len(option.edge_subset),
                                              rotated, iter, config.strategy, sa=config.sa)
        image_shape.w = image_to_append.size[0]
        image_shape.h = image_to_append.size[1]
        new_edge_images.append(image_to_append)
        new_edge_shapes.append(image_shape)
        top_left_corner = next_top_left(op_index, top_left_corner, edge.length(), iter, config.strategy, sa=config.sa)
        # and make the trimmed off parts as the new images
        if fabric_detail['needs_trimming']:
            print('needs trimming', edge)
            trimmed_image, trimmed_area = trim_image(fabric_image, length_to_keep, rotated, w, h, iter, config.strategy)
            if trimmed_image is not None:
                fabric_detail['trimmed_image'] = pil_image_to_base64(trimmed_image)
                fabric_detail['trim_line'] = option.shortest_side
                trimming_records.append({
                    'original_image': pil_image_to_base64(fabric_image),
                    'trimmed_image': pil_image_to_base64(trimmed_image),
                    'fabric_id': edge.p.id
                })
                trimmed_images.append(trimmed_image)
            else:
                option.wasted_area -= trimmed_area
        fabric_details.append(fabric_detail)

    # check current strip image
    homed_image_shapes = home_image_shapes(new_edge_shapes)
    curr_strip = composite_images(new_edge_images, homed_image_shapes, suppress_output=True, alpha=128)

    strip_image = None
    if packed_fabric is None: # need to keep additional seam allowance for rail-fence iter 0 and iter 6
        strip_image = crop_curr_strip(length_to_keep + config.sa, curr_strip, iter, config.strategy, sa=config.sa)
    else:
        strip_image = crop_curr_strip(length_to_keep, curr_strip, iter, config.strategy, sa=config.sa)

    trimmed_strip = trim_curr_image(target_L, curr_strip, iter, config.strategy)
    if trimmed_strip is not None and trimmed_strip.size[0] > config.min_scrap_size and trimmed_strip.size[1] > config.min_scrap_size:
        trimmed_images.append(trimmed_strip)
        fid = option.edge_subset[-1].p.id
        original_image = sorted_fabrics[fid] if bins is None else fabric_mapping[fid]
        trimming_records.append({
            'original_image': pil_image_to_base64(original_image),
            'trimmed_image': pil_image_to_base64(trimmed_strip),
            'fabric_id': fid
        })
    elif trimmed_strip is not None:
        option.wasted_area += trimmed_strip.size[0] * trimmed_strip.size[1]

    if option_display: # for front-end display
        return new_edge_images, homed_image_shapes, strip_image
    else: # for actual packing with this strip option
        after_crop, before_crop = None, None
        if len(option.edge_subset) > 1:
            after_crop, before_crop = crop_curr_strip(length_to_keep + config.sa, curr_strip, iter, config.strategy, sa=config.sa, should_draw_crop_line=True)
            if before_crop and after_crop.size == before_crop.size: before_crop = None
        else:
            after_crop = crop_curr_strip(length_to_keep + config.sa, curr_strip, iter, config.strategy, sa=config.sa)
        after_crop, before_crop = draw_seam_lines(after_crop, img_before=before_crop, seam_allowance=config.sa)
        return trimmed_images, trimming_records, fabric_details, strip_image, before_crop, after_crop, strip_shape, curr_fabric_shape, target_L

def option_to_strip_image(packed_fabric, sorted_fabrics, option, iter, bins=None, config=PackingConfig(),
                          should_save=False, session_id=None, save_folder=None, pickle_folder=None):

    new_edge_images, homed_image_shapes, curr_strip = option_to_strip(packed_fabric, sorted_fabrics, option, iter, bins, config, option_display=True)

    if should_save:
        assert session_id and save_folder and pickle_folder
        images_data = [{
            'color': [int(number) for number in list(np.array(im).mean(axis=(0, 1)))],
            'box_xywh': imshape.box()
        } for im, imshape in zip(new_edge_images, homed_image_shapes)]
        strip_image_path = f'iter_{iter}_strip_{option.index}.png'
        curr_strip.save(os.path.join(save_folder, strip_image_path))
        option_pickle_path = f'iter_{iter}_option_{option.index}.pkl'
        with open(os.path.join(pickle_folder, option_pickle_path), 'wb') as f:
            pickle.dump(option, f)
        return {
            'pickle_path': option_pickle_path,
            'strip_image': os.path.join(session_id[:10], strip_image_path),
            'wasted_area': option.wasted_area / config.dpi ** 2,
            'thickness': option.shortest_side,
            'images_data': images_data,
        }
    return curr_strip

def pack_with_option(packed_fabric, sorted_fabrics, iter, wasted, used, option,
                     bins=None, config=PackingConfig(), include_instruction=True):
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
    trimmed_images, trimming_records, fabric_details, curr_strip, \
        before_crop, after_crop, strip_shape, curr_fabric_shape, \
        target_L = option_to_strip(
            packed_fabric, sorted_fabrics,
            option, iter, bins, config)

    wasted += option.wasted_area
    used += option.total_area

    new_packing_shapes = []
    new_packing_images = []
    # add the first image the first so that in the final image it will be below
    if packed_fabric is not None:
        if config.strategy != 'rail-fence':
            packed_fabric = draw_seam_lines(packed_fabric, seam_allowance=config.sa)
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
            'strip_images': {
                'after_crop': pil_image_to_base64(after_crop)
            },
            'trimming_records': trimming_records,
            'trimming_instructions': trimming_instructions,
            'attachment_instruction': attach_instr,
            'final_result': pil_image_to_base64(new_packed_fabric)
        }
        if before_crop is not None:
            instruction['strip_images']['before_crop'] = pil_image_to_base64(before_crop)
        if cropped_new_curr_image.size != new_curr_image.size:
            instruction['final_before_crop'] = pil_image_to_base64(new_curr_image)
        return new_packed_fabric, remaining_fabrics, bins, iter, wasted, used, instruction
    return new_packed_fabric, remaining_fabrics, bins, iter, wasted, used

def bin_pack(fabrics, bin_filter=None, option_filter=None, option_rank=None, config=PackingConfig(), should_save=False, suppress_output=False):

    packed_fabric = None
    wasted = 0
    used = 0

    iter = 0
    timestamp = int(time())
    output_folder = f'images_{config.strategy}_{timestamp}'
    if should_save:
        os.makedirs(output_folder, exist_ok=True)

    while len(fabrics) > 0:

        # sort the remaining fabrics
        fabrics = sorted(fabrics, key=lambda x: min(x.size) ** 2, reverse=True)
        if packed_fabric is None:
            packed_fabric = fabrics[0]
            used += fabrics[0].size[0] * fabrics[0].size[1]
            if should_save:
                packed_fabric.save(f'{output_folder}/initial_image.png')
            fabrics = fabrics[1:]

        options = next_packing_options(packed_fabric, fabrics, iter, bin_filter, option_filter, option_rank, None, config)
        if len(options) == 0:
            print('No valid packing options found. Exiting...')
            if not suppress_output:
                plot_images_in_grid(fabrics, should_cvt_color=False)
            break
        packed_fabric, fabrics, iter, wasted, used = pack_with_option(packed_fabric, fabrics, iter, wasted, used, options[0], config, include_instruction=False)
        if should_save:
            packed_fabric.save(f'{output_folder}/iter_{iter}_packed.png')
        if not suppress_output:
            # print(f'Packing iteration {iter}')
            plt.imshow(packed_fabric)
            plt.axis('off')

    return packed_fabric, fabrics, wasted, used

def bin_pack_rail_fence(fabrics, bin_filter=None, option_filter=None, option_rank=None, config=PackingConfig(), should_save=False, suppress_output=False):

    assert config.strategy == 'rail-fence', 'The strategy must be rail-fence for this function.'

    packed_fabric = None
    wasted = 0
    used = 0

    iter = 0
    timestamp = int(time())
    output_folder = f'images_{config.strategy}_{timestamp}'
    if should_save:
        os.makedirs(output_folder, exist_ok=True)

    def run_step():
        nonlocal packed_fabric, fabrics, iter, bin_filter, option_filter, option_rank, config, wasted, used
        options = next_packing_options(packed_fabric, fabrics, iter, bin_filter, option_filter, option_rank, config)
        if len(options) == 0:
            if isinstance(option_filter, ThicknessFilter):
                options = next_packing_options(packed_fabric, fabrics, iter, bin_filter, None, option_rank, config)
            if len(options) == 0:
                print('No valid packing options found. Exiting...')
                if not suppress_output:
                    plot_images_in_grid(fabrics, should_cvt_color=False)
                return
        packed_fabric, fabrics, iter, wasted, used = pack_with_option(packed_fabric, fabrics, iter, wasted, used, options[0], config, include_instruction=False)
        if should_save:
            packed_fabric.save(f'{output_folder}/iter_{iter}_packed.png')
        if not suppress_output:
            # print(f'Packing iteration {iter}')
            plt.imshow(packed_fabric)
            plt.axis('off')

    if option_rank is None:
        option_rank = LargeThicknessRank()

    # first block
    config.target_L['top'] = config.start_length
    for _ in range(3):
        run_step()
    block1 = packed_fabric

    # second block
    config.target_L['right'] = block1.size[1]
    for _ in range(3):
        run_step()
    block12 = packed_fabric

    # third block
    config.target_L['bottom'] = block12.size[0] - config.target_L['top'] + 2 * config.sa
    packed_fabric = None
    for _ in range(3):
        run_step()
    block3 = packed_fabric

    # fourth block
    config.target_L['left'] = block3.size[1]
    # We no longer need to update option_filter as thickness constraints are handled in next_packing_options
    run_step()
    run_step()
    run_step()
    block34 = packed_fabric

    if block12.size[0] < block34.size[0]:
        block34 = block34.crop((block34.size[0] - block12.size[0], 0, block34.size[0], block34.size[1]))
    else:
        block12 = block12.crop((block12.size[0] - block34.size[0], 0, block12.size[0], block12.size[1]))
    block12 = draw_seam_lines(block12, seam_allowance=config.sa)
    block12 = draw_border(block12)
    block34 = draw_seam_lines(block34, seam_allowance=config.sa)
    block34 = draw_border(block34)

    block1234 = rail_fence_compose(block12, block34, sa=config.sa, suppress_output=True)
    if should_save:
        block1234.save(f'{output_folder}/final_packed.png')
    if not suppress_output:
        plt.imshow(block1234)
        plt.axis('off')

    return block1234, fabrics, wasted, used
