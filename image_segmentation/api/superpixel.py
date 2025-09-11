import cv2
from skimage.segmentation import slic
from skimage.segmentation import mark_boundaries
from skimage.util import img_as_float

def superpixel(image_path, n_segments=100, compactness=10, sigma=1):
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    img = img_as_float(img)
    segments_slic = slic(img, n_segments=n_segments, compactness=compactness, sigma=sigma, start_label=1, convert2lab=True)
    result_image = mark_boundaries(img, segments_slic)
    return result_image
