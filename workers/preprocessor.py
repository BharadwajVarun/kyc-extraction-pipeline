<<<<<<< HEAD
import cv2
import numpy as np


def load_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image from {image_path}")
    return image


def convert_to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def remove_noise(gray_image):
    return cv2.GaussianBlur(gray_image, (3, 3), 0)


def apply_threshold(blurred_image):
    return cv2.adaptiveThreshold(
        blurred_image, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )


def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess(image_path):
    image = load_image(image_path)
    gray = convert_to_grayscale(image)
    blurred = remove_noise(gray)
    thresholded = apply_threshold(blurred)
    deskewed = deskew(thresholded)
    return deskewed


def save_image(image, output_path):
    cv2.imwrite(output_path, image)
    print(f"Saved preprocessed image to {output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python preprocessor.py <input_path> <output_path>")
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    result = preprocess(input_path)
    save_image(result, output_path)
=======
import cv2
import numpy as np


def load_image(image_path):
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not load image from {image_path}")
    return image


def convert_to_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def remove_noise(gray_image):
    return cv2.GaussianBlur(gray_image, (3, 3), 0)


def apply_threshold(blurred_image):
    return cv2.adaptiveThreshold(
        blurred_image, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 11, 2
    )


def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        image, matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE
    )
    return rotated


def preprocess(image_path):
    image = load_image(image_path)
    gray = convert_to_grayscale(image)
    blurred = remove_noise(gray)
    thresholded = apply_threshold(blurred)
    deskewed = deskew(thresholded)
    return deskewed


def save_image(image, output_path):
    cv2.imwrite(output_path, image)
    print(f"Saved preprocessed image to {output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python preprocessor.py <input_path> <output_path>")
        sys.exit(1)
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    result = preprocess(input_path)
    save_image(result, output_path)
>>>>>>> f530946c4cd212f289bf5f1a8ec9a691424f0225
    print("Preprocessing complete.")