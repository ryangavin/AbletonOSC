import time
import pytest

#--------------------------------------------------------------------------------
# Add . to the path so that pythonosc can be imported, enabling unit testing
# without any external dependencies
#--------------------------------------------------------------------------------
import sys
sys.path.append(".")

from ..client import AbletonOSCClient, TICK_DURATION

# Live tick is 100ms. Wait for this long plus a short additional buffer.
TICK_DURATION = 0.125

# Test set configuration (from README)
NUM_TRACKS = 4
NUM_SCENES = 8

@pytest.fixture(scope="module")
def client() -> AbletonOSCClient:
    client = AbletonOSCClient()
    yield client
    client.stop()

@pytest.fixture(scope="session", autouse=True)
def reset_set(client):
    """Reset the Ableton set to a clean state once before all tests."""
    # Stop playback
    client.send_message("/live/song/stop_playing", ())
    client.send_message("/live/song/stop_all_clips", ())
    time.sleep(TICK_DURATION)

    # Create fresh tracks first (Ableton requires at least one track)
    # 2 MIDI, 2 Audio - insert at index 0 so they become tracks 0-3
    client.send_message("/live/song/create_midi_track", (0,))
    client.send_message("/live/song/create_midi_track", (1,))
    client.send_message("/live/song/create_audio_track", (2,))
    client.send_message("/live/song/create_audio_track", (3,))
    time.sleep(TICK_DURATION)

    # Now delete all old tracks (they're now at index 4+)
    num_tracks = client.query("/live/song/get/num_tracks", ())[0]
    for track_id in range(num_tracks - 1, NUM_TRACKS - 1, -1):
        client.send_message("/live/song/delete_track", (track_id,))
    time.sleep(TICK_DURATION)

    # Delete extra scenes beyond the expected 8
    num_scenes = client.query("/live/song/get/num_scenes", ())[0]
    for scene_id in range(num_scenes - 1, NUM_SCENES - 1, -1):
        client.send_message("/live/song/delete_scene", (scene_id,))
    time.sleep(TICK_DURATION)

    yield

    # Post-session cleanup: stop any clips that might still be playing
    client.send_message("/live/song/stop_all_clips", ())

def wait_one_tick():
    """
    Sleep for one Ableton Live tick (100ms).
    """
    time.sleep(TICK_DURATION)

c = AbletonOSCClient()
c.send_message("/live/api/reload")
c.stop()
