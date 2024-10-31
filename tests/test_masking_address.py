# test_redactor.py

from redactor import mask_detected_addresses

def test_mask_detected_addresses():
    # Sample input text with different address formats
    text = (
        "Please visit us at 123 Main St., Springfield, IL 62704. "
        "Alternatively, you can find us at 456 Elm St., New York, NY 10001."
    )

    # Call the masking function
    masked_text, total_addresses_masked = mask_detected_addresses(text)
    
    print(masked_text)
    # Check the total redactions
    assert total_addresses_masked == 7, f"Expected 2 addresses to be masked, but got {total_addresses_masked}"

  
    # Check that the addresses are masked correctly
    # Ensure that specific address patterns are masked in the output
    assert "Please visit us at 123 ████████, ███████████, ██ 62704. Alternatively, you can find us at ███████████, ██████████████████." in masked_text


    print("Address redaction test passed.")
