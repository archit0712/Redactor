import spacy
import re

# Load the medium or large SpaCy model with word vectors
nlp = spacy.load('en_core_web_md')

def normalize_text(text):
    # Replace line breaks within paragraphs with spaces
    normalized_text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
    return normalized_text

def detect_concept_related_sentences(text, concepts, threshold=0.2):
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

def apply_mask(text, start, end):
    # Replace the text in the given range with block characters
    length = end - start
    mask = '█' * length
    return text[:start] + mask + text[end:]

def mask_concept_related_text(text, concepts):
    # Redact text related to specified concepts.
    matched_concepts = detect_concept_related_sentences(text, concepts)
    masked_text = text
    total_concepts_masked = 0
    masked_positions = []

    # Sort matched spans in reverse order to avoid index shifting issues.
    matched_concepts = sorted(matched_concepts, key=lambda x: x[0], reverse=True)
    for start_char, end_char in matched_concepts:
        masked_text = apply_mask(masked_text, start_char, end_char)
        total_concepts_masked += 1
        masked_positions.append({'type': 'concept', 'start': start_char, 'end': end_char})
    
    return masked_text, total_concepts_masked

# Example usage
text = """Message-ID: <17450459.1075863593654.JavaMail.evans@thyme>
Date: Thu, 8 Jun 2000 04:41:00 -0700 (PDT)
From: dfuller@caiso.com
To: marketparticipants@caiso.com
Subject: Summer 2000 Market Participating Load Trial Program Re-Opener
Mime-Version: 1.0
Content-Type: text/plain; charset=us-ascii
Content-Transfer-Encoding: 7bit
X-From: "Fuller, Don" <DFuller@caiso.com>
X-To: Market Participants <IMCEAEX-_O=CAISO_OU=CORPORATE_CN=DISTRIBUTION+20LISTS_CN=MARKETPARTICIPANTS@caiso.com>
X-cc: 
X-bcc: 
X-Folder: \\Robert_Badeer_Aug2000\\Notes Folders\\All documents
X-Origin: Badeer-R
X-FileName: rbadeer.nsf

>    Market Participants:
>
>    This notice announces the "re-opening" of the Summer
> 2000 Market Participating Load Trial Program.  Note that this program has
> also been referred to as the Summer 2000 A/S Load Program.   It involves
> load participation in the Non-Spin and Replacement Reserve and also the
> Supplemental Energy markets.  This re-opening notice does not apply to the
> Summer 2000 Demand Relief Program.
>
>    On February 29, 2000, the ISO issued a Market Notice
> for the "Summer 2000 Market Participating Load Trial Program" soliciting
> participation in the ISO's Ancillary Services and Supplemental Energy
> markets by additional Participating Loads.  The ISO proposed to
> accommodate such participation from June 15 to October 15, 2000 by Loads
> that could provide telemetry of their Demand data to the ISO's Energy
> Management System pursuant to a "relaxed" Technical Standard.  The ISO
> indicated that it would accept proposals for up to the following amounts
> of capacity for bidding in the specified markets:
>
>      Non-Spinning Reserve:   400 MW
>      Replacement Reserve:   400 MW
>      Supplemental Energy: 1,000 MW
>
>    In response to that solicitation, the ISO received
> several proposals and has been working to implement participation by the
> respondents.  In the course of the implementation process, the ISO has
> determined that the actual amounts of capacity that will potentially be
> available to participate will be below the maximum for any of the listed
> services.  Approximately half of the 400 MW in Non-Spin and Replacement
> has been committed (some subject to CPUC approval) leaving approximately
> 200 MW available in each category.  Approximately 750 MW is still
> available in the Supplemental Energy category.
>
>    Therefore, the ISO wishes to announce a re-opening
> of the period for submittal of proposals for the "Summer 2000 Market
> Participating Load Trial Program"  The ISO seeks to obtain the total
> amount of participation requested for the trial program within the time
> available.  At this time the ISO plans to leave this solicitation open
> until the maximum capacities are reached as noted above.  Also it should
> be noted that while the solicitation will be open until the requested
> capacities are reached,  the current timeframe of the Summer 2000 Trial
> Program and the applicability of the "relaxed" Technical Standards runs
> only through October 15, 2000.  At this time the ISO expects to continue
> this Load Program beyond October 15, 2000, however a final decision on
> continuation and the exact technical and commercial details applicable to
> any such continuation will be reached late this year based on a review of
> the Summer 2000 Program experience.
>
>
>    Additional respondents should follow the process and
> requirements set forth in the February 29, 2000 Market Notice in all
> respects other than the date for delivery of proposals.  This can be
> located on the ISO Home Page at  http://www.caiso.com/clientserv/load/ .
> or by navigating from Client Services to Stakeholder Processes to
> Participating Loads.  There are 4 documents listed under the Feb 29
> posting entitled " Formal Invitation for the Summer 2000 Load
> Participation in the ISO Ancillary  Service and Supplemental Energy
> Markets. "
>
>    If you have any questions, please direct them to
> Mike Dozier at 916-608-5708.
>
>
>    Don Fuller
    Director, Client Relations
"""

concepts = ["summer"]

masked_text, total_concepts_masked = mask_concept_related_text(text, concepts)
print(masked_text)
