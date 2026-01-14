import os
import time
import cv2
from PIL import Image
import pytesseract
from pytesseract import Output

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
IMAGE_FOLDER = "images"

ACCEPT_CONF = 85.0
ESCALATE_CONF = 60.0
AI_RETRIES = 2   # AI fallback attempts

def confidence_score(img) -> float:
    data = pytesseract.image_to_data(img, output_type=Output.DICT)
    confs = []
    for c in data.get("conf", []):
        try:
            cf = float(c)
            if cf >= 0:
                confs.append(cf)
        except:
            pass
    return sum(confs) / max(len(confs), 1)

def preprocess_cv(image_path: str):
    img = cv2.imread(image_path)
    if img is None:
        return None
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    processed = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 11
    )
    return processed

def main():
    print("\nPHASE 3 - Hybrid OCR + retries + scrap detection\n")
    print(f"Accept if conf >= {ACCEPT_CONF}")
    print(f"Escalate if best(conf) < {ESCALATE_CONF}")
    print(f"AI retries allowed = {AI_RETRIES}\n")

    image_list = sorted([
        f for f in os.listdir(IMAGE_FOLDER)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ])

    latencies = []
    total = 0
    scrap = 0

    print(f"{'Image':30} {'Raw':>7} {'Retry':>7} {'AI':>7} {'Decision'}")
    print("-" * 75)

    start_all = time.time()

    for image_name in image_list:
        t0 = time.time()
        total += 1

        path = os.path.join(IMAGE_FOLDER, image_name)

        raw_img = Image.open(path)
        raw_conf = confidence_score(raw_img)

        retry_conf = None
        ai_conf = None

        # Step 1: raw
        if raw_conf >= ACCEPT_CONF:
            decision = "ACCEPT_RAW"

        else:
            # Step 2: retry with preprocess
            processed = preprocess_cv(path)
            if processed is not None:
                retry_conf = confidence_score(processed)

            best_local = max(raw_conf, retry_conf if retry_conf is not None else -1)

            if best_local >= ACCEPT_CONF:
                decision = "ACCEPT_RETRY"

            elif best_local < ESCALATE_CONF:
                
                decision = "ESCALATE_AI"

                best_ai = best_local
                for attempt in range(1, AI_RETRIES + 1):
                    if processed is None:
                        break
                    tmp_conf = confidence_score(processed)
                    best_ai = max(best_ai, tmp_conf)
                    ai_conf = tmp_conf

                    if best_ai >= ACCEPT_CONF:
                        decision = f"ACCEPT_AI_ATTEMPT_{attempt}"
                        break

                if best_ai < ACCEPT_CONF:
                    scrap += 1
                    decision = "SCRAP_IMAGE (send to DLQ/manual review)"
                    print(f" {image_name} looks unusable even after retries.")

            else:
                decision = "ACCEPT_WEAK (borderline but usable)"

        t1 = time.time()
        latencies.append(t1 - t0)

        raw_s = f"{raw_conf:7.2f}"
        retry_s = f"{retry_conf:7.2f}" if retry_conf is not None else "   -   "
        ai_s = f"{ai_conf:7.2f}" if ai_conf is not None else "   -   "
        print(f"{image_name:30} {raw_s} {retry_s} {ai_s} {decision}")

    elapsed_all = time.time() - start_all
    avg_latency = sum(latencies) / max(len(latencies), 1)
    throughput = total / max(elapsed_all, 1e-9)

    # simple p95
    lat_sorted = sorted(latencies)
    p95 = lat_sorted[int(0.95 * (len(lat_sorted) - 1))] if lat_sorted else 0

    print("\nPerformance Summary:")
    print("  total images:", total)
    print("  avg latency (sec):", round(avg_latency, 4))
    print("  p95 latency (sec):", round(p95, 4))
    print("  throughput (images/sec):", round(throughput, 2))
    print("  scrap images:", scrap)

if __name__ == "__main__":
    main()
