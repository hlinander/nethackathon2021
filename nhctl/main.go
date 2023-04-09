package main

import (
	"bufio"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/go-errors/errors"
	"github.com/otiai10/copy"
	"github.com/spf13/cobra"
	"golang.org/x/sync/errgroup"
)

func gitRootDir() (string, error) {
	cmd := exec.Command("git", "rev-parse", "--show-toplevel")

	path, err := cmd.Output()
	if err != nil {
		return "", errors.Errorf("failed extract output from git command: %w", err)
	}

	return strings.TrimSpace(string(path)), nil
}

func createTmpDir(rootPath string) (string, error) {
	tmpPath, err := os.MkdirTemp(rootPath, ".build-*")
	if err != nil {
		panic(errors.Errorf("failed to create temp dir %w", err))
	}

	tmpPath, err = filepath.Abs(tmpPath)
	if err != nil {
		panic(errors.Errorf("failed to get temp dir abs path %w", err))
	}

	return tmpPath, nil
}

func createCachedAssetsDir(rootPath string) (string, error) {
	path := filepath.Join(rootPath, ".assets")
	err := os.MkdirAll(path, 0755)
	if err != nil {
		panic(errors.Errorf("failed to create asset dir %w", err))
	}
	return path, nil
}

type RunCmdOpts struct {
	Cmd        []string
	WorkingDir string
	LogPrefix  string
}

func RunCmd(opts RunCmdOpts) error {
	buildCmd := exec.Command(opts.Cmd[0], opts.Cmd[1:]...)
	buildCmd.Dir = opts.WorkingDir
	for _, e := range os.Environ() {
		if !strings.HasPrefix(e, "TERM=") {
			buildCmd.Env = append(buildCmd.Env, e)
		}
	}

	stderrPipe, err := buildCmd.StderrPipe()
	if err != nil {
		return err
	}
	defer stderrPipe.Close()

	stdoutPipe, err := buildCmd.StdoutPipe()
	if err != nil {
		return err
	}
	defer stdoutPipe.Close()

	buildCmd.Start()

	go func() {
		scanner := bufio.NewScanner(stderrPipe)
		for scanner.Scan() {
			fmt.Fprintf(os.Stdout, "%s> %s\n", opts.LogPrefix, scanner.Text())
		}
		if err := scanner.Err(); err != nil {
			fmt.Println("Error reading stdin input:", err)
		}
	}()

	go func() {
		scanner := bufio.NewScanner(stdoutPipe)
		for scanner.Scan() {
			fmt.Fprintf(os.Stdout, "%s> %s\n", opts.LogPrefix, scanner.Text())
		}

		if err := scanner.Err(); err != nil {
			fmt.Println("Error reading stderr input:", err)
		}
	}()

	err = buildCmd.Wait()
	if err != nil {
		return errors.Errorf("command failed %w", err)
	}

	return nil
}

func main() {
	gitRootDir, err := gitRootDir()
	if err != nil {
		panic(err)
	}
	log.Println("git root dir path:", gitRootDir)

	tmpDir, err := createTmpDir(gitRootDir)
	if err != nil {
		panic(err)
	}
	log.Println("tmp work dir path:", tmpDir)

	assetDir, err := createCachedAssetsDir(gitRootDir)
	if err != nil {
		panic(err)
	}
	log.Println("asset path:", tmpDir)

	var rootCmd = &cobra.Command{
		Use:   "nhctl",
		Short: "build and deploy nethackathon related stuff",
		RunE: func(cmd *cobra.Command, args []string) error {
			fmt.Printf("hello world\n")
			return nil
		},
	}

	rootCmd.AddCommand(&cobra.Command{
		Use:   "oracle-worker",
		Short: "",
		RunE: func(cmd *cobra.Command, args []string) error {
			oracleSrcPath := filepath.Join(gitRootDir, "oracle-worker-service")
			stagingPath := filepath.Join(tmpDir, "oracle-worker-service")
			modelsPath := filepath.Join(assetDir, "models")

			err := copy.Copy(oracleSrcPath, stagingPath)
			if err != nil {
				return err
			}

			var wg errgroup.Group
			wg.Go(func() error {
				err = RunCmd(
					RunCmdOpts{
						Cmd:        []string{"sh", "build.sh"},
						WorkingDir: stagingPath,
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
						Cmd:        []string{"rsync", "-avz", "-e", "ssh -o StrictHostKeyChecking=no", "nethack@192.168.1.148:models", modelsPath},
						WorkingDir: stagingPath,
						LogPrefix:  "rsync",
					})
				if err != nil {
					return errors.Errorf("rsync command failed %w", err)
				}
				return nil
			})

			err = wg.Wait()
			if err != nil {
				return err
			}

			return nil
		},
	})

	err = rootCmd.Execute()
	if err != nil {
		var errWithStack *errors.Error
		if errors.As(err, &errWithStack) {
			fmt.Println(errWithStack.ErrorStack())
		} else {
			panic(err)
		}
	}
}
