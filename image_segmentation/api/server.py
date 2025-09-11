from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
# from io import BytesIO
# from PIL import Image, ImageDraw
from werkzeug.utils import secure_filename
import os
import numpy as np
import cv2
import json

from meanshift import meanshift
from superpixel import superpixel
from fabrics import PatternPiece, FabricScrap
from polygon import Points

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'  # Directory where files will be stored
app.config['SEG_FOLDER'] = 'segmented/'  # Directory where segmented images will be stored
app.config['RESULT_FOLDER'] = 'results/'  # Directory where results will be stored
app.config['IMAGE_FOLDER'] = 'images/'  # Directory where images will be stored
app.config['PUBLIC_FOLDER'] = '../public/'  # Directory where public files will be stored
for folder in [app.config['UPLOAD_FOLDER'], app.config['SEG_FOLDER'], app.config['RESULT_FOLDER']]:
    fullpath = os.path.join(app.config['PUBLIC_FOLDER'], folder)
    if not os.path.exists(fullpath):
        os.makedirs(fullpath)
app.config['DATA_FOLDER'] = '../data/'  # Directory where data will be stored
CORS(app)

### Data Persistence calls
@app.route('/api/save_polygons', methods=['POST'])
def save_polygons():
    data = request.json
    image_name = data.get('image_name', '')
    if image_name == '':
        return jsonify({"message": "No image name provided"}), 400    
    fabric_image = cv2.imread(os.path.join(app.config['PUBLIC_FOLDER'], image_name))

    image_name = image_name.split('/')[-1].split('.')[0]
    polygons = data.get('polygons', {})
    is_fabric = data.get('is_fabric', False)
    segmented_images = data.get('segmented_images', [])
    # print(segmented_images)
    label_to_polygon = {polygon['label']: polygon for polygon in polygons}
    fabric_image_width = None

    if is_fabric:
        calib_pattern_size = None
        calib_square_size = 1 # inch
        for image_path in segmented_images:
            if 'calib' in image_path:
                img = cv2.imread(image_path)
                calib_pattern_size = min(img.shape[:2])
                break
        for image_path in segmented_images:
            image_label = image_path.split('/')[-1].split('_')[-1].split('.')[0]
            if image_label in label_to_polygon:
                if 'size' not in label_to_polygon[image_label] or label_to_polygon[image_label]['size'] == '':
                    img = cv2.imread(image_path)
                    calib_size_x = img.shape[0] / calib_pattern_size * calib_square_size
                    calib_size_y = img.shape[1] / calib_pattern_size * calib_square_size
                    label_to_polygon[image_label]['size'] = f'{calib_size_x:.2f}" x {calib_size_y:.2f}"'
            else:
                print("No polygon found for", image_label)

        fabric_image_width = fabric_image.shape[0] / calib_pattern_size * calib_square_size

    with open(os.path.join(app.config['DATA_FOLDER'], f"{image_name}_polygons.json"), 'w') as f:
        data_to_write = {'label_to_polygon': label_to_polygon}
        if fabric_image_width is not None:
            data_to_write['fabric_image_width'] = fabric_image_width
            data_to_write['breadcrumb_message'] = f"Scale the fabric to width {fabric_image_width} inch in Glowforge"
        f.write(json.dumps(data_to_write))
    return jsonify({"message": "Polygons saved successfully"}), 200

@app.route('/api/get_segmented_images', methods=['POST'])
def get_segmented_images():
    data = request.json
    image_name = data.get('imageName', '')
    if image_name == '':
        return jsonify({"message": "No image name provided"}), 400

    image_name = image_name.split('/')[-1].split('.')[0]
    segmented_images = []
    labels = []
    for img in os.listdir(os.path.join(app.config['PUBLIC_FOLDER'], app.config['SEG_FOLDER'])):
        if 'calib' not in img and image_name in img and (not img.endswith('.svg')):
            segmented_images.append(os.path.join(app.config['SEG_FOLDER'], img))
            labels.append(img.split('.')[0])
    return jsonify({"segmented_images": segmented_images, "segmented_image_labels": labels})

