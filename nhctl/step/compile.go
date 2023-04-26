package step

import (
	_ "embed"
	"nhctl/build"
	"os"
	"path/filepath"
)

//go:embed compile.go
var compileSourceCode string

type Compile struct {
	build.StepBase
	ExecutableRel string
}

func (s *Compile) Stage(ctx build.Context) error {
	err := os.WriteFile(filepath.Join(s.StagingDir(), "step.go"), []byte(compileSourceCode), 0644)
	if err != nil {
		panic(err)
	}

	err = build.CopyDir(
		filepath.Join(ctx.GitRootDir, "dummy"),
		filepath.Join(s.StagingDir(), "dummy"),
	)
	if err != nil {
		panic(err)
	}

	genCode := s.Deps()[0].(*GenCode)

	err = build.CopyFile(
		filepath.Join(genCode.OutputDir(), genCode.OutputFilePathRel),
		filepath.Join(s.StagingDir(), "dummy/foo.go"),
		0644,
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
			WorkingDir: filepath.Join(s.OutputDir(), "dummy"),
			LogPrefix:  "go",
		})
	if err != nil {
		panic(err)
	}

	s.ExecutableRel = filepath.Join("dummy", "dummy")

	return nil
}
