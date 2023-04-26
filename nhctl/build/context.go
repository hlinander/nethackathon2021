package build

import (
	"context"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/go-errors/errors"
)

type Context struct {
	context.Context

	GitRootDir   string // absolute path to git repo root
	BuildRootDir string // absolute path to root for build files
}

func NewContext() (*Context, error) {
	gitRootDir, err := gitRootDir()
	if err != nil {
		panic(err)
	}
	log.Println("git root dir:", gitRootDir)

	buildDir, err := createBuildRootDir(gitRootDir)
	if err != nil {
		panic(err)
	}
	log.Println("build dir:", buildDir)

	return &Context{
		Context:      context.Background(),
		GitRootDir:   gitRootDir,
		BuildRootDir: buildDir,
	}, nil
}

func (c *Context) CreateStepStagingDir(name string) (string, error) {
	dirName := fmt.Sprintf("%s-%d", name, time.Now().UnixMilli())
	dirPathAbs := filepath.Join(c.BuildRootDir, "staging", dirName)
	err := os.MkdirAll(dirPathAbs, 0755)
	if err != nil {
		return "", errors.Errorf("failed to create dir: %w", err)
	}
	return dirPathAbs, nil
}

func (c *Context) CreateStepBuildDir(name string) (string, error) {
	dirName := fmt.Sprintf("%s-%d", name, time.Now().UnixMilli())
	dirPathAbs := filepath.Join(c.BuildRootDir, "build", dirName)
	err := os.MkdirAll(dirPathAbs, 0755)
	if err != nil {
		return "", errors.Errorf("failed to create dir: %w", err)
	}
	return dirPathAbs, nil
}

func (c *Context) IsCached(cacheDir string, hash string) (bool, error) {
	targetPath := filepath.Join(cacheDir, hash)
	fileInfo, err := os.Stat(targetPath)
	if os.IsNotExist(err) {
		return false, nil
	}
	if err != nil {
		return false, err
	}
	return fileInfo.IsDir(), nil
}

func gitRootDir() (string, error) {
	cmd := exec.Command("git", "rev-parse", "--show-toplevel")

	path, err := cmd.Output()
	if err != nil {
		return "", errors.Errorf("failed extract output from git command: %w", err)
	}

	return strings.TrimSpace(string(path)), nil
}

func createBuildRootDir(rootPath string) (string, error) {
	absPath := filepath.Join(rootPath, ".build")

	err := os.MkdirAll(absPath, 0755)
	if err != nil {
		return "", err
	}

	return absPath, nil
}
