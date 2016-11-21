#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Jake Sebright
# Michael Pregman
# CS 5340

# imports
import sys
from spacy.en import English
import editdistance
import xml.etree.ElementTree as ET
import os

new_id_count = 1
nlp = English()


def main(argv):
    global new_id_count
    list_file_path = argv[0]
    output_directory_path = argv[1]
    if output_directory_path[-1] != '/':
        output_directory_path += '/'

    files_to_process = list()
    with open(list_file_path, 'rb') as listfile:
        for line in listfile.readlines():
            files_to_process.append(line.strip())

    for file_name in files_to_process:
        corefs = []
        noun_chunks = []

        if os.path.isfile(file_name):
            print 'Processing', file_name
        else:
            print file_name, 'could not be found. Continuing to next file.'
            continue

        tree = ET.parse(file_name)
        root = tree.getroot()

        before_first_tag = root.text

        noun_chunks.extend(find_noun_chunks(before_first_tag))

        for coref in root.findall('COREF'):
            coref_obj = Coref(coref.get('ID'), coref.text)

            resolve_coreference(corefs, noun_chunks, coref_obj)

            corefs.append(coref_obj)

            preceding_noun_chunks = find_noun_chunks(coref.tail)

            # check for 'it' references
            for word in preceding_noun_chunks:
                if word == 'it' or word == 'he' or word == 'she':
                    ref_id = coref_obj.coref_id

                    corefs.append(Coref('X%d' % new_id_count, word, ref_id))
                    new_id_count += 1
                    preceding_noun_chunks.remove(word)
                    break

            noun_chunks.extend(preceding_noun_chunks)

        corefs_to_keep = []
        for coref in corefs:
            if coref.ref:
                if coref.ref not in corefs_to_keep:
                    corefs_to_keep.append(coref.ref)
                corefs_to_keep.append(coref.coref_id)

        if not os.path.exists(output_directory_path):
            os.makedirs(output_directory_path)

        output_filename = output_directory_path + file_name.split('/')[-1].replace('.crf', '.response')
        with open(output_filename, 'w+') as output_file:
            output_file.write('<TXT>\n')

            for coref in corefs:
                if coref.coref_id in corefs_to_keep:
                    if not coref.ref:
                        output_file.write('<COREF ID="%s">%s</COREF>\n' % (coref.coref_id, coref.text))
                    else:
                        output_file.write('<COREF ID="%s" REF="%s">%s</COREF>\n' % (coref.coref_id, coref.ref, coref.text))

            output_file.write('</TXT>\n')

    print 'Done. Output files in ' + output_directory_path + '.'


# Returns True if word is plural, False otherwise
def is_plural(word):
    return False


# Finds noun chunks in a text block and returns them as a list
def find_noun_chunks(text_block):
    noun_chunks = list()
    doc = nlp(unicode(text_block.strip(), 'utf-8'))
    for np in doc.noun_chunks:
        noun_chunks.append(np.text)
    return noun_chunks


def resolve_coreference(corefs, noun_chunks, coref_obj):
    global new_id_count

    for coref in corefs:
        if analyze_corefs(coref_obj.text, coref.text):
            coref_obj.ref = coref.coref_id
            return

    for nc in noun_chunks:
        if analyze_texts(coref_obj.text, nc):
            corefs.append(Coref('X%d' % new_id_count, nc))
            new_id_count += 1
            noun_chunks.remove(nc)
            return


def analyze_corefs(coref, previous_coref):
    return analyze_texts(coref, previous_coref)


def analyze_texts(coref, noun_chunk):
    # if editdistance.eval(coref, noun_chunk) < 2:
    #     return True

    # Exact match
    if coref == noun_chunk:
        return True

    # Capitals
    c_uppers = ''.join([c for c in coref if c.isupper()])
    nc_uppers = ''.join([c for c in noun_chunk if c.isupper()])
    if len(c_uppers) > 2 and c_uppers == nc_uppers:
        return True

    coref_arr = coref.split()
    noun_chunk_arr = noun_chunk.split()
    closed_class = ['the', 'a', 'an', 'and', 'but', 'or', 'because', 'when', 'if', 'this', 'that', 'these', 'to', 'for',
                'with', 'between', 'at', 'of', 'some', 'every', 'most', 'any', 'both', 'your', 'my', 'mine', 'our', 'ours', 'its', 'his', 'her', 'hers', 'their', 'theirs', 'your', 'yours']
    coref_words_without_closed_class = [x.lower() for x in coref_arr if x.lower() not in closed_class]
    noun_chunks_without_closed_class = [x.lower() for x in noun_chunk_arr if x.lower() not in closed_class]

    # Substringing
    if len(coref_words_without_closed_class) == 0:
        return

    similarity_count = 0.0
    for i in coref_words_without_closed_class:
        for j in noun_chunks_without_closed_class:
            if i == j:
                similarity_count += 1.0

    percentage_similar = similarity_count / float(len(coref_words_without_closed_class))

    if percentage_similar >= 0.01:
        return True


class Coref:
    def __init__(self, coref_id, text, ref=None):
        self.text = text
        self.coref_id = coref_id
        self.ref = None


if __name__ == '__main__':
    main(sys.argv[1:])
