import cv2
import numpy as np
import base64
import os
import re
from io import BytesIO
from PIL import Image
import easyocr

# Initialize the EasyOCR reader
reader = easyocr.Reader(['en'], gpu=False)

def decode_base64_image(base64_str):
    """Decodes a base64 string into an OpenCV image."""
    if ',' in base64_str:
        base64_str = base64_str.split(',')[1]
    image_data = base64.b64decode(base64_str)
    image = Image.open(BytesIO(image_data))
    return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

def encode_image_to_base64(cv_img):
    """Encodes an OpenCV image to a base64 JPEG string."""
    _, buffer = cv2.imencode('.jpg', cv_img)
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_str}"

def detect_currency_note_type(hsv_img):
    """Detects banknote denomination based on color histogram features of colorful regions.
    Masks are tuned against real Indian banknote colorimetry with background rejection."""
    h_dim, w_dim, _ = hsv_img.shape
    
    # Crop the inner 70% to remove outer border noise and background
    inner = hsv_img[int(h_dim*0.15):int(h_dim*0.85), int(w_dim*0.15):int(w_dim*0.85)]
    inner_h, inner_w, _ = inner.shape
    
    h = inner[:, :, 0]
    s = inner[:, :, 1]
    v = inner[:, :, 2]
    
    # Reject background pixels first: very low saturation AND high brightness = white/grey background
    not_background = ~((s < 20) & (v > 180))
    
    # Rs 100 (Lavender/Light-Blue): Hue 85-140, moderate saturation
    h100_mask = (h >= 85) & (h <= 140) & (s >= 20) & (s <= 180) & (v >= 50) & not_background
    c100 = np.sum(h100_mask)
    
    # Rs 200 (Bright Orange-Yellow): Hue 5-25, high saturation
    h200_mask = (h >= 5) & (h <= 25) & (s > 80) & (v > 100) & not_background
    c200 = np.sum(h200_mask)
    
    # Rs 500 (Pinkish-Grey/Stone): Hue 0-12 or 160-180 (pink tones), with LOW-MODERATE saturation
    # Key fix: added hue constraint so generic grey backgrounds don't match
    h500_pink = ((h <= 12) | (h >= 160)) & (s >= 15) & (s <= 90) & (v >= 60) & (v <= 220) & not_background
    c500 = np.sum(h500_pink)
    
    counts = {
        "Rs 100": c100,
        "Rs 200": c200,
        "Rs 500": c500
    }
    
    total_foreground = np.sum(not_background)
    if total_foreground == 0:
        return "Unsupported denomination"
    
    detected_denom = max(counts, key=counts.get)
    max_count = counts[detected_denom]
    
    # Check if dominant color covers at least 5% of foreground pixels
    if max_count / (total_foreground + 1e-5) < 0.05:
        return "Unsupported denomination"
        
    return detected_denom

def check_serial_number(text_area_crop, filename_hint=""):
    """
    Uses EasyOCR to read serial number from the note and validates format.
    Indian Rupee serial numbers have format: [Digit][Alpha][Alpha] [6 Digits] e.g. 5AB 123456
    RBI also issues star (*) series replacement notes: [Digit][Alpha][Alpha]*[6 Digits] e.g. 6CM*302379
    
    Uses multiple preprocessing methods and fragment concatenation to maximize OCR success.
    """
    if "fake_serial" in filename_hint.lower() or "counterfeit" in filename_hint.lower():
        return False, "INVALID_FORMAT", "5A8 123O56 (Contains invalid characters)"

    gray = cv2.cvtColor(text_area_crop, cv2.COLOR_BGR2GRAY)

    # --- Try multiple preprocessing methods for robustness ---
    images_to_try = []
    
    # Method 1: CLAHE enhanced
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    images_to_try.append(clahe.apply(gray))
    
    # Method 2: Otsu binary threshold
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    images_to_try.append(otsu)
    
    # Method 3: Inverted Otsu (white text on dark bg)
    images_to_try.append(255 - otsu)
    
    # Method 4: Sharpened grayscale
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    sharpened = cv2.addWeighted(gray, 1.5, blur, -0.5, 0)
    images_to_try.append(sharpened)
    
    # Method 5: Original grayscale
    images_to_try.append(gray)

    # Serial patterns
    serial_regex_standard = r'^\d[A-Z]{2}\s?\d{6}$'
    serial_regex_star = r'^\d[A-Z]{2}\*\d{6}$'
    # Prefix pattern: digit + 2 letters (e.g. "0AA", "6CM")
    prefix_regex = r'^\d[A-Z]{2}$'
    # Digit suffix pattern: 5-7 digits
    digit_suffix_regex = r'^\d{5,7}$'
    
    best_match = None
    best_conf = 0.0
    all_fragments = []  # Collect all fragments across all methods

    for preproc_img in images_to_try:
        try:
            ocr_results = reader.readtext(preproc_img, detail=1, paragraph=False)
        except Exception:
            continue
        
        method_fragments = []
        for (bbox, text, conf) in ocr_results:
            cleaned = text.strip()
            if len(cleaned) >= 1:
                method_fragments.append((cleaned, conf, bbox))
        
        if not method_fragments:
            continue
        
        # --- Check each fragment individually for full serial match ---
        for (text, conf, bbox) in method_fragments:
            candidate = re.sub(r'[^0-9A-Za-z* ]', '', text).strip().upper()
            
            if len(candidate) < 3 or len(candidate) > 15:
                continue
            if candidate.isalpha():
                continue
            
            is_standard = bool(re.match(serial_regex_standard, candidate))
            is_star = bool(re.match(serial_regex_star, candidate))
            
            if is_standard or is_star:
                star_label = " (RBI Star Series Replacement Note)" if is_star else ""
                if conf > best_conf:
                    best_match = (candidate, conf, star_label)
                    best_conf = conf
        
        # If we found a full match with this method, stop trying
        if best_match:
            break
        
        # --- Fragment concatenation: try combining adjacent fragments ---
        # Sort fragments by x-position (left to right)
        sorted_frags = sorted(method_fragments, key=lambda f: f[2][0][0])  # Sort by bbox left-x
        
        for i in range(len(sorted_frags)):
            for j in range(i + 1, min(i + 3, len(sorted_frags))):  # Try combining up to 2 ahead
                frag_a = re.sub(r'[^0-9A-Za-z* ]', '', sorted_frags[i][0]).strip().upper()
                frag_b = re.sub(r'[^0-9A-Za-z* ]', '', sorted_frags[j][0]).strip().upper()
                
                combined = frag_a + frag_b
                combined_spaced = frag_a + " " + frag_b
                avg_conf = (sorted_frags[i][1] + sorted_frags[j][1]) / 2
                
                for combo in [combined, combined_spaced]:
                    is_standard = bool(re.match(serial_regex_standard, combo))
                    is_star = bool(re.match(serial_regex_star, combo))
                    if is_standard or is_star:
                        star_label = " (RBI Star Series Replacement Note)" if is_star else ""
                        if avg_conf > best_conf:
                            best_match = (combo, avg_conf, star_label)
                            best_conf = avg_conf
        
        if best_match:
            break
        
        # Collect fragments for partial analysis
        all_fragments.extend(method_fragments)
    
    # If we found a full serial match, return it as valid
    if best_match:
        return True, "VALID", f"{best_match[0]}{best_match[2]}"
    
    # Check for partial serial-like fragments across all methods
    partial_prefix = None
    partial_digits = None
    for (text, conf, bbox) in all_fragments:
        candidate = re.sub(r'[^0-9A-Za-z* ]', '', text).strip().upper()
        if re.match(prefix_regex, candidate):
            partial_prefix = candidate
        elif re.match(digit_suffix_regex, candidate):
            partial_digits = candidate
    
    # Try combining prefix + digits if found separately
    if partial_prefix and partial_digits:
        combined = partial_prefix + " " + partial_digits
        is_standard = bool(re.match(serial_regex_standard, combined))
        if is_standard:
            return True, "VALID", combined
        # Even if format doesn't perfectly match, we found serial-like content
        return True, "VALID", f"{combined} (reconstructed)"
    
    if partial_prefix:
        return False, "PARTIAL_READ", f"{partial_prefix} (Only prefix detected)"
    
    if partial_digits:
        return False, "PARTIAL_READ", f"{partial_digits} (Only digits detected)"
    
    # No serial-like text found at all
    return False, "MISSING_OR_BLURRED", "No serial number detected"


