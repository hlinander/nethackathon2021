package main

import (
	"encoding/json"
	"fmt"
	"net"
	"time"
)

type Message struct {
	Type    string `json:"type"`
	Message string `json:"message"`
	Done    bool   `json:"done"`
}

func send_ping(conn net.Conn) {
	for {
		_, err := conn.Write([]byte(`{"type": "ping"}`))
		if err != nil {
			conn.Close()
			return
		}
		time.Sleep(time.Second * 5)
	}
}

func handleChat(conn net.Conn, message string) {
	encoder := json.NewEncoder(conn)
	encoder.Encode(&Message{
		Type:    "token",
		Message: "hello",
	})
	time.Sleep(time.Second * 3)
	encoder.Encode(&Message{
		Type:    "token",
		Message: "world",
		Done:    true,
	})
}

func connect() bool {
	conn, err := net.Dial("tcp", "localhost:8080")

	if err != nil {
		fmt.Println("Error connecting:", err)
		return false
	}
	defer conn.Close()

	go send_ping(conn)

	decoder := json.NewDecoder(conn)
	for {
		var msg Message
		err := decoder.Decode(&msg)
		if err != nil {
			fmt.Println("Error decoding:", err)
			return true
		}

		switch msg.Type {
		case "ping":
			fmt.Println("Received ping from", conn.RemoteAddr())
		case "chat":
			go handleChat(conn, msg.Message)
		default:
			fmt.Println("Unknown message type:", msg.Type)
		}

		fmt.Println("Received: ", msg)
	}
}

func main() {
	// establish TCP connection
	var retry int64 = 0
	for {
		if connect() {
			retry = 0
		}
		time.Sleep(time.Second * time.Duration(retry) * 5)
		if retry < 5 {
			retry += 1
		}
	}
}