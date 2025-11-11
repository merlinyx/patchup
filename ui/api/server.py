from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import dill as pickle
import os
import uuid
import sys
from rectpack import *
import time
import numpy as np
import json
from datetime import datetime
from PIL import Image
import threading

# Add file operation lock
file_operation_lock = threading.Lock()

WKDIR = '../../'
sys.path.insert(0, WKDIR)

from src.utils.bin_pack_api_rail_fence import next_packing_options, pack_with_option, option_to_strip
from src.results.reconstruct_high_res import reconstruct_high_res
from src.utils.config import *
from src.utils.filters import *
from src.utils.pack import update_rail_fence_packed_fabric_high_res_size
from src.utils.plot import *
from src.utils.binning import *
from src.utils.load_images import load_fabrics_for_binning
from src.utils.bins import UserFabricBins
from src.utils.tests import total_area

app = Flask(__name__)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'
CORS(app)

# In-memory storage for session data and options
session_store = {}
option_store = {}  # Will store options by session_id and option key
last_response = None
current_session_id = None  # Global variable to store current session ID
PUBLIC_DIR = os.path.join(os.getcwd(), '../public')
# remove files related to any previous sessions
if os.path.exists(PUBLIC_DIR):
    for f in os.listdir(PUBLIC_DIR):
        if os.path.isdir(os.path.join(PUBLIC_DIR, f)) and len(f) == 10:
            os.system(f'rm -rf {os.path.join(PUBLIC_DIR, f)}')
# Path where pickled files will be stored
PICKLE_DIR = os.path.join(os.path.dirname(__file__), 'pickle_store')
if not os.path.exists(PICKLE_DIR):
    os.makedirs(PICKLE_DIR)
else:
    os.system(f'rm -rf {PICKLE_DIR}/*')
# Logs directory
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)
else:
    os.system(f'rm -rf {LOG_DIR}/*')
# Results directory
RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results')
if not os.path.exists(RESULTS_DIR):
    os.makedirs(RESULTS_DIR)

# Explicit favicon route that works across all domains
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        PUBLIC_DIR,
        'favicon.ico', 
        mimetype='image/vnd.microsoft.icon'
    )

def create_rank(rank_method):
    if rank_method == 'wastedArea':
        return WastedAreaRank()
    elif rank_method == 'thicknessInc':
        return LargeThicknessRank()
    elif rank_method == 'thicknessDec':
        return SmallThicknessRank()
    elif rank_method == 'fabricCountInc':
        return HighFabricCountRank()
    elif rank_method == 'fabricCountDec':
        return LowFabricCountRank()
    elif rank_method == 'colorInc':
        return LowContrastRank()
    elif rank_method == 'colorDec':
        return HighContrastRank()
    elif rank_method == 'valueInc':
        return HighValueContrastRank() # I DON'T KNOW WHY BUT THIS IS INVERTED
    elif rank_method == 'valueDec':
        return LowValueContrastRank() # ...
    elif rank_method == 'hueInc':
        return HighHueContrastRank() # I DON'T KNOW WHY BUT THIS IS INVERTED
    elif rank_method == 'hueDec':
        return LowHueContrastRank() # ...
    elif rank_method != 'none':
        print(f'Unknown rank method: {rank_method}')
    return WastedAreaRank() # default to always rank by wasted area

def compute_utilization(fabrics, wasted, used, config):
    if used == 0:
        return 0, 0, total_area(fabrics) / config.dpi ** 2
    return used / config.dpi ** 2, (used - wasted) / used * 100, total_area(fabrics) / config.dpi ** 2

def find_session_id():
    global current_session_id
    if current_session_id is None:
        current_session_id = str(uuid.uuid4())
        session_store[current_session_id] = {
            'config': PackingConfig(),
            'bins': None,
            'packed_fabric': None,
            'initial_fabric_id': None,
            'sorted_fabrics': None,
            'iter': 0,
            'bin_filter': None,
            'option_filter': None,
            'option_rank': None,
            'wasted': 0,
            'used': 0,
            'chosen_options': [],
            'bins_per_iter': {},
            'strategy_per_iter': {},
            'instructions': []
        }
        option_store[current_session_id] = {}
    return current_session_id

def store_option(session_id, iter, option_index, option):
    """Store option in memory"""
    option_key = f'iter_{iter}_option_{option_index}'
    if session_id not in option_store:
        option_store[session_id] = {}
    option_store[session_id][option_key] = option
    return option_key

def get_option(session_id, option_key):
    """Retrieve option from memory"""
    return option_store.get(session_id, {}).get(option_key)

