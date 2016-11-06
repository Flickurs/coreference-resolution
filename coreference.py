#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Jake Sebright
# Michael Pregman
# CS 5340

# imports
from spacy.en import English
import sys
import xml.etree.ElementTree as ET

new_id_count = 1
nlp = English()


def main(argv):
    list_file_path = argv[0]
    output_directory_path = argv[1]

    files_to_process = list()
    with open(list_file_path, 'rb') as listfile:
        for line in listfile.readlines():
            files_to_process.append(line.strip())

    for file_name in files_to_process:
        corefs = []
        noun_chunks = []

        tree = ET.parse(file_name)
        root = tree.getroot()

        before_first_tag = root.text

        noun_chunks.extend(find_noun_chunks(before_first_tag))

        for coref in root.findall('COREF'):
            coref_obj = Coref(coref.get('ID'), coref.text)

            resolve_coreference(corefs, noun_chunks, coref_obj)

            corefs.append(coref_obj)
            noun_chunks.extend(find_noun_chunks(coref.tail))

        corefs_to_keep = []
        for coref in corefs:
            if coref.ref:
                if coref.ref not in corefs_to_keep:
                    corefs_to_keep.append(coref.ref)
                corefs_to_keep.append(coref.coref_id)

        output_filename = output_directory_path + file_name.split('/')[-1].replace('.crf', '.response')
        with open(output_filename, 'w+') as output_file:
            print '<TXT>'

            for coref in corefs:
                if coref.coref_id in corefs_to_keep:
                    if not coref.ref:
                        print '<COREF ID="%s">%s</COREF>' % (coref.coref_id, coref.text)
                    else:
                        print '<COREF ID="%s" REF="%s">%s</COREF>' % (coref.coref_id, coref.ref, coref.text)

            print '</TXT>'


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
        if coref.text == coref_obj.text:
            coref_obj.ref = coref.coref_id
            return

    for nc in noun_chunks:
        if nc == coref_obj.text:
            corefs.append(Coref('X%d' % (new_id_count), nc))
            new_id_count += 1
            noun_chunks.remove(nc)
            return

    print 'You failed'


class Coref:
    def __init__(self, coref_id, text):
        self.text = text
        self.coref_id = coref_id
        self.ref = None


if __name__ == '__main__':
    main(sys.argv[1:])
