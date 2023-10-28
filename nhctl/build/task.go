package build

// nomenclature:
// step: atomic part of the build process

// ideas:
// * always include a build log as a file
// * always use filesystem a staging area
// * the input of a step is the output folder of zero or more steps

// probably need multiple phases:
// 	- stage
//  - resolve deps
//  - build whats needed

type Task interface {
	Stage(ctx Context) error
	Build(ctx Context) error
	Identifier() string
	Deps() []Task
	StagingDir() string
	SetStagingDir(dir string)
	BuildDir() string
	SetBuildDir(dir string)
}

type TaskBase struct {
	id   string
	deps []Task

	stagingDir string
	buildDir   string
}

func NewTaskBase(id string, deps ...Task) TaskBase {
	return TaskBase{
		id:   id,
		deps: deps,
	}
}

func (s TaskBase) Identifier() string {
	return s.id
}

func (s *TaskBase) Deps() []Task {
	return s.deps
}

func (s TaskBase) StagingDir() string {
	return s.stagingDir
}

func (s *TaskBase) SetStagingDir(dir string) {
	s.stagingDir = dir
}

func (s TaskBase) BuildDir() string {
	return s.buildDir
}

func (s *TaskBase) SetBuildDir(dir string) {
	s.buildDir = dir
}
