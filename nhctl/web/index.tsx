import React from 'react';
import ReactDOM from 'react-dom';
import { Graph } from 'react-d3-graph';

const data = {
    nodes: [{ id: 'A' }, { id: 'B' }, { id: 'C' }],
    links: [{ source: 'A', target: 'B' }, { source: 'A', target: 'C' }, { source: 'B', target: 'C' }]
};

interface DagComponentProps {
    Nodes: [{ id: string }]
    Links: [{ src: string, dst: string }]
}

const DagComponent: React.FC<DagComponentProps> = ({ Nodes, Links }) => {
    const myConfig = {
        nodeHighlightBehavior: true,
        directed: true,
        height: 800,
        width: 400,
        d3: {
            alphaTarget: 0.05,
            gravity: -250,
            linkLength: 100,
            linkStrength: 1,
        },
        node: {
            color: 'lightgreen',
            size: 120,
            highlightStrokeColor: 'blue',
        },
        link: {
            highlightColor: 'lightblue',
        },
    };

    return (
        <Graph
            id="dag"
            data={data}
            config={myConfig}
        />
    );
};

let socket: WebSocket | null = null

interface ConsoleMessage {
    Type: "console"
    Data: string
}

interface GraphMessage {
    Type: "graph"
    Nodes: [{ id: string }]
    Links: [{ src: string, dst: string }]
}

function App() {

    const [log, setLog] = React.useState<string>("");
    const [connected, setConnected] = React.useState(false);
    const [started, setStarted] = React.useState(false);

    React.useEffect(() => {
        socket = new WebSocket('ws://localhost:8081/ws')

        socket.addEventListener('open', (event) => {
            setLog("")
            setConnected(true)
        });

        socket.addEventListener('message', (event) => {

            const msg: ConsoleMessage | GraphMessage = JSON.parse(event.data)

            switch(msg.Type) {
                case "console":
                    setLog(prev => prev += msg + "\n")
                    break
                case "graph":
                    
                    break    
            }

            
        });
    }, [])

    return (
        <>
            {!started && <button disabled={!connected} onClick={
                () => {
                    socket!.send(JSON.stringify({ type: 'start' }))
                    setStarted(true)
                }
            }>Start</button>}
            {started && <div style={{ display: "flex", flexDirection: "row" }}>
                <div>
                    <DagComponent />
                </div>
                <div>
                    <pre>{log}</pre>
                </div>
            </div>}
        </>
    );
}

ReactDOM.render(<App />, document.getElementById('root'));