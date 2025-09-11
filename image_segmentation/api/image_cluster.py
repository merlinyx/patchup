import cv2
import torch
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from skimage.color import rgb2lab, lab2rgb
from scipy.stats import mode
import os

midas = None
transform = None
device = None

def plot_color_palette(cluster_centers, title="Color Palette"):
    """
    Plots a color palette based on given cluster centers in Lab color space.
    
    Parameters:
        cluster_centers (array): An array of Lab color space cluster centers.
        title (str): The title of the plot.
    """
    # Number of clusters
    num_clusters = len(cluster_centers)
    
    # Convert LAB to RGB
    rgb_colors = [lab2rgb([[lab]])[0][0] for lab in cluster_centers]
    
    # Create a figure and a subplot
    fig, ax = plt.subplots(1, figsize=(num_clusters, 1), subplot_kw=dict(xticks=[], yticks=[], frame_on=False))
    ax.set_title(title)
    
    # Create a color bar
    ax.imshow([rgb_colors], aspect='auto')
    ax.set_xlim([0, num_clusters])

    plt.show()

def get_foreground_with_clustering(image_path, n_clusters = 6):
    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

    # Convert the image to Lab color space
    img_lab = rgb2lab(img)
    pixels = img_lab.reshape((-1, 3))

    # Perform K-means clustering on color
    kmeans_color = KMeans(n_clusters=n_clusters, random_state=42).fit(pixels)
    # Reshape the labels back into the image shape
    segmented_labels_color = kmeans_color.labels_.reshape(img.shape[:2])

    color_mode = mode(segmented_labels_color.flatten()).mode[0]
    color_clustered_mask = np.where(segmented_labels_color == color_mode, 0, 255).astype('uint8')
    # plt.imshow(color_clustered_mask)
    foreground_img = cv2.bitwise_and(img, img, mask=color_clustered_mask)
    return foreground_img

def depth(img):
    input_batch = transform(img).to(device)
    with torch.no_grad():
        prediction = midas(input_batch)

    prediction = torch.nn.functional.interpolate(
            prediction.unsqueeze(1),
            size=img.shape[:2],
            mode="bicubic",
            align_corners=False,
        ).squeeze()

    output = prediction.cpu().numpy()
    formatted = (output * 255 / np.max(output)).astype('uint8')
    img = Image.fromarray(formatted)
    return img

def cluster(image_path, n_clusters = 6):
    if not os.path.exists(os.path.join(os.path.dirname(image_path), 'cluster_results')):
        os.makedirs(os.path.join(os.path.dirname(image_path), 'cluster_results'))

    img = cv2.imread(image_path)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # Convert the image to Lab color space
    img_lab = rgb2lab(img)

    foreground_img = get_foreground_with_clustering(image_path)
    depth_image = depth(foreground_img)

    # Flatten the image and depth arrays
    pixels = img_lab.reshape((-1, 3))
    depth_flat = np.array(depth_image).reshape((-1, 1))

    # Normalize depth to be on the same scale as color
    depth_normalized = depth_flat / np.max(depth_flat)

    # Perform K-means clustering on color
    kmeans_color = KMeans(n_clusters=n_clusters, random_state=42).fit(pixels)

    # Combine color clustering labels and normalized depth into a single feature
    features_combined = np.hstack((pixels, depth_normalized))

    # Perform K-means clustering on the combined features
    kmeans_combined = KMeans(n_clusters=n_clusters, random_state=42).fit(features_combined)

    # Reshape the labels back into the image shape
    segmented_labels_color = kmeans_color.labels_.reshape(img.shape[:2])
    # plot_color_palette(kmeans_color.cluster_centers_, title=image_path.split('/')[-1] + " Color Palette")
    segmented_labels_combined = kmeans_combined.labels_.reshape(img.shape[:2])

    # Visualize the results
    fig, ax = plt.subplots(1, 2, figsize=(15, 5))
    # Color Segmentation
    ax[0].imshow(segmented_labels_color)
    # Combined Segmentation
    ax[1].imshow(segmented_labels_combined)
    end_path = image_path.split('/')[-1]
    fig.savefig(os.path.join(os.path.dirname(image_path), f'cluster_results/ncluster_{n_clusters}_{end_path}'))
    plt.close(fig)

def setup_midas():
    midas = torch.hub.load("intel-isl/MiDaS", "MiDaS")
    use_large_model = True

    if use_large_model:
        midas = torch.hub.load("intel-isl/MiDaS", "MiDaS")
    else:
        midas = torch.hub.load("intel-isl/MiDaS", "MiDaS_small")

    device = "cpu"
    midas.to(device)

    midas_transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
    if use_large_model:
        transform = midas_transforms.default_transform
    else:
        transform = midas_transforms.small_transform
    return midas, device, transform

def run_all():
    image_files = os.listdir('../../images')
    for image in image_files:
        image = image.lower()
        if image.endswith('.jpg') or image.endswith('.png'):
            cluster('../../images/' + image)

if __name__ == '__main__':
    midas, device, transform = setup_midas()

    run_all()
    # if len(sys.argv) > 2:
    #     cluster(sys.argv[1], int(sys.argv[2]))
    # elif len(sys.argv) > 1:
    #     cluster(sys.argv[1])
    # else:
    #     cluster('images/flower1.jpg')
