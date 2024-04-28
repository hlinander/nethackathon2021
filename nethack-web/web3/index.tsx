import { useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { Terminal } from "xterm";
import "xterm/css/xterm.css";
import "normalize.css/normalize.css";
import { makeAutoObservable } from "mobx";
import { observer } from "mobx-react-lite";

class TerminalManager {
  terminals = {};
  receivedBytes = {};

  constructor() {
    makeAutoObservable(this);
  }

  initializeTerminal(playerName) {
    const terminal = new Terminal({
      fontSize: 12,
      cursorBlink: true,
      macOptionIsMeta: true,
      allowTransparency: true,
      scrollOnUserInput: false,
      cols: 80,
      rows: 40,
    });
    this.terminals[playerName] = terminal;
    this.receivedBytes[playerName] = 0;
  }

  updateTerminalData(playerName, data) {
    if (!this.terminals[playerName]) {
      console.log('New player', playerName)
      this.initializeTerminal(playerName);
    }
    this.terminals[playerName].write(data);
    this.receivedBytes[playerName] += data.length;
  }
}

class DisplayState {
  displayOffset = 0;

  constructor() {
    makeAutoObservable(this);
  }

  updateDisplayOffset(totalTerminals) {
    this.displayOffset = (this.displayOffset + 4);
    if (this.displayOffset >= totalTerminals) {
      this.displayOffset = 0
    }
  }
}

class SongState {
  playername = null
  title = null
  text = null
  mp3 = null
  image = null

  constructor() {
    makeAutoObservable(this)
  }

  updateState(_playername, _title, _text, _song, _image) {
    playername = _playername
    title = _title
    text = _text
    mp3 = _song
    image = _image    
  }
}

const terminalManager = new TerminalManager();
const displayState = new DisplayState();
const songState = new SongState();

const SpectateComponent = observer(() => {
  const audioRef = useRef(null);

  useEffect(() => {
    if (songState.mp3 && !audioRef.current) {
      audioRef.current = new Audio(songState.mp3);
      audioRef.current.play();

      // Event listener for when the audio ends
      audioRef.current.onended = () => {
        setTimeout(() => {
          // Update the song state to revert back to the default view
          // Assuming there's a method in songState to reset or change the state
          songState.updateState(null, null, null, null, null, null);
          audioRef.current = null
        }, 2000); // wait for 1 second before switching
      };
    }

    // Cleanup function to remove the event listener
    return () => {
      if (audioRef.current) {
        audioRef.current.onended = null;
      }
    };
  }, [songState.mp3]);

  useEffect(() => {
    const fetchData = async () => {
      const updateInterval = 250;
      const updateId = setInterval(async () => {
        const response = await fetch("/spectate", {
          method: "POST",
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(terminalManager.receivedBytes)
        });
        const data = await response.json();
        Object.entries(data).forEach(([playerName, ttyDelta]) => {
          terminalManager.updateTerminalData(playerName, new Uint8Array(Array.from(atob(ttyDelta), c => c.charCodeAt(0))));
        });
      }, updateInterval);
    };

    const displayId = setInterval(async () => {
      displayState.updateDisplayOffset(Object.keys(terminalManager.terminals).length)
    }, 120000);

    const songId = setInterval(async () => {
      const events = await (await fetch('/events')).json();
      for(let event of events) {
        e = event.Vinst
        if ("event" == e.type && "coconut_song" == e.name) {
          const { extra } = e
          songState.updateState(extra.player_name, extra.song_title, extra.song_lyrics, extra.song_url, null)
        }
      }
    }, 500)

    fetchData();

    return () => {
      clearInterval(updateId)
      clearInterval(displayId) 
      clearInterval(songId)
    }
  }, []);


  return (
    <div>
      {!songState.mp3 ? (
        <div>
          <h3>Nethack Spectate</h3>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gridTemplateRows: "1fr 1fr", height: "100vh" }}>
            {Object.entries(terminalManager.terminals).slice(displayState.displayOffset, displayState.displayOffset+4).map(([key, terminal]) => (
              <div key={key} style={{ padding: "10px" }}>
                <h4>${key}</h4>
                <div ref={el => el && !el.firstChild && terminal.open(el)}></div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", height: "100vh" }}>
          <div style={{ gridRow: "1 / span 2" }}>
            <h4>{songState.playername}</h4>
            <div ref={el => el && songState.playername && terminalManager.terminals[songState.playername] && !el.firstChild && terminalManager.terminals[songState.playername].open(el)}></div>
          </div>
          <div>
            <h1>{songState.title}</h1>
            <p>{songState.text}</p>
          </div>
        </div>
      )}
    </div>
  )
})

const container = document.getElementById("app");
const root = createRoot(container);
root.render(<SpectateComponent />);
