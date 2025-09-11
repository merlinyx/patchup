import sys
import cv2
import matplotlib.pyplot as plt

def process_scrap_image(image_path, n_fabric_pieces=1, erosion_kernel_size=5, erosion_iterations=3, kernel_size=41):
    # Load the image
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    # Define the erosion kernel
    erosion_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (erosion_kernel_size, erosion_kernel_size))
    # Apply erosion
    eroded = cv2.erode(gray, erosion_kernel, iterations=erosion_iterations)
    blur = cv2.GaussianBlur(eroded, (kernel_size, kernel_size), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, kernel_size, 1)
    
    # Find contours
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = list(filter(lambda c: cv2.contourArea(c) > 0.001 * thresh.shape[0] * thresh.shape[1], contours))
    # Optionally approximate contours to reduce the number of points
    approx_contours = [cv2.approxPolyDP(contour, 0.01 * cv2.arcLength(contour, True), True) for contour in contours]
    # Take the n contours
    topn_contours = sorted(approx_contours, key=lambda x: cv2.contourArea(x), reverse=True)[:n_fabric_pieces]
    topn_hulls = [cv2.convexHull(contour) for contour in topn_contours]
    contour_image = image.copy()
    cv2.drawContours(contour_image, topn_hulls, -1, (255, 255, 255), 3)

    # List to hold rectangles and their centers
    rectangles = []
    # Calculate minimum area rectangle for each contour
    for contour in topn_contours:
        rect = cv2.minAreaRect(contour)
        center = rect[0]
        rectangles.append((rect, center))
    # Sort rectangles first by y then by x coordinate of the center
    rectangles.sort(key=lambda x: (int(x[1][1]), int(x[1][0])))

    # Extract and show sorted images
    cropped_images = []
    for rect, _ in rectangles:
        # To crop the rotated rectangle correctly, we need to apply a rotation
        center = rect[0]
        width = int(rect[1][0])
        height = int(rect[1][1])
        angle = rect[2]

        # Now crop the rotated rectangle
        x = int(center[0] - width / 2)
        y = int(center[1] - height / 2)
        # Note that it could return negative values if the rectangle is out of bounds
        if x < 0:
            center = center[0] - x, center[1]
            x = 0
        if y < 0:
            center = center[0], center[1] - y
            y = 0
        # Rotate the image around the center
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (image.shape[1], image.shape[0]))

        cropped = rotated[y:y+height, x:x+width]
        cropped_images.append(cropped)

    return contour_image, cropped_images

if __name__ == '__main__':
    image_path = sys.argv[1]
    contour_image, cropped_images = process_scrap_image(image_path, n_fabric_pieces=int(sys.argv[2]))
    output_path = sys.argv[1].split('.')[0] + '_overlay.png'
    plt.imshow(cv2.cvtColor(contour_image, cv2.COLOR_BGR2RGB))
    plt.axis('off')
    plt.savefig(output_path, bbox_inches='tight', pad_inches=0)
