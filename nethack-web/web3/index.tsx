import { useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { Terminal } from "xterm";
import "xterm/css/xterm.css";
import "normalize.css/normalize.css";
import { makeAutoObservable } from "mobx";
import { observer } from "mobx-react-lite";

class TerminalManager {
  terminal = null;
  receivedBytes = 0;

  constructor() {
    makeAutoObservable(this);
    this.initializeTerminal();
  }

  initializeTerminal() {
    this.terminal = new Terminal({
      fontSize: 18,
      cursorBlink: true,
      macOptionIsMeta: true,
      allowTransparency: true,
      cols: 512,
      rows: 512,
    });
  }

  updateTerminalData(data) {
    if (this.terminal) {
      this.terminal.write(data);
      this.receivedBytes += data.length;
    }
  }
}

class SongState {
  playername = null;
  title = null;
  text = null;
  mp3 = null;

  constructor() {
    makeAutoObservable(this);
  }

  updateState(_playername, _title, _text, _mp3) {
    this.playername = _playername;
    this.title = _title;
    this.text = _text;
    this.mp3 = _mp3;
  }
}

const terminalManager = new TerminalManager();
const songState = new SongState();
let lastTimestamp = null;

function isNewerEvent(eventTimestamp) {
  return lastTimestamp == null || eventTimestamp > lastTimestamp;
}

const SpectateComponent = observer(() => {
  const audioRef = useRef(null);

  useEffect(() => {
    if (songState.mp3 && !audioRef.current) {
      audioRef.current = new Audio(songState.mp3);
      const tryPlayAudio = setInterval(async () => {
        try {
          await audioRef.current.play();
          clearInterval(tryPlayAudio);
        } catch (error) {
          console.log('Waiting for user interaction...');
        }
      }, 100);

      audioRef.current.onended = () => {
        setTimeout(() => {
          songState.updateState(null, null, null, null);
          audioRef.current = null;
        }, 2000);
      };
    }

    return () => {
      if (audioRef.current) {
        audioRef.current.onended = null;
      }
    };
  }, [songState.mp3]);

  useEffect(() => {
    const fetchData = async () => {
      const updateInterval = 250;
      setInterval(async () => {
        const response = await fetch("/spectate", {
          method: "POST",
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ receivedBytes: terminalManager.receivedBytes })
        });
        const data = await response.json();
        terminalManager.updateTerminalData(new Uint8Array(Array.from(atob(data.ttyDelta), c => c.charCodeAt(0))));
      }, updateInterval);
    };

    const songId = setInterval(async () => {
      const events = await (await fetch('/events')).json();
      for (let event of events) {
        const ts = new Date(event.Timestamp);
        if (!isNewerEvent(ts)) continue;
        lastTimestamp = ts;
        const e = event.Vinst;
        if (e && e.type === "event" && e.name === "coconut_song") {
          const { playername, song_title, song_lyrics, song_url } = e.extra;
          songState.updateState(playername, song_title, song_lyrics, song_url);
        }
      }
    }, 500);

    fetchData();

    return () => {
      clearInterval(songId);
    };
  }, []);

  return (
    <div style={{ width: "512px", height: "512px" }}>
      <div ref={el => el && !el.firstChild && terminalManager.terminal.open(el)}></div>
    </div>
  )
});

const container = document.getElementById("app");
const root = createRoot(container);
root.render(<SpectateComponent />);
