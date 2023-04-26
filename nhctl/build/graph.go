package build

import (
	"os"

	"github.com/aybabtme/gexf"
	"github.com/go-errors/errors"
)

var ErrDuplicateIds = errors.New("duplicate ids")
var ErrCycles = errors.New("has cycles")

func CollectSteps(rootSteps []Step) []Step {
	visited := map[Step]bool{}
	accum := []Step{}

	for _, s := range rootSteps {
		collectStepsDfs(s, &visited, &accum)
	}

	return accum
}

func collectStepsDfs(
	s Step,
	visited *map[Step]bool,
	accum *[]Step,
) {
	_, exists := (*visited)[s]
	if exists {
		return
	}
	*accum = append(*accum, s)
	(*visited)[s] = true
	for _, d := range s.Deps() {
		collectStepsDfs(d, visited, accum)
	}
}

// todo: return what caused the cycle
func HasCycles(allSteps *[]Step) bool {
	visited := map[Step]bool{}
	inStack := map[Step]bool{}

	for _, s := range *allSteps {
		_, exists := visited[s]
		if !exists {
			if checkCyclesDfs(s, &visited, &inStack) {
				return true
			}
		}
	}
	return false
}

func checkCyclesDfs(
	start Step,
	visited *map[Step]bool,
	inStack *map[Step]bool,
) bool {
	(*visited)[start] = true
	(*inStack)[start] = true

	for _, d := range start.Deps() {
		_, exists := (*visited)[d]
		if !exists {
			if checkCyclesDfs(d, visited, inStack) {
				return true
			}
		}

		inStackVal, exists := (*inStack)[d]
		if exists && inStackVal {
			return true
		}
	}

	(*inStack)[start] = false
	return false
}

// file format that can be imported into gephi. useful for debugging.
func WriteGexfFile(filePath string, rootSteps []Step) error {
	allSteps := CollectSteps(rootSteps)
	g := gexf.NewGraph()

	for _, s := range allSteps {
		g.AddNode(s.Identifier(), s.Identifier(), []gexf.AttrValue{})
	}

	for _, s := range allSteps {
		for _, n := range s.Deps() {
			g.AddEdge(s.Identifier(), n.Identifier())
		}
	}

	file, err := os.OpenFile(filePath, os.O_CREATE|os.O_RDWR|os.O_TRUNC, 0755)
	if err != nil {
		return errors.Errorf("open file: %w", err)
	}
	defer file.Close()

	err = gexf.Encode(file, g)
	if err != nil {
		return errors.Errorf("encoding gexf file: %w", err)
	}

	return nil
}

func TopologicalSort(steps []Step) ([]Step, error) {
	visited := make(map[string]bool)
	stack := make([]Step, 0)

	for _, step := range steps {
		if err := topologicalSortVisit(step, visited, &stack); err != nil {
			return nil, err
		}
	}

	return stack, nil
}

func topologicalSortVisit(
	step Step,
	visited map[string]bool,
	stack *[]Step,
) error {
	id := step.Identifier()

	if !visited[id] {
		visited[id] = true

		for _, dep := range step.Deps() {
			if err := topologicalSortVisit(dep, visited, stack); err != nil {
				return err
			}
		}

		*stack = append(*stack, step)
	}

	return nil
}
