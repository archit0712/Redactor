# redactor.py

import argparse
import sys
import os
import glob
import json
import spacy
import re
from google.cloud import language_v1
from warnings import filterwarnings

filterwarnings("ignore", category=SyntaxWarning)
print('Loading spaCy model...')
nlp = spacy.load('en_core_web_lg')
print('spaCy model loaded.')

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'data-engineering-434614-245ce8e4d3e0.json'
EMAIL_HEADERS = ['From:', 'To:', 'Cc:', 'Bcc:', 'Subject:', 'X-From:', 'X-To:', 'X-cc:', 'X-bcc:', 'X-Folder:', 'X-Origin:', 'X-FileName:']



def get_input_files(input_patterns):
    files = []
    for pattern in input_patterns:
        matched_files = glob.glob(pattern)
        files.extend(matched_files)
    return files



def verify_person_name_via_gnlp(name):
    # Verify if the provided name is recognized as a PERSON entity using Google NLP.
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(
        content=name,
        type_=language_v1.Document.Type.PLAIN_TEXT,
        language="en"  # Specify the language as English
    )
    response = client.analyze_entities(document=document)
    return any(entity.type == language_v1.Entity.Type.PERSON for entity in response.entities)



def process_name_comma_format(name):
    # Format names that might be in 'Lastname, Firstname' format or email format.
    email_pattern = re.compile(r'\"?(.+?)\"?\s*<(.+)>')
    match = email_pattern.match(name)
    
    if match:
        name_segment, email_segment = match.groups()
        name_segment = sanitize_name(name_segment)  # Clean unwanted characters
        if ',' in name_segment:
            parts = [part.strip() for part in name_segment.split(',')]
            if len(parts) == 2:
                name_segment = ' '.join(parts[::-1])  # Convert to "Firstname Lastname"
        name = f"{name_segment} <{email_segment}>"
    else:
        name = sanitize_name(name)  # Directly clean names not in email format
        if ',' in name:
            parts = [part.strip() for part in name.split(',')]
            if len(parts) == 2:
                name = ' '.join(parts[::-1])
    return name



def sanitize_name(name):
    # Clean unwanted characters from a name and normalize the spacing.
    name = re.sub(r'[<>"\']', '', name)  # Remove unwanted characters
    name = re.sub(r'\s+', ' ', name).strip()  # Normalize extra spaces
    return name



def extract_and_validate_names(doc):
    # Extract names using SpaCy and optionally verify them with Google NLP.
    validated_names = []
    for ent in doc.ents:
        if ent.label_ in ["PERSON"] :
            formatted_name = process_name_comma_format(ent.text)
            if formatted_name:  # Ensure the cleaned name is not empty
                validated_names.append((formatted_name, ent.start_char, ent.end_char))
    return validated_names


def mask_names_in_email_addresses(text):
    # Regular expression to find email addresses
    email_regex = r'[\w\.-]+@[\w\.-]+'
    masked_text = text
    total_names_masked = 0
    offset = 0  # To adjust positions after masking

    # Find all email addresses in the text
    matches = list(re.finditer(email_regex, text))
    for match in matches:
        email = match.group()
        start_pos = match.start() + offset
        end_pos = match.end() + offset

        # Split the email into local part and domain
        local_part, domain = email.split('@', 1)
        # Mask the local part
        masked_local = '█' * len(local_part)
        masked_email = masked_local + '@' + domain

        # Replace the email in the text with the masked email
        masked_text = masked_text[:start_pos] + masked_email + masked_text[end_pos:]
        # Update the offset
        offset += len(masked_email) - (end_pos - start_pos)
        total_names_masked += 1

    return masked_text, total_names_masked

