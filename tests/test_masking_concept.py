from redactor import mask_concept_related_text

def test_mask_concept_related_text_simple():
    # Test for a single concept with direct match
    text = (
        "We went to the beach last summer. The cold winter this year was tough. Summertime brings joy to everyone. Winter sports, however, are also fun."
    )
    concepts = ["summer"]
    expected_output = "█████████████████████████████████ The cold winter this year was tough. ██████████████████████████████████ Winter sports, however, are also fun."


    # Call the masking function
    masked_text, total_concepts_masked = mask_concept_related_text(text, concepts)
    print(masked_text)
    # Check the total redactions
    assert total_concepts_masked == 2, f"Expected 2 instances of concept to be masked, but got {total_concepts_masked}"

    # Check that the concept-related words are masked correctly
    assert masked_text == expected_output, "Concept masking output did not match expected output."
