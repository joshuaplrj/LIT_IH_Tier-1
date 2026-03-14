# AIDS-P1: NeuroDecode EEG Dataset

## Overview
Simulated EEG motor imagery dataset. 10 subjects, 400 trials each, 4 classes.

## Files
- eeg_data/subject_01.npy ... subject_10.npy : shape (400, 500, 64) float32
- labels.csv : subject_id, trial_id, class_label, class_name
- channel_info.json : 64 EEG channel names (10-20 system)

## Classes: 0=left_hand, 1=right_hand, 2=feet, 3=tongue
