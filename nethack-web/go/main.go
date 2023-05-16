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
	"github.com/georgysavva/scany/v2/pgxscan"
	"github.com/go-playground/validator/v10"
	"github.com/gorilla/websocket"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type Player struct {
	ID       int64
	Clan     int64
	Username string
	Ticker   string
}

type Clan struct {
	ID         int64
	Name       string
	Power_gems int64
}

type ClanReward struct {
	Name   string
	Reward int64
}

// type Reward struct {
// 	Id               int64
// 	Clanname         string
// 	Playername       string
// 	Objectiveliteral string
// 	Score            int64
// 	Timestamp        time.Time
// }

type Event struct {
	Playername string
	Clanname   string
	Vinst      json.RawMessage
	Timestamp  time.Time
	Player_id  int64
}

type IndexPageData struct {
}

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

var dbPool *pgxpool.Pool

func init() {
	var err error
	dbPool, err = pgxpool.New(context.Background(), "postgres://postgres:vinst@localhost/nh")
	if err != nil {
		panic(err)
	}
}

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

func readPump(ctx context.Context, ws *websocket.Conn, s *Session, cancel context.CancelFunc) {
	defer func() {
		cancel()
	}()

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
			log.Printf("looking up player %s", msg.Name)
			err = conn.QueryRow(ctx, "SELECT id FROM players WHERE username=$1", msg.Name).Scan(&id)
			if err != nil {
				log.Printf("unable to query player in db: %s", err)
				break read_msg_loop
			}

			// c := exec.Command("/home/eracce/nethackathon2021/build/bin/nethack", "-u", msg.Name)
			c := exec.Command("sh", "/home/herden/projects/nethackathon2023/wrapped_nethack", msg.Name)
			s.C = c
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
				return
			}

		default:
			log.Printf("ignoring message with unknown type: %s", typeVal)
			continue
		}
	}
}

func writeEvents(ctx context.Context, ws *websocket.Conn) {

}

func writePump(ctx context.Context, ws *websocket.Conn, s *Session, cancel context.CancelFunc) {
	defer cancel()
	buf := make([]byte, maxMessageSize)
	for {
		if s.PtyPipe == nil {
			time.Sleep(time.Second)
			continue
		}

		n, err := s.PtyPipe.Read(buf)
		if err != nil {
			log.Printf("failed to read message from pty: %s", err)
			return
		}

		var msg DataMsg = DataMsg{
			Type: "data",
			Data: base64.RawStdEncoding.EncodeToString(buf[:n]),
		}

		msgJson, err := json.MarshalIndent(msg, "", "  ")
		if err != nil {
			log.Printf("failed create json msg: %s", err)
			return
		}

		ws.SetWriteDeadline(time.Now().Add(writeWait))
		err = ws.WriteMessage(websocket.TextMessage, msgJson)
		if err != nil {
			log.Printf("failed to send message to ws pty: %s", err)
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
	C       *exec.Cmd
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

	go writePump(ctx, ws, &session, cancel)
	go readPump(ctx, ws, &session, cancel)
	go ping(ctx, ws)

	log.Println("waiting for done")
	<-ctx.Done()
	log.Println("after done")

	defer func() {
		if session.PtyPipe != nil {
			log.Println("closing pipe")
			session.PtyPipe.Close()
			session.C.Process.Kill()
		}
	}()

	log.Printf("closing connection: %s", r.RemoteAddr)
	ws.SetWriteDeadline(time.Now().Add(writeWait))
	ws.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseNormalClosure, ""))
	time.Sleep(closeGracePeriod)
}

func serveEvents(w http.ResponseWriter, r *http.Request) {
	var events []*Event
	err := pgxscan.Select(context.Background(), dbPool, &events, `
WITH vinst AS (
    (
        SELECT
            timestamp,
            player_id,
            json_build_object('type', 'event', 'name', "name", 'string_value', string_value, 'value', value, 'turn', session_turn)::jsonb AS vinst
        FROM
            event
        WHERE
            ("name" IN ('death', 'reach_depth'))
			OR (session_turn=1 and string_value='hp')
    )
    UNION
    (
        SELECT
            timestamp,
            player AS player_id,
            json_build_object('type', 'reward', 'literal', objectives.literal, 'score', rewards.score)::jsonb AS vinst
        FROM
            rewards
        INNER JOIN objectives ON rewards.objective = objectives.id
    )
    ORDER BY
        timestamp DESC
    LIMIT 20
)
SELECT
    vinst.*,
    players.username AS playername,
    clans."name" AS clanname
FROM
    vinst
INNER JOIN players ON vinst.player_id = players.id
INNER JOIN clans ON clans.id = players.clan
		ORDER BY timestamp DESC;
					`)
	if err != nil {
		fmt.Printf("CR ERROR %v\n", err)
	}

	jsonBytes, _ := json.Marshal(&events)
	w.Header().Set("Content-Type", "application/json")
	w.Write(jsonBytes)
}

func main() {

	flag.Parse()
	http.Handle("/", http.FileServer(http.Dir("../web2/dist")))
	http.HandleFunc("/ws", serveWs)
	http.HandleFunc("/events", func(w http.ResponseWriter, r *http.Request) {
		serveEvents(w, r)
	})
	ctx := context.Background()
	http.HandleFunc("/poll", func(w http.ResponseWriter, r *http.Request) {
		var clans []*Clan
		err := pgxscan.Select(ctx, dbPool, &clans, `SELECT id, name, power_gems FROM clans ORDER BY power_gems DESC`)
		if err != nil {
			fmt.Printf("Clan ERROR %v\n", err)
		}

		var players []*Player
		err = pgxscan.Select(ctx, dbPool, &players, `SELECT id, clan, username, ticker FROM players`)
		if err != nil {
			fmt.Printf("Player ERROR %v\n", err)
		}

		var clan_rewards []*ClanReward
		err = pgxscan.Select(ctx, dbPool, &clan_rewards, `select
	clans.name as name, SUM(rewards.score) as reward
from
	rewards inner join objectives on rewards.objective = objectives.id
	inner join players on players.id = rewards.player
	inner join clans on players.clan = clans.id
	group by clans.name`)
		if err != nil {
			fmt.Printf("CR ERROR %v\n", err)
		}

		type PollData struct {
			Clans       []*Clan
			Players     []*Player
			ClanRewards []*ClanReward
		}

		data := PollData{
			Clans:       clans,
			Players:     players,
			ClanRewards: clan_rewards,
		}

		jsonBytes, _ := json.Marshal(&data)
		w.Header().Set("Content-Type", "application/json")
		w.Write(jsonBytes)
	})

	log.Fatal(http.ListenAndServe(*addr, nil))
}