def mask_names_in_text(text):
    # Redact names found in the text using SpaCy
    doc = nlp(text)
    validated_names = extract_and_validate_names(doc)
    masked_text = text
    total_names_masked = 0
    masked_positions = []

    # First, mask names extracted from regular text using SpaCy.
    # Sort names by start position in reverse order to avoid index shifting
    validated_names = sorted(validated_names, key=lambda x: x[1], reverse=True)
    for name, start_pos, end_pos in validated_names:
        masked_text = apply_mask(masked_text, start_pos, end_pos)
        total_names_masked += 1
        masked_positions.append({'type': 'name', 'start': start_pos, 'end': end_pos})
    
    # Then, mask names found within email addresses.
    masked_text, email_name_count = mask_names_in_email_addresses(masked_text)
    total_names_masked += email_name_count

    return masked_text, total_names_masked



def apply_mask(text, start_pos, end_pos):
    # Apply a censorship mask to a specified portion of text, adjusting for new lines.
    segment = text[start_pos:end_pos]
    newline_idx = segment.find('\n')
    
    # Adjust end position if a newline character is found within the segment
    if newline_idx != -1:
        end_pos = start_pos + newline_idx
    
    return text[:start_pos] + "█" * (end_pos - start_pos) + text[end_pos:]

dict_for_date_match = [
    {
        "label": "DATE",
        "pattern": [
            {"TEXT": {"REGEX": r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"}},               # Format: MM/DD/YYYY or similar
            {"TEXT": {"REGEX": r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s+\d{4})?\b"}},  # Format: "Jan 1, 2024" or similar
            {"TEXT": {"REGEX": r"^\w{3},\s\d{2}\s\w{3}\s\d{4}$"}},                    # Format: "Mon, 01 Jan 2024"
            {"TEXT": {"REGEX": r"\b\d{1,2}[/-]\d{1,2}\b"}}                            # Format: MM/DD
        ]
    }
]

# dict_for_date_match = [{"label":"DATE","pattern":[{"TEXT":{"REGEX":"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"}},{"TEXT":{"REGEX":"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s+\d{4})?\b"}},{"TEXT":{"REGEX":"^\w{3},\s\d{2}\s\w{3}\s\d{4}$"}},{"TEXT":{"REGEX":"\b\d{1,2}[/-]\d{1,2}"}}]},
#                        {"label":"PERSON","pattern":[{"TEXT":{"REGEX":"\b[A-Z][a-z]*\s[A-Z][a-z]*\b"}},{"TEXT":{"REGEX":"\b[A-Z][a-z]*\b"}},{"TEXT":{"REGEX":"\b[A-Z][a-z]*\s[A-Z]\.\s[A-Z][a-z]*\b"}}]}]
ruler = nlp.add_pipe("entity_ruler", before="ner")
ruler.add_patterns(dict_for_date_match)

def redact_dates(text):
    redacted_text = text
    count = 0
    offsets = [] 
    doc = nlp(text)
    spans = [ent for ent in doc.ents if ent.label_ == 'DATE']
    unique_spans = set()
    for span in spans:
        if isinstance(span, dict):
            unique_spans.add((span['start_char'], span['end_char']))
        else:
            unique_spans.add((span.start_char, span.end_char))
    
    spans = sorted(unique_spans, key=lambda x: x[0], reverse=True)
    
    for start, end in spans:
        redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
        count += 1
        offsets.append({'type': 'date', 'start': start, 'end': end})
    
    return redacted_text, count


# Regex pattern for phone numbers
phone_number_regex = re.compile(
    r'''
    (\+\d{1,3}[\s-]?)?                      # Optional international prefix
    (\(?\d{3}\)?[\s-]?)?                    # Optional area code
    (\d{3}[\s-]?\d{4}|\d{2,4}[\s-]?\d{2,4}[\s-]?\d{2,4}) # Main number
    ''', re.VERBOSE | re.IGNORECASE)



def validate_phone_number_format(text):
    # Check if a given string is likely a phone number.
    return re.match(r'\+\d{1,4}\s\d+', text) or any(sep in text for sep in ['-', ' ']) and len(re.sub(r'\D', '', text)) >= 7






def detect_concept_related_sentences(text, concepts, threshold=0.75):
    # Normalize text to handle line breaks
    text = normalize_text(text)
    doc = nlp(text)
    matched_concepts = []

    for sentence in doc.sents:
        sentence_text_lower = sentence.text.lower()
        for concept in concepts:
            concept_lower = concept.lower()
            # Direct string matching
            if concept_lower in sentence_text_lower:
                matched_concepts.append((sentence.start_char, sentence.end_char))
                break  # Stop checking other concepts if this sentence matches
            else:
                # Calculate similarity between the sentence and the concept
                concept_doc = nlp(concept)
                similarity = sentence.similarity(concept_doc)
                if similarity >= threshold:
                    matched_concepts.append((sentence.start_char, sentence.end_char))
                    break

    return matched_concepts


def normalize_text(text):
    # Replace line breaks within paragraphs with spaces
    normalized_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return normalized_text

def mask_concept_related_text(text, concepts):
    # Redact text related to specified concepts.
    matched_concepts = detect_concept_related_sentences(text, concepts)
    masked_text = text
    concept_count = 0
    masked_positions = []

    # Sort matched spans in reverse order to avoid index shifting issues.
    matched_concepts = sorted(matched_concepts, key=lambda x: x[0], reverse=True)
    for start_char, end_char in matched_concepts:
        masked_text = apply_mask(masked_text, start_char, end_char)
        concept_count += 1
        masked_positions.append({'type': 'concept', 'start': start_char, 'end': end_char})
    
    return masked_text, concept_count


def mask_phone_numbers_in_text(text):
    """Identify and mask phone numbers in the given text."""
    phone_matches = re.finditer(phone_number_regex, text)
    masked_text = text
    total_phones_masked = 0
    masked_positions = []

    for match in phone_matches:
        matched_string = match.group().strip()
        if validate_phone_number_format(matched_string):
            start, end = match.span()
            masked_text = apply_mask(masked_text, start, end)
            total_phones_masked += 1
            masked_positions.append({'type': 'phone', 'start': start, 'end': end})
    
    return masked_text, total_phones_masked

def mask_detected_addresses(text):
    """Redact detected addresses from the text using Google NLP and regex patterns."""
    masked_text = text
    total_addresses_masked = 0

    # Regex patterns for common address formats
    address_patterns = [
        r"\d{1,5}\s\w+\s(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane)\.?(\s\w+)?",   # E.g., 123 Main St or 123 Main Street Springfield
        r"\d{1,5}\s\w+\s\w+\s\w+,\s\w+\s\d{5}",                                                          # E.g., 456 Elm St., New York, NY 10001
        r"\d{1,5}\s\w+\s\w+,\s\w+,\s[A-Z]{2}\s\d{5}",                                                    # E.g., 123 Main St., Springfield, IL 62704
    ]

    # Mask detected addresses with Google NLP, consolidating related address components
    detected_addresses = consolidate_addresses(extract_addresses_using_gnlp(text))
    for address in detected_addresses:
        # Mask the full address in the text if found
        address_pattern = re.escape(address)
        masked_text = re.sub(address_pattern, '█' * len(address), masked_text)
        total_addresses_masked += 1

    # Additionally, mask common address formats using regex
    for pattern in address_patterns:
        matches = re.finditer(pattern, masked_text)
        for match in matches:
            start, end = match.span()
            
            masked_text = masked_text[:start] + '█' * (end - start) + masked_text[end:]
            total_addresses_masked += 1

    return masked_text, total_addresses_masked

def extract_addresses_using_gnlp(text):
    """Extract address components using Google NLP and return them as individual segments."""
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
    response = client.analyze_entities(document=document)

    # Extract entities that represent addresses or locations.
    detected_addresses = [
        entity.name for entity in response.entities
        if entity.type_ in [language_v1.Entity.Type.ADDRESS, language_v1.Entity.Type.LOCATION]
    ]
    return detected_addresses

def consolidate_addresses(components):
    """Consolidate individual address components into full address strings."""
    consolidated_addresses = []
    current_address = []

    for component in components:
        # Check if this component should be part of the current address
        if current_address and not component[0].isnumeric():
            # If the current component is not numeric and we have an ongoing address, finalize it
            consolidated_addresses.append(" ".join(current_address))
            current_address = []
        
        current_address.append(component)

    # Add any remaining components as a final address
    if current_address:
        consolidated_addresses.append(" ".join(current_address))

    return consolidated_addresses

def write_statistics(stats, stats_output):
    stats_json = json.dumps(stats, indent=4)
    if stats_output.lower() == 'stdout':
        print(stats_json)
    elif stats_output.lower() == 'stderr':
        print(stats_json, file=sys.stderr)
    else:
        # Assume stats_output is a filename
        try:
            with open(stats_output, 'w', encoding='utf-8') as f:
                f.write(stats_json)
        except Exception as e:
            print(f'Error writing stats to {stats_output}: {e}', file=sys.stderr)



def main():
    parser = argparse.ArgumentParser(description='Redact sensitive information from text files.')

    # --input flag (can be repeated)
    parser.add_argument('--input', action='append', required=True,
                        help='Glob pattern(s) to specify input files. Can be repeated.')

    # --output flag
    parser.add_argument('--output', required=True,
                        help='Directory where censored files will be saved.')

    # Censor flags
    parser.add_argument('--names', action='store_true', help='Redact names.')
    parser.add_argument('--dates', action='store_true', help='Redact dates.')
    parser.add_argument('--phones', action='store_true', help='Redact phone numbers.')
    parser.add_argument('--address', action='store_true', help='Redact addresses.')

    # --concept flag (can be repeated)
    parser.add_argument('--concept', action='append', help='Concept(s) to redact. Can be repeated.')

    # --stats flag
    parser.add_argument('--stats', required=True,
                        help='File or location to write statistics (filename, stderr, or stdout).')

    args = parser.parse_args()
    
    # print(args)
    # Get list of input files
    input_files = get_input_files(args.input)

    if not input_files:
        print('No input files found. Please check the --input patterns.', file=sys.stderr)
        sys.exit(1)

    # Ensure output directory exists
    output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Initialize statistics
    statistics = {
        'files_processed': 0,
        'total_redactions': 0,
        'redaction_counts': {
            'names': 0,
            'dates': 0,
            'phones': 0,
            'addresses': 0,
            'concepts': 0,
        },
        'file_stats': {}  # To store per-file statistics
    }

    # Process each file
    for file_path in input_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f'Error reading file {file_path}: {e}', file=sys.stderr)
            continue

        # Initialize per-file stats
        file_stat = {
            'redactions': 0,
            'redaction_counts': {
                'names': 0,
                'dates': 0,
                'phones': 0,
                'addresses': 0,
                'concepts': 0,
            }
        }

        # Apply redaction functions based on flags
        if args.names:
            text, name_count = mask_names_in_text(text)
            file_stat['redactions'] += name_count
            file_stat['redaction_counts']['names'] += name_count
            statistics['redaction_counts']['names'] += name_count

        if args.dates:
            text, count = redact_dates(text)
            file_stat['redactions'] += count
            file_stat['redaction_counts']['dates'] += count
            statistics['redaction_counts']['dates'] += count

        if args.phones:
            text, phone_count = mask_phone_numbers_in_text(text)
            file_stat['redactions'] += phone_count
            file_stat['redaction_counts']['phones'] += phone_count
            statistics['redaction_counts']['phones'] += phone_count

        if args.address:
            text, address_count = mask_detected_addresses(text)
            file_stat['redactions'] += address_count
            file_stat['redaction_counts']['addresses'] += address_count
            statistics['redaction_counts']['addresses'] += address_count

        # Inside main function
        if args.concept:
            text, concept_count = mask_concept_related_text(text, args.concept)
            file_stat['redactions'] += concept_count
            file_stat['redaction_counts']['concepts'] += concept_count
            statistics['redaction_counts']['concepts'] += concept_count


        # Update global stats
        statistics['files_processed'] += 1
        statistics['total_redactions'] += file_stat['redactions']
        statistics['file_stats'][os.path.basename(file_path)] = file_stat

        # Write censored text to output file
        output_file_name = os.path.basename(file_path) + '.censored'
        output_file_path = os.path.join(output_dir, output_file_name)
        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(text)

    # Write statistics
    write_statistics(statistics, args.stats)

if __name__ == '__main__':
    main()