def clear_option_store(session_id):
    """
    Clear all stored options for a given session_id.
    
    Args:
        session_id: The session identifier
    """
    if session_id in option_store:
        option_store[session_id] = {}

def option_to_strip_image(packed_fabric, sorted_fabrics, option, iter, bins=None, config=PackingConfig(),
                                 should_save=False, session_id=None, save_folder=None, use_high_res=False):
    """Modified version to use in-memory option storage"""
    # Always use low-res for display but compute high-res dimensions for storage
    new_edge_images, homed_image_shapes, curr_strip = option_to_strip(
        packed_fabric, sorted_fabrics, option, iter, bins, config, option_display=True, use_high_res=use_high_res)

    if should_save:
        images_data = [{
            'id': edge.p.id,
            'width': im.size[0],
            'height': im.size[1],
            'rotated': image_shape.rotated()
        } for im, image_shape, edge in zip(new_edge_images, homed_image_shapes, option.edge_subset)]

        strip_image_path = f'iter_{iter}_strip_{option.index}.png'
        with file_operation_lock:
            with open(os.path.join(save_folder, strip_image_path), 'wb') as f:
                curr_strip.save(f, format='PNG')

        # Store option in memory instead of pickle file
        option_key = store_option(session_id, iter, option.index, option)

        return {
            'option_key': option_key,
            'strip_image': os.path.join(session_id[:10], strip_image_path),
            'wasted_area': option.wasted_area / config.dpi ** 2,
            'thickness': option.shortest_side,
            'thickness_px': option.shortest_side_px,
            'images_data': images_data,
        }
    return curr_strip

@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Max-Age', '3600')  # Cache preflight for 1 hour
    return response

@app.route('/api/generate_options', methods=['OPTIONS'])
def handle_generate_options_preflight():
    response = jsonify({})
    response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    return response

@app.route('/api/retrieve_last_response', methods=['GET'])
def retrieve_last_response():
    global last_response
    if last_response is None:
        return jsonify({'message': 'No last response found'}), 404
    response = last_response
    return jsonify(response)

