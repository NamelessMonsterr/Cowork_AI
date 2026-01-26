
import pytest
import numpy as np
from unittest import mock
from assistant.voice.audio_recorder import AudioRecorder, AudioError

class TestAudioRecorder:
    
    @mock.patch("assistant.voice.audio_recorder.sd")
    def test_device_not_found(self, mock_sd):
        # Mock query_devices to return empty list or no input devices
        mock_sd.query_devices.return_value = []
        
        recorder = AudioRecorder()
        # Should not crash on init
        
        data, error = recorder.record(1)
        assert data is None
        assert error is not None
        assert error["code"] == "device_not_found"

    @mock.patch("assistant.voice.audio_recorder.sd")
    def test_record_success(self, mock_sd):
        # Mock query_devices to return a valid input device
        mock_sd.query_devices.return_value = [
            {'name': 'Mock Mic', 'max_input_channels': 1}
        ]
        
        # Mock recording
        mock_sd.rec.return_value = np.zeros((16000, 1), dtype='float32')
        mock_sd.wait.return_value = None
        
        recorder = AudioRecorder()
        data, error = recorder.record(1)
        
        assert error is None
        assert data is not None
        assert len(data) > 0
