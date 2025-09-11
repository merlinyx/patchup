import numpy as np
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.metrics import silhouette_score
from skimage.color import rgb2lab, rgb2hsv
from colormath.color_diff import delta_e_cie1976, delta_e_cie1994, delta_e_cie2000, delta_e_cmc
from colormath.color_objects import LabColor
import warnings

def compute_criteria(image, mode='average', criterion='hue'):
    """
    Compute the specified criterion for an image.

    Parameters:
        image (PIL.Image): a PIL Image.
        mode (str): 'average' for average pixel values or 'dominant' for dominant colors.
        criterion (str): Criterion to compute ('hue', 'value', 'hue-value', 'lab').

    Returns:
        np.array: Criterion value(s) for the image.
    """
    if image.mode != 'RGB':
        image = image.convert('RGB')
    pixels = np.array(image).reshape(-1, 3) / 255.0  # Normalize to [0, 1]

    if criterion in ['hue', 'value', 'hue-value']:
        hsv_pixels = rgb2hsv(pixels.reshape(-1, 1, 3)).reshape(-1, 3)
        color = None
        if mode == 'average':
            color = np.mean(hsv_pixels, axis=0)
        elif mode == 'dominant':
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                kmeans = KMeans(n_clusters=3, random_state=0).fit(hsv_pixels)
                # Find the largest cluster
                labels = kmeans.labels_
                cluster_sizes = np.bincount(labels)
                dominant_cluster = np.argmax(cluster_sizes)
                color = kmeans.cluster_centers_[dominant_cluster]
        if criterion == 'hue':
            return color[0]
        elif criterion == 'value':
            return color[2]
        elif criterion == 'hue-value':
            return np.array([color[0], color[2]])

    elif criterion == 'lab':
        lab_pixels = rgb2lab(pixels.reshape(-1, 1, 3)).reshape(-1, 3)
        if mode == 'average':
            return np.mean(lab_pixels, axis=0)
        elif mode == 'dominant':
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                kmeans = KMeans(n_clusters=3, random_state=0).fit(lab_pixels)
                # Find the largest cluster
                labels = kmeans.labels_
                cluster_sizes = np.bincount(labels)
                dominant_cluster = np.argmax(cluster_sizes)
                return kmeans.cluster_centers_[dominant_cluster]

    raise ValueError("Invalid criterion or mode")

def get_mode_color(image, mode='average', criterion='hue'):
    """
    Compute the specified criterion for an image.

    Parameters:
        image (str): a PIL Image.
        mode (str): 'average' for average pixel values or 'dominant' for dominant colors.
        criterion (str): Criterion to compute ('hue', 'value', 'hue-value', 'lab').

    Returns:
        mode_color: Mode color for the image.
    """
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    pixels = np.array(image).reshape(-1, 3) / 255.0  # Normalize to [0, 1]

    if criterion in ['hue', 'value', 'hue-value']:
        pixels = rgb2hsv(pixels.reshape(-1, 1, 3)).reshape(-1, 3)
    elif criterion == 'lab':
        pixels = rgb2lab(pixels.reshape(-1, 1, 3)).reshape(-1, 3)

    if mode == 'average':
        return np.mean(pixels, axis=0)
    elif mode == 'dominant':
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            kmeans = KMeans(n_clusters=3, random_state=0).fit(pixels)
            # Find the largest cluster
            labels = kmeans.labels_
            cluster_sizes = np.bincount(labels)
            dominant_cluster = np.argmax(cluster_sizes)
            return kmeans.cluster_centers_[dominant_cluster]

    raise ValueError("Invalid criterion or mode")

def estimate_clusters(criteria_values, max_clusters=10):
    """
    Estimate the optimal number of clusters for the given list of images.

    Parameters:
        criteria_values (list): List of criterion values.
        max_clusters (int): Maximum number of clusters to test.

    Returns:
        int: Optimal number of clusters.
    """
    best_clusters = 2
    best_score = -1

    for k in range(2, max_clusters + 1):
        kmeans = KMeans(n_clusters=k, random_state=42).fit(criteria_values)
        score = silhouette_score(criteria_values, kmeans.labels_)
        if score > best_score:
            best_score = score
            best_clusters = k

    return best_clusters

def color_distance(color1, color2, metric):
    if "hue" in metric or "value" in metric:
        if metric == "hue":
            return min(abs(color1[0] - color2[0]), 1 - abs(color1[0] - color2[0]))
        elif metric == "value":
            return min(abs(color1[2] - color2[2]), 1 - abs(color1[2] - color2[2]))
        else:
            min_hue_diff = min(abs(color1[0] - color2[0]), 1 - abs(color1[0] - color2[0]))
            min_val_diff = min(abs(color1[2] - color2[2]), 1 - abs(color1[2] - color2[2]))
            return np.sqrt(min_hue_diff ** 2 + min_val_diff ** 2)
    else:
        c1 = LabColor(*color1)
        c2 = LabColor(*color2)
        if metric == "CIE1976":
            return delta_e_cie1976(c1, c2)
        elif metric == "CIE1994":
            # using textiles weights
            return delta_e_cie1994(c1, c2, K_1=0.048, K_2=0.014, K_L=2)
        elif metric == "CIE2000":
            return delta_e_cie2000(c1, c2)
        elif metric == "CMC":
            return delta_e_cmc(c1, c2)
        else:
            raise ValueError(f"Unknown metric: {metric}")

def group_images(fabric_list, n_clusters=None, criterion='hue', mode='average'):
    """
    Group images into clusters based on the specified criterion.

    Parameters:
        fabric_list (list): List of fabrics.
        n_clusters (int or None): Number of clusters. If None, estimate the optimal number.
        criterion (str): Criterion for clustering ('hue', 'value', 'hue-value', 'lab').
        mode (str): 'average' or 'dominant'.
        equal_ranges (bool): If True, split the range into equal intervals; otherwise, split into equal-sized groups.

    Returns:
        list of lists: Grouped image file paths.
    """
    criteria_values = [compute_criteria(fabric['img'], mode, criterion) for fabric in fabric_list]
    criteria_values = [np.linalg.norm(value) if isinstance(value, np.ndarray) else value for value in criteria_values]
    criteria_values = np.array(criteria_values).reshape(-1, 1)
    if n_clusters is None:
        n_clusters = estimate_clusters(criteria_values)

    cluster_labels = None
    # Compute the distance matrix
    num_images = len(fabric_list)
    colors = [get_mode_color(fabric['img'], mode, criterion) for fabric in fabric_list]
    distance_matrix = np.zeros((num_images, num_images))
    if criterion == 'lab': criterion = 'CIE1994'
    for i in range(num_images):
        for j in range(i + 1, num_images):
            dist = color_distance(colors[i], colors[j], metric=criterion)
            distance_matrix[i, j] = distance_matrix[j, i] = dist
    # Use hierarchical clustering with the precomputed distance matrix
    clustering = AgglomerativeClustering(
        n_clusters=n_clusters, metric="precomputed", linkage="average"
    )
    cluster_labels = clustering.fit_predict(distance_matrix)

    # Create groups based on cluster labels
    groups = [[] for _ in range(n_clusters)]
    for fabric, value in zip(fabric_list, cluster_labels):
        fabric.pop('img')
        groups[value].append(fabric)

    return groups