@app.route('/api/generate_options', methods=['POST'])
def generate_options():
    start_time = time.time()

    data = request.json
    iter = data.get('currentStep', 0)
    data_folder = data.get('dataFolder', 'ui_test1')
    packed_fabric_path = data.get('packedFabric', None)
    strategy = data.get('packingStrategy', 'log-cabin')
    start_length = data.get('startLength', None)
    dpi = int(data.get('dpi', 100))
    bin_filter = data.get('binFilter', None)
    selected_bins = data.get('selectedBins', [])
    sort_by = data.get('sortBy', 'none')
    thickness_min = data.get('thicknessMin', None)
    thickness_max = data.get('thicknessMax', None)
    fabric_count_min = data.get('fabricCountMin', None)
    fabric_count_max = data.get('fabricCountMax', None)

    session_id = find_session_id()
    session_data = session_store[session_id]

    session_data['config'].update_dpi(dpi)
    # Update session data
    session_data['iter'] = iter
    # Create bin filter if bins are selected
    bin_filter = FabricFilter({'must_have_fabric': bin_filter}) if bin_filter else None
    if selected_bins:
        bin_filter = UserBinFilter({'user_selected_bins': selected_bins})
    session_data['bin_filter'] = bin_filter
    session_data['option_filter'] = None # turn off option filters for now
    session_data['option_rank'] = create_rank(sort_by)
    if iter > 0 and strategy != session_data['config'].strategy:
        if session_data['config'].strategy == 'rail-fence':
            update_rail_fence_packed_fabric_high_res_size(session_data['config'])
        session_data['strategy_per_iter'][iter] = strategy
    session_data['config'].strategy = strategy

    # Initialize session data for new packing
    if iter == 0:
        # Load fabrics
        fabrics = None
        high_res_fabrics_sizes = None
        if session_data['bins'] is None:
            print('Loading fabrics from folder')
            fabrics = load_fabrics_for_binning(PUBLIC_DIR, os.path.join('fabric_data', data_folder.lstrip('/')), images_only=True)
            high_res_folder = os.path.join('fabric_data', data_folder.lstrip('/').replace('_resized', ''))
            if os.path.exists(os.path.join(PUBLIC_DIR, high_res_folder)):
                high_res_fabrics = load_fabrics_for_binning(PUBLIC_DIR, high_res_folder, images_only=True)
                high_res_fabrics_sizes = [f.size for f in high_res_fabrics]
        else:
            # case 2: use fabrics from selected bins
            print('Loading fabrics from bins')
            fabrics = session_data['bins'].to_id_fabric_map(bin_filter=bin_filter)
            if len(fabrics) == 0:
                return jsonify({'message': 'No fabrics could be loaded from bins'})
            if 0 not in session_data['bins_per_iter']:
                session_data['bins_per_iter'][0] = session_data['bins'].to_bins_data()

        session_data['strategy_per_iter'][iter] = strategy
        if strategy == 'rail-fence':
            sorted_fabrics = None
            if session_data['bins'] is not None:
                fabric_imgs = list(fabrics.values())
                sorted_fabrics = sorted(fabric_imgs, key=lambda x: min(x.size) * min(x.size), reverse=True)
            else:
                sorted_fabrics = sorted(fabrics, key=lambda x: min(x.size) * min(x.size), reverse=True)
            session_data['packed_fabric'] = None
            session_data['config'].packed_fabric_high_res_size = None
            session_data['sorted_fabrics'] = sorted_fabrics
        elif session_data['packed_fabric'] is None:
            if session_data['bins'] is None:
                fabric_ids = [i for i in range(len(fabrics))]
                sorted_args = sorted(fabric_ids, key=lambda x: min(fabrics[x].size) * min(fabrics[x].size), reverse=True)
                session_data['packed_fabric'] = fabrics[sorted_args[0]]
                if high_res_fabrics_sizes is not None:
                    session_data['config'].packed_fabric_high_res_size = high_res_fabrics_sizes[sorted_args[0]]
                session_data['sorted_fabrics'] = [fabrics[i] for i in sorted_args[1:]]
            else:
                fabric_ids = list(fabrics.keys())
                fabric_imgs = list(fabrics.values())
                sorted_fabrics = sorted(fabric_imgs, key=lambda x: min(x.size) * min(x.size), reverse=True)
                sorted_args = sorted(fabric_ids, key=lambda x: min(fabrics[x].size) * min(fabrics[x].size), reverse=True)
                session_data['initial_fabric_id'] = sorted_args[0]
                session_data['packed_fabric'] = sorted_fabrics[0]
                removed, high_res_image_size = session_data['bins'].remove_fabric(sorted_args[0])
                if not removed:
                    print('Failed to remove the first fabric from the bins')
                remaining_fabrics = session_data['bins'].to_id_fabric_map()
                session_data['sorted_fabrics'] = list(remaining_fabrics.values())
                session_data['config'].packed_fabric_high_res_size = high_res_image_size
            session_data['wasted'] = 0
            session_data['used'] = session_data['packed_fabric'].size[0] * session_data['packed_fabric'].size[1]

    # Handle packed fabric
    if packed_fabric_path:
        full_path = os.path.join(PUBLIC_DIR, packed_fabric_path.lstrip('/'))
        if os.path.exists(full_path):
            with Image.open(full_path) as img:
                session_data['packed_fabric'] = img.copy()  # Copy and release memory

    # Handle rail-fence specific logic
    if strategy == 'rail-fence':
        if iter == 0:
            if start_length is None:
                avg_size = sum(min(f.size) for f in session_data['sorted_fabrics']) / len(session_data['sorted_fabrics'])
                start_length = max(int(avg_size * 1.2), min(max(f.size) for f in session_data['sorted_fabrics']))
            session_data['config'].start_length_high_res = int(start_length) # use the start length for high res
            session_data['config'].start_length = int(int(start_length) * session_data['config'].scale_factor)
            session_data['config'].target_L = {
                'top': session_data['config'].start_length,
                'right': None,
                'bottom': None,
                'left': None
            }
            session_data['config'].target_L_high_res = {
                'top': session_data['config'].start_length_high_res,
                'right': None,
                'bottom': None,
                'left': None
            }
        # Update target lengths based on current iteration
        if iter == 3:
            session_data['config'].target_L['right'] = session_data['packed_fabric'].size[1] + 2 * session_data['config'].sa
            session_data['config'].target_L_high_res['right'] = session_data['config'].packed_fabric_high_res_size[1] + 50
        elif iter == 6:
            session_data['config'].target_L['bottom'] = session_data['packed_fabric'].size[0] - session_data['config'].target_L['top'] + 2 * session_data['config'].sa
            session_data['config'].target_L_high_res['bottom'] = session_data['config'].packed_fabric_high_res_size[0] - session_data['config'].target_L_high_res['top'] + 50
        elif iter == 9:
            session_data['config'].target_L['left'] = session_data['packed_fabric'].size[1] - session_data['config'].target_L['right'] + 2 * session_data['config'].sa
            session_data['config'].target_L_high_res['left'] = session_data['config'].packed_fabric_high_res_size[1] - session_data['config'].target_L_high_res['right'] + 50

    # Generate options
    method_time = time.time()
    options = next_packing_options(
        session_data['packed_fabric'],
        session_data['sorted_fabrics'],
        session_data['iter'],
        session_data['bin_filter'],
        session_data['option_filter'],
        session_data['option_rank'],
        session_data['bins'],
        session_data['config'],
        thickness_min=thickness_min,
        thickness_max=thickness_max,
        fabric_count_min=fabric_count_min,
        fabric_count_max=fabric_count_max
    )
    method_time = time.time() - method_time
    print(f'next_packing_options() took {method_time} seconds')

    # Convert options to JSON and save images
    strip_image_folder = os.path.join(PUBLIC_DIR, session_id[:10])
    if not os.path.exists(strip_image_folder):
        os.makedirs(strip_image_folder)

    clear_option_store(session_id)
    option_jsons = [option_to_strip_image(
        session_data['packed_fabric'],
        session_data['sorted_fabrics'],
        option,
        session_data['iter'],
        session_data['bins'],
        session_data['config'],
        should_save=True,
        session_id=session_id,
        save_folder=strip_image_folder
    ) for option in options]

    # Save packed fabric image
    if session_data['packed_fabric']:
        packed_fabric_path = os.path.join(strip_image_folder, 'packed_fabric.png')
        with file_operation_lock:
            with open(packed_fabric_path, 'wb') as f:
                session_data['packed_fabric'].save(f, format='PNG')

    response_data = {
        'options': option_jsons,
        'message': f'Generated {len(option_jsons)} options',
    }

    if 'bins' in session_data and session_data['bins'] is not None:
        response_data['bins_merged'] = session_data['bins'].bins_merged
        session_data['bins'].bins_merged = False

    if strategy != 'rail-fence' or iter != 0:
        response_data['packed_fabric_path'] = f'/{session_id[:10]}/packed_fabric.png'

    if strategy != 'rail-fence' and iter == 0:
        response_data['packed_fabric_size'] = session_data['packed_fabric'].size
        response_data['utilization'] = '100'

    global last_response
    last_response = response_data
    print(f'generate_options() api call took {time.time() - start_time} seconds')
    return jsonify({'message': 'Options generated successfully!'})