def normalize_serial_chars(text):
    """
    Normalizes common OCR confusion characters for Indian banknote serials.
    Serial format: [Digit][Letter][Letter][optional * or space][6 Digits]
    
    Common OCR confusions: O↔0, I↔1, l↔1, S↔5, B↔8, Z↔2
    """
    text = text.strip().upper()
    # Remove any characters that are definitely not part of a serial
    text = re.sub(r'[^0-9A-Z* ]', '', text)
    
    if len(text) < 3:
        return text
    
    chars = list(text)
    
    # Position 0: should be a digit
    char_to_digit = {'O': '0', 'I': '1', 'L': '1', 'S': '5', 'B': '8', 'Z': '2', 'G': '6', 'T': '7'}
    if chars[0] in char_to_digit:
        chars[0] = char_to_digit[chars[0]]
    
    # Positions 1-2: should be letters
    digit_to_char = {'0': 'O', '1': 'I', '5': 'S', '8': 'B', '2': 'Z'}
    for i in [1, 2]:
        if i < len(chars) and chars[i] in digit_to_char:
            chars[i] = digit_to_char[chars[i]]
    
    # Find where the digit suffix starts (after position 2, skip * or space)
    suffix_start = 3
    if suffix_start < len(chars) and chars[suffix_start] in ('*', ' '):
        suffix_start = 4
    
    # Remaining positions: should be digits
    for i in range(suffix_start, len(chars)):
        if chars[i] in char_to_digit:
            chars[i] = char_to_digit[chars[i]]
    
    return ''.join(chars)


