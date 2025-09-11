import cv2
import sys
import matplotlib.pyplot as plt
from skimage.segmentation import slic
from skimage.segmentation import mark_boundaries
from skimage.util import img_as_float

def superpixel(image_path, n_segments=50, compactness=30, sigma=2):
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    img = img_as_float(img)
    segments_slic = slic(img, n_segments=n_segments, compactness=compactness, sigma=sigma, start_label=1, convert2lab=True)
    result_image = mark_boundaries(img, segments_slic)
    return result_image

if __name__ == '__main__':
    image_path = sys.argv[1]
    result_image = superpixel(image_path)
    output_path = sys.argv[1].split('.')[0] + '_overlay.png'
    plt.imshow(result_image)
    plt.axis('off')
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
