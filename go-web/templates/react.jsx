"use strict";

function MyApp() {
  const [state, setState] = React.useState({ Clans: [], Players: [] });

  React.useEffect(() => {
    setInterval(() => {
      fetch("/poll")
        .then((response) => response.json())
        .then((data) => {
          setState(prev => {

            if(!data && !data.Clans) {
              return prev;
            }
      
            console.log("new", data);
            console.log("prev", prev);
            data.Clans.forEach(c => { 
              const oldClan = prev.Clans.find(cOld => cOld.ID === c.ID)
              if(oldClan) {
                c.Changed = oldClan.Power_gems !== c.Power_gems; 
              } else {
                c.Changed = false;
              }

              console.log(c.Changed);

            })

            return data;
          });
        });
    }, 2000);
  }, []);

  return (
    <div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        backgroundImage: `url("static/stonkathon.jpg")`,
        backgroundRepeat: "no-repeat",
        backgroundSize: "cover",
        alignItems: "center",
        justifyContent: "space-evenly"
      }}
    >
      {state.Clans.map((c) => (
        <div key={c.Name} style={{ display: "flex", alignItems: "baseline" }}>
          <div className={"text"} style={{ marginRight: "30px" }}>{c.Name}</div>
          <div style={{
              color: c.Power_gems > 0 ? "#05b605" : "red",
              textShadow: "-5px 5px 0px #000000, -10px 10px 0px #000000, -15px 15px 0px #000000",
              fontFamily: "cursive",
              fontWeight: "bolder",
              fontSize: "130px",
              animationDuration: "0.5s",
              animationName: c.Changed ? "tilt-shaking" : "unset",
          }}>{c.Power_gems > 0 ? "+" : ""}{c.Power_gems}</div> 
        </div>
      ))}
    </div>
  );
}

const domContainer = document.querySelector("#root");
const root = ReactDOM.createRoot(domContainer);
root.render(<MyApp />);
