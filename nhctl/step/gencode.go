package step

import (
	_ "embed"
	"nhctl/build"
	"os"
	"path/filepath"
)

//go:embed compile.go
var genCodeSourceCode string

type GenCode struct {
	build.StepBase
	OutputFilePathRel string
}

func (s *GenCode) Stage(ctx build.Context) error {
	err := os.WriteFile(filepath.Join(s.StagingDir(), "step.go"), []byte(compileSourceCode), 0644)
	if err != nil {
		panic(err)
	}
	return nil
}

func (s *GenCode) Build(ctx build.Context) error {
	s.OutputFilePathRel = "gen.go"
	file, err := os.Create(filepath.Join(s.OutputDir(), s.OutputFilePathRel))
	if err != nil {
		panic(err)
	}

	_, err = file.WriteString(`package main
func foo() {
	print("hello world1") 
}`)
	if err != nil {
		panic(err)
	}

	return nil
}
