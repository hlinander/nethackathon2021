import { createRoot } from "react-dom/client";
import React from "react";
import "normalize.css/normalize.css";
import { Terminal } from "xterm";
import "xterm/css/xterm.css";
import { makeAutoObservable } from "mobx";
import { observer } from "mobx-react";
import nethacklogo from "./NetHack-Logo.svg"
import leaderboardbg from "./stonkathon.jpg"
import { formatDistanceToNow } from 'date-fns'
import Objectives from "./objectives";

class GameState {
  term: Terminal | null = null
  name: String | null = null
  showObjectives: boolean = false
  backendOffline: boolean = false
  autoScroll: boolean = true

  constructor() {
    makeAutoObservable(this);
  }

  newGame(name) {
    this.term = new Terminal({
      fontSize: 12,
      cursorBlink: true,
      macOptionIsMeta: true,
      allowTransparency: true,
      scrollOnUserInput: false,
      cols: 80,
      rows: 40,
    });
    this.name = name;
  }

  setShowObjectives(show: boolean) { 
    this.showObjectives = show
  }

  setBackendOffline(offline: boolean) {
    this.backendOffline = offline
  }

  setAutoscroll(autoscroll: boolean) {
    this.autoScroll = autoscroll
  }
}

const gameState = new GameState();

const Game = observer(({ state }) => {
  let dialogRef = React.useRef<HTMLInputElement>(null)
  React.useEffect(() => {
    dialogRef.current?.focus()
  }, [])
  return (<div style={{ gridArea: "game", overflow: "hidden" }}> {state.term !== null ? (
    <GameView state={state} />
  ) : (
    <div style={{
        display: 'flex',
      alignItems: 'center',
    width: '100%',
    height: '100%',
      }}>
      <dialog open>
        <img src={nethacklogo} />
        <p>What is your name, adventurer?</p>
        <input ref={dialogRef} autoComplete="text" onKeyPress={(event) => {
          if (event.key === "Enter") {
            state.newGame(event.target.value)
          }
        }} />
      </dialog>
    </div>
  )}
  </div>);
}
);

const GameView = observer(({ state }) => {
  return (
    <div style={{
      width: "100%", 
      display: "flex", 
      alignItems:"center", 
      justifyContent: "flex-end"
    }}>
    <div ref={(el) => {
      if (el != null) {
        state.term.open(el)
        state.term.focus()
        let socket = new WebSocket("ws://nh.hampe.nu:8484/ws");
        socket.onopen = function(e) {
          console.log("[open] Connection established");

          state.term.onData(data => {
            socket.send(JSON.stringify({ type: "data", data: btoa(data) }));
          });

          state.term.onResize((evt) => {
            socket.send(JSON.stringify({ type: "resize", cols: evt.cols, rows: evt.rows }))
          });
          socket.send(JSON.stringify({ type: "hello", name: state.name }));

        };

        socket.onmessage = function(event) {
          console.log(`[message] Data received from server`, event);
          let msg = JSON.parse(event.data)

          switch (msg.type) {
            case "data":
              let u8data = new Uint8Array(Array.from(atob(msg.data), c => c.charCodeAt(0)));
              state.term.write(u8data)
              break;
            default:
              console.log("unknown message", msg)
          }
        };

        socket.onclose = function(event) {
          if (event.wasClean) {
            console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
          } else {
            console.log('[close] Connection died');
          }
        };

        socket.onerror = function(error) {
          console.log(`[error]`);
        };

      }
    }}></div></div>
  )
})


function LeaderBoard() {
  const [state, setState] = React.useState({ Clans: [], Players: [] });

  React.useEffect(() => {
    setInterval(() => {
      fetch("http://nh.hampe.nu:8484/poll")
        .then((response) => response.json())
        .then((data) => {
          gameState.setBackendOffline(false)

          setState(prev => {

            if (!data && !data.Clans) {
              return prev;
            }

            data.Clans.forEach(c => {
              const oldClan = prev.Clans.find(cOld => cOld.ID === c.ID)
              if (oldClan) {
                c.Changed = oldClan.Power_gems !== c.Power_gems;
              } else {
                c.Changed = false;
              }
            })

            return data;
          });
        }).catch(e => {
          gameState.setBackendOffline(true)
        });
    }, 2000);
  }, []);

  return (
    <div style={{
      position: 'relative',
      display: "flex",
      alignItems: "center"
    }}>
      <div
        style={{
          position: "absolute",
          backgroundImage: 'url(' + leaderboardbg + ')',
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          backgroundRepeat: "no-repeat",
          backgroundSize: "cover",
          borderRadius: "8px 0 0 0",
          gridArea: "leaderboard",
          width: "100%",
          height: "100%",
          overflow: "hidden",
          opacity: "0.5"
        }}
      />
      <div style={{ position: 'relative', zIndex: 1, flex: "1 0 100%"}}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gap: "0px 0px",
          marginRight: "8px",
          gridAutoFlow: "row",
          textAlign: "left",
          marginLeft: "15px"

        }}>
          <div style={{ opacity: 0.7, gridColumn: 1, marginRight: "1px", color: "white", fontFamily: "cursive", fontSize: "20px" }}>Clan</div>
          <span style={{ opacity: 0.7, gridColumn: 2, marginRight: "1em", color: "white", fontFamily: "cursive", fontSize: "20px" }}>Reward</span>
          <span style={{ opacity: 0.7, gridColumn: 3, marginBottom: "1px", fontFamily: "cursive", color: "white", fontSize: "20px" }}>Power gems</span>
          {state.Clans.map((c) => {
            let style = {
              color: c.Power_gems > 0 ? "#05b605" : "red",
              textShadow: "-1px 1px 0px #000000, -2px 2px 0px #000000, -3px 3px 0px #000000",
              fontFamily: "cursive",
              fontWeight: "bolder",
              fontSize: "20px",
              animationDuration: "0.5s",
              animationName: c.Changed ? "tilt-shaking" : "unset",
            }
            return (
              <React.Fragment key={c.Name}>
                <div className={"text"} style={{ gridColumn: 1, marginRight: "0px" }}>{c.Name}</div>
                <span className={"rewards"} style={{ gridColumn: 2, marginRight: "1em", color: "#0F0", ...style }}>{state.ClanRewards?.filter(cr => cr.Name == c.Name).map(cr => cr.Reward)}</span>
                <span className={"gems"} style={{ gridColumn: 3, ...style }}>${c.Power_gems > 0 ? "+" : ""}{c.Power_gems}</span>
              </React.Fragment>
            )
          })}
        </div>
      </div>
    </div>
  );
}

