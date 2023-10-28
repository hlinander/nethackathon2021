package task

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"nhctl/build"
	"os"
	"path/filepath"
)

//go:embed download.go
var downloadSourceCode string

type DownloadParams struct {
	Url string
}

type Download struct {
	build.TaskBase
	Input             DownloadParams
	DownloadedFileRel string
}

func (s *Download) Stage(ctx build.Context) error {
	jsonBytes, err := json.MarshalIndent(s.Input, "", "  ")
	if err != nil {
		panic(err)
	}
	err = os.WriteFile(filepath.Join(s.StagingDir(), "input.json"), jsonBytes, 0644)
	if err != nil {
		panic(err)
	}

	return nil
}

func (s *Download) Build(ctx build.Context) error {
	response, err := http.Get(s.Input.Url)
	if err != nil {
		return err
	}
	defer response.Body.Close()

	if response.StatusCode != http.StatusOK {
		return fmt.Errorf("failed to download file: status code %d", response.StatusCode)
	}

	s.DownloadedFileRel = "downloaded.html"

	file, err := os.Create(filepath.Join(s.BuildDir(), s.DownloadedFileRel))
	if err != nil {
		return err
	}
	defer file.Close()

	_, err = io.Copy(file, response.Body)
	if err != nil {
		return err
	}

	return nil
}