@app.route('/api/load_polygons', methods=['GET'])
def load_polygons():
    image_name = request.args.get('image_name', '')
    image_name = image_name.split('/')[-1].split('.')[0]
    if image_name == '':
        return jsonify({"message": "No image name provided"}), 400

    json_file_path = os.path.join(app.config['DATA_FOLDER'], f"{image_name}_polygons.json")
    polygons = []
    if not os.path.exists(json_file_path):
        print("No polygons found for this image")
    else:
        print("Loading polygons from", json_file_path)
        with open(json_file_path, 'r') as f:
            polygons = json.load(f)['label_to_polygon']
    return jsonify({"polygons": polygons, "is_empty": len(polygons) == 0})

### Image segmentation calls
@app.route('/api/segment_image', methods=['POST'])
def segment_image():
    data = request.json
    polygons = data.get('polygons', {})
    bg_image = data.get('bgImageSrc', '')
    ratio = data.get('bgScaleRatio', 1) # it's maxwidth / imagewidth

    # Create a blank image or use the background image
    img = None
    if bg_image != '':
        file_path = os.path.join(app.config['PUBLIC_FOLDER'], bg_image[2:])
        img = cv2.imread(file_path)

    segmented_images = []
    if img is None:
        return jsonify({"segmented_images": segmented_images})

    for (label, flattened_points) in polygons.items():
        original_scale_points = [coord / ratio for coord in flattened_points]
        contour = np.array(original_scale_points).reshape((-1, 2)).astype(np.int32)

        mask = np.zeros((img.shape[0], img.shape[1]))  # Create a mask that's the same size as the image
        cv2.drawContours(mask, [contour], -1, 255, -1)  # Draw the contour filled with white

        # If you want to keep the area transparent outside the contour
        # Create a 4 channel image (RGBA) where alpha is the mask
        rgba_image = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)  # Convert BGR to BGRA
        rgba_image[:, :, 3] = mask  # Set alpha channel to the mask

        x, y, w, h = cv2.boundingRect(contour)  # Get bounding box for each contour
        cropped_image = rgba_image[y:y+h, x:x+w]  # Crop the region from the original image

        image_name = bg_image.split('/')[-1].split('.')[0]
        polygon_path = os.path.join(app.config['PUBLIC_FOLDER'], app.config['SEG_FOLDER'], f"{image_name}_{'-'.join(label.split())}.png")
        print("Storing at", polygon_path)
        cv2.imwrite(polygon_path, cropped_image)
        segmented_images.append(polygon_path)

    return jsonify({"segmented_images": segmented_images})

### Fit pattern calls
@app.route('/api/fit_pattern', methods=['POST'])
def fit_pattern():
    data = request.json
    assignment = data.get('assignment', {})
    # print(assignment)
    turned_edge = data.get('turnedEdge', False)

    # first load the json data
    pattern_image = list(assignment.keys())[0]
    pattern_image_name = pattern_image.split('/')[-1].split('_')[0]
    pattern_image_data = {}
    with open(os.path.join(app.config['DATA_FOLDER'], f"{pattern_image_name}_polygons.json"), 'r') as f:
        pattern_image_data = json.loads(f.read())['label_to_polygon']

    scraps_image = assignment[pattern_image][0]
    scraps_image_name = scraps_image.split('/')[-1].split('_')[0]
    scraps_image_data = {}
    with open(os.path.join(app.config['DATA_FOLDER'], f"{scraps_image_name}_polygons.json"), 'r') as f:
        scraps_image_data = json.loads(f.read())['label_to_polygon']

    # next get the calib_size
    scraps_calib_path = os.path.join(app.config['PUBLIC_FOLDER'], app.config['SEG_FOLDER'], f"{scraps_image_name}_calib.png")
    calib_img = cv2.imread(scraps_calib_path)
    calib_pattern_size = min(calib_img.shape[:2])

    # a helper method for getting all the ratios
    def get_ratios(w1, h1, w2, h2):
        return [w1 / w2, h1 / h2, w1 / h2, h1 / w2]

    # then get the polygons
    max_ratios = []
    for (pattern, scraps) in assignment.items():
        pattern_piece = pattern.split('_')[1].split('.')[0]
        pattern_polygon = pattern_image_data[pattern_piece]["points"]
        pattern_image_path = os.path.join(app.config['PUBLIC_FOLDER'], pattern)
        pp = PatternPiece(pattern_image_path, pattern_polygon)
        if turned_edge:
            pp.add_seam_allowance(0.25 * calib_pattern_size)
        pp_min_wh = pp.min_wh()
        for scrap in scraps:
            scrap_piece = scrap.split('_')[1].split('.')[0]
            scrap_polygon = scraps_image_data[scrap_piece]["points"]
            scrap_image_path = os.path.join(app.config['PUBLIC_FOLDER'], scrap)
            fs = FabricScrap(scrap_image_path, scrap_polygon)
            fs_min_wh = fs.min_wh()

            max_possible_ratio = 1. / max(get_ratios(pp_min_wh[0], pp_min_wh[1], fs_min_wh[0], fs_min_wh[1]))
            max_ratios.append(max_possible_ratio)

    # print("Max ratios", max_ratios)
    # print("Pattern scaling", min(max_ratios))
    return jsonify({"pattern_scaling": min(max_ratios)})

