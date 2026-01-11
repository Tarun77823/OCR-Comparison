import os
import time
import math
import cv2
from PIL import Image
import pytesseract
from pytesseract import Output
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
IMAGE_FOLDER = "images"

# Phase-1 Timing summary
SECONDS_PER_IMAGE = 0.6638
OVERHEAD = 1.25

# Costs(Rough Assumptions)
CPU_COST_PER_VCPU_HOUR = 0.04
API_COST_PER_IMAGE = 0.01
SECONDS_PER_DAY = 86400

VOLUMES = [
    ("1/day", 1),
    ("1/min", 1 * 60 * 24),
    ("1,000/min", 1000 * 60 * 24),
    ("100,000/min", 100000 * 60 * 24),
]

#thresholds(Phase-3)
ACCEPT_CONF = 85.0
ESCALATE_CONF = 60.0
def confidence(img) -> float:
    
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    confs = []
    for c in data.get("conf", []):
        try:
            c = float(c)
            if c >= 0:
                confs.append(c)
        except:
            pass
    return sum(confs) / max(len(confs), 1)


def preprocess_cv(image_path: str):
    img = cv2.imread(image_path)
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
    return processed


def workers_needed(images_per_day: int) -> int:
    sec = images_per_day * SECONDS_PER_IMAGE * OVERHEAD
    return max(1, math.ceil(sec / SECONDS_PER_DAY))


def library_cost_per_day(workers: int) -> float:
    return workers * CPU_COST_PER_VCPU_HOUR * 24


def api_cost_per_day(images_per_day: int, escalation_rate: float) -> float:
    return images_per_day * escalation_rate * API_COST_PER_IMAGE


def flags(workers: int, api_cost: float) -> str:
    f = []
    if workers >= 500:
        f.append("BREAK: huge worker fleet")
    elif workers >= 50:
        f.append("WARN: many workers")

    if api_cost >= 100000:
        f.append("BREAK: API cost explosion")
    elif api_cost >= 1000:
        f.append("WARN: high API spend")

    return " | ".join(f) if f else "OK"
# Phase-3 
def main():
    print("\nPHASE 3 - Hybrid OCR (Library-first + confidence routing + API fallback)\n")

    print("Using Phase-1 timing summary:")
    print(f"  seconds per image = {SECONDS_PER_IMAGE}")
    print("\nCosts (rough):")
    print(f"  overhead = {OVERHEAD}")
    print(f"  CPU $ per vCPU hour = ${CPU_COST_PER_VCPU_HOUR}")
    print(f"  API $ per image = ${API_COST_PER_IMAGE}")
    print("\nConfidence thresholds:")
    print(f"  Accept if conf >= {ACCEPT_CONF}")
    print(f"  Escalate to API if conf < {ESCALATE_CONF} after retry\n")

    start_time = time.time()

    total = 0
    accepted_raw = 0
    accepted_retry = 0
    escalated_api = 0
    accepted_weak = 0

    # Per-image routing history
    print("Per-image routing:")
    print(f"{'Image':30} {'RawConf':>8} {'RetryConf':>9} {'Decision'}")
    print("-" * 70)

    for image_name in os.listdir(IMAGE_FOLDER):
        if not image_name.lower().endswith((".jpg", ".jpeg", ".png")):
            continue

        total += 1
        path = os.path.join(IMAGE_FOLDER, image_name)

        # 1) Raw OCR
        raw_img = Image.open(path)
        raw_conf = confidence(raw_img)

        retry_conf = None

        if raw_conf >= ACCEPT_CONF:
            accepted_raw += 1
            decision = "ACCEPT_RAW"

        else:
            # 2) Retry with preprocessing
            processed = preprocess_cv(path)
            retry_conf = confidence(processed)

            if retry_conf >= ACCEPT_CONF:
                accepted_retry += 1
                decision = "ACCEPT_RETRY"
            else:
                best = max(raw_conf, retry_conf)

                if best < ESCALATE_CONF:
                    escalated_api += 1
                    decision = "ESCALATE_API"
                else:
                    accepted_weak += 1
                    decision = "ACCEPT_WEAK"

        print(f"{image_name:30} {raw_conf:8.2f} {('' if retry_conf is None else f'{retry_conf:9.2f}'):>9} {decision}")

    elapsed = time.time() - start_time

    escalation_rate = (escalated_api / total) if total else 0.0

    print("\nRouting Summary:")
    print("  total images:", total)
    print("  accepted raw:", accepted_raw)
    print("  accepted after retry:", accepted_retry)
    print("  escalated to API:", escalated_api)
    print("  accepted but weak:", accepted_weak)
    print("  escalation rate:", f"{escalation_rate*100:.2f}%")
    print("  run time (sec):", round(elapsed, 2))

    # Hybrid cost table 
    print("\nHybrid Cost Table (Traditional OCR for all + AI only for escalations)\n")
    print(f"{'Volume':12} {'Images/day':12} {'Workers':8} {'Library $/day':14} {'API $/day':14} {'Total $/day':14} {'Notes'}")
    print("-" * 95)

    for label, imgs_day in VOLUMES:
        w = workers_needed(imgs_day)
        lib = library_cost_per_day(w)
        api = api_cost_per_day(imgs_day, escalation_rate)
        total_cost = lib + api
        note = flags(w, api)

        print(f"{label:12} {imgs_day:<12,} {w:<8} ${lib:<13,.2f} ${api:<13,.2f} ${total_cost:<13,.2f} {note}")

    print("\nDone.\n")


if __name__ == "__main__":
    main()
