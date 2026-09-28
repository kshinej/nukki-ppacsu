"""
Configuration settings for Video-to-Lottie Converter.
"""

# Video Input Constraints
MAX_DURATION_SECONDS = 10.0

# Background Color Detection
# Percentage of image width/height sampled from each corner (0.03 to 0.05 recommended)
CORNER_SAMPLE_RATIO = 0.04
# Frame sample checkpoints (fractions of total duration) for validation
VALIDATION_CHECKPOINTS = [0.0, 0.25, 0.50, 0.75, 1.0]

# Background Removal / Mask Settings
BACKGROUND_THRESHOLD = 35.0  # Color distance threshold in LAB space
SOFT_THRESHOLD_DELTA = 10.0  # Soft transition range for alpha edge smoothing
MORPH_KERNEL_SIZE = 3        # Size of morphological filter kernel (e.g., 3x3)

# Edge & Halo Cleanup Settings (Fixes dark/light border halos around background)
DEFAULT_EDGE_TRIM = 1        # Pixels to shrink mask inward (0~5px) to slice off compression halos
DEFAULT_EDGE_BLUR = 0        # Gaussian feathering blur radius (0~7px) for smooth edges

# Contour Extraction & Simplification
MIN_CONTOUR_AREA_RATIO = 0.0005  # Minimum area ratio (0.05% of total frame area)
CONTOUR_EPSILON_RATIO = 0.002    # Epsilon ratio for cv2.approxPolyDP relative to arc length

# Lottie Output Settings
DEFAULT_TARGET_FPS = 30
COORDINATE_PRECISION = 2        # Round float coordinates to N decimal places
DEFAULT_FILL_COLOR = [1.0, 1.0, 1.0, 1.0]  # RGBA normalized (0.0 ~ 1.0)

# Paths
INPUT_DIR = "input"
OUTPUT_DIR = "lottie-output"
DEBUG_DIR = "debug"
