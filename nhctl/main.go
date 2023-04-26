package main

import (
	"fmt"
	"nhctl/build"
	"nhctl/step"
	"path/filepath"

	"github.com/alecthomas/repr"
	"github.com/go-errors/errors"
	"github.com/spf13/cobra"
)

func main() {
	var rootCmd = &cobra.Command{
		Use:   "nhctl",
		Short: "build and deploy nethackathon",
		RunE: func(cmd *cobra.Command, args []string) error {

			stepGenCode := step.GenCode{
				StepBase: build.NewStepBase("gencode"),
			}
			stepCompile := step.Compile{
				StepBase: build.NewStepBase("compile", &stepGenCode),
			}

			err := build.Build([]build.Step{&stepCompile})
			if err != nil {
				return errors.Errorf("build: %w", err)
			}

			// repr.Print(stepCompile)
			repr.Print(filepath.Join(stepCompile.OutputDir(), stepCompile.ExecutableRel))

			return nil
		},
	}

	rootCmd.AddCommand(
		&cobra.Command{
			Use:   "oracle-worker",
			Short: "",
			RunE: func(cmd *cobra.Command, args []string) error {
				// artifact, err := BuildOracleWorker(ctx)
				// if err != nil {
				// 	return err
				// }

				// err = DeployOracleWorker(ctx, artifact)
				// if err != nil {
				// 	return err
				// }

				return nil
			},
		})

	err := rootCmd.Execute()
	if err != nil {
		var errWithStack *errors.Error
		if errors.As(err, &errWithStack) {
			fmt.Println(errWithStack.ErrorStack())
		} else {
			panic(err)
		}
	}
}
