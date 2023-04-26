package build

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

type MockStep struct {
	StepBase
}

func (m MockStep) Stage(ctx Context) error {
	return nil
}

func (m MockStep) Build(ctx Context) error {
	return nil
}

// func TestCollectSteps(t *testing.T) {
// 	step1 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step1",
// 			DepsList: []Step{},
// 		},
// 	}
// 	step2 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step2",
// 			DepsList: []Step{&step1},
// 		},
// 	}
// 	step3 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step3",
// 			DepsList: []Step{&step2},
// 		},
// 	}

// 	rootSteps := []Step{&step3}

// 	result := CollectSteps(rootSteps)

// 	assert.Len(t, result, 3)
// }

// func TestCollectStepsWithCycle(t *testing.T) {
// 	step1 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step1",
// 			DepsList: []Step{},
// 		},
// 	}
// 	step2 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step2",
// 			DepsList: []Step{&step1},
// 		},
// 	}
// 	step3 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step3",
// 			DepsList: []Step{&step2, &step1},
// 		},
// 	}
// 	step1.DepsList = append(step1.DepsList, &step3)

// 	rootSteps := []Step{&step3}

// 	result := CollectSteps(rootSteps)

// 	assert.Len(t, result, 3)
// }

// func TestCycleCheck(t *testing.T) {
// 	step1 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step1",
// 			DepsList: []Step{},
// 		},
// 	}
// 	step2 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step2",
// 			DepsList: []Step{&step1},
// 		},
// 	}
// 	step3 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step3",
// 			DepsList: []Step{&step2, &step1},
// 		},
// 	}
// 	// create a cycle back from 1 to 3
// 	step1.DepsList = append(step1.DepsList, &step3)

// 	step4 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step4",
// 			DepsList: []Step{},
// 		},
// 	}

// 	collectedSteps := CollectSteps([]Step{&step3, &step4})

// 	assert.Len(t, collectedSteps, 4)
// 	assert.Truef(t, HasCycles(&collectedSteps), "expected cycles but found none")
// }

// func TestCycleCheckNoCycles(t *testing.T) {
// 	step1 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step1",
// 			DepsList: []Step{},
// 		},
// 	}
// 	step2 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step2",
// 			DepsList: []Step{&step1},
// 		},
// 	}
// 	step3 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step3",
// 			DepsList: []Step{&step2, &step1},
// 		},
// 	}

// 	// disconnected step
// 	step4 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "step4",
// 			DepsList: []Step{},
// 		},
// 	}

// 	collectedSteps := CollectSteps([]Step{&step3, &step4})

// 	assert.Len(t, collectedSteps, 4)

// 	hasCycles := HasCycles(&collectedSteps)
// 	if hasCycles == true {
// 		t.Errorf("expected cycle no cycles got one")
// 	}
// }

// func TestDuplicateName(t *testing.T) {
// 	step1 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "foo",
// 			DepsList: []Step{},
// 		},
// 	}
// 	step2 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "bar",
// 			DepsList: []Step{&step1},
// 		},
// 	}

// 	// disconnected step
// 	step4 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "foo",
// 			DepsList: []Step{},
// 		},
// 	}

// 	err := Build([]Step{&step2, &step4})
// 	if err == nil {
// 		t.Errorf("expected duplicate id error")
// 	}
// }

// func TestGraphCycle(t *testing.T) {
// 	step1 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "foo",
// 			DepsList: []Step{},
// 		},
// 	}
// 	step2 := MockStep{
// 		StepBase: StepBase{
// 			Id:       "bar",
// 			DepsList: []Step{&step1},
// 		},
// 	}
// 	step1.DepsList = append(step1.DepsList, &step2)

// 	err := Build([]Step{&step2})
// 	if err == nil {
// 		t.Errorf("expected cycle")
// 	}
// }

func TestIfMapIsByValue(t *testing.T) {
	myMap := map[string]bool{}

	addItemFunc := func(m map[string]bool) {
		m["hello"] = true
		m["world"] = true
	}

	addItemFunc(myMap)

	assert.Len(t, myMap, 2)
}

func TestIfSlicesAreByValue(t *testing.T) {
	myArray := []string{
		"world",
	}

	addItemFunc := func(m []string) {
		m[0] = "world"
		// m = append(m, "world")
	}

	addItemFunc(myArray)

	assert.Len(t, myArray, 1)
	assert.Equal(t, myArray[0], "world")
}