@app.route('/api/pack_with_selected_option', methods=['POST'])
def pack_with_selected_option():
    data = request.json
    iter = data.get('currentStep', 0)
    strategy = data.get('packingStrategy', 'log-cabin')
    option_key = data.get('optionKey', None)
    option_order = data.get('optionOrder', None)

    session_id = find_session_id()
    session_data = session_store[session_id]
    
    # Save current state for undo before modifying
    if not os.path.exists(os.path.join(RESULTS_DIR, session_id[:10])):
        os.makedirs(os.path.join(RESULTS_DIR, session_id[:10]))
    with open(os.path.join(RESULTS_DIR, session_id[:10], 'previous_state.pkl'), 'wb') as f:
        pickle.dump(session_data, f)
    
    # Get selected option from memory
    selected_option = get_option(session_id, option_key)
    if not selected_option:
        return jsonify({'message': 'Selected option not found'}), 404

    if option_order:
        selected_option.update_order(option_order)

    session_data['iter'] = iter
    session_data['config'].strategy = strategy

    # Pack with selected option
    (session_data['packed_fabric'],
     session_data['sorted_fabrics'],
     session_data['bins'],
     session_data['iter'],
     session_data['wasted'],
     session_data['used'],
     instruction) = pack_with_option(
        session_data['packed_fabric'],
        session_data['sorted_fabrics'],
        session_data['iter'],
        session_data['wasted'],
        session_data['used'],
        selected_option,
        session_data['bins'],
        session_data['config']
    )

    session_data['chosen_options'].append(selected_option)
    session_data['instructions'].append(instruction)

    used, utilization, unused = compute_utilization(
        session_data['sorted_fabrics'],
        session_data['wasted'],
        session_data['used'],
        session_data['config']
    )

    # Save packed fabric image
    if session_data['packed_fabric']:
        packed_fabric_path = os.path.join(PUBLIC_DIR, session_id[:10], 'packed_fabric.png')
        with file_operation_lock:
            with open(packed_fabric_path, 'wb') as f:
                session_data['packed_fabric'].save(f, format='PNG')
    packed_fabric_size = session_data['packed_fabric'].size if session_data['packed_fabric'] else None

    global last_response
    last_response = None

    return jsonify({
        'message': 'Packed with the selected option',
        'iter': session_data['iter'],
        'packed_fabric_path': f'/{session_id[:10]}/packed_fabric.png',
        'packed_fabric_size': packed_fabric_size,
        'utilization': f'{utilization:.2f}',
        'used_area': f'{used:.2f}',
        'unused_fabrics': f'{unused:.2f}'
    })

