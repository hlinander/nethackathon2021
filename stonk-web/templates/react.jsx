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
        // display: "flex",
        // flexDirection: "column",
        backgroundImage: `url("static/stonkathon.jpg")`,
        backgroundRepeat: "no-repeat",
        backgroundSize: "cover",
        // alignItems: "center",
        // justifyContent: "space-evenly"
      }}
    >
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr 1fr",
        gap: "0px 0px",
        gridAutoFlow: "row",
        padding: "10%",
        textAlign: "right"
    
  }}>
        
      <div style={{ opacity:  0.5, gridColumn: 1, marginRight: "30px", color: "black", fontFamily: "cursive", fontSize: "100px" }}>Clan</div>
      <span style={{ opacity: 0.5, gridColumn: 2, marginRight: "1em", color: "black", fontFamily: "cursive", fontSize: "100px"}}>Reward</span>
      <span style={{ opacity: 0.5, gridColumn: 3, marginBottom: "100px", fontFamily: "cursive", color: "black", fontSize: "100px"}}>Power gems</span>
      {state.Clans.map((c) => {
        let style = {
              color: c.Power_gems > 0 ? "#05b605" : "red",
              textShadow: "-5px 5px 0px #000000, -10px 10px 0px #000000, -15px 15px 0px #000000",
              fontFamily: "cursive",
              fontWeight: "bolder",
              fontSize: "130px",
              animationDuration: "0.5s",
              animationName: c.Changed ? "tilt-shaking" : "unset",
          }
        return (
          <React.Fragment>
          <div className={"text"} style={{ gridColumn: 1, marginRight: "30px" }}>{c.Name}</div>
          <span className={"rewards"} style={{ gridColumn: 2, marginRight: "1em", color: "#0F0", ...style}}>{ state.ClanRewards.filter(cr => cr.Name == c.Name).map(cr => cr.Reward) }</span>
          <span className={"gems"} style={{gridColumn: 3, ...style}}>${c.Power_gems > 0 ? "+" : ""}{c.Power_gems}</span>
          </React.Fragment> 
      )})}
    </div>
    </div>
  );
}

const domContainer = document.querySelector("#root");
const root = ReactDOM.createRoot(domContainer);
root.render(<MyApp />);
