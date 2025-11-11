import os
import sys
import dill as pickle
import argparse
import threading

from src.utils.bin_pack_api_rail_fence import pack_with_option, option_to_strip_image
from src.utils.load_images import load_fabrics_for_binning
from src.utils.bins import UserFabricBins
from src.utils.pack import update_rail_fence_packed_fabric_high_res_size

# Add file operation lock
file_operation_lock = threading.Lock()

def compute_utilization(wasted, used, config):
    if used == 0:
        return 0, 0, 0
    return used / config.dpi ** 2, (used - wasted) / config.dpi ** 2, (used - wasted) / used * 100

def reconstruct_high_res(session_data, fabric_folder, output_dir, public_dir='public', save_steps=False, save_post_imgs=False, step_by_step=True):
    try:
        # Get original folder path
        original_folder = fabric_folder.replace('_resized', '').replace('_tiny', '').lstrip('/')

        chosen_options = session_data['chosen_options']
        config = session_data['config']
        current_dpi = config.dpi
        config.reset_dpi()  # reset dpi to default value 100
        bins_per_iter = session_data['bins_per_iter']
        if 'strategy_per_iter' in session_data:
            strategy_per_iter = session_data['strategy_per_iter']
            config.strategy = strategy_per_iter[0]
        else:
            strategy_per_iter = {0: config.strategy}

        wasted = 0
        used = 0
        instructions = []

        # Initialize bins with high-res fabrics
        high_res_fabrics = load_fabrics_for_binning(public_dir, os.path.join('fabric_data', original_folder), should_include_image=True)
        binning_bins = bins_per_iter[0]
        bins = UserFabricBins(public_dir, binning_bins, sa=config.sa, high_res_fabrics=high_res_fabrics)

        # Initialize packing
        packed_fabric = None
        current_fabrics = None
        fabrics = bins.to_id_fabric_map()

        if config.strategy == 'rail-fence':
            fabric_imgs = list(fabrics.values())
            sorted_fabrics = sorted(fabric_imgs, key=lambda x: min(x.size) * min(x.size), reverse=True)
            packed_fabric = None
            current_fabrics = sorted_fabrics
            config.packed_fabric_high_res_size = None
        else:
            if 'initial_fabric_id' in session_data and session_data['initial_fabric_id'] is not None:
                initial_fabric_id = session_data['initial_fabric_id']
                removed, high_res_image_size = bins.remove_fabric(initial_fabric_id)
                if not removed:
                    raise Exception(f"Failed to remove initial fabric {initial_fabric_id}")
                packed_fabric = fabrics[initial_fabric_id]
                current_fabrics = bins.to_id_fabric_map().values()
            else:
                fabric_ids = list(fabrics.keys())
                fabric_imgs = list(fabrics.values())
                sorted_fabrics = sorted(fabric_imgs, key=lambda x: min(x.size) * min(x.size), reverse=True)
                sorted_args = sorted(fabric_ids, key=lambda x: min(fabrics[x].size) * min(fabrics[x].size), reverse=True)
                removed, high_res_image_size = bins.remove_fabric(sorted_args[0])
                packed_fabric = sorted_fabrics[0]
                current_fabrics = sorted_fabrics[1:]
            config.packed_fabric_high_res_size = high_res_image_size
            used = packed_fabric.size[0] * packed_fabric.size[1]
            if not removed:
                print('Failed to remove the first fabric from the bins')

        # Reconstruct the packing process
        for iter, option in enumerate(chosen_options):
            print(f'========= Reconstructing step {iter} ========')
            if iter > 0 and iter in strategy_per_iter:
                if config.strategy == 'rail-fence' and strategy_per_iter[iter] != 'rail-fence':
                    print(f"Updating rail-fence packed fabric high-res size")
                    update_rail_fence_packed_fabric_high_res_size(config)
                config.strategy = strategy_per_iter[iter]
            if iter > 0 and iter in bins_per_iter:
                binning_bins = bins_per_iter[iter]
                bins.update_bins(binning_bins)
            try:
                new_option = bins.create_from_option(option)
                packed_fabric, current_fabrics, bins, iter, wasted, used, instruction = pack_with_option(
                    packed_fabric=packed_fabric,
                    sorted_fabrics=current_fabrics,
                    iter=iter,
                    wasted=wasted,
                    used=used,
                    option=new_option,
                    bins=bins,
                    config=config,
                    use_high_res=True,
                    include_instruction=True
                )

                if instruction:
                    instructions.append(instruction)
                if save_steps:
                    packed_fabric.save(os.path.join(output_dir, f'packed_fabric_{iter}.png'), format='PNG', quality=100)

            except Exception as e:
                print(f"Error processing step {iter}: {str(e)}")
                print(f"Only outputting up to step {iter}")
                raise e
                break

        if save_post_imgs:
            save_dir = os.path.join(os.path.join('fabric_data', original_folder.replace('_pp', '').rstrip('/') + '_post'))
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
            for fabric_id, fabric in bins.to_fabric_map().items():
                fabric.image.save(os.path.join(save_dir, f'{fabric_id}.png'), format='PNG', quality=100)

        total, used, utilization = compute_utilization(wasted, used, session_data['config'])

        config.update_dpi(current_dpi)

        # Save the high-res final image
        if packed_fabric:
            final_image_path = os.path.join(output_dir, 'final_packing.png')
            with file_operation_lock:
                with open(final_image_path, 'wb') as f:
                    packed_fabric.save(f, format='PNG', quality=100)

        # Generate and save HTML instructions
        if step_by_step:
            html_content = generate_html_instructions(instructions, total, used, utilization)
        else:
            html_content = generate_strip_first_instructions_html(instructions, total, used, utilization)
        instructions_path = os.path.join(output_dir, 'instructions.html')
        with open(instructions_path, 'w') as f:
            f.write(html_content)

        print(f'High-res reconstruction completed successfully!')
        print(f'Instructions saved at: {instructions_path}')
        print(f'Final image saved at: {final_image_path}')
        return True

    except Exception as e:
        print(f"Error reconstructing high-res results: {e}")
        raise e

