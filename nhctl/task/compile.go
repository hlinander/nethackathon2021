package task

import (
	_ "embed"
	"nhctl/build"
	"path/filepath"
)

//go:embed compile.go
var compileSourceCode string

type Compile struct {
	build.TaskBase
	ExecutableRel string
}

func (s *Compile) Stage(ctx build.Context) error {
	err := build.CopyDir(
		s.Deps()[0].BuildDir(),
		s.StagingDir(),
	)
	if err != nil {
		panic(err)
	}

	return nil
}

func (s *Compile) Build(ctx build.Context) error {
	err := build.RunCmd(
		build.RunCmdOpts{
			Cmd:        []string{"go", "build", "."},
			WorkingDir: filepath.Join(s.BuildDir()),
			LogPrefix:  "go",
		})
	if err != nil {
		panic(err)
	}

	s.ExecutableRel = filepath.Join("dummy", "dummy")

	println(filepath.Join(s.BuildDir()))

	return nil
}
