# redactor.py

import argparse
import sys
import os
import glob
import json
import re
import spacy

# Load the SpaCy model with word vectors (for concept redaction)
# You may need to download the model if not already installed:
# python -m spacy download en_core_web_md
nlp = spacy.load('en_core_web_md')

# List of email headers that may contain names
EMAIL_HEADERS = [
    'From:', 'To:', 'Cc:', 'Bcc:', 'Subject:',
    'X-From:', 'X-To:', 'X-cc:', 'X-bcc:',
    'X-Folder:', 'X-Origin:', 'X-FileName:'
]

def get_input_files(input_patterns):
    files = []
    for pattern in input_patterns:
        matched_files = glob.glob(pattern, recursive=True)
        # Debug: print matched files
        # print(f"Pattern: {pattern} | Matched Files: {matched_files}")
        files.extend(matched_files)
    return files

def redact_email_addresses(text):
    redacted_text = text
    email_pattern = re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w+\b')
    count = 0
    offsets = []

    for match in email_pattern.finditer(redacted_text):
        email = match.group()
        local_part = email.split('@')[0]
        # Split local part by delimiters
        name_parts = re.split(r'[._-]', local_part)
        for part in name_parts:
            if part.isalpha() and part[0].isalpha():
                # Redact the name part
                start = match.start() + email.find(part)
                end = start + len(part)
                redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
                count += 1
                offsets.append({'type': 'name', 'start': start, 'end': end})
    return redacted_text, count, offsets

def redact_names(text):
    redacted_text = text
    total_count = 0
    total_offsets = []

    # Step 1: Redact names in email headers
    header_pattern = re.compile(r'^(' + '|'.join(re.escape(hdr) for hdr in EMAIL_HEADERS) + r')(.*)$', re.MULTILINE)
    # Pattern to match names in headers
    name_in_header_pattern = re.compile(
        r'([A-Z][a-z]+,\s*[A-Z][a-z]+)'            # LastName, FirstName
        r'|([A-Z][a-z]+(\s+[A-Z]\.)?\s+[A-Z][a-z]+)'   # FirstName Middle Initial LastName
        r'|([A-Z]\.\s+[A-Z][a-z]+)'                # Initial LastName
        r'|([A-Z][a-z]+)'                          # Single capitalized names
    )

    for header_match in header_pattern.finditer(text):
        header = header_match.group(1)
        content = header_match.group(2)
        for match in name_in_header_pattern.finditer(content):
            start = match.start() + header_match.start(2)
            end = match.end() + header_match.start(2)
            redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
            total_count += 1
            total_offsets.append({'type': 'name', 'start': start, 'end': end})

    # Step 2: Redact names in email addresses
    email_redacted_text, email_count, email_offsets = redact_email_addresses(redacted_text)
    redacted_text = email_redacted_text
    total_count += email_count
    total_offsets.extend(email_offsets)

    # Step 3: Redact names in the body using SpaCy
    # Find where headers end
    last_header_end = 0
    for match in header_pattern.finditer(text):
        last_header_end = match.end()
    body_text = redacted_text[last_header_end:]

    doc = nlp(body_text)
    spans = [ent for ent in doc.ents if ent.label_ == 'PERSON']
    spans = sorted(spans, key=lambda span: span.start_char, reverse=True)

    for span in spans:
        start = last_header_end + span.start_char
        end = last_header_end + span.end_char
        redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
        total_count += 1
        total_offsets.append({'type': 'name', 'start': start, 'end': end})

    return redacted_text, total_count, total_offsets

def redact_dates(text):
    redacted_text = text
    count = 0
    offsets = []

    # Use SpaCy NER to find dates
    doc = nlp(text)
    spans = [ent for ent in doc.ents if ent.label_ == 'DATE']

    # Add regex patterns for dates not detected by NER
    date_patterns = [
        r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',  # Matches 4/9/2025, 22/2/22
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?(?:,\s+\d{4})?\b',  # Matches April 9th, 2025
    ]

    for pattern in date_patterns:
        for match in re.finditer(pattern, redacted_text, flags=re.IGNORECASE):
            start, end = match.span()
            spans.append({'start_char': start, 'end_char': end})

    # Remove duplicates and sort
    unique_spans = {(span['start_char'], span['end_char']) if isinstance(span, dict) else (span.start_char, span.end_char) for span in spans}
    spans = sorted(unique_spans, key=lambda x: x[0], reverse=True)

    for start, end in spans:
        redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
        count += 1
        offsets.append({'type': 'date', 'start': start, 'end': end})

    return redacted_text, count, offsets