def reconstruct_high_res_from_file(session_file, fabric_folder, output_dir=None, public_dir='public', save_steps=False):
    session_data = None
    with open(session_file, 'rb') as f:
        session_data = pickle.load(f)
    # Create output directory for high-res results
    if output_dir is None:
        session_file_folder = os.path.dirname(session_file)
        output_dir = os.path.join(session_file_folder, 'high_res')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return reconstruct_high_res(session_data, fabric_folder, output_dir, public_dir=public_dir, save_steps=save_steps)

def reconstruct_high_res_from_id(session_id, fabric_folder, results_dir='results', public_dir='public', save_steps=False):
    session_data = None
    # Load saved session data
    session_file = os.path.join(results_dir, session_id, 'current_session.pkl')
    if not os.path.exists(session_file):
        print(f'No saved session found for {session_id}')
        return False
    with open(session_file, 'rb') as f:
        session_data = pickle.load(f)
    output_dir = os.path.join(results_dir, session_id)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    return reconstruct_high_res(session_data, fabric_folder, output_dir, public_dir=public_dir, save_steps=save_steps)

def generate_html_instructions(instructions, total, used, utilization):
    """Generate HTML instructions from the instruction data."""
    html_content = generate_header_html(total, used, utilization)

    for i, instruction in enumerate(instructions, 1):
        # Generate fabric images HTML
        fabric_images_html = generate_fabric_images_html(instruction)
        
        # Generate trimming records HTML
        trimming_records_html = generate_trimming_records_html(instruction)
        
        # Generate strip images HTML
        strip_images_html = generate_strip_images_html(instruction)
        
        # Generate final result HTML
        final_result_html = generate_final_result_html(instruction)

        # Combine all HTML parts
        html_content += f"""
            <div class="instruction-step">
                <h3>Step {i}</h3>
                <div class="used-fabrics">
                    <p>Prepare the following fabrics for this step (fabric sizes aren't to scale):</p>
                    <div class="fabric-images">
                        {fabric_images_html}
                    </div>
                </div>
                <div class="strip-images">
                    {strip_images_html}
                </div>
                {trimming_records_html}
                <div class="final-result">
                    {final_result_html}
                </div>
            </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """
    
    return html_content

