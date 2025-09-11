import cv2

def meanshift(image_path, spatial_radius, color_radius,
              output_segmented, output_filtered, num_iters = 100):
    img = cv2.imread(image_path)
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = cv2.pyrMeanShiftFiltering(img, spatial_radius, color_radius)
    cv2.imwrite(output_filtered, img)
