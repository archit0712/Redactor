# Redactor

The **Redactor** tool is a Python-based utility for redacting sensitive information from text files. It supports redaction of names, dates, phone numbers, addresses, and concept-related content using both regex patterns and Google NLP API for accuracy. Additionally, it provides statistical reports of the redactions performed.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Arguments](#arguments)
- [Examples](#examples)
- [Code Explanation](#code-explanation)
- [Design Choices](#design-choices)
- [Test Cases](#test-cases)
- [Running Tests](#running-tests)
- [Dependencies](#dependencies)

## Features

- **Name Redaction**: Identifies and redacts personal names using SpaCy NLP and Google NLP API.
- **Date Redaction**: Redacts various date formats (e.g., `MM/DD/YYYY`, `Jan 1st, 2023`).
- **Phone Number Redaction**: Detects and redacts different phone number formats.
- **Address Redaction**: Uses regex and Google NLP to identify and redact complete addresses.
- **Concept-based Redaction**: Redacts sentences or phrases that are related to a given concept.
- **Statistics Output**: Provides a summary of redactions performed in each file.

## Installation

1. **Clone the repository**:
    ```bash
    git clone https://github.com/archit0712/cis6930fa24-project1.git
    cd redactor
    ```

2. **Install dependencies using pipenv**:
    ```bash
    pipenv install
    ```

3. **Activate the pipenv shell**:
    ```bash
    pipenv shell
    ```

4. **Set up Google NLP**:
   - Ensure you have a Google Cloud project with the Google NLP API enabled.
   - Download the service account key and set the environment variable:
     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account-file.json"
     ```

## Usage

Run the `redactor.py` script with the following arguments:

```bash
pipenv run python redactor.py --input <file-patterns> --output <output-directory> --names --dates --phones --address --concept <concepts> --stats <stats-output>
```

## Arguments
1. ``--input``: Glob pattern(s) for input files.
2. ``--output``: Directory to save the redacted files.
3. ``--names``: Redact names from the text.
4. ``--dates``: Redact dates from the text.
5. ``--phones``: Redact phone numbers from the text.
6. ``--address``: Redact addresses from the text.
7. ``--concept``: Specify concepts to redact (can be used multiple times).
8. ``--stats``: Specify where to write statistics (stdout, stderr, or a filename).


## Examples
1. Redact names and dates:

```bash
pipenv run python redactor.py --input "data/*.txt" --output redacted --names --dates --stats stdout

```
2. Redact addresses and concept-related content:
```bash
pipenv run python redactor.py --input "emails/*.txt" --output redacted --address --concept "summer" --stats redaction_stats.json
```

## How It Works
1. Input Files: The tool accepts file patterns (e.g., *.txt) and collects files matching these patterns.
2. Redaction Functions: Based on specified flags, the tool applies individual redaction functions:
    * Name Redaction: Uses SpaCy NLP and Google NLP API to identify and mask names.
    * Date Redaction: Identifies dates with regex patterns and masks them.
    * Phone Number Redaction: Uses regex to detect phone numbers and redacts them.
    * Address Redaction: Combines regex and Google NLP to identify full addresses and mask them.
    * Concept-based Redaction: Masks sentences or phrases closely related to a given concept using SpaCy similarity.
    * Output and Statistics: Redacted text is saved to the specified output directory, and redaction statistics are printed or saved as specified.

## Code Explanation
The Redactor tool is designed to redact sensitive information, such as personal names, dates, phone numbers, addresses, and concept-related sentences, from text documents. Below is an explanation of each function and the reasoning behind the design choices made for this redactor.

1. **Main Functions**
    *   ``get_input_files``: Collects all input files based on provided patterns, making it possible to process multiple files at once. The use of glob patterns helps manage files efficiently without hardcoding file paths.

    * ``verify_person_name_via_gnlp``: Uses Google Cloud’s Natural Language Processing (NLP) API to identify names categorized as “PERSON.” This enhances accuracy by filtering only verified personal names, minimizing false positives.

    * ``process_name_comma_format`` and ``sanitize_name``: These helper functions ensure that names are standardized (e.g., converting "Lastname, Firstname" to "Firstname Lastname") and remove unwanted characters, thus improving the accuracy of name redaction.

    * ``extract_and_validate_names``: Uses SpaCy to extract names and optionally verifies them with Google NLP to ensure accuracy in redacting actual personal names. This multi-step approach combines SpaCy’s speed and Google’s robustness.

    * ``mask_names_in_email_addresses``: Redacts names within email addresses by masking the local part of the email, which often contains personal information. By adjusting position offsets, this function ensures that all email addresses are masked correctly without affecting the surrounding text.

    * ``mask_names_in_text``: Combines extracted names from regular text and email addresses, masking them while maintaining text structure. Names are sorted in reverse order to prevent position-shifting issues during masking.

    * ``apply_mask``: Replaces a portion of text with censorship characters (█). It also adjusts for newline positions, ensuring redactions are accurate across lines.

    * ``redact_dates``: Uses regex patterns and SpaCy’s entity_ruler to identify and redact various date formats (e.g., MM/DD/YYYY, Month DD). This approach ensures consistent date masking by relying on SpaCy’s entity recognition in conjunction with custom date patterns.

    * ``mask_phone_numbers_in_text``: Detects and masks phone numbers in multiple formats, using regex to capture local and international patterns. This approach reduces complexity by using re.VERBOSE for readability and ensuring phone numbers are accurately masked across text.

    * ``mask_detected_addresses``: Combines regex patterns and Google NLP to capture and mask full addresses. The consolidate_addresses function merges partial address components, improving the reliability of address masking by treating multi-part addresses as single entities.

    * ``detect_concept_related_sentences`` and ``mask_concept_related_text``: These functions identify and redact sentences related to user-defined concepts (e.g., "summer") by comparing each sentence to the concept with a similarity threshold. This flexible approach uses SpaCy’s similarity functionality, allowing related phrases to be accurately redacted based on context.

    * ``normalize_text``: Handles text normalization to replace line breaks within paragraphs, enhancing readability and processing accuracy for multi-line sentences.

    * ``write_statistics``: Outputs the redaction statistics in a JSON format, supporting both file output and console display. This provides users with an overview of redactions performed, enhancing transparency and auditability.

    *  ``main``: Sets up argument parsing for various redaction options (names, dates, phones, addresses, concepts). It processes each file individually, applies the requested redactions, and generates a .censored file for each input. The main function integrates each of the redaction components, making it user-friendly by providing clear options and summarizing the results in a final statistics report.

## Design Choices
1. **SpaCy and Google NLP Integration**: By combining SpaCy and Google NLP, the tool leverages SpaCy’s speed and Google’s NLP accuracy, especially for names and addresses. This hybrid approach improves both performance and reliability.

2. **Regex Patterns for Date, Phone, and Address Matching**: Regex patterns are used for faster matching of structured data (dates, phones, addresses), which are predictable in format. This approach enhances efficiency, as regex-based searches are quicker for standardized patterns.

3. **Concept-based Redaction with Similarity Matching**: Using similarity matching with SpaCy allows the tool to identify phrases related to user-defined concepts beyond exact word matches, offering flexibility for broader and contextually relevant redactions.

## Test Cases
The test folder includes pytest test cases to ensure accurate redaction across various functions. Test cases are:

1. **Phone Number Masking** (```File Name : test_masking_phone_num.py```): Tests various phone number formats for correct masking.Ensures that both local and international formats are properly redacted.

2. **Name Redaction** (```File Name : test_masking_names.py```):Tests name formats (e.g., "John Doe," "Mr. John A. Doe") to ensure full redaction.
Verifies that partial names and common prefixes are handled correctly.

3. **Address Redaction** (```File Name : test_masking_address.py```): Verifies regex and Google NLP redaction of full address formats, including variations (e.g., "123 Main St., Springfield, IL 62704").
Tests both direct regex matches and Google NLP-detected locations for accurate masking.

4. **Date Redaction** (```File Name : test_masking_dates.py```): Tests various date formats, including MM/DD/YYYY, Month DD, YYYY, and MM/DD, to ensure accurate redaction.
Confirms that all date instances in the text are masked as expected.

5. **Concept-based Redaction** (```File Name : test_masking_concept.py```): Tests simple and complex sentences for redaction based on concepts (e.g., "summer").
Includes cases with both direct matches ("summer") and indirect matches (e.g., "summertime" or "warm season").
Verifies no redaction occurs when unrelated text is present.

## Running Tests
To run all tests with pytest:

```bash
pipenv run python -m pytest
```
Ensure all dependencies are installed and pytest is available. Test outputs will confirm that each redaction function performs as expected.


## Dependencies
* **Python 3.12.7**
* **SpaCy**: NLP processing
* **Google Cloud NLP API**: For advanced entity recognition
* **pytest**: For running tests