def generate_strip_first_instructions_html(instructions, total, used, utilization):
    """Generate HTML for strip-first instructions section."""
    html_content = generate_header_html(total, used, utilization) + """
            <div class="strip-section">
                <h2>Strip Preparation</h2>
    """

    # Add strip preparation instructions
    for i, instruction in enumerate(instructions):
        # Generate fabric images HTML
        fabric_images_html = generate_fabric_images_html(instruction, with_packed_fabric=False)
        
        # Generate strip images HTML
        strip_images_html = generate_strip_images_html(instruction)
        
        # Generate trimming records HTML
        trimming_records_html = generate_trimming_records_html(instruction)

        html_content += f"""
            <div class="instruction-step">
                <h3>Strip {instruction['step']}</h3>
                <div class="used-fabrics">
                    <p>Prepare the following fabrics for this strip (fabric sizes aren't to scale):</p>
                    <div class="fabric-images">
                        {fabric_images_html}
                    </div>
                </div>
                <div class="strip-images">
                    {strip_images_html}
                    {trimming_records_html}
                </div>
            </div>
        """

    # Add final result section
    html_content += """
            <div class="final-result-section">
                <h2>Strip Assembly</h2>
    """

    for i, instruction in enumerate(instructions):
        # Generate final result HTML
        final_result_html = generate_final_result_html(instruction)
        
        html_content += f"""
                <div class="instruction-step">
                    <h3>Step {instruction['step']}</h3>
                    <div class="final-result">
                        {final_result_html}
                    </div>
                </div>
        """

    html_content += """
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return html_content

def generate_header_html(total, used, utilization):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Packing Instructions</title>
        <link rel="stylesheet" href="/Users/Bluefish_/Desktop/thesis_project/scrapcollage/ipack/src/lib/packing.css">
        <link rel="stylesheet" href="/Users/Bluefish_/Desktop/thesis_project/scrapcollage/ipack/src/index.css">
        <link rel="stylesheet" href="/Users/Bluefish_/Desktop/thesis_project/scrapcollage/ipack/src/lib/instructions.css">
    </head>
    <body>
        <div class="instructions-container">
            <h1>Packing Instructions</h1>
            <p>Overall Utilization: {utilization:.2f}%</p>
            <p>Total Fabric Area: {total:.2f} sq in.</p>
            <p>Total Used Area: {used:.2f} sq in.</p>
            
            <div class="supplies-section">
                <h2>Supplies Needed</h2>
                <ul>
                    <li>Sewing machine or needles</li>
                    <li>Threads</li>
                    <li>Scissors</li>
                    <li>Iron</li>
                    <li>Ironing mat or board</li>
                    <li>Ruler</li>
                    <li>Seam ripper (optional)</li>
                    <li>Clips (optional)</li>
                    <li>Cutting board (optional)</li>
                    <li>Rotary cutter (optional)</li>
                </ul>
            </div>
    """

def generate_fabric_images_html(instruction, with_packed_fabric=True):
    """Generate HTML for fabric images section."""
    fabric_images_html = ""
    if 'used_fabrics' in instruction:
        for j, fabric in enumerate(instruction['used_fabrics']):
            fabric_images_html += f"""
                <div class="fabric-item">
                    <img src="data:image/png;base64,{fabric['image']}" alt="Fabric {j}" />
                    <p>Fabric {fabric['order'] + 1} 
                    ({fabric['size'][0] / 100:.2f} x {fabric['size'][1] / 100:.2f} in.)
                    </p>
                </div>
            """ # {'(rotated)' if fabric['rotated'] else ''} # rotated is confusing so removing for now
    if with_packed_fabric and 'packed_fabric' in instruction and instruction['packed_fabric'] is not None:
        fabric_images_html += f"""
            <div class="fabric-item">
                <img src="data:image/png;base64,{instruction['packed_fabric']}" alt="Packed fabric" />
                <p>Packed fabric</p>
                <p>The packed fabric should be ({instruction['packed_fabric_size'][0]/100:.2f} x {instruction['packed_fabric_size'][1]/100:.2f} in.)</p>
            </div>
        """
    return fabric_images_html

