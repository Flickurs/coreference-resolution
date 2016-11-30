#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Jake Sebright
# Michael Pregman
# CS 5340

# imports
import sys
from spacy.en import English
from dateutil import parser
import xml.etree.ElementTree as ET
import os

new_id_count = 1
nlp = English()
closed_class = ['the', 'a', 'an', 'and', 'but', 'or', 'because', 'when', 'if', 'this', 'that', 'these', 'to', 'for',
                'with', 'between', 'at', 'of', 'some', 'every', 'most', 'any', 'both', 'your', 'my', 'mine', 'our',
                'ours', 'its', 'his', 'her', 'hers', 'their', 'theirs', 'your', 'yours', 'it', 'he', 'she', 'they',
                'them', 'those', 'itself', 'himself', 'herself', 'themselves']


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

        split_on_white_space = root.text.strip().split()
        preceding_noun_chunks, other_words = find_noun_chunks(root.text)

        for coref in root.findall('COREF'):
            coref_obj = Coref(coref.get('ID'), coref.text.replace('\n', ' '))

            resolve_coreference(corefs, coref_obj, noun_chunks, preceding_noun_chunks, other_words,
                                split_on_white_space, coref.tail[0])

            corefs.append(coref_obj)

            noun_chunks.extend(preceding_noun_chunks)
            next_preceding_noun_chunks, next_other_words = find_noun_chunks(coref.tail)
            split_on_white_space.extend(coref.tail.strip().split())
            preceding_noun_chunks = next_preceding_noun_chunks
            other_words.extend(next_other_words)

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


# Finds noun chunks in a text block and returns them as a list
def find_noun_chunks(text_block):
    text_block = text_block.replace('\n', ' ')
    noun_chunks = list()
    other_words = list()
    doc = nlp(unicode(text_block.strip(), 'utf-8'))
    for np in doc.noun_chunks:
        noun_chunks.append(np.text)
    for token in doc:
        other_words.append(token.string.strip())
    return noun_chunks, other_words


def resolve_coreference(corefs, coref_obj, noun_chunks, preceding_noun_chunks, other_words,
                        split_on_white_space, first_following_char):
    global new_id_count

    # Date
    date = get_date(coref_obj.text)
    if date:
        for nc in noun_chunks:
            preceding_date = get_date(nc)
            if preceding_date and preceding_date.day == date.day and preceding_date.month == date.month:
                corefs.append(Coref('X%d' % new_id_count, nc))
                new_id_count += 1
                noun_chunks.remove(nc)
                coref_obj.ref = corefs[-1].coref_id
                return

        for word in split_on_white_space:
            preceding_date = get_date(word)
            if preceding_date and preceding_date.day == date.day and preceding_date.month == date.month:
                corefs.append(Coref('X%d' % new_id_count, word))
                new_id_count += 1
                split_on_white_space.remove(word)
                coref_obj.ref = corefs[-1].coref_id
                return

    # Appositive
    if other_words and other_words[-1] == first_following_char and first_following_char == ',':
        if preceding_noun_chunks:
            corefs.append(Coref('X%d' % new_id_count, preceding_noun_chunks[-1]))
            new_id_count += 1
            del preceding_noun_chunks[-1]
        coref_obj.ref = corefs[-1].coref_id
        return

    if coref_obj.text in closed_class and len(corefs) > 0:
        # if preceding_noun_chunks:
        #     corefs.append(Coref('X%d' % new_id_count, preceding_noun_chunks[-1]))
        #     new_id_count += 1
        #     del preceding_noun_chunks[-1]

        coref_obj.ref = corefs[-1].coref_id
        return

    for coref in corefs:
        if analyze_corefs(coref_obj.text, coref.text):
            coref_obj.ref = coref.coref_id
            return

    for nc in noun_chunks:
        if analyze_texts(coref_obj.text, nc):
            corefs.append(Coref('X%d' % new_id_count, nc))
            new_id_count += 1
            noun_chunks.remove(nc)
            coref_obj.ref = corefs[-1].coref_id
            return

    for nc in preceding_noun_chunks:
        if analyze_texts(coref_obj.text, nc):
            corefs.append(Coref('X%d' % new_id_count, nc))
            new_id_count += 1
            preceding_noun_chunks.remove(nc)
            coref_obj.ref = corefs[-1].coref_id
            return

    for word in other_words:
        if coref_obj.text.lower() == word.lower():
            corefs.append(Coref('X%d' % new_id_count, word))
            new_id_count += 1
            other_words.remove(word)
            coref_obj.ref = corefs[-1].coref_id
            return

    if corefs:
        coref_obj.ref = corefs[-1].coref_id
    return


def analyze_corefs(coref, previous_coref):
    return analyze_texts(coref, previous_coref)


def analyze_texts(coref, noun_chunk):
    # if editdistance.eval(coref, noun_chunk) < 2:
    #     return True

    # Exact match
    if coref.lower() == noun_chunk.lower():
        return True

    # Capitals
    c_uppers = ''.join([c for c in coref if c.isupper()])
    nc_uppers = ''.join([c for c in noun_chunk if c.isupper()])
    if len(c_uppers) > 2 and c_uppers == nc_uppers:
        return True

    coref_arr = coref.split()
    noun_chunk_arr = noun_chunk.split()
    coref_words_without_closed_class = [x.lower() for x in coref_arr if x.lower() not in closed_class]
    noun_chunks_without_closed_class = [x.lower() for x in noun_chunk_arr if x.lower() not in closed_class]

    # Substringing
    if len(coref_words_without_closed_class) == 0 or len(noun_chunks_without_closed_class) == 0:
        return

    similarity_count = 0.0
    for i in coref_words_without_closed_class:
        for j in noun_chunks_without_closed_class:
            if type(i) is str:
                i = unicode(i, 'utf-8')
            if type(j) is str:
                j = unicode(j, 'utf-8')

            if nlp(i.lower())[0].lemma_ == nlp(j.lower())[0].lemma_:
                similarity_count += 1.0

    if similarity_count > 1:
        return True

    if coref_words_without_closed_class[-1].lower() == noun_chunks_without_closed_class[-1].lower():
        return True


def get_date(string):
    try:
        date = parser.parse(string)
        return date
    except:
        return None


class Coref:
    def __init__(self, coref_id, text, ref=None):
        self.text = text
        self.coref_id = coref_id
        self.ref = None


if __name__ == '__main__':
    main(sys.argv[1:])
