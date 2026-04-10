from workers.regex_extractor import extract_fields

# Simulating clean OCR output
sample_text = """
GOVERNMENT OF INDIA
Unique Identification Authority of India
AADHAAR
Name: Varun Bharadwaj
Date of Birth: 15/08/1998
Gender: Male
2167 6218 9564
"""

import json
result = extract_fields(sample_text)
print(json.dumps(result, indent=2))