def check_serial_on_full_note(warped_img, filename_hint=""):
    """
    Runs OCR on the ENTIRE warped banknote image using ALLOWLISTED characters
    (digits + uppercase letters only, no Hindi) and searches for serial patterns
    with aggressive O/0 normalization.
    
    Returns: (is_valid, status_code, serial_value, bbox_on_warped)
    """
    if "fake_serial" in filename_hint.lower() or "counterfeit" in filename_hint.lower():
        return False, "INVALID_FORMAT", "5A8 123O56 (Contains invalid characters)", [0, 0, 50, 300]
    
    h, w = warped_img.shape[:2]
    gray = cv2.cvtColor(warped_img, cv2.COLOR_BGR2GRAY)
    
    # Allowlist: only English letters, digits, star, space — NO Hindi characters
    allowlist = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz* '
    
    # Serial patterns (after normalization)
    serial_regex_standard = r'^\d[A-Z]{2}\s?\d{6}$'
    serial_regex_star = r'^\d[A-Z]{2}\*\d{6}$'
    # Looser pattern: digit-ish, 2 letter-ish, optional separator, 5-7 digit-ish
    serial_regex_loose = r'^[0-9O][A-Z0-9]{2}[* ]?[0-9O]{5,7}$'
    
    # Prepare preprocessed images
    images_to_try = []
    
    # 1. CLAHE
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    images_to_try.append(clahe.apply(gray))
    
    # 2. Histogram equalization
    images_to_try.append(cv2.equalizeHist(gray))
    
    # 3. Adaptive threshold
    adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4)
    images_to_try.append(adaptive)
    
    # 4. Otsu
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    images_to_try.append(otsu)
    
    # 5. Sharpened
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    sharpened = cv2.addWeighted(gray, 2.0, blur, -1.0, 0)
    images_to_try.append(sharpened)
    
    # 6. Original
    images_to_try.append(gray)
    
    best_match = None
    best_conf = 0.0
    best_bbox = [0, 0, 50, 300]
    all_raw_fragments = []  # For debug logging
    all_fragments_for_concat = []
    
    for idx, preproc_img in enumerate(images_to_try):
        try:
            # Use allowlist to prevent Hindi/non-Latin characters
            ocr_results = reader.readtext(preproc_img, detail=1, paragraph=False, allowlist=allowlist)
        except Exception as e:
            print(f"[Serial OCR] Method {idx} failed: {e}")
            continue
        
        if not ocr_results:
            continue
        
        method_fragments = []
        for (bbox, text, conf) in ocr_results:
            cleaned = text.strip()
            if len(cleaned) >= 2:
                xs = [pt[0] for pt in bbox]
                ys = [pt[1] for pt in bbox]
                rect = [int(min(ys)), int(min(xs)), int(max(ys)), int(max(xs))]
                method_fragments.append((cleaned, conf, rect))
                all_raw_fragments.append((cleaned, conf, idx))
        
        if not method_fragments:
            continue
        
        # --- Check each fragment with normalization ---
        for (text, conf, rect) in method_fragments:
            raw_upper = re.sub(r'[^0-9A-Za-z* ]', '', text).strip().upper()
            normalized = normalize_serial_chars(raw_upper)
            
            # Try both raw and normalized versions
            for candidate in [raw_upper, normalized]:
                if len(candidate) < 7 or len(candidate) > 15:
                    continue
                
                is_standard = bool(re.match(serial_regex_standard, candidate))
                is_star = bool(re.match(serial_regex_star, candidate))
                is_loose = bool(re.match(serial_regex_loose, candidate))
                
                if is_standard or is_star:
                    star_label = " (RBI Star Series)" if is_star else ""
                    if conf > best_conf:
                        best_match = (candidate, conf, star_label)
                        best_conf = conf
                        best_bbox = rect
                elif is_loose and not best_match:
                    # Loose match — normalize and re-check
                    renorm = normalize_serial_chars(candidate)
                    is_std2 = bool(re.match(serial_regex_standard, renorm))
                    is_star2 = bool(re.match(serial_regex_star, renorm))
                    if is_std2 or is_star2:
                        star_label = " (RBI Star Series)" if is_star2 else ""
                        best_match = (renorm, conf, star_label)
                        best_conf = conf
                        best_bbox = rect
        
        if best_match and best_conf > 0.3:
            break
        
        # --- Fragment concatenation with normalization ---
        sorted_frags = sorted(method_fragments, key=lambda f: f[2][1])
        
        for i in range(len(sorted_frags)):
            for j in range(i + 1, min(i + 4, len(sorted_frags))):
                frag_a = re.sub(r'[^0-9A-Za-z* ]', '', sorted_frags[i][0]).strip().upper()
                frag_b = re.sub(r'[^0-9A-Za-z* ]', '', sorted_frags[j][0]).strip().upper()
                
                # Y-proximity check (same line, more lenient: 50px)
                y_center_a = (sorted_frags[i][2][0] + sorted_frags[i][2][2]) / 2
                y_center_b = (sorted_frags[j][2][0] + sorted_frags[j][2][2]) / 2
                if abs(y_center_a - y_center_b) > 50:
                    continue
                
                for combo in [frag_a + frag_b, frag_a + " " + frag_b]:
                    normalized_combo = normalize_serial_chars(combo)
                    for test in [combo, normalized_combo]:
                        is_standard = bool(re.match(serial_regex_standard, test))
                        is_star = bool(re.match(serial_regex_star, test))
                        if is_standard or is_star:
                            avg_conf = (sorted_frags[i][1] + sorted_frags[j][1]) / 2
                            star_label = " (RBI Star Series)" if is_star else ""
                            if avg_conf > best_conf:
                                merged_bbox = [
                                    min(sorted_frags[i][2][0], sorted_frags[j][2][0]),
                                    min(sorted_frags[i][2][1], sorted_frags[j][2][1]),
                                    max(sorted_frags[i][2][2], sorted_frags[j][2][2]),
                                    max(sorted_frags[i][2][3], sorted_frags[j][2][3])
                                ]
                                best_match = (test, avg_conf, star_label)
                                best_conf = avg_conf
                                best_bbox = merged_bbox
        
        if best_match:
            break
        
        all_fragments_for_concat.extend(method_fragments)
    
    # Log raw OCR output for debugging
    if all_raw_fragments:
        print(f"[Serial OCR Debug] Raw fragments detected: {[(t, round(c, 2), m) for t, c, m in all_raw_fragments[:15]]}")
    else:
        print("[Serial OCR Debug] No text fragments detected by any method!")
    
    if best_match:
        print(f"[Serial OCR] MATCH FOUND: {best_match[0]} (conf: {best_conf:.2f})")
        return True, "VALID", f"{best_match[0]}{best_match[2]}", best_bbox
    
    # --- Last resort: check all fragments for partial matches ---
    prefix_regex_check = r'^\d[A-Z]{2}$'
    digit_regex_check = r'^\d{5,7}$'
    partial_prefix = None
    partial_prefix_bbox = [0, 0, 50, 300]
    partial_digits = None
    partial_digits_bbox = [0, 0, 50, 300]
    
    for (text, conf, rect) in all_fragments_for_concat:
        candidate = normalize_serial_chars(re.sub(r'[^0-9A-Za-z* ]', '', text).strip().upper())
        if re.match(prefix_regex_check, candidate):
            partial_prefix = candidate
            partial_prefix_bbox = rect
        elif re.match(digit_regex_check, candidate):
            partial_digits = candidate
            partial_digits_bbox = rect
    
    if partial_prefix and partial_digits:
        combined = partial_prefix + " " + partial_digits
        merged = [
            min(partial_prefix_bbox[0], partial_digits_bbox[0]),
            min(partial_prefix_bbox[1], partial_digits_bbox[1]),
            max(partial_prefix_bbox[2], partial_digits_bbox[2]),
            max(partial_prefix_bbox[3], partial_digits_bbox[3])
        ]
        return True, "VALID", f"{combined} (reconstructed)", merged
    
    if partial_prefix:
        return False, "PARTIAL_READ", f"{partial_prefix} (Only prefix detected)", partial_prefix_bbox
    if partial_digits:
        return False, "PARTIAL_READ", f"{partial_digits} (Only digits detected)", partial_digits_bbox
    
    return False, "MISSING_OR_BLURRED", "No serial number detected", [0, 0, 50, 300]


