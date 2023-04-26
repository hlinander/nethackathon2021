package main

import (
	"path/filepath"

	"github.com/go-errors/errors"
	"github.com/otiai10/copy"
	"golang.org/x/sync/errgroup"
)

type BuildOracleWorkerArtifact struct {
	Path string
}

func BuildOracleWorker(ctx BuildContext) (*BuildOracleWorkerArtifact, error) {
	stagingDir, err := ctx.CreateStagingDir("oracle-worker-service")
	if err != nil {
		return nil, err
	}

	// copy all source files to staging dir
	err = copy.Copy(filepath.Join(ctx.GitRootDir, "oracle-worker-service"), stagingDir)
	if err != nil {
		return nil, err
	}

	// hash, err := HashDir(stagingDir, "", DefaultHash)
	// if err != nil {
	// 	return err
	// }

	// log.Println("hash:", hash)

	var wg errgroup.Group
	wg.Go(func() error {
		err = RunCmd(
			RunCmdOpts{
				Cmd:        []string{"sh", "build.sh"},
				WorkingDir: stagingDir,
				LogPrefix:  "build",
			})
		if err != nil {
			return errors.Errorf("build command failed %w", err)
		}
		return nil
	})

	wg.Go(func() error {
		err = RunCmd(
			RunCmdOpts{
				Cmd:        []string{"rsync", "-avz", "-e", "ssh -o StrictHostKeyChecking=no", "nethack@192.168.1.148:/home/nethack/models/raw_wiki_sharran/ckpt/ggml-model-q4_0.bin", ctx.AssetDir},
				WorkingDir: stagingDir,
				LogPrefix:  "rsync",
			})
		if err != nil {
			return errors.Errorf("rsync command failed %w", err)
		}
		return nil
	})

	err = wg.Wait()
	if err != nil {
		return nil, err
	}

	return nil, nil
}
