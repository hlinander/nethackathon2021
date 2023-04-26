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

type Step interface {
	Stage(ctx Context) error
	Build(ctx Context) error
	Identifier() string
	Deps() []Step
	StagingDir() string
	SetStagingDir(dir string)
	BuildDir() string
	SetBuildDir(dir string)
}

type StepBase struct {
	id   string
	deps []Step

	stagingDir string
	buildDir   string
}

func NewStepBase(id string, deps ...Step) StepBase {
	return StepBase{
		id:   id,
		deps: deps,
	}
}

func (s StepBase) Identifier() string {
	return s.id
}

func (s *StepBase) Deps() []Step {
	return s.deps
}

func (s StepBase) StagingDir() string {
	return s.stagingDir
}

func (s *StepBase) SetStagingDir(dir string) {
	s.stagingDir = dir
}

func (s StepBase) BuildDir() string {
	return s.buildDir
}

func (s *StepBase) SetBuildDir(dir string) {
	s.buildDir = dir
}