@app.route('/api/undo', methods=['POST'])
def undo_last_action():
    session_id = find_session_id()
    
    previous_state_path = os.path.join(RESULTS_DIR, session_id[:10], 'previous_state.pkl')
    if not os.path.exists(previous_state_path):
        return jsonify({'error': 'No previous state to restore'}), 404
    
    # Restore previous state
    del session_store[session_id]
    del option_store[session_id]
    with open(previous_state_path, 'rb') as f:
        session_store[session_id] = pickle.load(f)
    session_data = session_store[session_id]
    # Remove the used previous state to ensure only one level of undo
    os.remove(previous_state_path)
    
    # Regenerate packed fabric image
    if session_data['packed_fabric']:
        packed_fabric_path = os.path.join(PUBLIC_DIR, session_id[:10], 'packed_fabric.png')
        with file_operation_lock:
            with open(packed_fabric_path, 'wb') as f:
                session_data['packed_fabric'].save(f, format='PNG')
    
    packed_fabric_size = session_data['packed_fabric'].size if session_data['packed_fabric'] else None
    
    # Calculate utilization data
    used, utilization, unused = compute_utilization(
        session_data['sorted_fabrics'],
        session_data['wasted'],
        session_data['used'],
        session_data['config']
    )
    
    global last_response
    last_response = None
    
    return jsonify({
        'message': 'Reverted to previous state',
        'iter': session_data['iter'],
        'packed_fabric_path': f'/{session_id[:10]}/packed_fabric.png',
        'packed_fabric_size': packed_fabric_size,
        'utilization': f'{utilization:.2f}',
        'used_area': f'{used:.2f}',
        'unused_fabrics': f'{unused:.2f}'
    })

@app.route('/api/finish_packing', methods=['POST'])
def finish_packing():
    session_id = find_session_id()
    session_data = session_store.get(session_id)

    if not session_data:
        return jsonify({'error': 'No session found'}), 404

    # Create output directory if it doesn't exist
    output_dir = os.path.join(RESULTS_DIR, current_session_id[:10])
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save session data
    session_file = os.path.join(output_dir, 'current_session.pkl')
    with open(session_file, 'wb') as f:
        pickle.dump(session_data, f)

    print(f"Session data saved to /results/{current_session_id[:10]}/current_session.pkl")

    return jsonify({
        'instructions': session_data['instructions'],
        'total_steps': len(session_data['instructions'])
    })

@app.route('/api/finish_packing_high_res', methods=['POST'])
def finish_packing_high_res():
    session_id = find_session_id()
    session_data = session_store.get(session_id)
    try:
        data = request.json
        fabric_folder = data.get('fabricFolder', '')
        use_step_by_step = data.get('stepByStep', True)
        # Create output directory for high-res results
        output_dir = os.path.join(RESULTS_DIR, session_id[:10])
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        success = reconstruct_high_res(session_data, fabric_folder, output_dir, public_dir=PUBLIC_DIR, step_by_step=use_step_by_step)
        if success:
            return jsonify({'message': 'High-res results generated successfully!'})
        else:
            return jsonify({'error': 'High-res results generation failed'}), 500
    except Exception as e:
        print(f"Error finishing packing high res: {str(e)}")
        session_id = find_session_id()
        session_data = session_store.get(session_id)
        with open(os.path.join(RESULTS_DIR, session_id[:10], 'current_session.pkl'), 'wb') as f:
            pickle.dump(session_data, f)
        return jsonify({'error': str(e)}), 500

@app.route('/api/load_fabrics', methods=['POST'])
def load_fabrics():
    data = request.json
    fabric_folder = data.get('fabric_folder')
    fabric_json = load_fabrics_for_binning(PUBLIC_DIR, os.path.join('fabric_data', fabric_folder.lstrip('/')))
    return jsonify({'fabrics': fabric_json})

@app.route('/api/estimate_nbins', methods=['POST'])
def estimate_nbins():
    data = request.json
    fabric_folder = data.get('fabric_folder')
    group_criterion = data.get('group_criterion')
    mode = data.get('mode')

    fabric_json = load_fabrics_for_binning(PUBLIC_DIR, os.path.join('fabric_data', fabric_folder.lstrip('/')), should_include_image=True)
    criteria_values = [compute_criteria(fabric['img'], mode=mode, criterion=group_criterion) for fabric in fabric_json]
    criteria_values = np.array(criteria_values).reshape(-1, 1)
    n_bins = estimate_clusters(criteria_values)
    return jsonify({'nbins': n_bins})

