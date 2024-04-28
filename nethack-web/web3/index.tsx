import { useEffect } from "react";
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
      this.initializeTerminal(playerName);
    }
    this.terminals[playerName].write(data);
    this.receivedBytes[playerName] += data.length;
  }
}

const terminalManager = new TerminalManager();

const SpectateComponent = observer(() => {
  useEffect(() => {
    const fetchData = async () => {
      const updateInterval = 500;
      setInterval(async () => {
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

    fetchData();
  }, []);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gridTemplateRows: "1fr 1fr", height: "100vh" }}>
      {Object.entries(terminalManager.terminals).slice(0, 4).map(([key, terminal]) => (
        <div key={key} style={{ padding: "10px" }}>
          <div ref={el => el && terminal.open(el)}></div>
        </div>
      ))}
    </div>
  );
});

const container = document.getElementById("app");
const root = createRoot(container);
root.render(<SpectateComponent />);