### Image transformation calls
# THIS IS BUGGY!
@app.route('/api/compute_render_transforms', methods=['POST'])
def compute_render_transforms():
    data = request.json
    imageName = data.get('imageName', '')
    imageScaleRatio = data.get('imageScaleRatio', 1)
    scrapsName = data.get('scrapsName', '')
    scrapsScaleRatio = data.get('scrapsScaleRatio', 1)
    layerScale = data.get('layerScale', 1)
    patternToScrapScaling = data.get('patternToScrapScaling', 1)
    assignments = data.get('assignments', {})
    imageTransforms = data.get('imageTransforms', {})

    # print('imageScaleRatio', imageScaleRatio)
    # print('scrapsScaleRatio', scrapsScaleRatio)
    # print('layerScale', layerScale)
    # print('patternToScrapScaling', patternToScrapScaling)
    # print('assignments', assignments)
    # print('imageTransforms', imageTransforms)

    # first load the json data
    pattern_image_name = imageName.split('/')[-1].split('.')[0]
    pattern_image_data = {}
    with open(os.path.join(app.config['DATA_FOLDER'], f"{pattern_image_name}_polygons.json"), 'r') as f:
        pattern_image_data = json.loads(f.read())['label_to_polygon']
    scraps_image_name = scrapsName.split('/')[-1].split('.')[0]
    scraps_image_data = {}
    with open(os.path.join(app.config['DATA_FOLDER'], f"{scraps_image_name}_polygons.json"), 'r') as f:
        scraps_image_data = json.loads(f.read())['label_to_polygon']

    pattern_clip_images = []
    pattern_on_scraps = []

    # Compute the pattern view where scrap fabrics are clipped by pattern
    polygons_to_plot = []
    names = []

    pattern_scaling = 1 / imageScaleRatio * patternToScrapScaling
    scrap_scaling = 1 / scrapsScaleRatio
    layer_scale = layerScale

    scrap_scaling *= layer_scale
    pattern_scaling = layer_scale * patternToScrapScaling * patternToScrapScaling

    for polygon, fabrics in assignments.items():
        name = polygon.split('_')[1].split('.')[0]
        names.append(name)
        pt = imageTransforms[polygon]
        pp = Points(pattern_image_data[name]['points'])
        for fabric in fabrics:
            name = fabric.split('_')[1].split('.')[0]
            names.append(name)
            ft = imageTransforms[fabric]
            fp = Points(scraps_image_data[name]['points'])
            ###########

            # transform pattern points -> update: do not transform
            # 1. translate to fabric top left
            # pp = pp.translate(fp.top_left()[0] - pp.top_left()[0], fp.top_left()[1] - pp.top_left()[1])
            # 2. scale the pattern to the fabric
            # pp = pp.scale(pattern_scaling, anchor=pp.top_left())
            # 3. rotate the pattern
            # pp = pp.rotate(pt['rotation'])
            # 4. translate the pattern to the imagetransform point
            pattern_dx = pt['x'] - pp.top_left()[0]
            pattern_dy = pt['y'] - pp.top_left()[1]
            # pp = pp.translate(pattern_dx, pattern_dy)

            # transform fabric points -> update: reverse the transform on pattern
            fp = fp.translate(-(fp.top_left()[0] - pp.top_left()[0]), -(fp.top_left()[1] - pp.top_left()[1]))
            fabric_dx = ft['x'] - fp.top_left()[0]
            fabric_dy = ft['y'] - fp.top_left()[1]
            fp = fp.translate(fabric_dx, fabric_dy)
            fp = fp.scale(scrap_scaling, anchor=fp.top_left())
            fp = fp.translate(-pattern_dx, -pattern_dy)
            fp = fp.scale(1/pattern_scaling, anchor=fp.top_left())
            fp = fp.rotate(-pt['rotation'])

            ################
            polygons_to_plot.append(pp)
            polygons_to_plot.append(fp)

            pattern_clip_images.append({
                'src': fabric,
                'x': fp.top_left()[0],
                'y': fp.top_left()[1],
                'rotation': -pt['rotation'],
                'sx': scrap_scaling / pattern_scaling,
                'sy': scrap_scaling / pattern_scaling,
                'clipPath': pp.flattened(),
            })
            # print(pattern_clip_images[-1])

    # Compute the scrap image view where pattern pieces are placed on scraps
    polygons_to_plot = []
    names = []

    pattern_scaling = 1 / imageScaleRatio * patternToScrapScaling
    scrap_scaling = 1 / scrapsScaleRatio / patternToScrapScaling

    for polygon, fabrics in assignments.items():
        name = polygon.split('_')[1].split('.')[0]
        names.append(name)
        pt = imageTransforms[polygon]
        pp = Points(pattern_image_data[name]['points'])
        for fabric in fabrics:
            name = fabric.split('_')[1].split('.')[0]
            names.append(name)
            ft = imageTransforms[fabric]
            fp = Points(scraps_image_data[name]['points'])
            ###########

            # transform fabric points -> update: do not transform
            fabric_dx = ft['x'] - fp.top_left()[0]
            fabric_dy = ft['y'] - fp.top_left()[1]
            # fp = fp.translate(fabric_dx, fabric_dy)
            # fp = fp.scale(scrap_scaling, anchor=fp.top_left())

            # transform pattern points -> update: reverse transform of the fabric points
            # 1. translate to fabric top left
            # pp = pp.translate(fp.top_left()[0] - pp.top_left()[0], fp.top_left()[1] - pp.top_left()[1])
            # 2. scale the pattern to the fabric
            pp = pp.scale(pattern_scaling, anchor=pp.top_left())
            pp = pp.scale(1/scrap_scaling, anchor=pp.top_left())
            # 3. rotate the pattern
            pp = pp.rotate(pt['rotation'])
            # 4. translate the pattern to the imagetransform point
            pattern_dx = pt['x'] - pp.top_left()[0]
            pattern_dy = pt['y'] - pp.top_left()[1]
            pp = pp.translate(pattern_dx, pattern_dy)
            pp = pp.translate(-fabric_dx, -fabric_dy)

            ################
            polygons_to_plot.append(pp)
            polygons_to_plot.append(fp)

            pattern_on_scraps.append({
                'src': polygon,
                'x': pp.top_left()[0],
                'y': pp.top_left()[1],
                'sx': pattern_scaling / scrap_scaling, # the scaling is on pattern piece
                'sy': pattern_scaling / scrap_scaling,
                'clipPath': fp.flattened(), # clipPath here is the scrap fabric and not really a clip path
                'patternPath': pp.flattened(),
                'rotation': pt['rotation'],
            })
            # print("Pattern on scrap", pattern_on_scraps[-1])

    return jsonify({"pattern_clip_images": pattern_clip_images, "pattern_on_scraps": pattern_on_scraps})

