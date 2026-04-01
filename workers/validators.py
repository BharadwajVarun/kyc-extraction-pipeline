from datetime import datetime, date


# ─── Verhoeff Lookup Tables ────────────────────────────────────────

VERHOEFF_MULTIPLICATION = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

VERHOEFF_PERMUTATION = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

VERHOEFF_INVERSE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


# ─── Aadhaar Validator ─────────────────────────────────────────────

def validate_aadhaar(uid: str) -> dict:
    # Remove spaces if any
    uid_clean = uid.replace(" ", "")

    # Basic format check
    if not uid_clean.isdigit():
        return {
            "valid": False,
            "reason": "UID contains non-numeric characters",
            "uid": uid_clean
        }

    if len(uid_clean) != 12:
        return {
            "valid": False,
            "reason": f"UID must be 12 digits, got {len(uid_clean)}",
            "uid": uid_clean
        }

    if uid_clean[0] in ("0", "1"):
        return {
            "valid": False,
            "reason": "UID cannot start with 0 or 1",
            "uid": uid_clean
        }

    # Verhoeff algorithm
    check = 0
    reversed_uid = reversed(uid_clean)
    for i, digit in enumerate(reversed_uid):
        p = VERHOEFF_PERMUTATION[i % 8][int(digit)]
        check = VERHOEFF_MULTIPLICATION[check][p]

    is_valid = check == 0

    return {
        "valid": is_valid,
        "reason": "Verhoeff checksum passed" if is_valid else "Verhoeff checksum failed — UID is invalid or misread",
        "uid": uid_clean
    }


# ─── Date Validators ───────────────────────────────────────────────

def validate_dob(dob_str: str) -> dict:
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            dob = datetime.strptime(dob_str, fmt).date()
            today = date.today()
            if dob >= today:
                return {
                    "valid": False,
                    "reason": "Date of birth cannot be today or in the future",
                    "dob": dob_str
                }
            age = (today - dob).days // 365
            if age > 120:
                return {
                    "valid": False,
                    "reason": "Age exceeds 120 years — likely misread",
                    "dob": dob_str
                }
            return {
                "valid": True,
                "reason": "Valid date of birth",
                "dob": dob_str,
                "age": age
            }
        except ValueError:
            continue

    return {
        "valid": False,
        "reason": "Could not parse date — unrecognised format",
        "dob": dob_str
    }


def validate_expiry(expiry_str: str) -> dict:
    formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
    for fmt in formats:
        try:
            expiry = datetime.strptime(expiry_str, fmt).date()
            today = date.today()
            if expiry < today:
                return {
                    "valid": False,
                    "reason": "Document has expired",
                    "expiry": expiry_str
                }
            return {
                "valid": True,
                "reason": "Document is valid",
                "expiry": expiry_str
            }
        except ValueError:
            continue

    return {
        "valid": False,
        "reason": "Could not parse expiry date",
        "expiry": expiry_str
    }


# ─── PAN Validator ─────────────────────────────────────────────────

def validate_pan(pan: str) -> dict:
    import re
    pan_clean = pan.strip().upper()
    pattern = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

    if not pattern.match(pan_clean):
        return {
            "valid": False,
            "reason": "PAN format invalid — expected AAAAA0000A",
            "pan": pan_clean
        }

    # 4th character indicates taxpayer type
    type_map = {
        "P": "Individual",
        "C": "Company",
        "H": "Hindu Undivided Family",
        "F": "Firm",
        "A": "Association of Persons",
        "T": "Trust",
        "B": "Body of Individuals",
        "L": "Local Authority",
        "J": "Artificial Juridical Person",
        "G": "Government"
    }
    taxpayer_type = type_map.get(pan_clean[3], "Unknown")

    return {
        "valid": True,
        "reason": "PAN format valid",
        "pan": pan_clean,
        "taxpayer_type": taxpayer_type
    }


# ─── Master Validator ──────────────────────────────────────────────

def validate_extraction(extracted_fields: dict) -> dict:
    validation_results = {}

    uid = extracted_fields.get("aadhaar_uid", {}).get("value")
    if uid:
        validation_results["aadhaar_uid"] = validate_aadhaar(uid)

    pan = extracted_fields.get("pan_number", {}).get("value")
    if pan:
        validation_results["pan_number"] = validate_pan(pan)

    dob = extracted_fields.get("date_of_birth", {}).get("value")
    if dob:
        validation_results["date_of_birth"] = validate_dob(dob)

    return validation_results


if __name__ == "__main__":
    import json

    print("─── Aadhaar UID Validation ───\n")

    # Test with the UID your pipeline already extracted
    test_uid = "216762189564"
    result = validate_aadhaar(test_uid)
    print(f"UID: {test_uid}")
    print(json.dumps(result, indent=2))

    print("\n─── Testing invalid UID ───\n")
    fake_uid = "216762189560"
    result2 = validate_aadhaar(fake_uid)
    print(f"UID: {fake_uid}")
    print(json.dumps(result2, indent=2))

    print("\n─── DOB Validation ───\n")
    result3 = validate_dob("15/08/1998")
    print(json.dumps(result3, indent=2))

    print("\n─── PAN Validation ───\n")
    result4 = validate_pan("ABCDE1234F")
    print(json.dumps(result4, indent=2))