def redact_phones(text):
    redacted_text = text
    count = 0
    offsets = []

    phone_patterns = [
        r'\b\+?\d{1,3}[\s.-]?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,4}\b',
        r'\(\d{3}\)\s*\d{3}-\d{4}',
    ]

    for pattern in phone_patterns:
        for match in re.finditer(pattern, redacted_text):
            start, end = match.span()
            redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
            count += 1
            offsets.append({'type': 'phone', 'start': start, 'end': end})

    return redacted_text, count, offsets

def redact_addresses(text):
    redacted_text = text
    count = 0
    offsets = []

    # Use SpaCy NER to find addresses
    doc = nlp(text)
    spans = [ent for ent in doc.ents if ent.label_ in ['GPE', 'LOC', 'FAC']]

    # Add regex patterns for addresses
    address_patterns = [
        r'\b\d{1,5}\s+[\w\s]+(?:Street|St\.?|Avenue|Ave\.?|Road|Rd\.?|Boulevard|Blvd\.?)\b',
    ]

    for pattern in address_patterns:
        for match in re.finditer(pattern, redacted_text, flags=re.IGNORECASE):
            start, end = match.span()
            spans.append({'start_char': start, 'end_char': end})

    # Remove duplicates and sort
    unique_spans = {(span['start_char'], span['end_char']) if isinstance(span, dict) else (span.start_char, span.end_char) for span in spans}
    spans = sorted(unique_spans, key=lambda x: x[0], reverse=True)

    for start, end in spans:
        redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
        count += 1
        offsets.append({'type': 'address', 'start': start, 'end': end})

    return redacted_text, count, offsets

def redact_concepts(text, concepts):
    redacted_text = text
    count = 0
    offsets = []

    doc = nlp(text)
    concept_tokens = [nlp(concept.lower())[0] for concept in concepts]
    sentences = list(doc.sents)
    spans_to_redact = []

    for sent in sentences:
        redact_sentence = False
        for token in sent:
            for concept_token in concept_tokens:
                similarity = token.similarity(concept_token)
                if similarity > 0.7:
                    redact_sentence = True
                    break
            if redact_sentence:
                break
        if redact_sentence:
            start = sent.start_char
            end = sent.end_char
            spans_to_redact.append((start, end))

    # Redact the sentences
    for start, end in sorted(spans_to_redact, key=lambda x: x[0], reverse=True):
        redacted_text = redacted_text[:start] + '█' * (end - start) + redacted_text[end:]
        count += 1
        offsets.append({'type': 'concept', 'start': start, 'end': end})

    return redacted_text, count, offsets

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
            },
            'offsets': []  # Collect offsets here if needed
        }

        # Apply redaction functions based on flags
        if args.names:
            text, count, offsets = redact_names(text)
            file_stat['redactions'] += count
            file_stat['redaction_counts']['names'] += count
            file_stat['offsets'].extend(offsets)
            statistics['redaction_counts']['names'] += count

        if args.dates:
            text, count, offsets = redact_dates(text)
            file_stat['redactions'] += count
            file_stat['redaction_counts']['dates'] += count
            file_stat['offsets'].extend(offsets)
            statistics['redaction_counts']['dates'] += count

        if args.phones:
            text, count, offsets = redact_phones(text)
            file_stat['redactions'] += count
            file_stat['redaction_counts']['phones'] += count
            file_stat['offsets'].extend(offsets)
            statistics['redaction_counts']['phones'] += count

        if args.address:
            text, count, offsets = redact_addresses(text)
            file_stat['redactions'] += count
            file_stat['redaction_counts']['addresses'] += count
            file_stat['offsets'].extend(offsets)
            statistics['redaction_counts']['addresses'] += count

        if args.concept:
            text, count, offsets = redact_concepts(text, args.concept)
            file_stat['redactions'] += count
            file_stat['redaction_counts']['concepts'] += count
            file_stat['offsets'].extend(offsets)
            statistics['redaction_counts']['concepts'] += count

        # Update global stats
        statistics['files_processed'] += 1
        statistics['total_redactions'] += file_stat['redactions']
        statistics['file_stats'][os.path.basename(file_path)] = file_stat

        # Write censored text to output file
        output_file_name = os.path.basename(file_path) + '.censored'
        output_file_path = os.path.join(output_dir, output_file_name)
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(text)
        except Exception as e:
            print(f'Error writing file {output_file_path}: {e}', file=sys.stderr)
            continue

    # Write statistics
    write_statistics(statistics, args.stats)

if __name__ == '__main__':
    main()
