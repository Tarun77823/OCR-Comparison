# Phase3 — Production Thinking (Hybrid Strategy)

# (1)Hybrid Routing Explanation (Library-first + API fallback)

# Why hybrid
At scale, running every image through an AI vision API can become expensive and harder to control. Running only a library can be cheap but will fail on some low-quality images. The hybrid approach uses the library as the default and only escalates to an API when needed.

# Routing steps
1. Ingest image → store raw image
2. Run OCR library (Tesseract/Paddle/EasyOCR)
3. Compute confidence score from OCR output
4. Decide:
   - If confidence is good → accept library output
   - If confidence is low → send to AI OCR API (fallback)
5. Store final text + confidence + method used (library or API)

This Approach controls cost because only a small portion of hard images go to the API.

# (2) Confidence thresholds
These are practical thresholds :

- Confidence >= 85  → ACCEPT (library result)
- Confidence 60–85  → RETRY ONCE (optional: preprocessing / different OCR settings)
- Confidence < 60   → ESCALATE to AI API

Notes:
- Confidence is taken from OCR word/line confidence.
- Escalation rate = escalated_images / total_images.
- The key metric for cost is escalation rate. Even small escalation % matters at high scale.

# (3) Retry / fallback logic
- Maximum attempts per image:
  - 1 library pass
  - 1 retry pass (only if medium confidence)
  - 1 API fallback pass (only if there is low confidence)
- If API call fails (timeout / error):
  - mark as FAILED_API
  - send to manual review queue

This gives reliability and avoids infinite retries.

# (4) CPU vs GPU decision points 
- run OCR library workers on CPU.
- Use GPU only if:
  - you switch to a GPU-optimized OCR model AND
  - throughput becomes a bottleneck at high volume.
- AI API fallback is separate from CPU/GPU decisions (API cost is Mainly taken from Escalation Rate).

# (5) Updated Architecture Diagram (Hybrid)
## Updated Architecture (Hybrid OCR)

+--------------------+
|   Image Upload     |
+--------------------+ |
          v
+--------------------+
|  OCR Library       |
|  (CPU Workers)     |
+--------------------+
          |
          v
+--------------------+
| Confidence Check   |
+--------------------+
     |           |
     |           |
     |           v
     |     +--------------------+
     |     |  AI OCR API        |
     |     |  (Fallback)        |
     |     +--------------------+
     |               |
     |               v
     |     +--------------------+
     |     |  Store Result      |
     |     |  (Text + Conf)     |
     |     +--------------------+
     |
     v
+--------------------+
| Accept Library OCR |
+--------------------+
          |
          v
+--------------------+
|  Store Result      |
|  (Text + Conf)     |
+--------------------+

Decision:
- Confidence >= 60  → Accept Library OCR
- Confidence < 60   → Escalate to AI OCR API

# (6) Clear Recommendation for MeCentral
Recommendation:
- Use a library-first OCR pipeline for the majority of images.
- Add confidence-based routing so only low-confidence cases go to an AI OCR API.
- Track escalation rate, latency, and cost per image.
- Start with CPU workers for library OCR and only consider GPU if throughput becomes the bottleneck.

Reason:
This approach is reliable, keeps cost under control, and scales better while still handling hard images through fallback.
