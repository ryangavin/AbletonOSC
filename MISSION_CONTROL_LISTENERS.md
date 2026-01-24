# Mission Control: AbletonOSC Listener Extensions

> **Purpose**: Add listeners for tracks, scenes, and sends to support event-driven sync
> **Target**: Upstream contribution to `ideoforms/AbletonOSC`

---

## Background

Mission Control needs event-driven updates for:
1. **Track/scene count changes** - currently polled every 1000ms
2. **Send value changes** - currently polled every 500ms

The Live Python API supports these listeners, but AbletonOSC doesn't expose them yet.

---

## Live API References

Confirmed to exist in Live's Python API:
- `song.add_tracks_listener(callback)` / `song.remove_tracks_listener(callback)`
- `song.add_scenes_listener(callback)` / `song.remove_scenes_listener(callback)`
- `mixer_device.sends[i].add_value_listener(callback)` / `remove_value_listener(callback)`

Reference: [Tranzport.py in ableton-live9-remote-scripts](https://github.com/phs/ableton-live9-remote-scripts/blob/master/Tranzport/Tranzport.py) shows `self.song().add_tracks_listener(self.__on_tracks_changed)`.

---

## Changes Required

### 1. Song: Tracks/Scenes Listeners

**File**: `abletonosc/song.py`

**Location**: After line 95 (after the existing property handlers loop)

**New OSC Endpoints**:
| Endpoint | Description |
|----------|-------------|
| `/live/song/start_listen/tracks` | Subscribe to track list changes |
| `/live/song/stop_listen/tracks` | Unsubscribe from track changes |
| `/live/song/start_listen/scenes` | Subscribe to scene list changes |
| `/live/song/stop_listen/scenes` | Unsubscribe from scene changes |

**Response Address** (follows AbletonOSC convention):
- `/live/song/get/tracks` → `[num_tracks]` - sent when track list changes
- `/live/song/get/scenes` → `[num_scenes]` - sent when scene list changes

**Implementation**:

```python
#--------------------------------------------------------------------------------
# Callbacks for Song: list properties that change on add/remove/reorder
# These are special because they're list properties, not simple values
#--------------------------------------------------------------------------------
def start_listen_tracks(params):
    def tracks_changed():
        """Called when tracks are added, removed, or reordered."""
        self.osc_server.send("/live/song/get/tracks", len(self.song.tracks))

    listener_key = ('tracks', ())
    if listener_key in self.listener_functions:
        stop_listen_tracks(params)

    self.logger.info("Adding tracks listener")
    self.song.add_tracks_listener(tracks_changed)
    self.listener_functions[listener_key] = tracks_changed
    # Send initial value
    tracks_changed()

def stop_listen_tracks(params):
    listener_key = ('tracks', ())
    if listener_key in self.listener_functions:
        self.logger.info("Removing tracks listener")
        try:
            self.song.remove_tracks_listener(self.listener_functions[listener_key])
            del self.listener_functions[listener_key]
        except Exception as e:
            self.logger.warning("Exception removing tracks listener: %s" % e)

def start_listen_scenes(params):
    def scenes_changed():
        """Called when scenes are added, removed, or reordered."""
        self.osc_server.send("/live/song/get/scenes", len(self.song.scenes))

    listener_key = ('scenes', ())
    if listener_key in self.listener_functions:
        stop_listen_scenes(params)

    self.logger.info("Adding scenes listener")
    self.song.add_scenes_listener(scenes_changed)
    self.listener_functions[listener_key] = scenes_changed
    scenes_changed()

def stop_listen_scenes(params):
    listener_key = ('scenes', ())
    if listener_key in self.listener_functions:
        self.logger.info("Removing scenes listener")
        try:
            self.song.remove_scenes_listener(self.listener_functions[listener_key])
            del self.listener_functions[listener_key]
        except Exception as e:
            self.logger.warning("Exception removing scenes listener: %s" % e)

self.osc_server.add_handler("/live/song/start_listen/tracks", start_listen_tracks)
self.osc_server.add_handler("/live/song/stop_listen/tracks", stop_listen_tracks)
self.osc_server.add_handler("/live/song/start_listen/scenes", start_listen_scenes)
self.osc_server.add_handler("/live/song/stop_listen/scenes", stop_listen_scenes)
```

---

### 2. Track: Send Value Listeners

**File**: `abletonosc/track.py`

**Location**: After line 103 (after the existing `get/send` and `set/send` handlers)

**New OSC Endpoints**:
| Endpoint | Args | Description |
|----------|------|-------------|
| `/live/track/start_listen/send` | `[track_id, send_id]` | Subscribe to send value changes |
| `/live/track/stop_listen/send` | `[track_id, send_id]` | Unsubscribe from send changes |

**Response Address**:
- `/live/track/get/send` → `[track_id, send_id, value]` - sent when send value changes

**Note**: This follows the exact same pattern as volume/panning listeners (see `_start_mixer_listen` at line 244). Sends are accessed via `track.mixer_device.sends[send_id]` which is a `DeviceParameter` with `add_value_listener`/`remove_value_listener`.

**Implementation**:

```python
#--------------------------------------------------------------------------------
# Send value listeners
# Sends are DeviceParameter objects on mixer_device, same as volume/panning
#--------------------------------------------------------------------------------
def track_start_listen_send(track, params):
    track_id = params[0]
    send_id = params[1]

    try:
        send_param = track.mixer_device.sends[send_id]
    except IndexError:
        self.logger.warning("Invalid send_id %d for track %d" % (send_id, track_id))
        return

    def send_changed():
        self.osc_server.send("/live/track/get/send", track_id, send_id, send_param.value)

    listener_key = ('send', track_id, send_id)
    if listener_key in self.listener_functions:
        track_stop_listen_send(track, params)

    self.logger.info("Adding send listener for track %d send %d" % (track_id, send_id))
    send_param.add_value_listener(send_changed)
    self.listener_functions[listener_key] = send_changed
    # Send initial value
    send_changed()

def track_stop_listen_send(track, params):
    track_id = params[0]
    send_id = params[1]

    try:
        send_param = track.mixer_device.sends[send_id]
    except IndexError:
        return

    listener_key = ('send', track_id, send_id)
    if listener_key in self.listener_functions:
        self.logger.info("Removing send listener for track %d send %d" % (track_id, send_id))
        try:
            send_param.remove_value_listener(self.listener_functions[listener_key])
            del self.listener_functions[listener_key]
        except Exception as e:
            self.logger.warning("Exception removing send listener: %s" % e)

self.osc_server.add_handler("/live/track/start_listen/send",
    create_track_callback(track_start_listen_send, include_track_id=True))
self.osc_server.add_handler("/live/track/stop_listen/send",
    create_track_callback(track_stop_listen_send, include_track_id=True))
```

---

## Testing

### Manual Testing with run-console.py

```bash
cd /Users/ryan/The\ Source/AbletonOSC
python run-console.py
```

Test commands:
```
# Test tracks listener
/live/song/start_listen/tracks
# Add/delete a track in Ableton, should see /live/song/get/tracks message
/live/song/stop_listen/tracks

# Test scenes listener
/live/song/start_listen/scenes
# Add/delete a scene in Ableton
/live/song/stop_listen/scenes

# Test send listener (track 0, send 0)
/live/track/start_listen/send 0 0
# Adjust send A on track 1 in Ableton
/live/track/stop_listen/send 0 0
```

### Unit Tests

**File**: `tests/test_song.py`

```python
def test_song_tracks_listener(client):
    """Test tracks listener fires on track add/delete."""
    # Start listener
    client.send_message("/live/song/start_listen/tracks")
    initial_count = client.receive_message()  # Should get initial track count

    # Add track
    client.send_message("/live/song/create_midi_track", [-1])
    wait_one_tick()

    response = client.receive_message()
    assert response[0] == "/live/song/get/tracks"
    assert response[1][0] == initial_count[1][0] + 1

    # Cleanup
    client.send_message("/live/song/delete_track", [initial_count[1][0]])
    client.send_message("/live/song/stop_listen/tracks")

def test_song_scenes_listener(client):
    """Test scenes listener fires on scene add/delete."""
    client.send_message("/live/song/start_listen/scenes")
    initial = client.receive_message()

    client.send_message("/live/song/create_scene", [-1])
    wait_one_tick()

    response = client.receive_message()
    assert response[0] == "/live/song/get/scenes"
    assert response[1][0] == initial[1][0] + 1

    client.send_message("/live/song/delete_scene", [initial[1][0]])
    client.send_message("/live/song/stop_listen/scenes")
```

**File**: `tests/test_track.py`

```python
def test_track_send_listener(client):
    """Test send listener fires on send value change."""
    track_id = 0
    send_id = 0

    # Start listener
    client.send_message("/live/track/start_listen/send", [track_id, send_id])
    initial = client.receive_message()  # Initial value

    assert initial[0] == "/live/track/get/send"
    assert initial[1][0] == track_id
    assert initial[1][1] == send_id

    # Change value
    new_value = 0.75
    client.send_message("/live/track/set/send", [track_id, send_id, new_value])
    wait_one_tick()

    response = client.receive_message()
    assert response[0] == "/live/track/get/send"
    assert abs(response[1][2] - new_value) < 0.01

    # Cleanup
    client.send_message("/live/track/stop_listen/send", [track_id, send_id])
```

---

## Integration with Mission Control

After changes are tested:

1. Copy modified files to bundled version:
   ```bash
   cp abletonosc/song.py ../mission-control/desktop/resources/AbletonOSC/abletonosc/
   cp abletonosc/track.py ../mission-control/desktop/resources/AbletonOSC/abletonosc/
   ```

2. Update Mission Control's protocol layer (`/protocol/messages.ts`)

3. Update bridge to handle new listener events

---

## Upstream Contribution

When ready to contribute back:

```bash
git checkout -b feature/structure-send-listeners
git add abletonosc/song.py abletonosc/track.py tests/
git commit -m "Add tracks, scenes, and send value listeners"
git push origin feature/structure-send-listeners
# Create PR to ideoforms/AbletonOSC
```

**PR Description Template**:
```
## Summary
Adds listeners for track/scene list changes and send values.

## New Endpoints
- `/live/song/start_listen/tracks` / `stop_listen/tracks`
- `/live/song/start_listen/scenes` / `stop_listen/scenes`
- `/live/track/start_listen/send` / `stop_listen/send`

## Use Case
Enables event-driven sync for applications that need to detect:
- Track/scene additions, deletions, and reordering
- Send value changes in real-time (without polling)

## Implementation
Uses Live API's existing `add_tracks_listener`, `add_scenes_listener`,
and `DeviceParameter.add_value_listener` methods.
```
