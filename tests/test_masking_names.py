# test_redactor.py

from redactor import mask_names_in_text

def test_mask_names_in_text():
    # Sample input text with different name formats
    text = (
        "John Doe attended the meeting with Jane Smith. "
        "Mr. John A. Doe was also present, along with Dr. Emily Thompson."
    )

    # Call the masking function
    masked_text, total_names_masked = mask_names_in_text(text)

    # Check the total redactions
    assert total_names_masked == 4, f"Expected 4 names to be masked, but got {total_names_masked}"
    print(masked_text)
    # Check that the names are masked correctly
    # Assert that the text contains masked characters (using '█' character) where names were present
    assert "████████ attended the meeting with ██████████. Mr. ███████████ was also present, along with Dr. ██████████████." in masked_text


    print("Name redaction test passed.")
