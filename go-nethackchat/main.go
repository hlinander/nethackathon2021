package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"sync"
	"time"
)

type Worker struct {
	Available bool
}

type Workers struct {
	EndpointsMutex sync.RWMutex
	Endpoints      map[string]Worker
}

var ErrNoAvailableWorkers = fmt.Errorf("no available workers")

func (w *Workers) AllocAvailableWorker() (string, error) {
	w.EndpointsMutex.Lock()
	defer w.EndpointsMutex.Unlock()
	for endpoint, worker := range w.Endpoints {
		if worker.Available {
			worker.Available = false
			return endpoint, nil
		}
	}

	return "", ErrNoAvailableWorkers
}

var workers Workers = Workers{
	Endpoints: make(map[string]Worker),
}

type RootHandlerRequest struct {
	Promt string `json:"prompt"`
}

func rootHandler(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "streaming not supported", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "text/plain")

	endpoint, err := workers.AllocAvailableWorker()
	if err != nil {
		if errors.Is(err, ErrNoAvailableWorkers) {
			http.Error(w, "no workers available", http.StatusServiceUnavailable)
			return
		}
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	reqData := RootHandlerRequest{}
	reqDataJsonBytes, err := json.Marshal(reqData)
	if err != nil {
		panic(err)
	}
	req, err := http.NewRequest("GET", fmt.Sprintf("%s/chat", endpoint), bytes.NewBuffer(reqDataJsonBytes))
	if err != nil {
		panic(err)
	}
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		if errors.Is(err, io.EOF) {
			return
		}
		http.Error(w, fmt.Sprintf("endpoint error %s", err), http.StatusInternalServerError)
		return
	}
	defer resp.Body.Close()

	for {
		var buf []byte = make([]byte, 1024)
		n, err := resp.Body.Read(buf)
		if err != nil {
			if errors.Is(err, io.EOF) {
				return
			}

			http.Error(w, fmt.Sprintf("endpoint error %s", err), http.StatusInternalServerError)
			return
		}

		_, err = w.Write(buf[0:n])
		if err != nil {
			if errors.Is(err, io.EOF) {
				return
			}
			http.Error(w, fmt.Sprintf("endpoint error %s", err), http.StatusInternalServerError)
			return
		}
		flusher.Flush()
	}
}

type RegisterWorkerRequest struct {
	Endpoint string `json:"endpoint"`
}

func registerWorkerHandler(w http.ResponseWriter, r *http.Request) {
	var req RegisterWorkerRequest

	err := json.NewDecoder(r.Body).Decode(&req)
	if err != nil {
		log.Println("register worker error:", err.Error())
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Println("register worker called")

	if req.Endpoint == "" {
		http.Error(w, "bad input: 'endpoint' was not set", http.StatusBadRequest)
		return
	}

	log.Println("locking mutex")
	workers.EndpointsMutex.Lock()
	defer workers.EndpointsMutex.Unlock()

	_, exists := workers.Endpoints[req.Endpoint]
	if exists {
		http.Error(w, "Endpoint already exists", http.StatusBadRequest)
		return
	}

	workers.Endpoints[req.Endpoint] = Worker{}

	w.Write([]byte{})

	log.Println("checking of worker is alive")
	go checkWorkerAlive(req.Endpoint)
}

func checkWorkerAlive(endpoint string) {
	retries := 3
	for {
		log.Printf("pinging worker: %s", endpoint)
		_, err := http.Get(fmt.Sprintf("%s/ping", endpoint))
		if err != nil {
			retries -= 1
			log.Printf("worker ping failed: %s because of error: %s, retries left: %d", endpoint, err, retries)
			if retries == 0 {
				log.Printf("deleting worker: %s", endpoint)
				workers.EndpointsMutex.Lock()
				defer workers.EndpointsMutex.Unlock()
				delete(workers.Endpoints, endpoint)
				return
			}
		} else {
			retries = 3
		}

		time.Sleep(time.Second * 5)
	}
}

func main() {
	http.HandleFunc("/", rootHandler)
	http.HandleFunc("/register_worker", registerWorkerHandler)

	if err := http.ListenAndServe(":8383", nil); err != nil {
		log.Panic("Error:", err)
	}
}
