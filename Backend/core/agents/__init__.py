"""
core/agents/__init__.py
========================
AI agents for malpractice detection.
"""
from .base_agent import MalpracticeDetectionAgent
from .face_tracking_agent import FaceTrackingAgent
from .object_detection_agent import ObjectDetectionAgent
from .audio_analysis_agent import AudioAnalysisAgent
from .disconnect_pattern_agent import DisconnectPatternAgent
from .gap_video_forensics_agent import GapVideoForensicsAgent
from .device_fingerprint_agent import DeviceFingerprintAgent
from .behavior_anomaly_agent import BehaviorAnomalyAgent

__all__ = [
    'MalpracticeDetectionAgent',
    'FaceTrackingAgent',
    'ObjectDetectionAgent',
    'AudioAnalysisAgent',
    'DisconnectPatternAgent',
    'GapVideoForensicsAgent',
    'DeviceFingerprintAgent',
    'BehaviorAnomalyAgent',
]
