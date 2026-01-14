# Phase 1 – OCR Comparison (Traditional OCR vs AI-Vision OCR)

This project compares **Traditional OCR** with an **AI-Vision OCR** to understand where OCR systems fail and how vision preprocessing improves text extraction.

## Objective
To compare two OCR approaches on real-world images and analyze their performance using multiple quality metrics.

## Approaches Compared

### (1)Traditional OCR
- Raw image is directly passed to the OCR engine (Tesseract).
- Works well on clean, scanned documents.
- Struggles with noisy, low-quality, or unevenly lit images.

### (2)AI-Vision OCR
- Image is preprocessed using OpenCV (grayscale, denoising, adaptive thresholding).
- The processed image is then passed to Tesseract OCR.
- Improves robustness on real-world images.

## Parameters(Metrics) Used
For each image, the following metrics are reported:

- Character count
- Word count
- Edit distance between OCR outputs
- Average OCR confidence score
- Numeric detection count
- Special character detection count
- Line count (structural accuracy)

