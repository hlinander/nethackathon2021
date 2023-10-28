package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"nhctl/build"
	"nhctl/task"
	"os"
	"os/signal"
	"path/filepath"
	"syscall"

	"github.com/go-errors/errors"
	"github.com/gorilla/websocket"
	"github.com/spf13/cobra"
)

var cleanCache bool

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type Message struct {
	Type string
	Data string
}

var webChannel = make(chan Message)

func handleConnection(w http.ResponseWriter, r *http.Request) {
	// Upgrade initial GET request to a websocket
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		fmt.Println(err)
		return
	}
	// Close the connection when the function returns
	defer conn.Close()

	go func() {
		// Read message from browser
		_, inMsgData, err := conn.ReadMessage()
		if err != nil {
			fmt.Println(err)
			return
		}

		inMsg := Message{}
		json.Unmarshal(inMsgData, &inMsg)
		if inMsg.Type == "start" {
			if cleanCache {
				ctx, err := build.NewContext()
				if err != nil {
					panic(err)
				}
				cacheRootAbs := filepath.Join(ctx.BuildRootDir, "cache")
				log.Printf("cleaning cache dir %s", cacheRootAbs)
				os.RemoveAll(cacheRootAbs)
			}

			downloadGenCompile := task.NewDownloadGenCompile()

			err := build.Build([]build.Task{downloadGenCompile})
			if err != nil {
				panic(errors.Errorf("build: %w", err))
			}
		}
	}()

	for {
		msg := <-webChannel

		jsonData, err := json.Marshal(msg)
		if err != nil {
			fmt.Println("Error encoding JSON:", err)
			return
		}

		// Write message back to browser
		if err = conn.WriteMessage(1, []byte(string(jsonData))); err != nil {
			fmt.Println(err)
			return
		}
	}
}

func main() {
	originalStdout := os.Stdout
	r, w, _ := os.Pipe() // Create a pipe
	os.Stdout = w
	log.SetOutput(w)

	// Copy the output in a separate goroutine so printing can't block indefinitely
	go func() {
		scanner := bufio.NewScanner(r)
		for scanner.Scan() {
			line := scanner.Text()
			originalStdout.WriteString(line + "\n")

			select {
			case webChannel <- Message{
				Type: "console",
				Data: line,
			}:
			default:
			}
		}
	}()

	var rootCmd = &cobra.Command{
		Use:   "nhctl",
		Short: "build and deploy nethackathon",
		RunE: func(cmd *cobra.Command, args []string) error {

			// Create a channel to receive OS signals
			sigChan := make(chan os.Signal, 1)

			go func() {
				fs := http.FileServer(http.Dir("web"))
				http.Handle("/", fs)
				http.ListenAndServe(":8080", nil)
				fmt.Println("Please connect to localhost:8080")
			}()

			go func() {
				http.HandleFunc("/ws", handleConnection)
				err := http.ListenAndServe(":8081", nil)
				if err != nil {
					fmt.Println("websocket ListenAndServe: ", err)
				}
			}()

			// Notify sigChan when a SIGINT (Ctrl+C) is received
			signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

			// Create a goroutine to block until a signal is received
			go func() {
				sig := <-sigChan
				fmt.Println("\nReceived signal:", sig)
				os.Exit(0)
			}()

			// Rest of your program goes here
			fmt.Println("Press Ctrl+C to exit...")
			select {} // Block forever
		},
	}

	rootCmd.Flags().BoolVarP(&cleanCache, "clean-cache", "c", false, "clean the cache")

	err := rootCmd.Execute()
	if err != nil {
		var errWithStack *errors.Error
		if errors.As(err, &errWithStack) {
			fmt.Println(errWithStack.ErrorStack())
		} else {
			panic(err)
		}
	}
}