@app.route('/api/save_polygon_as_svg', methods=['POST'])
def save_polygon_as_svg():
    data = request.json
    image_name = data.get('patternName', '')
    fabric_name = data.get('scrapsName', '')
    annotate_width = data.get('annotateWidth', 400)
    patterns = data.get('patterns', {})
    polygons = [pattern['clipPath'] for pattern in patterns]
    pattern_polygons = [pattern['patternPath'] for pattern in patterns]

    fabric_image_size = cv2.imread(os.path.join(app.config['PUBLIC_FOLDER'], fabric_name)).shape[:2]
    image_height = annotate_width / fabric_image_size[0] * fabric_image_size[1]

    image_name = image_name.split('/')[-1].split('.')[0]
    fabric_name = fabric_name.split('/')[-1].split('.')[0]
    svg_path = os.path.join(app.config['PUBLIC_FOLDER'], app.config['RESULT_FOLDER'], f"{image_name}_on_{fabric_name}.svg")

    json_file_path = os.path.join(app.config['DATA_FOLDER'], f"{fabric_name}_polygons.json")
    breadcrumb_message = ""
    if not os.path.exists(json_file_path):
        print("No polygons found for this image")
    else:
        with open(json_file_path, 'r') as f:
            breadcrumb_message = json.load(f)['breadcrumb_message']

    with open(svg_path, 'w') as f:
        f.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{annotate_width}" height="{image_height}" fill="none">\n')
        for polygon in polygons:
            polygon_str = ""
            for i in range(0, len(polygon), 2):
                polygon_str += f"{polygon[i]},{polygon[i+1]} "
            f.write(f'<polygon points="{polygon_str}" style="fill:white;stroke:black;stroke-width:1" />\n')
        for pattern in pattern_polygons:
            pattern_str = ""
            for i in range(0, len(pattern), 2):
                pattern_str += f"{pattern[i]},{pattern[i+1]} "
            f.write(f'<polygon points="{pattern_str}" style="fill:none;stroke:red;stroke-width:1" />\n')
        f.write('</svg>')
    return jsonify({"svg_path": svg_path, "message": breadcrumb_message})

