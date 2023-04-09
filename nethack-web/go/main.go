// Copyright 2015 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"sync"
	"time"

	"github.com/creack/pty"
	"github.com/go-playground/validator/v10"
	"github.com/gorilla/websocket"
	"github.com/jackc/pgx/v5"
)

type ResizeMsg struct {
	Type string `json:"type" validate:"required,eq=resize"`
	Cols *int   `json:"cols" validate:"required"`
	Rows *int   `json:"rows" validate:"required"`
}

type DataMsg struct {
	Type string `json:"type" validate:"required,eq=data"`
	Data string `json:"data" validate:"required,base64"`
}

type HelloMsg struct {
	Type string `json:"type" validate:"required,eq=hello"`
	Name string `json:"name" validate:"required"`
}

type Players struct {
	Type    string   `json:"type" validate:"required,eq=players"`
	Players []string `json:"type" validate:"required"`
}

var (
	addr = flag.String("addr", ":8484", "http service address")
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

	defaultPtyRows = 35
	defaultPtyCols = 80
)

func readPump(ctx context.Context, ws *websocket.Conn, s *Session) {
	_, cancel := context.WithCancel(ctx)
	defer func() { cancel() }()

	defer ws.Close()

	ws.SetReadLimit(maxMessageSize)
	ws.SetReadDeadline(time.Now().Add(pongWait))
	ws.SetPongHandler(func(string) error {
		ws.SetReadDeadline(time.Now().Add(pongWait))
		return nil
	})

read_msg_loop:
	for {
		_, message, err := ws.ReadMessage()
		if err != nil {
			log.Printf("failed to read websocket message: %s", err)
			cancel()
			return
		}

		msgKeys := map[string]any{}
		err = json.Unmarshal(message, &msgKeys)
		if err != nil {
			log.Printf("ignoring unknown message with invalid json: %s", message)
			continue
		}

		typeVal, exists := msgKeys["type"]
		if !exists {
			log.Printf("ignoring message with no type: %s", message)
			continue
		}

		switch typeVal {
		case "resize":
			if s.PtyPipe == nil {
				log.Printf("got a resize message before starting. ignoring.")
				break read_msg_loop
			}

			var msg ResizeMsg
			err = json.Unmarshal(message, &msg)
			if err != nil {
				log.Printf("failed to unmarshal message from web: %s", err)
				break read_msg_loop
			}

			validate := validator.New()
			err := validate.Struct(msg)
			if err != nil {
				log.Printf("failed to validate message: %s", err)
				break read_msg_loop
			}

			err = pty.Setsize(
				s.PtyPipe,
				&pty.Winsize{
					Rows: uint16(*msg.Rows),
					Cols: uint16(*msg.Cols),
				})
			if err != nil {
				log.Printf("failed to set pty size: %s", err)
				break read_msg_loop
			}

		case "data":
			if s.PtyPipe == nil {
				log.Printf("got a data message before starting. ignoring.")
				break read_msg_loop
			}
			var msg DataMsg
			err = json.Unmarshal(message, &msg)
			if err != nil {
				log.Printf("failed to unmarshal message from web: %s", err)
				break read_msg_loop
			}

			validate := validator.New()
			err := validate.Struct(msg)
			if err != nil {
				log.Printf("failed to validate message: %s", err)
				break read_msg_loop
			}

			decoded, err := base64.StdEncoding.DecodeString(msg.Data)
			if err != nil {
				log.Printf("failed to decode base64 data in message from web: %s", err)
				break read_msg_loop
			}

			_, err = s.PtyPipe.Write(decoded)
			if err != nil {
				log.Printf("failed to write data to pty: %s", err)
				break read_msg_loop
			}

		case "hello":
			if s.PtyPipe != nil {
				log.Printf("got a hello message after already started. ignoring.")
				break read_msg_loop
			}

			var msg HelloMsg
			err = json.Unmarshal(message, &msg)
			if err != nil {
				log.Printf("failed to unmarshal message from web: %s", err)
				break read_msg_loop
			}

			validate := validator.New()
			err := validate.Struct(msg)
			if err != nil {
				log.Printf("failed to validate message: %s", err)
				break read_msg_loop
			}

			url := "postgres://postgres:vinst@localhost/nh"
			conn, err := pgx.Connect(ctx, url)
			if err != nil {
				log.Printf("unable to connect to postgres db: %s", err)
				break read_msg_loop
			}
			defer conn.Close(ctx)

			var id string
			err = conn.QueryRow(ctx, "SELECT id FROM players WHERE username=$1", msg.Name).Scan(&id)
			if err != nil {
				log.Printf("unable to query player in db")
				break read_msg_loop
			}

			c := exec.Command("/home/eracce/nethackathon2021/build/bin/nethack", "-u", msg.Name)
			c.Env = os.Environ()
			c.Env = append(c.Env, fmt.Sprintf("USER=%s", msg.Name))
			c.Env = append(c.Env, fmt.Sprintf("DB_USER_ID=%s", id))
			s.Name = &msg.Name
			s.PtyPipe, err = pty.StartWithSize(
				c,
				&pty.Winsize{
					Rows: defaultPtyRows,
					Cols: defaultPtyCols,
				})
			if err != nil {
				log.Printf("failed to start %s", err)
				cancel()
			}

		default:
			log.Printf("ignoring message with unknown type: %s", typeVal)
			continue
		}
	}
}

