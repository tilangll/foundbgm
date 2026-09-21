# Memory Tape

Memory Tape turns a photo into a cassette and matches it with music. The interface moves between a bright daytime cassette player and a surreal nighttime jukebox, using insertion video, tape-reading sound, and a `Loading..` animation to make music discovery feel tactile.

## Run locally

Install the repository dependencies, then start the bundled server from the repository root:

```bash
pip install -r requirements.txt
python3 memory-tapes/memory_tape_server.py
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/).

Use `memory_tape_server.py`, rather than `python -m http.server`: the bundled server serves the page and implements the `/api/match` endpoint used by uploaded photos. Music matching requires internet access to search and stream Audius tracks.

## Interaction

- Pull the lamp control to switch between day and night.
- Select one of the four sample cassettes to play its bundled local track.
- Upload or drop an image to create a new cassette and start matching automatically.
- Select the active cassette again to take it out.

## Tests

```bash
python3 memory-tapes/server.test.py
node memory-tapes/page.test.js
```

Music and sound-effect attribution is documented in [`audio/SOURCES.md`](audio/SOURCES.md).