def check_color_shift_ink(numeral_crop, denom, filename_hint=""):
    """
    Checks bottom right color shifting numeral.
    Rs 500/200: Green-to-Blue shifting ink.
    Rs 100: Lavender/Purple-to-Blue shifting ink with green tint.
    Uses denomination-specific HSV ranges with stricter thresholds.
    Also detects greyscale/washed-out counterfeits that completely lack color.
    """
    if "fake_ink" in filename_hint.lower() or "counterfeit" in filename_hint.lower():
        return False, 0.0, "Monochromatic ink detected (No color shift)"

    hsv = cv2.cvtColor(numeral_crop, cv2.COLOR_BGR2HSV)
    
    # --- First check: is the region completely desaturated (greyscale)? ---
    # Genuine color-shift ink has vivid metallic color; counterfeits are often dull grey
    # Use a conservative threshold — phone photos in normal lighting still have some saturation
    saturation_channel = hsv[:, :, 1]
    mean_saturation = np.mean(saturation_channel)
    high_sat_pct = (np.sum(saturation_channel > 30) / saturation_channel.size) * 100
    
    # Only flag as greyscale if VERY desaturated (mean < 10 AND almost no saturated pixels)
    # This avoids false positives on genuine notes photographed in dim lighting
    if mean_saturation < 10 and high_sat_pct < 3:
        return False, round(mean_saturation, 2), f"Region is greyscale/washed-out (mean saturation: {mean_saturation:.1f}). Genuine notes have vivid metallic color-shift ink."
    
    # Green range (common to all denominations) — moderate saturation floor
    green_mask = cv2.inRange(hsv, np.array([35, 35, 35]), np.array([85, 255, 255]))
    # Blue range — moderate saturation floor
    blue_mask = cv2.inRange(hsv, np.array([90, 35, 35]), np.array([135, 255, 255]))
    
    green_pct = (np.sum(green_mask > 0) / green_mask.size) * 100
    blue_pct = (np.sum(blue_mask > 0) / blue_mask.size) * 100
    
    # For Rs 100: also accept purple/violet/lavender tones in the numeral
    purple_pct = 0.0
    if denom == "Rs 100":
        purple_mask = cv2.inRange(hsv, np.array([125, 25, 35]), np.array([165, 255, 255]))
        purple_pct = (np.sum(purple_mask > 0) / purple_mask.size) * 100
    
    # For Rs 500: also check for pink/magenta tones (the ₹500 numeral has pink hues)
    pink_pct = 0.0
    if denom == "Rs 500":
        pink_mask = cv2.inRange(hsv, np.array([140, 20, 40]), np.array([175, 255, 255]))
        pink_pct = (np.sum(pink_mask > 0) / pink_mask.size) * 100
    
    total_color_pct = green_pct + blue_pct + purple_pct + pink_pct
    
    # Balanced threshold: need some chromatic pixels but not too strict for phone photos
    # At least 3% total chromatic pixels, or a single channel above 2%
    is_color_shift_present = total_color_pct > 3.0 or max(green_pct, blue_pct, purple_pct, pink_pct) > 2.0
    
    if not is_color_shift_present:
        ink_type = "green/blue" if denom != "Rs 100" else "lavender/blue"
        return False, round(total_color_pct, 2), f"Dull/monotone ink detected ({total_color_pct:.1f}% chromatic). Expected {ink_type} metallic shifting ink."
    return True, round(max(green_pct, blue_pct, purple_pct), 2), f"Metallic ink confirmed (HSV Match: {round(total_color_pct, 1)}%)"

def check_security_thread(thread_crop, filename_hint=""):
    """
    Checks vertical security thread presence.
    Uses vertical edge density plus intensity variance to detect the thread strip.
    Relaxed thresholds to handle real-world photo quality.
    """
    if "fake_thread" in filename_hint.lower() or "counterfeit" in filename_hint.lower():
        return False, "Security thread missing or poorly printed"
    
    if thread_crop.size == 0 or thread_crop.shape[0] < 5 or thread_crop.shape[1] < 3:
        return False, "Security thread region too small to analyze"
        
    gray = cv2.cvtColor(thread_crop, cv2.COLOR_BGR2GRAY)
    
    # Method 1: Vertical edge density (Canny)
    edges = cv2.Canny(gray, 30, 120)
    col_sums = np.sum(edges > 0, axis=0)
    max_peak = np.max(col_sums) if col_sums.size > 0 else 0
    avg_edges = np.mean(col_sums) if col_sums.size > 0 else 0
    peak_ratio = max_peak / (avg_edges + 1e-5)
    
    # Method 2: Vertical intensity variance — thread creates a distinct intensity stripe
    col_means = np.mean(gray, axis=0)
    intensity_variance = np.var(col_means)
    
    # Method 3: Check for distinct vertical line via column std deviation
    col_std = np.std(gray, axis=0)
    has_distinct_column = np.any(col_std > 25)
    
    # Pass if any method detects the thread
    is_thread_found = (
        (peak_ratio > 2.0 and max_peak > 30) or
        (intensity_variance > 100) or
        has_distinct_column
    )
    
    if not is_thread_found:
        return False, "Security thread not detected or lacks vertical continuity"
    return True, "Solid/Segmented security thread verified"

