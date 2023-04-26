package build

import (
	"encoding/json"
	"os"
	"path/filepath"

	"github.com/go-errors/errors"
)

func Build(rootSteps []Step) error {
	allSteps := CollectSteps(rootSteps)

	// make sure no two steps have the same id
	ids := map[string]struct{}{}
	for _, s := range allSteps {
		_, exists := ids[s.Identifier()]
		if exists {
			return errors.Errorf("%w: %s", ErrDuplicateIds, s.Identifier())
		}
		ids[s.Identifier()] = struct{}{}
	}

	if HasCycles(&allSteps) {
		return ErrCycles
	}

	sortedSteps, err := TopologicalSort(rootSteps)
	if err != nil {
		return errors.Errorf("topological sort: %w", err)
	}

	ctx, err := NewContext()
	if err != nil {
		panic(err)
	}

	for _, s := range sortedSteps {
		stagingDir, err := ctx.CreateStepStagingDir(s.Identifier())
		if err != nil {
			panic(err)
		}
		s.SetStagingDir(stagingDir)

		err = s.Stage(*ctx)
		if err != nil {
			return errors.Errorf("staging for step '%s': %w", s.Identifier(), err)
		}

		// calculate hash for setup staging dir
		hash, err := HashDir(stagingDir, "", Hash1)
		if err != nil {
			panic(err)
		}

		cacheRootAbs := filepath.Join(ctx.BuildRootDir, "cache")
		cachedStepAbs := filepath.Join(cacheRootAbs, hash)

		// check if hash is cached.
		isCached, err := ctx.IsCached(cacheRootAbs, hash)
		if err != nil {
			panic(err)
		}
		if isCached {
			// load from cache dir
			jsonBytes, err := os.ReadFile(filepath.Join(cachedStepAbs, "step.json"))
			if err != nil {
				panic(err)
			}
			err = json.Unmarshal(jsonBytes, s)
			if err != nil {
				panic(err)
			}
			s.SetBuildDir(cachedStepAbs)
		} else {
			// build
			buildDir, err := ctx.CreateStepBuildDir(s.Identifier())
			if err != nil {
				panic(err)
			}
			s.SetBuildDir(buildDir)

			// copy stage to output dir
			err = CopyDir(s.StagingDir(), s.BuildDir())
			if err != nil {
				panic(err)
			}

			err = s.Build(*ctx)
			if err != nil {
				return errors.Errorf("build for step '%s': %w", s.Identifier(), err)
			}

			// save to cache dir
			err = CopyDir(buildDir, cachedStepAbs)
			if err != nil {
				panic(err)
			}

			jsonData, err := json.MarshalIndent(s, "", "  ")
			if err != nil {
				panic(err)
			}

			err = os.WriteFile(filepath.Join(cachedStepAbs, "step.json"), jsonData, 0644)
			if err != nil {
				panic(err)
			}
		}
	}

	// repr.Print(sortedSteps)

	return nil
}
