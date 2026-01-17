try:
    import sounddevice
    print("sounddevice: OK")
except ImportError:
    print("sounddevice: MISSING")

try:
    import faster_whisper
    print("faster_whisper: OK")
except ImportError:
    print("faster_whisper: MISSING")

try:
    import numpy
    print("numpy: OK")
except ImportError:
    print("numpy: MISSING")
