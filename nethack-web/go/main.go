// Copyright 2015 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package main

import (
	"bytes"
	"flag"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"time"

	"github.com/creack/pty"
	"github.com/gorilla/websocket"
)

var (
	addr    = flag.String("addr", "127.0.0.1:8080", "http service address")
	cmdPath string
)

const (
	// Time allowed to write a message to the peer.
	writeWait = 10 * time.Second

	// Maximum message size allowed from peer.
	maxMessageSize = 8192

	// Time allowed to read the next pong message from the peer.
	pongWait = 60 * time.Second

	// Send pings to peer with this period. Must be less than pongWait.
	pingPeriod = (pongWait * 9) / 10

	// Time to wait before force close on connection.
	closeGracePeriod = 10 * time.Second
)

func pumpStdin(ws *websocket.Conn, w *os.File) {
	defer ws.Close()
	ws.SetReadLimit(maxMessageSize)
	ws.SetReadDeadline(time.Now().Add(pongWait))

	ws.SetPongHandler(func(string) error { ws.SetReadDeadline(time.Now().Add(pongWait)); return nil })

	for {
		_, message, err := ws.ReadMessage()
		if err != nil {
			break
		}
		if _, err := w.Write(message); err != nil {
			break
		}
	}
}

func NormalizeNewlines(d []byte) []byte {
	// replace CR LF \r\n (windows) with LF \n (unix)
	d = bytes.Replace(d, []byte{13, 10}, []byte{10}, -1)
	// replace CF \r (mac) with LF \n (unix)
	d = bytes.Replace(d, []byte{13}, []byte{10}, -1)
	return d
}

func pumpStdout(ws *websocket.Conn, r io.Reader, done chan struct{}) {
	buf := make([]byte, 1024)
	for {
		n, err := r.Read(buf)
		if err != nil {
			close(done)
			log.Fatal(err)
		}
		// ws.SetWriteDeadline(time.Now().Add(writeWait))
		if err := ws.WriteMessage(websocket.BinaryMessage, NormalizeNewlines(buf[:n])); err != nil {
			ws.Close()
			break
		}

		log.Printf("wrote %d bytes", n)
	}
	// ws.SetWriteDeadline(time.Now().Add(writeWait))
	// ws.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
	// time.Sleep(closeGracePeriod)
	// ws.Close()
}

func ping(ws *websocket.Conn, done chan struct{}) {
	ticker := time.NewTicker(pingPeriod)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			if err := ws.WriteControl(websocket.PingMessage, []byte{}, time.Now().Add(writeWait)); err != nil {
				log.Println("ping:", err)
			}
		case <-done:
			return
		}
	}
}

func internalError(ws *websocket.Conn, msg string, err error) {
	log.Println(msg, err)
	ws.WriteMessage(websocket.TextMessage, []byte("Internal server error."))
}

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

func serveWs(w http.ResponseWriter, r *http.Request) {
	ws, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Println("upgrade:", err)
		return
	}

	defer ws.Close()

	c := exec.Command("bash")

	// Start the command with a pty.
	ptmx, err := pty.Start(c)
	if err != nil {
		panic(err)
	}

	// Make sure to close the pty at the end.
	defer func() { _ = ptmx.Close() }() // Best effort.

	// // Handle pty size.
	// ch := make(chan os.Signal, 1)
	// signal.Notify(ch, syscall.SIGWINCH)
	// go func() {
	// 	for range ch {
	// 		if err := pty.InheritSize(os.Stdin, ptmx); err != nil {
	// 			log.Printf("error resizing pty: %s", err)
	// 		}
	// 	}
	// }()
	// ch <- syscall.SIGWINCH                        // Initial resize.
	// defer func() { signal.Stop(ch); close(ch) }() // Cleanup signals when done.

	// outr, outw, err := os.Pipe()
	// if err != nil {
	// 	internalError(ws, "stdout:", err)
	// 	return
	// }
	// defer outr.Close()
	// defer outw.Close()

	// inr, inw, err := os.Pipe()
	// if err != nil {
	// 	internalError(ws, "stdin:", err)
	// 	return
	// }
	// defer inr.Close()
	// defer inw.Close()

	// proc, err := os.StartProcess(cmdPath, flag.Args(), &os.ProcAttr{
	// 	Files: []*os.File{inr, outw, outw},
	// })
	// if err != nil {
	// 	internalError(ws, "start:", err)
	// 	return
	// }

	// inr.Close()
	// outw.Close()

	stdoutDone := make(chan struct{})
	go pumpStdout(ws, ptmx, stdoutDone)
	go ping(ws, stdoutDone)

	pumpStdin(ws, ptmx)

	// Some commands will exit when stdin is closed.
	// inw.Close()

	// Other commands need a bonk on the head.
	// if err := proc.Signal(os.Interrupt); err != nil {
	// 	log.Println("inter:", err)
	// }

	// select {
	// case <-stdoutDone:
	// case <-time.After(time.Second):
	// 	// A bigger bonk on the head.
	// 	if err := proc.Signal(os.Kill); err != nil {
	// 		log.Println("term:", err)
	// 	}
	// 	<-stdoutDone
	// }

	// if _, err := proc.Wait(); err != nil {
	// 	log.Println("wait:", err)
	// }
}

func serveHome(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path != "/" {
		http.Error(w, "Not found", http.StatusNotFound)
		return
	}
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	http.ServeFile(w, r, "home.html")
}

func main() {
	flag.Parse()
	if len(flag.Args()) < 1 {
		log.Fatal("must specify at least one argument")
	}
	var err error
	cmdPath, err = exec.LookPath(flag.Args()[0])
	if err != nil {
		log.Fatal(err)
	}
	http.HandleFunc("/", serveHome)
	http.HandleFunc("/ws", serveWs)
	log.Fatal(http.ListenAndServe(*addr, nil))
}
