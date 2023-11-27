import sys
from pathlib import Path
from helpers.modality_agnostic import get_dataset_description
import os
from glob import glob
import re

def parse_command_line(args, dataset_description):
    '''
    Takes as input command line arguments as a list of strings
    Ensures origin path is specified and valid
    Returns origin and dest as pathlib.Path
    '''
    
    # If no command line arguments given, quit
    # For now, restrict args to only source and dest
    if len(args) not in [1,2]:
        raise ValueError('Usage: python eeg-to-bids.py origin_dir <dest_dir>')

    # Save command line arguments as separate variables
    origin_path = Path(args[0])
    if len(args) > 1:
        dest_path = Path(args[-1])

    # If no destination path is provided
    else:
        # infer one from the dataset name
        prefix = re.sub(r'[^\w]', '', dataset_description['Name'])
        dest_path = Path('_'.join([prefix, 'BIDS_data']))

    # Ensure the origin directory exists
    if not os.path.exists(origin_path):
        raise ValueError('The origin path for the source data that you supplied cannot be found.')

    if origin_path == dest_path:
        raise ValueError('Cannot have same dir for origin and destination!')

    return [origin_path, dest_path]


def has_sessions(subject_path):
    '''
    Takes as input a subject path as Path object
    If there are sessions, returns dict mapping session number to path
    Else, returns false
    (Just looks one dir under subject dir to check whether any sub dirs
    have 'session' in label
    '''

    subdirs = os.listdir(subject_path)

    sessions = [x for x in subdirs if 'session' in x.lower()]
    out = {}

    if sessions:
        for session in sessions:
            session_number = ''.join([char for char in session if char.isnumeric()])
            session_number = session_number.zfill(3)
            out[session_number] = session

        return out

    return False

    



def parse_subjects(origin_path):
    '''
    Takes in the origin path as a Path object
    returns a dict mapping three digit subject numbers to the dir in origin
    path
    '''
    
    err = "Couldn't find subject numbers in first level of origin path. Make sure origin directory is structured such that subject directories are in the first level."

    # Import all first-level dirs
    dirs = os.listdir(origin_path)
    # keep only numeric portion of dirs
    subjects = []

    if not dirs:
        raise ValueError(err)

    for dir_ in dirs:
        subject = {}
        subject_number = ''.join([char for char in dir_ if char.isnumeric()]).zfill(3)
        sessions = has_sessions(origin_path / Path(dir_))
        subject['number'] = subject_number
        subject['path'] = dir_
        subject['sessions'] = sessions
        subjects.append(subject)

    if not subjects:
        raise ValueError(err)

    return sorted(subjects, key = lambda x: x['number'])


def parse_data_type(origin_path):
    '''
    Takes as input origin path
    returns a boolean tuple indicating whether there is EEG and fMRI data
    present, respectively
    '''

    eeg = False
    fmri = False

    if glob(origin_path.stem + '/**/*.eeg', recursive=True):
        eeg = True
    if glob(origin_path.stem + '/**/*.nii', recursive=True):
        fmri = True

    return (eeg, fmri)

def make_skeleton(subjects, dest_path, eeg, fmri):
    '''
    Takes as input
        subjects
            list of dicts for each subject
            with keys: number, path, sessions
            sessions is its own dict with key session number and value as
            path
            False if no sessions
        dest path as pathlib.Path
        eeg and fmri are booleans indicating whether that data is present
    Makes the template bids-compatible folder structure
    '''
    modalities = []

    if eeg:
        modalities.append('eeg')
    if fmri:
        modalities += ['anat', 'func', 'fmap']

    if not modalities:
        raise ValueError('We need some type of neuro data')

    for subject in subjects:
        subject_dir = Path('sub-' + subject['number'])
        # Session dirs is an empty path if there is only one session
        session_dirs = [Path('')]
        if subject['sessions']:
            session_dirs = []
            for session in subject['sessions'].keys():
                session_dirs.append(Path('ses-' + session))

        for session_dir in session_dirs:
            for modality in modalities:
                p = dest_path / subject_dir / session_dir / Path(modality)
                if not os.path.exists(p):
                    os.makedirs(p)


    
