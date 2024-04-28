package main

import (
	"bufio"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"os/exec"
	"time"
)

var oracleHost = flag.String("oracle-host", "localhost:8080", "Oracle host ip")
var modelPath = flag.String("model-path", "../models/raw_wiki_sharran/ckpt/ggml-model-q4_0.bin", "ggml model")
var ggmlBinPath = flag.String("ggml-bin", "../oracle-rag-chat/target/release/oracle-rag-chat", "ggml binary")

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
	cmd := exec.Command(*ggmlBinPath, message)
	fmt.Println(cmd.Args)
	stdout, err := cmd.StdoutPipe()
	if err != nil {
		panic(err)
	}

	if err := cmd.Start(); err != nil {
		panic(err)
	}

	reader := bufio.NewReader(stdout)
	buf := make([]byte, 10)
	for {
		n, err := reader.Read(buf)
		if err != nil {
			if errors.Is(err, io.EOF) {
				log.Println("LLM process EOF")
				break
			}
			log.Println("Error when reading LLM process")
			break
		}
		fmt.Print("~")
		fmt.Print(string(buf[:n]))
		encoder.Encode(&Message{
			Type:    "token",
			Message: string(buf[:n]),
		})
	}
	encoder.Encode(&Message{
		Type:    "token",
		Message: "",
		Done:    true,
	})
}

func connect() bool {
	conn, err := net.Dial("tcp", *oracleHost)

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
	flag.Parse()
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