@app.route('/api/group_fabrics', methods=['POST'])
def group_fabrics():
    data = request.json
    fabric_folder = data.get('fabric_folder')
    available_fabrics = data.get('available_fabrics')
    n_bins = int(data.get('n_bins'))
    group_criterion = data.get('group_criterion')
    mode = data.get('mode')
    fixed_bins = data.get('fixed_bins', [])  # Get fixed bins from request

    # Extract fabric IDs from fixed bins to exclude them from grouping
    fixed_fabric_ids = []
    for bin_fabrics in fixed_bins:
        if bin_fabrics is not None:
            fixed_fabric_ids.extend([fabric['id'] for fabric in bin_fabrics])

    # Load fabrics, excluding those in fixed bins
    fabric_json = load_fabrics_for_binning(
        PUBLIC_DIR, 
        os.path.join('fabric_data', fabric_folder.lstrip('/')), 
        available_fabrics=available_fabrics, 
        should_include_image=True,
        exclude_ids=fixed_fabric_ids  # Add parameter to exclude fixed fabric IDs
    )
    
    # Group the remaining fabrics
    groups = group_images(fabric_json, n_clusters=n_bins, criterion=group_criterion, mode=mode)

    return jsonify({'bins': groups})

@app.route('/api/load_bins', methods=['POST'])
def load_bins():
    data = request.json
    filepath = data.get('binsFile')
    filepath = os.path.join(os.getcwd(), filepath.lstrip('/'))

    session_id = find_session_id()
    session_data = session_store[session_id]

    pickle_file_path = os.path.join(PICKLE_DIR, f'{session_id}.pkl')
    if not os.path.exists(pickle_file_path):
        pickle_file_path = os.path.join(PICKLE_DIR, filepath)
    if not os.path.exists(pickle_file_path):
        return jsonify({'message': 'No bins found'}), 404
    else:
        with open(pickle_file_path, 'rb') as f:
            bins = pickle.load(f)
        session_data['bins'] = UserFabricBins(PUBLIC_DIR, bins, sa=session_data['config'].sa)
        return jsonify({'bins': bins, 'message': 'User-defined bins loaded successfully!'})

@app.route('/api/load_bin_options', methods=['POST']) 
def load_bin_options():
    session_id = find_session_id()
    session_data = session_store[session_id]
    is_binning = request.json.get('isBinning', False)

    if 'bins' not in session_data or session_data['bins'] is None:
        return jsonify({'message': 'No bins found'})

    bins_data = session_data['bins'].to_bins_data() if is_binning else session_data['bins'].to_json()

    return jsonify({'message': 'User-defined bins loaded successfully!',
                    'bins': bins_data})

@app.route('/api/save_bins', methods=['POST'])
def save_bins():
    data = request.json
    bins = data.get('bins')
    is_modify = data.get('isModify', False)
    non_empty_bins = []
    for bin in bins:
        if len(bin) > 0:
            non_empty_bins.append(bin)
    if len(non_empty_bins) == 0:
        return jsonify({'message': 'No bins to save'})
    dpi = int(data.get('dpi', 100))

    session_id = find_session_id()
    session_data = session_store[session_id]
    session_data['config'].update_dpi(dpi)

    # Create UserFabricBins object and store it in session data
    if session_data['iter'] == 0:
        session_data['bins'] = UserFabricBins(PUBLIC_DIR, bins, sa=session_data['config'].sa)
        # save initial bins as a pickle file
        pickle_file_path = os.path.join(PICKLE_DIR, f'{session_id}.pkl')
        with file_operation_lock:
            with open(pickle_file_path, 'wb') as f:
                pickle.dump(bins, f)
    else:
        try:
            session_data['bins'].update_bins(bins)
        except Exception as e:
            print(f"Error updating bins; constructing new UserFabricBins object (likely the previous packing is not reset)")
            session_data['bins'] = UserFabricBins(PUBLIC_DIR, bins, sa=session_data['config'].sa)
    if 0 not in session_data['bins_per_iter']:
        assert session_data['iter'] == 0, "the current iter should be 0, is actually:" + str(session_data['iter'])
    if session_data['iter'] == 0: # always update the bins for iter 0
        session_data['bins_per_iter'][0] = bins
    if is_modify: # otherwise, only update the bins for the current iter if it is a modifying operation
        session_data['bins_per_iter'][session_data['iter']] = bins

    return jsonify({'message': 'User-defined bins saved successfully!'})

