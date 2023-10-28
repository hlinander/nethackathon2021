package task

import (
	_ "embed"
	"nhctl/build"
)

type Inline struct {
	build.TaskBase
	staging func(s *Inline, ctx build.Context)
}

func (s *Inline) Stage(ctx build.Context) error {
	s.staging(s, ctx)
	return nil
}

func (s *Inline) Build(ctx build.Context) error {
	return build.CopyDir(s.StagingDir(), s.BuildDir())
}
