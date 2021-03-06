#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Make character-level labels for CTC model (Fisher corpus)."""

import os
import re
import numpy as np
from tqdm import tqdm

from prepare_path import Prepare
from utils.util import mkdir
from utils.labels.character import char2num


# NOTE:
# 26 alphabets(a-z), 10 numbers(0-9),
# space(_), apostorophe('), hyphen(-),
# L:laughter, N:noise
# = 26 + 10 + 3 + 2 = 41 labels


def read_trans(label_paths, speaker, save_path=None):
    """Read transcripts (*_trans.txt) & save files (.npy).
    Args:
        label_paths: list of paths to label files
        speaker: A or B
        save_path: path to save labels. If None, don't save labels
    Returns:
        speaker_dict: dictionary of speakers
            key => speaker name
            value => dictionary of utterance infomation of each speaker
                key => utterance index
                value => [start_frame, end_frame, transcript]
    """
    print('===> Reading target labels...')
    speaker_dict = {}
    char_set = set([])
    for label_path in tqdm(label_paths):
        utterance_dict = {}
        with open(label_path, 'r') as f:
            utt_index = 0
            session_name = os.path.basename(label_path).split('.')[0]
            for line in f:
                line = line.strip().split(' ')
                if line[0] in ['#', '']:
                    continue
                start_frame = int(float(line[0]) * 100 + 0.05)
                end_frame = int(float(line[1]) * 100 + 0.05)
                which_speaker = line[2].replace(':', '')
                if which_speaker != speaker:
                    continue
                speaker_name = session_name + which_speaker

                # convert to lowercase
                transcript_original = ' '.join(line[3:]).lower()

                # clean transcript
                transcript = fix_transcript(transcript_original)

                # skip silence
                if transcript == '':
                    continue

                # merge silence around each utterance
                transcript = '_' + transcript + '_'

                # remove double underbar
                transcript = re.sub('__', '_', transcript)

                for char in list(transcript.lower()):
                    char_set.add(char)

                utterance_dict[str(utt_index).zfill(4)] = [
                    start_frame, end_frame, transcript]

                utt_index += 1
            speaker_dict[speaker_name] = utterance_dict

    # make the mapping file (from character to number)
    prep = Prepare()
    mapping_file_path = os.path.join(prep.run_root_path,
                                     'labels/ctc/fisher/char2num.txt')

    char_set.add('5')
    char_set.add('9')
    char_set.add('L')
    char_set.add('N')
    # if not os.path.isfile(mapping_file_path):
    with open(mapping_file_path, 'w') as f:
        for index, char in enumerate(sorted(list(char_set))):
            f.write('%s  %s\n' % (char, str(index)))

    if save_path is not None:
        # save target labels
        print('===> Saving target labels...')
        for speaker_name, utterance_dict in tqdm(speaker_dict.items()):
            mkdir(os.path.join(save_path, speaker_name))
            for utt_index, utt_info in utterance_dict.items():
                start_frame, end_frame, transcript = utt_info
                save_file_name = speaker_name + '_' + utt_index + '.npy'

                # convert from character to number
                char_index_list = char2num(transcript, mapping_file_path)

                # save as npy file
                np.save(os.path.join(save_path, speaker_name,
                                     save_file_name), char_index_list)

    return speaker_dict


def fix_transcript(transcript):

    transcript = re.sub(r'\[laughter\]', 'L', transcript)
    transcript = re.sub(r'\[laugh\]', 'L', transcript)

    # replace all to NOISE
    transcript = re.sub(r'\[noise\]', 'N', transcript)
    transcript = re.sub(r'\[sigh\]', 'N', transcript)
    transcript = re.sub(r'\[cough\]', 'N', transcript)
    transcript = re.sub(r'\[mn\]', 'N', transcript)
    transcript = re.sub(r'\[breath\]', 'N', transcript)
    transcript = re.sub(r'\[lipsmack\]', 'N', transcript)
    transcript = re.sub(r'\[sneeze\]', 'N', transcript)

    # remove
    transcript = re.sub(r'\[pause\]', '', transcript)
    transcript = re.sub(r'\[\[skip\]\]', '', transcript)
    transcript = re.sub(r'\?', '', transcript)
    transcript = re.sub(r'\*', '', transcript)
    transcript = re.sub(r'~', '', transcript)
    transcript = re.sub(r'\,', '', transcript)
    transcript = re.sub(r'\.', '', transcript)

    # remove sentences which include german words
    german = re.match(r'(.*)<german (.+)>(.*)', transcript)
    if german is not None:
        transcript = ''

    # remove ((  ))
    transcript = re.sub(r'\(\([\s]+\)\)', '', transcript)
    kakko_expr = re.compile(r'(.*)\(\( ([^(]+) \)\)(.*)')
    while re.match(kakko_expr, transcript) is not None:
        kakko = re.match(kakko_expr, transcript)
        transcript = kakko.group(1) + kakko.group(2) + kakko.group(3)

    # replace "&" to "and"
    transcript = re.sub('&', ' and ', transcript)

    # remove "/"
    # transcript = re.sub('/', '', transcript)

    # remove double space
    transcript = re.sub('  ', ' ', transcript)

    # replace space( ) to "_"
    transcript = re.sub(' ', '_', transcript)

    return transcript