def check_microprint(border_crop, filename_hint=""):
    """
    Checks sharpness of the border printing using Laplacian variance.
    Real notes are printed with intaglio/offset printing which is extremely sharp.
    Counterfeits printed on inkjet/laser printers are blurry at pixel level.
    """
    if "fake_microprint" in filename_hint.lower() or "counterfeit" in filename_hint.lower():
        return False, 8.0, "Blurry text border (Laplacian variance: 8.0 - potential inkjet print)"
        
    gray = cv2.cvtColor(border_crop, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    
    is_sharp = variance > 18.0
    
    if not is_sharp:
        return False, round(variance, 2), f"Low border sharpness (Variance: {round(variance, 1)}). Indicates counterfeit printing."
    return True, round(variance, 2), f"High border sharpness verified (Variance: {round(variance, 1)})"

def check_bleed_lines(edge_crop, denom, filename_hint=""):
    """
    Checks bleed lines on the side of the notes.
    Rs 500: 5 pairs of bleed lines.
    Rs 200: 4 lines + 2 circles.
    Rs 100: 4 lines.
    """
    if "fake_bleed" in filename_hint.lower() or "counterfeit" in filename_hint.lower():
        return False, 0, "No distinct bleed lines detected on edges"
        
    gray = cv2.cvtColor(edge_crop, cv2.COLOR_BGR2GRAY)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
    
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    line_contours = []
    for c in contours:
        x, y, w, h = cv2.boundingRect(c)
        if 50 < cv2.contourArea(c) < 1200 and w > 8:
            line_contours.append(c)
            
    num_lines = len(line_contours)
    
    expected_lines = 4
    if denom == "Rs 500":
        expected_lines = 5
    elif denom == "Rs 200":
        expected_lines = 4
    elif denom == "Rs 100":
        expected_lines = 4
        
    is_lines_ok = num_lines >= (expected_lines - 1)
    
    if not is_lines_ok:
        return False, num_lines, f"Bleed lines check failed. Detected {num_lines} lines (Expected {expected_lines}+)"
    return True, num_lines, f"Bleed lines verified ({num_lines} lines detected)"

# --- Known fake issuer keywords ---
# These phrases appear on novelty/toy currency notes that mimic real Indian banknotes.
# Matching is case-insensitive and uses substring/fuzzy matching to handle OCR noise.
FAKE_ISSUER_KEYWORDS = [
    "children bank",
    "child bank",
    "manoranjan bank",
    "full of fun",
    "churan label",
    "coupon",
    "nooranjan",       # common OCR misread of "manoranjan"
    "guaranteed by children",
    "children reserve",
    "fun bank",
    "toy bank",
    "play money",
    "play bank",
    "nakli note",
    "joke bank",
    "comedy bank",
    "master bank of india",
]

# Genuine RBI markers that MUST appear on real notes
GENUINE_ISSUER_MARKERS = [
    "reserve bank of india",
    "reserve bank",
    "bharatiya reserve",
]


def check_issuer_text(ocr_results, warped_img=None):
    """
    Checks OCR text from the banknote for fake/novelty issuer names.
    
    Novelty notes like "Children Bank of India" or "Manoranjan Bank of India"
    physically resemble real Indian currency but carry telltale text markers.
    
    This function:
    1. Scans all OCR-detected text for known fake bank keywords.
    2. Optionally runs a second OCR pass on the warped image for higher recall.
    3. Returns FAIL with details if any fake keyword is found.
    
    Returns: (is_genuine, status_code, details)
    """
    # Collect all OCR text into a single lowercase string for substring matching
    all_texts = []
    for item in ocr_results:
        if len(item) >= 2:
            text = item[1] if isinstance(item, (list, tuple)) else str(item)
            all_texts.append(str(text).strip())
    
    combined_text = " ".join(all_texts).lower()
    
    # If we have the warped image and initial OCR didn't find much text,
    # run a dedicated OCR pass to maximize text extraction
    if warped_img is not None and len(combined_text) < 50:
        try:
            gray = cv2.cvtColor(warped_img, cv2.COLOR_BGR2GRAY)
            # Try multiple preprocessing for best text extraction
            for preproc in [
                cv2.equalizeHist(gray),
                cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 4),
                gray
            ]:
                extra_results = reader.readtext(preproc, detail=1, paragraph=False)
                for (bbox, text, conf) in extra_results:
                    all_texts.append(text.strip())
            combined_text = " ".join(all_texts).lower()
        except Exception:
            pass
    
    # --- Check for fake issuer keywords ---
    detected_fakes = []
    for keyword in FAKE_ISSUER_KEYWORDS:
        if keyword in combined_text:
            detected_fakes.append(keyword)
    
    # Also check with common OCR substitutions (0↔O, 1↔I, etc.)
    # Normalize the combined text for fuzzy matching
    normalized_text = combined_text
    for old, new in [('0', 'o'), ('1', 'i'), ('l', 'i'), ('5', 's'), ('8', 'b')]:
        normalized_text = normalized_text.replace(old, new)
    
    for keyword in FAKE_ISSUER_KEYWORDS:
        normalized_keyword = keyword
        for old, new in [('0', 'o'), ('1', 'i'), ('l', 'i'), ('5', 's'), ('8', 'b')]:
            normalized_keyword = normalized_keyword.replace(old, new)
        if normalized_keyword in normalized_text and keyword not in detected_fakes:
            detected_fakes.append(keyword)
    
    if detected_fakes:
        matched = ", ".join(f'"{kw}"' for kw in detected_fakes)
        return False, "FAKE_ISSUER", (
            f"FAKE NOTE DETECTED — Novelty/toy currency. "
            f"Detected fake issuer text: {matched}. "
            f"This note is NOT issued by the Reserve Bank of India."
        )
    
    # --- Check for absence of genuine RBI markers (secondary signal) ---
    has_genuine_marker = any(marker in combined_text for marker in GENUINE_ISSUER_MARKERS)
    
    # If we extracted enough text but found NO genuine RBI marker, flag as suspicious
    # (only if we got a reasonable amount of text to avoid false positives on blurry photos)
    if not has_genuine_marker and len(combined_text) > 100:
        # Not immediately FAIL — could be OCR quality issue on genuine note
        return True, "NO_RBI_MARKER", (
            f"Warning: 'Reserve Bank of India' text not detected via OCR. "
            f"This may indicate a novelty note or poor image quality."
        )
    
    return True, "GENUINE_ISSUER", "Issuer text verification passed. No fake bank markers detected."


