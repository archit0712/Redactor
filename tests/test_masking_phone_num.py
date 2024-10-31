from redactor import mask_phone_numbers_in_text

import re
import pytest



def test_mask_phone_numbers_in_text():
    # Input text containing various phone numbers
    text = (
        "Contact us at +1 (123) 456-7890 or 123-456-7890. "
        "For international, call +44 20 7946 0958. "
        "Also, try our toll-free number: 800-555-1234."
    )

    # Call the masking function
    masked_text, total_phones_masked = mask_phone_numbers_in_text(text)

    # Check the total redactions
    assert total_phones_masked == 4, f"Expected 4 phone numbers to be masked, but got {total_phones_masked}"

    # Check that the phone numbers are masked correctly
    # Regular expression to match the masking of phone numbers (using '█' character)
    masked_phone_regex = re.compile(r'█{10,}')
    
    # Ensure all phone numbers in the text are masked
    assert len(re.findall(masked_phone_regex, masked_text)) == 4, "Not all phone numbers were masked as expected."
    
    print(masked_text)
    # Ensure the masking is correct for each phone number
    assert "Contact us at █████████████████ or ████████████. For international, call ████████████████. Also, try our toll-free number: ████████████." in masked_text

    print("Phone number masking test passed.")