def compute_packing_gaps(packer, packing_width, packing_height):
    """Compute the total gap area in a packing solution."""
    # Find the bin with most rectangles
    max_rects_bin = 0
    max_rects_count = 0
    for b in range(len(packer)):
        if len(packer[b]) > max_rects_count:
            max_rects_count = len(packer[b])
            max_rects_bin = b
    
    # Calculate total area of packed rectangles
    packed_area = sum(w * h for b, x, y, w, h, rid in packer.rect_list() if b == max_rects_bin)
    bin_area = packing_width * packing_height
    
    return bin_area - packed_area

def estimate_packing_width_height(images, bin_algo=PackingBin.BNF, sort_algo=SORT_AREA,
                                  max_iterations=20, gap_threshold=100, offset=0):
    """
    Estimate optimal width and height for rectpack to minimize gaps.
    
    Args:
        images: List of PIL Images to pack
        bin_algo: Rectangle packing algorithm
        sort_algo: Sorting algorithm for rectangles
        max_iterations: Maximum number of iterations to try
        gap_threshold: Acceptable gap area threshold
    
    Returns:
        tuple: (optimal_width, optimal_height, stats)
    """
    # Calculate total area of all images
    total_area = sum(img.size[0] * img.size[1] for img in images)
    
    # Generate aspect ratios from 1:1 to 1:2
    aspect_ratios = np.linspace(1.0, 2.0, 8)
    
    # Stats tracking
    stats = {
        'iterations': 0,
        'time_taken': 0,
        'final_gaps': float('inf'),
        'area_tried': []
    }
    
    start_time = time.time()
    current_area = total_area
    best_result = None
    
    for iteration in range(max_iterations):
        stats['iterations'] += 1
        min_gaps = float('inf')
        best_wh = None
        
        # Try different aspect ratios
        for ratio in aspect_ratios:
            # Calculate width and height for this ratio and area
            height = int(np.sqrt(current_area / ratio))
            width = int(height * ratio)
            
            try:
                # Create packer
                packer = newPacker(
                    bin_algo=bin_algo,
                    sort_algo=sort_algo,
                    rotation=True
                )
                
                # Add rectangles
                for img in images:
                    w, h = img.size
                    w = max(1, w - offset * 2)
                    h = max(1, h - offset * 2)
                    packer.add_rect(w, h)
                
                # Add bin and pack
                packer.add_bin(width, height)
                packer.pack()
                
                # Compute gaps
                gaps = compute_packing_gaps(packer, width, height)
                
                if gaps < min_gaps:
                    min_gaps = gaps
                    best_wh = (width, height)
                
            except Exception as e:
                print(f"Packing failed for {width}x{height}: {str(e)}")
                continue
        
        stats['area_tried'].append(current_area)
        
        # If we found a solution with acceptable gaps, save it
        if min_gaps <= gap_threshold:
            best_result = best_wh
            stats['final_gaps'] = min_gaps
            break
        
        # If this iteration produced better results, save it as backup
        if best_result is None or min_gaps < stats['final_gaps']:
            best_result = best_wh
            stats['final_gaps'] = min_gaps
        
        # Reduce area and try again
        current_area = int(current_area * 0.99)
    
    stats['time_taken'] = time.time() - start_time
    
    if best_result is None:
        raise ValueError("Could not find suitable packing dimensions")
    
    return best_result[0], best_result[1], stats

@app.route('/api/estimate_packing_wh', methods=['POST'])
def estimate_packing_wh():
    data = request.json
    fabric_folder = data['fabric_folder']
    bin_algo = getattr(PackingBin, data.get('bin_algo', 'BNF'))  
    sort_algo = {
        'AREA': SORT_AREA,
        'DIFF': SORT_DIFF,
        'RATIO': SORT_RATIO,
        'SSIDE': SORT_SSIDE,
        'LSIDE': SORT_LSIDE,
        'PERI': SORT_PERI,
        'NONE': SORT_NONE
    }.get(data.get('sort_algo', 'AREA'), SORT_AREA)
    dpi = int(data.get('dpi', 100))
  
    folder_path = os.path.join('fabric_data', fabric_folder.lstrip('/'))
    config = PackingConfig()
    config.update_dpi(dpi)

    fabrics = load_fabrics_for_binning(PUBLIC_DIR, folder_path, should_include_image=True)
    list_of_images = [fabric['img'] for fabric in fabrics]
    offset = config.sa
    width, height, _ = estimate_packing_width_height(list_of_images, bin_algo, sort_algo, offset=offset)
    return jsonify({
        'message': 'Successfully estimated best packing width and height',
        'width': width,
        'height': height
    })

