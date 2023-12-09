import librosa
import numpy as np
import pandas as pd
import os
from mutagen.mp3 import MP3
from multiprocessing import Pool
import traceback


def process_files_parallel(file_paths, num_processes=6):
    with Pool(num_processes) as pool:
        results = pool.map(analyze_audio_features, file_paths)
    return results


def analyze_audio_features(audio_path, calculate_tempo=True, calculate_basic_features=True, calculate_extended_features=True, sr=22050, frame_size=2048, hop_length=1024, n_mfcc=13):
    # Load audio file
    y, sr = librosa.load(audio_path, sr=sr)
    features = {}

    if calculate_tempo:
        # Tempo and Timbre
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        features.update({
            "tempo": tempo,
        })

    if calculate_basic_features:
        # Basic Features
        stft = np.abs(librosa.stft(y=y, n_fft=frame_size, hop_length=hop_length))
        spectral_centroids = librosa.feature.spectral_centroid(S=stft, sr=sr)[0]
        spectral_bandwidth = librosa.feature.spectral_bandwidth(S=stft, sr=sr)[0]
        spectral_spread = np.std(stft, axis=0)
        spectral_rolloff = librosa.feature.spectral_rolloff(S=stft, sr=sr)[0]

        features.update({
            'centroid_mean': np.mean(spectral_centroids),
            'centroid_std': np.std(spectral_centroids),
            'spread_mean': np.mean(spectral_spread),
            'spread_std': np.std(spectral_spread),
            'rolloff_mean': np.mean(spectral_rolloff),
            'rolloff_std': np.std(spectral_rolloff)
        })

    if calculate_extended_features:
        # Extended Features
        chroma_stft = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=frame_size, hop_length=hop_length)
        rms = librosa.feature.rms(y=y, frame_length=frame_size, hop_length=hop_length)
        harmonic, percussive = librosa.effects.hpss(y=y)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)

        features.update({
            'chroma_stft_mean': chroma_stft.mean(),
            'chroma_stft_var': chroma_stft.var(),
            'rms_mean': rms.mean(),
            'rms_std': rms.std(),
            'harmony_mean': harmonic.mean(),
            'harmony_var': harmonic.var(),
            'percu_mean': percussive.mean(),
            'percu_var': percussive.var(),
            **{f'mfcc_{i+1}_mean': m for i, m in enumerate(mfcc.mean(axis=1))},
            **{f'mfcc_{i+1}_var': v for i, v in enumerate(mfcc.var(axis=1))}
        })

    return features
