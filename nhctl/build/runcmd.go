package build

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"github.com/go-errors/errors"
)

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
