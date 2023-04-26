package step

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

//go:embed compile.go
var downloadSourceCode string

type DownloadParams struct {
	Url string
}

type Download struct {
	build.StepBase
	Input             DownloadParams
	DownloadedFileRel string
}

func (s *Download) Stage(ctx build.Context) error {
	err := os.WriteFile(
		filepath.Join(s.StagingDir(), "step.go"),
		[]byte(downloadSourceCode),
		0644,
	)
	if err != nil {
		panic(err)
	}

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