def generate_trimming_records_html(instruction):
    """Generate HTML for trimming records section."""
    if not ('trimming_records' in instruction and instruction['trimming_records']):
        return ""
        
    html = """
        <div class="trimming-records">
            <p>Note: The following fabrics will be trimmed, and the remaining pieces will be saved for later use:</p>
            <div class="trimming-images">
    """
    
    for record in instruction['trimming_records']:
        html += f"""
            <div class="trimming-record">
                <div class="original-fabric">
                    <img src="data:image/png;base64,{record['original_image']}" alt="Original fabric {record['fabric_id'] + 1}" />
                    <p>Original Fabric {record['fabric_id'] + 1}</p>
                </div>
                <div class="trimmed-fabric">
                    <img src="data:image/png;base64,{record['trimmed_image']}" alt="Remaining fabric {record['fabric_id'] + 1}" />
                    <p>Remaining piece (will be saved)</p>
                </div>
            </div>
        """
        
    html += """
            </div>
        </div>
    """
    return html

def generate_strip_images_html(instruction):
    """Generate HTML for strip images section."""
    has_before_crop = 'strip_images' in instruction and 'before_crop' in instruction['strip_images']

    before_crop_html = f"""
        <div class="strip-before-crop">
            <p>Stack fabrics as illustrated below and ensure all edges are properly aligned, then trim along the red dotted line shown in the diagram.</p>
            <img src="data:image/png;base64,{instruction['strip_images']['before_crop']}" alt="Strip before crop" />
        </div>
    """ if has_before_crop else ""

    after_crop_html = f"""
        <div class="strip-after-crop">
            <p>{'After trimming, y' if has_before_crop else 'Stack fabrics as illustrated below and ensure all edges are properly aligned. Y'}ou should have a neat strip like this:</p>
            <img src="data:image/png;base64,{instruction['strip_images']['after_crop']}" alt="Strip after crop" />
            <p>The strip should be ({instruction['strip_images']['after_crop_size'][0]/100:.2f} x {instruction['strip_images']['after_crop_size'][1]/100:.2f} in.)</p>
            <p>Stitch using a straight seam with quarter inch seam allowance and press seams open to create a flat strip.</p>
        </div>
    """

    return before_crop_html + after_crop_html

def generate_final_result_html(instruction):
    """Generate HTML for final result section."""
    html = ""
    
    if 'packed_fabric' in instruction:
        html += f"""
            <p class="attachment-instruction">{instruction['attachment_instruction']}</p>
        """
    
    if 'final_before_crop' in instruction:
        html += f"""
            <img src="data:image/png;base64,{instruction['final_before_crop']}" alt="Final result before trimming" />
        """
        
    html += f"""
        <p>{'After trimming any extra materials, ' if 'final_before_crop' in instruction else 'And '}the final packed result looks like:</p>
        <img src="data:image/png;base64,{instruction['final_result']}" alt="Final result" />
        <p>The final packed result should be ({instruction['final_result_size'][0]/100:.2f} x {instruction['final_result_size'][1]/100:.2f} in.)</p>
    """
    
    return html

def main():
    parser = argparse.ArgumentParser(description='Reconstruct high-res packing results from saved session data')
    parser.add_argument('session', help='Session ID (length 10) or session file to reconstruct')
    parser.add_argument('fabric_folder', help='Path to fabric folder')
    parser.add_argument('--results-dir', default='ipack/api/results', help='Path to results directory')
    parser.add_argument('--public-dir', default='ipack/public', help='Path to public directory')
    parser.add_argument('-s', '--step', action='store_true', help='Save all intermediate steps')

    args = parser.parse_args()
    if args.session.endswith('.pkl'):
        success = reconstruct_high_res_from_file(
            args.session,
            args.fabric_folder,
            public_dir=args.public_dir,
            save_steps=args.step
        )
    else:
        success = reconstruct_high_res_from_id(
            args.session,
            args.fabric_folder,
            results_dir=args.results_dir,
            public_dir=args.public_dir,
            save_steps=args.step
        )
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

# Usage:
# python scripts/reconstruct_high_res.py <path/to/current_session.pkl> <fabric_folder_name>
# or 
# python scripts/reconstruct_high_res.py <session_id> <fabric_folder_name>