@app.route('/api/rectpack', methods=['POST'])
def rectpack():
    data = request.json
    fabric_folder = data['fabric_folder']
    bin_algo = getattr(PackingBin, data.get('bin_algo', 'BNF'))  
    sort_algo = {
        'AREA': SORT_AREA,
        'DIFF': SORT_DIFF,
        'RATIO': SORT_RATIO,
        'SSIDE': SORT_SSIDE,
        'LSIDE': SORT_LSIDE,
        'PERI': SORT_PERI,
        'NONE': SORT_NONE
    }.get(data.get('sort_algo', 'AREA'), SORT_AREA)
    dpi = int(data.get('dpi', 100))

    packing_width = data.get('width', 3200)        
    packing_height = data.get('height', 2500)          
    folder_path = os.path.join('fabric_data', fabric_folder.lstrip('/'))
    config = PackingConfig()
    config.update_dpi(dpi)

    try:
        fabrics = load_fabrics_for_binning(PUBLIC_DIR, folder_path, should_include_image=True)
        list_of_images = [fabric['img'] for fabric in fabrics]
        image_whs = [fabric.size for fabric in list_of_images]
        offset = config.sa

        try:
            packer = newPacker(
                bin_algo=bin_algo,
                sort_algo=sort_algo,
                rotation=True
            )
        except Exception as e:
            print(f"Error creating packer: {str(e)}")
            packer = newPacker(
                bin_algo=PackingBin.BNF,
                sort_algo=SORT_AREA,
                rotation=True
            )

        for i in range(len(image_whs)):
            w, h = image_whs[i]
            w = max(1, w - offset * 2)
            h = max(1, h - offset * 2)
            packer.add_rect(w, h, i)

        packer.add_bin(packing_width, packing_height, count=float('inf'))

        packer.pack()

        final_image = Image.new('RGBA', (packing_width, packing_height), (255, 255, 255, 0))
        packed_rects = []
        max_rects_bin = 0
        max_rects_count = 0

        for b in range(len(packer)):
            if len(packer[b]) > max_rects_count:
                max_rects_count = len(packer[b])
                max_rects_bin = b

        for rect in packer.rect_list():
            b, x, y, w, h, rid = rect
            if b != max_rects_bin:
                continue

            w = w + offset * 2
            h = h + offset * 2
            img = list_of_images[rid]
            imgw, imgh = img.size

            if imgw != w or imgh != h:
                img = img.rotate(90, expand=True)

            packed_rects.append({
                'x': x,
                'y': y,
                'width': w,
                'height': h,
                'image': fabrics[rid]['image'],
                'base64': pil_image_to_base64(img)
            })

            final_image = trans_paste(final_image, img.convert("RGBA"), box=(x, y, x + w, y + h))

        final_base64 = pil_image_to_base64(final_image)

        return jsonify({
            'message': 'Successfully packed rectangles',
            'packed_rects': packed_rects,
            'final_image': f'data:image/png;base64,{final_base64}',
            'success': True
        })

    except Exception as e:
        print(f"Error in rectpack: {str(e)}")
        return jsonify({
            'message': f"Error packing rectangles: {str(e)}",
            'success': False
        })

# Reset session data
@app.route('/api/reset_session', methods=['POST'])
def reset_session():
    session_id = find_session_id()
    strip_image_folder = os.path.join(PUBLIC_DIR, session_id[:10])
    if os.path.exists(strip_image_folder):
        os.system(f'rm -r {strip_image_folder}')
    # if os.path.exists(LOG_DIR):
    #     os.system(f'rm {LOG_DIR}/*.json')
    global current_session_id
    del session_store[current_session_id]
    del option_store[current_session_id]
    current_session_id = None
    global last_response
    last_response = None
    # completely use a new session id
    session_id = find_session_id()
    return jsonify({'message': 'Session reset successfully'})

@app.route('/api/log_action', methods=['POST'])
def log_action():
    """Log user actions to a JSON file organized by date and timestamp."""
    try:
        data = request.json
        timestamp = datetime.now()
        
        # Create unique filename based on date and timestamp
        log_file = os.path.join(
            LOG_DIR, 
            f'user_actions_{timestamp.strftime("%Y-%m-%d_%H-%M-%S_%f")}.json'
        )
        
        # Add metadata to the log entry
        session_id = find_session_id()
        data['session_id'] = session_id
        data['timestamp'] = timestamp.isoformat()
        
        # Write to new file
        with open(log_file, 'w') as f:
            json.dump(data, f, indent=2)

        return jsonify({'message': 'Action logged successfully'})

    except Exception as e:
        print(f"Error logging action: {str(e)}")
        return jsonify({'message': f'Failed to log action: {str(e)}'})

if __name__ == '__main__':
    app.run()#debug=True)
