package task

import (
	_ "embed"
	"nhctl/build"
	"path/filepath"
)

//go:embed copyfromrepo.go
var copyfromRepoSourceCode string

type CopyFromRepoParams struct {
	RepoPath string
}

type CopyFromRepo struct {
	build.TaskBase
	Input CopyFromRepoParams
}

func (s *CopyFromRepo) Stage(ctx build.Context) error {
	err := build.CopyDir(filepath.Join(ctx.GitRootDir, s.Input.RepoPath), s.StagingDir())
	if err != nil {
		panic(err)
	}

	return nil
}

func (s *CopyFromRepo) Build(ctx build.Context) error {
	err := build.CopyDir(s.StagingDir(), s.BuildDir())
	if err != nil {
		panic(err)
	}
	return nil
}