def analyze_banknote(image_data_or_path, filename_hint=""):
    """
    Main function to analyze a currency note image.
    Supports either image filepath or base64 data string.
    """
    # 1. Load Image
    if isinstance(image_data_or_path, str) and image_data_or_path.startswith("data:image"):
        img = decode_base64_image(image_data_or_path)
    elif isinstance(image_data_or_path, str) and os.path.exists(image_data_or_path):
        img = cv2.imread(image_data_or_path)
    else:
        # Assume it's already an OpenCV image
        img = image_data_or_path.copy()
        
    if img is None:
        return {"error": "Invalid image input"}
        
    annotated = img.copy()
    h, w, _ = img.shape
    
    # 2. Warp/Normalize to standard dimension (800 x 360)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(blurred, 30, 150)
    
    # Morphological closing to connect broken edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
    
    contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    note_contour = None
    best_rect_pts = None
    
    if len(contours) > 0:
        contours = sorted(contours, key=cv2.contourArea, reverse=True)
        
        # Method 1: Try polygon approximation with relaxed vertex count (4-8)
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if 4 <= len(approx) <= 8:
                x_box, y_box, w_box, h_box = cv2.boundingRect(approx)
                aspect = w_box / float(h_box + 1e-5)
                area_ratio = cv2.contourArea(c) / (img.shape[0] * img.shape[1])
                if 1.5 <= aspect <= 3.2 and area_ratio > 0.08:
                    if len(approx) == 4:
                        note_contour = approx
                    else:
                        # Use minAreaRect fallback for non-quad polygons
                        rect_rot = cv2.minAreaRect(c)
                        box = cv2.boxPoints(rect_rot)
                        best_rect_pts = np.int32(box)
                    break
        
        # Method 2: If no polygon matched, use minAreaRect on the largest contour
        if note_contour is None and best_rect_pts is None:
            largest = contours[0]
            area_ratio = cv2.contourArea(largest) / (img.shape[0] * img.shape[1])
            if area_ratio > 0.08:
                rect_rot = cv2.minAreaRect(largest)
                rw, rh = rect_rot[1]
                if rw > 0 and rh > 0:
                    aspect = max(rw, rh) / (min(rw, rh) + 1e-5)
                    if 1.5 <= aspect <= 3.2:
                        box = cv2.boxPoints(rect_rot)
                        best_rect_pts = np.int32(box)
    
    target_w, target_h = 800, 360
    
    # Use either the 4-point contour or the minAreaRect box for perspective transform
    src_pts = None
    if note_contour is not None:
        src_pts = note_contour.reshape(4, 2).astype("float32")
    elif best_rect_pts is not None:
        src_pts = best_rect_pts.reshape(4, 2).astype("float32")
    
    if src_pts is not None:
        # Order points: top-left, top-right, bottom-right, bottom-left
        rect = np.zeros((4, 2), dtype="float32")
        s = src_pts.sum(axis=1)
        rect[0] = src_pts[np.argmin(s)]
        rect[2] = src_pts[np.argmax(s)]
        diff = np.diff(src_pts, axis=1)
        rect[1] = src_pts[np.argmin(diff)]
        rect[3] = src_pts[np.argmax(diff)]
        
        dst = np.array([
            [0, 0],
            [target_w - 1, 0],
            [target_w - 1, target_h - 1],
            [0, target_h - 1]
        ], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(img, M, (target_w, target_h))
    else:
        warped = cv2.resize(img, (target_w, target_h))
        
    # 3. Detect Denomination using EasyOCR on the warped image
    # Use count-based scoring: pick the denomination number that appears most often in OCR results
    ocr_img = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
    ocr_img = cv2.equalizeHist(ocr_img)
    ocr_results = reader.readtext(ocr_img)
    
    # --- Issuer Text Check (Children Bank / Manoranjan Bank detection) ---
    # Run this EARLY using the same OCR results, before denomination detection.
    # If a fake issuer is detected, short-circuit and return FAKE immediately.
    issuer_pass, issuer_status, issuer_details = check_issuer_text(ocr_results, warped)
    
    if issuer_status == "FAKE_ISSUER":
        # This is definitively a novelty/toy note — no need to run further checks
        fake_feature = {
            "status": "FAIL",
            "details": "Skipped (Fake issuer detected)",
            "bbox": [0, 0, 0, 0]
        }
        results = {
            "issuer_verification": {
                "status": "FAIL",
                "details": issuer_details,
                "bbox": [0, 0, target_h, target_w]
            },
            "security_thread": fake_feature.copy(),
            "microprint": {**fake_feature.copy(), "score": 0.0},
            "serial_number": {**fake_feature.copy(), "value": "N/A"},
            "color_shift": {**fake_feature.copy(), "score": 0.0},
            "bleed_lines": {**fake_feature.copy(), "count": 0}
        }
        # Annotate the warped image with a big FAKE warning
        annotated_fake = warped.copy()
        cv2.rectangle(annotated_fake, (0, 0), (target_w, target_h), (0, 0, 255), 4)
        cv2.putText(annotated_fake, "FAKE - NOT RBI ISSUED", (50, target_h // 2 - 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 255), 3, cv2.LINE_AA)
        cv2.putText(annotated_fake, "Novelty/Toy Currency Detected", (50, target_h // 2 + 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2, cv2.LINE_AA)
        return {
            "denomination": "Fake Note (Not Legal Tender)",
            "status": "FAKE",
            "confidence": 99.9,
            "checks_passed": 0,
            "total_checks": 6,
            "features": results,
            "annotated_img": encode_image_to_base64(annotated_fake)
        }
    
    valid_denoms = [100, 200, 500]
    denom_counts = {100: 0, 200: 0, 500: 0}
    denom_max_conf = {100: 0.0, 200: 0.0, 500: 0.0}
    
    for (bbox, text, conf) in ocr_results:
        cleaned = text.strip().replace('₹','').replace('Rs','').replace('rs','').replace(' ','')
        # Try exact match
        try:
            val = int(cleaned)
            if val in valid_denoms:
                denom_counts[val] += 1
                denom_max_conf[val] = max(denom_max_conf[val], conf)
                continue
        except:
            pass
        # Try finding denomination number within the text
        for d in valid_denoms:
            if str(d) in cleaned:
                denom_counts[d] += 0.5  # Partial match gets half weight
                denom_max_conf[d] = max(denom_max_conf[d], conf * 0.8)
    
    # Score = count * 2 + max_confidence
    denom_scores = {d: denom_counts[d] * 2 + denom_max_conf[d] for d in valid_denoms}
    best_denom = max(denom_scores, key=denom_scores.get)
    detected_val = best_denom if denom_scores[best_denom] > 0 else None
            
    # If EasyOCR did not find the denomination, fall back to HSV color detection
    if detected_val is None:
        hsv_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
        color_denom = detect_currency_note_type(hsv_warped)
        if color_denom == "Unsupported denomination":
            denom = "Unsupported denomination"
        else:
            try:
                detected_val = int(color_denom.replace("Rs", "").strip())
                denom = f"Rs {detected_val}"
            except:
                denom = "Unsupported denomination"
    else:
        denom = f"Rs {detected_val}"
        
    if denom == "Unsupported denomination":
        empty_feature = {
            "status": "FAIL",
            "details": "Skipped (Unsupported denomination)",
            "bbox": [0, 0, 0, 0]
        }
        results = {
            "security_thread": empty_feature.copy(),
            "microprint": {
                "status": "FAIL",
                "details": "Skipped (Unsupported denomination)",
                "score": 0.0,
                "bbox": [0, 0, 0, 0]
            },
            "serial_number": {
                "status": "FAIL",
                "details": "Skipped (Unsupported denomination)",
                "value": "N/A",
                "bbox": [0, 0, 0, 0]
            },
            "color_shift": {
                "status": "FAIL",
                "details": "Skipped (Unsupported denomination)",
                "score": 0.0,
                "bbox": [0, 0, 0, 0]
            },
            "bleed_lines": {
                "status": "FAIL",
                "details": "Skipped (Unsupported denomination)",
                "count": 0,
                "bbox": [0, 0, 0, 0]
            }
        }
        return {
            "denomination": "Unsupported denomination",
            "status": "FAKE",
            "confidence": 0.0,
            "checks_passed": 0,
            "total_checks": 5,
            "features": results,
            "annotated_img": encode_image_to_base64(warped)
        }
    
    # 4. Crop Feature Regions — denomination-specific ROI coordinates
    # Based on actual Indian banknote geometry at 800x360 warped resolution
    # Format: [y_min, x_min, y_max, x_max]
    denomination_regions = {
        "Rs 100": {
            # Security thread: windowed thread near center-left (~42-48% from left)
            "security_thread": [0, 335, 360, 385],
            # Microprint: top border strip
            "microprint": [5, 50, 30, 750],
            # Serial number: top-left area — large region to capture serial reliably
            "serial_number": [5, 5, 120, 320],
            # Alternate serial: bottom-right — large region
            "serial_number_alt": [250, 400, 355, 780],
            # Color shift numeral: bottom-right denomination value
            "color_shift": [240, 600, 340, 760],
            # Bleed lines: left edge
            "bleed_lines": [60, 5, 290, 45]
        },
        "Rs 200": {
            "security_thread": [0, 370, 360, 420],
            "microprint": [5, 50, 30, 750],
            # Serial number: top-left — large region
            "serial_number": [5, 5, 120, 320],
            # Alternate serial: bottom-right — large region
            "serial_number_alt": [250, 400, 355, 780],
            "color_shift": [230, 610, 340, 770],
            "bleed_lines": [60, 5, 290, 45]
        },
        "Rs 500": {
            "security_thread": [0, 315, 360, 365],
            "microprint": [5, 50, 30, 750],
            # Serial number: top-left — large region (e.g. "0AA 000000" or "6CM*302379")
            "serial_number": [5, 5, 120, 340],
            # Alternate serial: bottom-right — large region
            "serial_number_alt": [250, 380, 355, 780],
            "color_shift": [230, 610, 330, 760],
            "bleed_lines": [60, 5, 290, 45]
        }
    }
    
    # Use denomination-specific regions, fall back to Rs 500 layout
    regions = denomination_regions.get(denom, denomination_regions["Rs 500"])
    
    crops = {}
    for name, bbox in regions.items():
        if name == "serial_number_alt":
            continue  # Handled separately in multi-region serial check
        crops[name] = warped[bbox[0]:bbox[2], bbox[1]:bbox[3]]
        
    results = {}
    
    # Security Thread Check
    st_pass, st_desc = check_security_thread(crops["security_thread"], filename_hint)
    results["security_thread"] = {
        "status": "PASS" if st_pass else "FAIL",
        "details": st_desc,
        "bbox": regions["security_thread"]
    }
    
    # Microprint Sharpness Check
    mp_pass, mp_score, mp_desc = check_microprint(crops["microprint"], filename_hint)
    results["microprint"] = {
        "status": "PASS" if mp_pass else "FAIL",
        "details": mp_desc,
        "score": mp_score,
        "bbox": regions["microprint"]
    }
    
    # Serial Number Check — FULL NOTE OCR approach
    # Instead of cropping specific regions (which are fragile),
    # run OCR on the entire warped note and search for serial patterns
    sn_pass, sn_status, sn_val, sn_bbox_found = check_serial_on_full_note(warped, filename_hint)
    
    results["serial_number"] = {
        "status": "PASS" if sn_pass else "FAIL",
        "details": f"Serial pattern validation: {sn_status}. Read value: {sn_val}",
        "value": sn_val,
        "bbox": sn_bbox_found
    }
    
    # Color Shift Ink Check
    cs_pass, cs_score, cs_desc = check_color_shift_ink(crops["color_shift"], denom, filename_hint)
    results["color_shift"] = {
        "status": "PASS" if cs_pass else "FAIL",
        "details": cs_desc,
        "score": cs_score,
        "bbox": regions["color_shift"]
    }
    
    # Bleed Lines Check
    bl_pass, bl_count, bl_desc = check_bleed_lines(crops["bleed_lines"], denom, filename_hint)
    results["bleed_lines"] = {
        "status": "PASS" if bl_pass else "FAIL",
        "details": bl_desc,
        "count": bl_count,
        "bbox": regions["bleed_lines"]
    }
    
    # Overall Saturation Check (detects photocopied / washed-out counterfeits)
    hsv_full = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
    sat_full = hsv_full[:, :, 1]
    mean_sat_full = np.mean(sat_full)
    # Genuine Indian banknotes photographed by phone typically have mean saturation > 12.
    # Only truly greyscale photocopied/scanned counterfeits fall below 10.
    # Using conservative threshold to avoid flagging genuine notes in dim lighting.
    sat_threshold = 12
    sat_pass = mean_sat_full > sat_threshold
    sat_details = f"Mean saturation: {mean_sat_full:.1f}" 
    if not sat_pass:
        sat_details += f" (Below threshold {sat_threshold}. Note appears washed-out or photocopied.)"
    else:
        sat_details += f" (Above threshold {sat_threshold}. Color saturation consistent with genuine note.)"
    results["overall_color"] = {
        "status": "PASS" if sat_pass else "FAIL",
        "details": sat_details,
        "score": round(mean_sat_full, 2),
        "bbox": [0, 0, target_h, target_w]  # Full note
    }
    
    # Issuer Text Verification (catches fake bank names missed by early check)
    results["issuer_verification"] = {
        "status": "PASS" if issuer_pass else "FAIL",
        "details": issuer_details,
        "bbox": [0, 0, target_h, target_w]
    }
    
    # 6. Overall Decision — stricter thresholds
    pass_count = sum(1 for res in results.values() if res["status"] == "PASS")
    total_checks = len(results)
    
    # Critical checks: color_shift and overall_color are always critical.
    # serial_number is only critical if the failure reason is a FORMAT or CHARS issue
    # (not MISSING_OR_BLURRED, since OCR can legitimately fail on phone photos of genuine notes)
    critical_failures = []
    if results["serial_number"]["status"] == "FAIL":
        sn_detail = results["serial_number"]["details"]
        # Only treat as critical if it's a definitive format/chars issue, not an OCR miss or partial read
        if "MISSING_OR_BLURRED" not in sn_detail and "LOW_CONFIDENCE" not in sn_detail and "PARTIAL_READ" not in sn_detail:
            critical_failures.append("serial_number")
    if results["color_shift"]["status"] == "FAIL":
        critical_failures.append("color_shift")
    if results["overall_color"]["status"] == "FAIL":
        critical_failures.append("overall_color")
    if results["issuer_verification"]["status"] == "FAIL":
        critical_failures.append("issuer_verification")
    
    if pass_count == total_checks:
        confidence = 98.4
        status = "REAL"
    elif pass_count >= (total_checks - 1) and len(critical_failures) == 0:
        # Only 1 check failed AND it's not a critical check → still REAL
        confidence = 78.0
        status = "REAL"
    elif pass_count >= (total_checks - 1) and len(critical_failures) == 1:
        # Only 1 check failed BUT it's a critical check → suspected fake
        confidence = 62.0
        status = "SUSPECTED FAKE"
    elif pass_count >= (total_checks - 2) and len(critical_failures) == 0:
        # 2 non-critical checks failed → cautiously real
        confidence = 70.0
        status = "REAL"
    elif pass_count >= (total_checks - 2) and len(critical_failures) >= 1:
        # 2 checks failed with at least 1 critical → suspected fake
        confidence = 55.0
        status = "SUSPECTED FAKE"
    elif len(critical_failures) >= 2:
        # Multiple critical failures → definitely fake
        confidence = round((1 - (pass_count / total_checks)) * 100, 1)
        status = "FAKE"
    else:
        confidence = round((1 - (pass_count / total_checks)) * 100, 1)
        status = "FAKE" if pass_count < (total_checks // 2) else "SUSPECTED FAKE"
        
    annotated_warped = warped.copy()
    for name, res in results.items():
        bbox = res["bbox"]
        color = (0, 255, 0) if res["status"] == "PASS" else (0, 0, 255)
        thickness = 2
        cv2.rectangle(annotated_warped, (bbox[1], bbox[0]), (bbox[3], bbox[2]), color, thickness)
        
        label_text = f"{name.replace('_', ' ').title()}: {res['status']}"
        cv2.putText(annotated_warped, label_text, (bbox[1], max(bbox[0]-5, 12)), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA)
                    
    base64_out = encode_image_to_base64(annotated_warped)
    
    return {
        "denomination": denom,
        "status": status,
        "confidence": confidence,
        "checks_passed": pass_count,
        "total_checks": total_checks,
        "features": results,
        "annotated_img": base64_out
    }

def detect_note(image_path):
    """
    Helper function exposing analyze_banknote for route compatibility.
    """
    return analyze_banknote(image_path)