func writePump(ctx context.Context, ws *websocket.Conn, s *Session) {
	_, cancel := context.WithCancel(ctx)
	buf := make([]byte, maxMessageSize)
	for {
		if s.PtyPipe == nil {
			time.Sleep(time.Second)
			continue
		}

		n, err := s.PtyPipe.Read(buf)
		if err != nil {
			log.Printf("failed to read message from pty: %s", err)
			cancel()
			return
		}

		var msg DataMsg = DataMsg{
			Type: "data",
			Data: base64.RawStdEncoding.EncodeToString(buf[:n]),
		}

		msgJson, err := json.MarshalIndent(msg, "", "  ")
		if err != nil {
			log.Printf("failed create json msg: %s", err)
			cancel()
			return
		}

		ws.SetWriteDeadline(time.Now().Add(writeWait))
		err = ws.WriteMessage(websocket.TextMessage, msgJson)
		if err != nil {
			log.Printf("failed to send message to ws pty: %s", err)
			cancel()
			break
		}
	}
}

func ping(ctx context.Context, ws *websocket.Conn) {
	ctx, cancel := context.WithCancel(ctx)
	defer func() { cancel() }()

	ticker := time.NewTicker(pingPeriod)
	defer ticker.Stop()
	for {
		select {
		case <-ticker.C:
			err := ws.WriteControl(websocket.PingMessage, []byte{}, time.Now().Add(writeWait))
			if err != nil {
				log.Printf("ping failed: %s. disconnecting", err)
				cancel()
			}
		case <-ctx.Done():
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

type Session struct {
	Name    *string
	PtyPipe *os.File
}

var sessionMutex sync.Mutex
var sessions []string = []string{}

func serveWs(w http.ResponseWriter, r *http.Request) {
	log.Printf("connected: %s", r.RemoteAddr)
	ctx, cancel := context.WithCancel(context.Background())
	defer func() { cancel() }()

	ws, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("websocket upgrade failed: %s", err)
		return
	}
	defer ws.Close()

	session := Session{}

	go writePump(ctx, ws, &session)
	go readPump(ctx, ws, &session)
	go ping(ctx, ws)

	<-ctx.Done()

	defer func() {
		if session.PtyPipe != nil {
			session.PtyPipe.Close()
		}
	}()

	log.Printf("closing connection: %s", r.RemoteAddr)
	ws.SetWriteDeadline(time.Now().Add(writeWait))
	ws.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
	time.Sleep(closeGracePeriod)
}

func main() {
	flag.Parse()
	http.Handle("/", http.FileServer(http.Dir("../web/")))
	http.HandleFunc("/ws", serveWs)
	log.Fatal(http.ListenAndServe(*addr, nil))
}