########################### BELOW ARE DEPRECATED ###########################
### Previous filtering calls
@app.route('/meanshift_image', methods=['POST'])
def meanshift_image():
    file = check_file(request)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        spatial_radius = int(request.form['spatial_radius']) if 'spatial_radius' in request.form else 21
        color_radius = int(request.form['color_radius']) if 'color_radius' in request.form else 51
        output_segmented = os.path.join(app.config['RESULT_FOLDER'], 'segmented_' + filename)
        output_filtered = os.path.join(app.config['RESULT_FOLDER'], 'filtered_' + filename)
        if not os.path.exists(app.config['RESULT_FOLDER']):
            os.makedirs(app.config['RESULT_FOLDER'])

        meanshift(file_path, spatial_radius, color_radius, output_segmented, output_filtered)
        # segmented_url = request.url_root + 'results/' + 'segmented_' + filename
        # segmented_url = url_for(app.config['RESULT_FOLDER'], filename='segmented_' + filename)
        filtered_url = request.url_root + 'results/' + 'filtered_' + filename
        # filtered_url = url_for(app.config['RESULT_FOLDER'], filename='filtered_' + filename)
        return jsonify({
            'message': 'Mean shift applied successfully!',
            # 'segmented_image_url': segmented_url,
            'filtered_image_url': filtered_url
        }), 200

    return jsonify({'error': 'Invalid file type'}), 400

@app.route('/superpixel', methods=['POST'])
def superpixel():
    print(request.files)
    if 'image' not in request.files:
        return jsonify({'error': 'No image part'}), 400

    file = request.files['image']
    output_segmented = os.path.join(app.config['PUBLIC_FOLDER'], app.config['SEG_FOLDER'], f"{file.split('.')[0]}_slic_segmented.png")
    if not os.path.exists(output_segmented):
        segmented_image = superpixel(os.path.join(app.config['PUBLIC_FOLDER'], file))
        segmented_image.save(output_segmented)
    return send_file(output_segmented, mimetype='image/png')

### Previous file uploading methods
@app.route('/results/<path:filename>')
def results(filename):
    return send_from_directory(app.config['RESULT_FOLDER'], filename)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def check_file(request):
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    return file

@app.route('/upload_file', methods=['POST'])
def upload_file():
    file = check_file(request)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        file.save(file_path)
        # You can now process the image file as needed
        return jsonify({'message': 'File uploaded successfully!'}), 200

    return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    app.run(debug=True)
