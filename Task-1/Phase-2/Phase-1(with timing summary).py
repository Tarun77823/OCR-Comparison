#importing libraries
import os
import cv2
from PIL import Image
import pytesseract
from pytesseract import Output
import re
import time

#path configuration
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASK1_ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))
IMAGE_FOLDER = os.path.join(TASK1_ROOT, "images")

#timing
start_time = time.time()
processed_count = 0

# functions
def edit_distance(a, b):  # function to calculate edit distance
    dp = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        prev = dp[0]
        dp[0] = i
        for j, cb in enumerate(b, 1):
            cur = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + (ca != cb))
            prev = cur
    return dp[-1]  # return final distance value

def confidence(img):  # function to calculate confidence score
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    confs = [c for c in data["conf"] if isinstance(c, int) and c >= 0]
    return sum(confs) / max(len(confs), 1)

def count_chars(text): return len(text)  # character count
def count_words(text): return len(text.split())  # word count
def count_numbers(text): return len(re.findall(r"\d+", text))  # number count
def count_specials(text): return len(re.findall(r"[^\w\s]", text))  # special characters
def count_lines(text): return len(text.splitlines())  # line count

for image_name in os.listdir(IMAGE_FOLDER):  # loop images
    if not image_name.lower().endswith((".jpg", ".jpeg", ".png")):
        continue

    IMAGE_PATH = os.path.join(IMAGE_FOLDER, image_name)  # image path
    print(f"IMAGE: {image_name}")  # image name

    # Traditional OCR
    raw_image = Image.open(IMAGE_PATH)
    traditional_text = pytesseract.image_to_string(raw_image).strip()

    # AI-Vision OCR (preprocessing + tesseract)
    img = cv2.imread(IMAGE_PATH)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    processed = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )
    vision_text = pytesseract.image_to_string(processed).strip()

    # counting processed images
    processed_count += 1

    # Comparison table
    metrics = [
        ("Characters", count_chars(traditional_text), count_chars(vision_text)),
        ("Words", count_words(traditional_text), count_words(vision_text)),
        ("Edit Distance", edit_distance(traditional_text, vision_text), "-"),
        ("Confidence Score", f"{confidence(raw_image):.2f}", f"{confidence(processed):.2f}"),
        ("Numeric Count", count_numbers(traditional_text), count_numbers(vision_text)),
        ("Special Characters", count_specials(traditional_text), count_specials(vision_text)),
        ("Line Count (Structure)", count_lines(traditional_text), count_lines(vision_text)),
    ]

    print("\nPhase1")

    print("\nTraditional OCR output")
    print(traditional_text)

    print("\nAi-Vision output")
    print(vision_text)

    print("\nComparision Table")
    print(f"{'Metric':25} {'Traditional OCR':20} {'AI-Vision OCR'}")

    for m in metrics:
        print(f"{m[0]:25} {str(m[1]):20} {m[2]}")

    print("\nFinal Decision")
    if len(vision_text) > len(traditional_text):
        print("AI-Vision Ocr is Best")
        print("Reason:Vision preprocessing improved text extraction quality.")
    elif len(traditional_text) > len(vision_text):
        print("Traditional OCR is best")
        print("Reason:Image was already clean; preprocessing added no benefit.")
    else:
        print("Both methods Give same Result")

#Timing and to caluculate seconds per image
end_time = time.time()
total_seconds = end_time - start_time
seconds_per_image = total_seconds / max(processed_count, 1)

print("\nTiming Summary")
print("Images processed:", processed_count)
print("Total seconds:", round(total_seconds, 2))
print("Seconds per image:", round(seconds_per_image, 4))
