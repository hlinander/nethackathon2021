package task

import (
	_ "embed"
	"nhctl/build"
	"path/filepath"
)

//go:embed download_gen_compile.go
var download_gen_compile string

type DownloadGenCompile struct {
	build.TaskBase
}

func NewDownloadGenCompile() *DownloadGenCompile {
	download := Download{
		TaskBase: build.NewTaskBase("download"),
		Input: DownloadParams{
			Url: "https://example.com",
		},
	}

	genCode := GenCode{
		TaskBase: build.NewTaskBase("gencode", &download),
		Input: GenCodeParams{
			Name: "shahrouzz",
		},
	}

	merger := Inline{
		TaskBase: build.NewTaskBase("merger", &genCode),
		staging: func(s *Inline, ctx build.Context) {
			build.CopyDir(filepath.Join(ctx.GitRootDir, "dummy"), s.StagingDir())
			build.CopyDir(genCode.BuildDir(), s.StagingDir())
		},
	}

	compile := Compile{
		TaskBase: build.NewTaskBase("compile", &merger),
	}

	downloadGenCompile := DownloadGenCompile{
		TaskBase: build.NewTaskBase("downloadgencompile", &compile),
	}

	return &downloadGenCompile
}

func (s *DownloadGenCompile) Stage(ctx build.Context) error {
	return nil
}

func (s *DownloadGenCompile) Build(ctx build.Context) error {
	return nil
}
