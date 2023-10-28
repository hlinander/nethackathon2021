package task

import (
	_ "embed"
	"encoding/json"
	"fmt"
	"nhctl/build"
	"os"
	"path/filepath"
)

//go:embed gencode.go
var genCodeSourceCode string

type GenCodeParams struct {
	Name string
}

type GenCode struct {
	build.TaskBase
	Input             GenCodeParams
	OutputFilePathRel string
}

func (s *GenCode) Stage(ctx build.Context) error {
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

func (s *GenCode) Build(ctx build.Context) error {
	s.OutputFilePathRel = "gen.go"
	file, err := os.Create(filepath.Join(s.BuildDir(), s.OutputFilePathRel))
	if err != nil {
		panic(err)
	}

	_, err = file.WriteString(
		fmt.Sprintf(`package main
func foo() {
	print("hello %s") 
}`, s.Input.Name))
	if err != nil {
		panic(err)
	}

	return nil
}