function RenderEvent({event}) {
  let elapsed = formatDistanceToNow(new Date(event.Timestamp), { addSuffix: true });
  let elapsedEl = <span style={{fontSize: "8px", opacity: 0.5}}>{elapsed}</span>
  let pn = <b>{event.Playername}</b>
  let cn = <b>{event.Clanname}</b>
  let event_data = event.Vinst
  switch (event_data.type) {
    case "event":
      switch (event_data.name) {
        case "payout_stonk":
          return <div style={{ color: "pink" }}>💰{cn} profited {event_data.extra.roi} gems from a {event_data.extra.is_long ? "long" : "short"} in {event.Stonk_boi}</div>
        case "buy_stonk":
          return <div style={{ color: "pink" }}>{pn} is {event_data.extra.buy_long ? "long" : "short"} in {event.Stonk_boi} betting {event_data.extra.spent_gems} gems</div>
        case "death":
          return <div style={{ color: "red" }}>{pn} died on turn {event_data.turn}</div>
        case "reach_depth":
          return <div><b>{event_data.Playername}</b>{pn} reached dungeon level {event_data.value}</div>
        case "change_stat":
          if (event_data.string_value == "hp") {
            return <div>{pn} entered the dungeon of doom. {elapsedEl}</div>
          }
      }
    case "reward":
      return <div style={{color: "gold"}}>{pn} was rewarded {event_data.score} for "{event_data.literal}"</div>
  }
  return <div><b>{event_data.playername}</b> did something</div>
}

const Events = observer(() => {
  const [state, setState] = React.useState([]);

  React.useEffect(() => {
    setInterval(() => {
      fetch("http://nh.hampe.nu:8484/events")
        .then((response) => response.json())
        .then((data) => {
          setState(prev => {
            return data;
          })
        }).catch(e => {
          console.log("error:", e) 
        })
    }, 1000)
  }, [])

  return (
    <div 
     style={{ 
      gridArea: "events", 
      position: "relative",
      minHeight: 0,
    }}>
      {
        !gameState.autoScroll &&
       <button 
          style={{ position: "absolute", bottom: 0, right: 0 }}
          onClick={e => { gameState.setAutoscroll(true) }}>
          resume auto scroll
       </button>
      }
    <div 
      style={{
        overflowY: "scroll",
        minHeight: 0,
        height: "100%"
      }}
      onScroll={e => {
        const { scrollHeight, scrollTop, clientHeight } = e.target as Element;
        const atBottom = Math.ceil(scrollHeight - scrollTop) === clientHeight;
        gameState.setAutoscroll(atBottom)
      }}
    >
      <div
        style={{
          display: "flex",
          flexDirection: "column-reverse",
          fontFamily: "monospace",
          margin: "8px",
          minWidth: 0,          
          minHeight: 0,
        }}
      >
        {
          state.map((event, i) =>
            <div className="fade-in"
              ref={el => {
                if (el !== null && i === 0 && gameState.autoScroll) {
                  el.scrollIntoView({ behavior: "smooth" })
                }
              }}
              style={{
                minWidth: 0,
                width: "100%",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap"
              }} key={event.Timestamp}>
              <RenderEvent event={event} />
            </div>)
        }
      </div>
    </div>
    </div>)
})

const App = observer(() => {
  return (
    <div style={{
      width: "100vw", 
      height: "100vh",
      display: "grid",
      gridTemplateColumns: "1.8fr 1fr",
      gridTemplateRows: "1fr 1fr",
      gap: "0px 0px",
      gridAutoFlow: "row",
      gridTemplateAreas: `'game events' 'game leaderboard'`
    }}>
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          margin: "4px",
          cursor: "pointer",
          userSelect: "none"
        }}
        onClick={() => {
          gameState.setShowObjectives(!gameState.showObjectives)
        }}
      >
        🏆
      </div>
      {gameState.showObjectives && <Objectives state={gameState}/>}
      {gameState.backendOffline && 
      <h1 
        style={{
          color: "red",
          outline: "4px solid red",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          textAlign: "center",
          minHeight: "100vh"
        }}>
        backend offline
      </h1>
      }
      <Events />
      <Game state={gameState} />
      <LeaderBoard />
    </div>);
})

const container = document.getElementById("app");
const root = createRoot(container)
root.render(<App />);
