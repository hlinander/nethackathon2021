package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"sync"
	"time"
)

type Worker struct {
	Available    bool
	TokenChannel chan Message
}

type Workers struct {
	EndpointsMutex sync.RWMutex
	Endpoints      map[net.Conn]*Worker
}

type Message struct {
	Type    string `json:"type"`
	Message string `json:"message"`
	Done    bool   `json:"done"`
}

var ErrNoAvailableWorkers = fmt.Errorf("no available workers")

func (w *Workers) AllocWorker() (*Worker, net.Conn, error) {
	w.EndpointsMutex.Lock()
	defer w.EndpointsMutex.Unlock()
	for conn, worker := range w.Endpoints {
		if worker.Available {
			worker.Available = false
			worker.TokenChannel = make(chan Message)
			return worker, conn, nil
		}
	}

	return nil, nil, ErrNoAvailableWorkers
}

func (w *Workers) NumAvailWorkers() int {
	w.EndpointsMutex.RLock()
	defer w.EndpointsMutex.RUnlock()
	counter := 0
	for _, worker := range w.Endpoints {
		if worker.Available {
			counter++
		}
	}

	return counter
}

func (w *Workers) DeallocWorker(conn net.Conn) {

	w.EndpointsMutex.Lock()
	defer w.EndpointsMutex.Unlock()

	e, exists := w.Endpoints[conn]
	if !exists {
		return
	}

	e.Available = true
	close(e.TokenChannel)
}

var workers Workers = Workers{
	Endpoints: make(map[net.Conn]*Worker),
}

type RootHandlerRequest struct {
	Promt string `json:"prompt"`
}

func rootHandler(w http.ResponseWriter, r *http.Request) {
	ctx := r.Context()
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/plain")

	log.Println("allocating worker")
	worker, conn, err := workers.AllocWorker()
	if err != nil {
		if errors.Is(err, ErrNoAvailableWorkers) {
			log.Println("no workers available")
			http.Error(w, "no workers available", http.StatusServiceUnavailable)
			return
		}
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer workers.DeallocWorker(conn)

	log.Printf("num available workers: %d", workers.NumAvailWorkers())

	reqJsonDataBytes, err := io.ReadAll(r.Body)
	if err != nil {
		if errors.Is(err, io.EOF) {
			return
		}
		http.Error(w, fmt.Sprintf("endpoint error %s", err), http.StatusInternalServerError)
		return
	}

	log.Printf("calling worker with prompt: %s", reqJsonDataBytes)
	conn.Write(reqJsonDataBytes)

	defer func() {
		log.Printf("prompt '%s' done. num available workers: %d", reqJsonDataBytes, workers.NumAvailWorkers())
	}()

	for {
		log.Println("Waiting for channel input...")
		select {
		case msg, ok := <-worker.TokenChannel:
			if !ok {
				return
			}
			_, err = w.Write([]byte(msg.Message))
			if err != nil {
				if errors.Is(err, io.EOF) {
					return
				}
				http.Error(w, fmt.Sprintf("endpoint error %s", err), http.StatusInternalServerError)
				return
			}
			flusher.Flush()
			if msg.Done {
				return
			}
		case <-time.After(time.Second * 10):
			http.Error(w, "timeout", http.StatusInternalServerError)
			return
		case <-ctx.Done():
			conn.Close()
			delete_worker(conn)
			return

		}
		//log.Println("channel input ", msg)
	}

}

type RegisterWorkerRequest struct {
	Endpoint string `json:"endpoint"`
}

func delete_worker(conn net.Conn) {
	workers.EndpointsMutex.Lock()
	defer workers.EndpointsMutex.Unlock()
	delete(workers.Endpoints, conn)
}

func send_ping(conn net.Conn) {
	for {
		_, err := conn.Write([]byte(`{"type": "ping"}`))
		if err != nil {
			conn.Close()
			delete_worker(conn)
			return
		}
		time.Sleep(time.Second * 5)
	}
}

func handleWorker(conn net.Conn) {
	fmt.Println("Accepted connection from", conn.RemoteAddr())

	workers.EndpointsMutex.Lock()
	_, exists := workers.Endpoints[conn]
	if exists {
		log.Println("Worker already exist?")
		return
	}
	worker := Worker{
		Available: true,
	}
	workers.Endpoints[conn] = &worker
	workers.EndpointsMutex.Unlock()

	go send_ping(conn)
	// create a JSON decoder for the connection
	decoder := json.NewDecoder(conn)

	// read JSON messages from the connection
	for {
		var msg Message
		err := decoder.Decode(&msg)
		if err != nil {
			fmt.Println("Error decoding:", err)
			break
		}

		switch msg.Type {
		case "ping":
			fmt.Println("Received ping from", conn.RemoteAddr())
		case "token":
			log.Println(msg)
			select {
			case worker.TokenChannel <- msg:
				log.Println("Sent token!")
			}
		default:
			fmt.Println("Unknown message type:", msg.Type)
		}
	}

	// close the connection
	conn.Close()
	fmt.Println("Closed connection from", conn.RemoteAddr())
}

// func registerWorkerHandler(w http.ResponseWriter, r *http.Request) {
// 	var req RegisterWorkerRequest

// 	err := json.NewDecoder(r.Body).Decode(&req)
// 	if err != nil {
// 		log.Println("register worker error:", err.Error())
// 		http.Error(w, err.Error(), http.StatusBadRequest)
// 		return
// 	}

// 	fmt.Printf("register worker called %+v\n", req)

// 	if req.Endpoint == "" {
// 		http.Error(w, "bad input: 'endpoint' was not set", http.StatusBadRequest)
// 		return
// 	}

// 	workers.EndpointsMutex.Lock()
// 	defer workers.EndpointsMutex.Unlock()

// 	_, exists := workers.Endpoints[req.Endpoint]
// 	if exists {
// 		http.Error(w, "Endpoint already exists", http.StatusBadRequest)
// 		return
// 	}

// 	workers.Endpoints[req.Endpoint] = &Worker{
// 		Available: true,
// 	}

// 	w.Write([]byte{})

// 	log.Println("checking if worker is alive")
// 	go checkWorkerAlive(req.Endpoint)
// }

// func checkWorkerAlive(endpoint string) {
// 	retries := 3
// 	for {
// 		_, err := http.Get(fmt.Sprintf("%s/ping", endpoint))
// 		if err != nil {
// 			retries -= 1
// 			log.Printf("worker ping failed: %s because of error: %s, retries left: %d", endpoint, err, retries)
// 			if retries == 0 {
// 				log.Printf("deleting worker: %s", endpoint)
// 				workers.EndpointsMutex.Lock()
// 				defer workers.EndpointsMutex.Unlock()
// 				delete(workers.Endpoints, endpoint)
// 				return
// 			}
// 		} else {
// 			retries = 3
// 		}

// 		time.Sleep(time.Second * 5)
// 	}
// }

func listen_for_workers() {
	listener, err := net.Listen("tcp", ":8080")
	if err != nil {
		fmt.Println("Error listening:", err)
		return
	}
	defer listener.Close()

	fmt.Println("Listening on", listener.Addr())

	// accept incoming connections
	for {
		conn, err := listener.Accept()
		if err != nil {
			fmt.Println("Error accepting:", err)
			continue
		}

		// handle connection in a separate goroutine
		go handleWorker(conn)
	}

}

func main() {
	http.HandleFunc("/", rootHandler)

	go listen_for_workers()

	if err := http.ListenAndServe(":8383", nil); err != nil {
		log.Panic("Error:", err)
	}
}
