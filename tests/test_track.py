from . import client, wait_one_tick, TICK_DURATION
import pytest
import itertools

#--------------------------------------------------------------------------------
# Test track properties
#--------------------------------------------------------------------------------

def _test_track_property(client, track_id, property, values):
    for value in values:
        print("Testing property %s, value: %s" % (property, value))
        client.send_message("/live/track/set/%s" % property, [track_id, value])
        wait_one_tick()
        assert client.query("/live/track/get/%s" % property, [track_id]) == (track_id, value,)

def test_track_property_panning(client):
    _test_track_property(client, 2, "panning", [0.5, 0.0])

def test_track_property_volume(client):
    _test_track_property(client, 2, "volume", [0.5, 1.0])

def test_track_property_color(client):
    # Only specific colors from the color picker can be used
    _test_track_property(client, 2, "color", [0x001AFF2F, 0x001A2F96])

def test_track_property_mute(client):
    _test_track_property(client, 2, "mute", [1, 0])

def test_track_property_solo(client):
    _test_track_property(client, 2, "solo", [1, 0])

def test_track_property_name(client):
    _test_track_property(client, 2, "name", ["Test", "Track"])

#--------------------------------------------------------------------------------
# Test track properties - sends
#--------------------------------------------------------------------------------

def test_track_get_send(client):
    track_id = 2
    send_id = 1

    for value in [0.5, 0.0]:
        client.send_message("/live/track/set/send", [track_id, send_id, value])
        wait_one_tick()
        assert client.query("/live/track/get/send", (track_id, send_id)) == (track_id, send_id, value,)

def test_track_listen_send(client):
    """Test send listener fires on send value change."""
    track_id = 0
    send_id = 0

    # Reset to known value first
    client.send_message("/live/track/set/send", [track_id, send_id, 0.0])
    wait_one_tick()

    # Start listener - should get initial value
    client.send_message("/live/track/start_listen/send", [track_id, send_id])
    initial = client.await_message("/live/track/get/send", TICK_DURATION * 2)
    assert initial is not None
    assert initial[0] == track_id
    assert initial[1] == send_id
    # initial[2] is the value

    # Change value
    new_value = 0.75
    client.send_message("/live/track/set/send", [track_id, send_id, new_value])
    wait_one_tick()

    response = client.await_message("/live/track/get/send", TICK_DURATION * 2)
    assert response is not None
    assert response[0] == track_id
    assert response[1] == send_id
    assert abs(response[2] - new_value) < 0.01

    # Change to another value
    new_value = 0.25
    client.send_message("/live/track/set/send", [track_id, send_id, new_value])
    wait_one_tick()

    response = client.await_message("/live/track/get/send", TICK_DURATION * 2)
    assert response is not None
    assert abs(response[2] - new_value) < 0.01

    # Cleanup
    client.send_message("/live/track/stop_listen/send", [track_id, send_id])
    client.send_message("/live/track/set/send", [track_id, send_id, 0.0])
    wait_one_tick()

#--------------------------------------------------------------------------------
# Test track properties - clips
#--------------------------------------------------------------------------------

def test_track_clips(client):
    track_id = 0
    client.send_message("/live/clip_slot/create_clip", (track_id, 0, 4))
    client.send_message("/live/clip_slot/create_clip", (track_id, 1, 2))
    client.send_message("/live/clip/set/name", (track_id, 0, "Alpha"))
    client.send_message("/live/clip/set/name", (track_id, 1, "Beta"))

    wait_one_tick()
    assert client.query("/live/track/get/clips/name", (track_id,)) == (track_id,
                                                                       "Alpha", "Beta", None, None,
                                                                       None, None, None, None)
    assert client.query("/live/track/get/clips/length", (track_id,)) == (track_id,
                                                                         4, 2, None, None,
                                                                         None, None, None, None)

    client.send_message("/live/clip_slot/delete_clip", (track_id, 0))
    client.send_message("/live/clip_slot/delete_clip", (track_id, 1))

#--------------------------------------------------------------------------------
# Test track properties - devices
#--------------------------------------------------------------------------------

def test_track_devices(client):
    track_id = 0
    assert client.query("/live/track/get/num_devices", (track_id,)) == (track_id, 0,)

#--------------------------------------------------------------------------------
# Test track properties - listeners
#--------------------------------------------------------------------------------

def test_track_listen_playing_slot_index(client):
    # 1/16th quantize
    client.send_message("/live/song/set/clip_trigger_quantization", (11,))
    for track_id, clip_id in itertools.product((0, 1), (0, 1)):
        client.send_message("/live/clip_slot/create_clip", (track_id, clip_id, 4))

    client.send_message("/live/track/start_listen/playing_slot_index", (0,))
    assert client.await_message("/live/track/get/playing_slot_index", TICK_DURATION * 2) == (0, -1,)
    client.send_message("/live/track/start_listen/playing_slot_index", (1,))
    assert client.await_message("/live/track/get/playing_slot_index", TICK_DURATION * 2) == (1, -1,)

    client.send_message("/live/clip_slot/fire", (0, 0))
    assert client.await_message("/live/track/get/playing_slot_index", TICK_DURATION * 2) == (0, 0,)

    client.send_message("/live/clip_slot/fire", (0, 1))
    assert client.await_message("/live/track/get/playing_slot_index", TICK_DURATION * 2) == (0, 1,)

    client.send_message("/live/clip_slot/fire", (1, 1))
    assert client.await_message("/live/track/get/playing_slot_index", TICK_DURATION * 2) == (1, 1,)

    client.send_message("/live/clip_slot/fire", (1, 0))
    assert client.await_message("/live/track/get/playing_slot_index", TICK_DURATION * 2) == (1, 0,)

    client.send_message("/live/track/stop_listen/playing_slot_index", (0,))
    client.send_message("/live/track/stop_listen/playing_slot_index", (1,))

    for track_id, clip_id in itertools.product((0, 1), (0, 1)):
        client.send_message("/live/clip_slot/delete_clip", (track_id, clip_id))
