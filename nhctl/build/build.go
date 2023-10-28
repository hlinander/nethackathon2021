package build

import (
	"encoding/json"
	"log"
	"os"
	"path/filepath"

	"github.com/go-errors/errors"
)

func Build(rootTasks []Task) error {
	allTasks := CollectTasks(rootTasks)

	// make sure no two tasks have the same id
	ids := map[string]struct{}{}
	for _, t := range allTasks {
		_, exists := ids[t.Identifier()]
		if exists {
			return errors.Errorf("%w: %s", ErrDuplicateIds, t.Identifier())
		}
		ids[t.Identifier()] = struct{}{}
	}

	if HasCycles(&allTasks) {
		return ErrCycles
	}

	sortedTasks, err := TopologicalSort(rootTasks)
	if err != nil {
		return errors.Errorf("topological sort: %w", err)
	}

	ctx, err := NewContext()
	if err != nil {
		panic(err)
	}

	for _, s := range sortedTasks {
		stagingDir, err := ctx.CreateTaskStagingDir(s.Identifier())
		if err != nil {
			panic(err)
		}
		s.SetStagingDir(stagingDir)

		err = s.Stage(*ctx)
		if err != nil {
			return errors.Errorf("staging for task '%s': %w", s.Identifier(), err)
		}

		// calculate hash for setup staging dir
		hash, err := HashDir(stagingDir, "", Hash1)
		if err != nil {
			panic(err)
		}

		log.Printf("%s cache hash: %s", s.Identifier(), hash)

		cacheRootAbs := filepath.Join(ctx.BuildRootDir, "cache")
		cachedTaskAbs := filepath.Join(cacheRootAbs, hash)

		// check if hash is cached.
		isCached, err := ctx.IsCached(cacheRootAbs, hash)
		if err != nil {
			panic(err)
		}
		if isCached {
			// load from cache dir
			jsonBytes, err := os.ReadFile(filepath.Join(cachedTaskAbs, "task.json"))
			if err != nil {
				panic(err)
			}
			err = json.Unmarshal(jsonBytes, s)
			if err != nil {
				panic(err)
			}
			s.SetBuildDir(cachedTaskAbs)
		} else {
			// build
			buildDir, err := ctx.CreateTaskBuildDir(s.Identifier())
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
				return errors.Errorf("build for task '%s': %w", s.Identifier(), err)
			}

			// save to cache dir
			err = CopyDir(buildDir, cachedTaskAbs)
			if err != nil {
				panic(err)
			}

			jsonData, err := json.MarshalIndent(s, "", "  ")
			if err != nil {
				panic(err)
			}

			err = os.WriteFile(filepath.Join(cachedTaskAbs, "task.json"), jsonData, 0644)
			if err != nil {
				panic(err)
			}
		}
	}

	// repr.Print(sortedTasks)

	return nil
}
