from redactor import redact_dates

def test_redact_dates():
    # Sample input text with various date formats
    text = (
        "The event is scheduled on 01/01/2023. Another event is on January 15th, 2024. "
        "We also have an anniversary on Mar 3."
    )

    
   

    # Call the redaction function
    masked_text, total_dates_masked = redact_dates(text)

    # Check the total redactions
    assert total_dates_masked == 3, f"Expected 4 dates to be masked, but got {total_dates_masked}"

    # Check that the dates are masked correctly
    assert masked_text == "The event is scheduled on ██████████. Another event is on ██████████████████. We also have an anniversary on █████.", "Date masking output did not match expected output."

    print("Date redaction test passed.")