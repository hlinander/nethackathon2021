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
	Endpoints      map[string]*Worker
}

var ErrNoAvailableWorkers = fmt.Errorf("no available workers")

func (w *Workers) AllocWorker() (string, error) {
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

func (w *Workers) DeallocWorker(endpoint string) {

	w.EndpointsMutex.Lock()
	defer w.EndpointsMutex.Unlock()

	e, exists := w.Endpoints[endpoint]
	if !exists {
		return
	}

	e.Available = true
}

var workers Workers = Workers{
	Endpoints: make(map[string]*Worker),
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

	log.Println("allocating worker")
	endpoint, err := workers.AllocWorker()
	if err != nil {
		if errors.Is(err, ErrNoAvailableWorkers) {
			log.Println("no workers available")
			http.Error(w, "no workers available", http.StatusServiceUnavailable)
			return
		}
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer workers.DeallocWorker(endpoint)

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
	req, err := http.NewRequest("GET", fmt.Sprintf("%s/chat", endpoint), bytes.NewBuffer(reqJsonDataBytes))
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
	if resp.StatusCode != 200 {
		http.Error(w, fmt.Sprintf("no endpoint available %s", err), http.StatusServiceUnavailable)
		return
	}

	defer func() {
		log.Printf("prompt '%s' done. num available workers: %d", reqJsonDataBytes, workers.NumAvailWorkers())
	}()

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

	workers.EndpointsMutex.Lock()
	defer workers.EndpointsMutex.Unlock()

	_, exists := workers.Endpoints[req.Endpoint]
	if exists {
		http.Error(w, "Endpoint already exists", http.StatusBadRequest)
		return
	}

	workers.Endpoints[req.Endpoint] = &Worker{
		Available: true,
	}

	w.Write([]byte{})

	log.Println("checking if worker is alive")
	go checkWorkerAlive(req.Endpoint)
}

func checkWorkerAlive(endpoint string) {
	retries := 3
	for {
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
