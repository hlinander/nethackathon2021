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

			download := step.Download{
				StepBase: build.NewStepBase("download"),
				Input: step.DownloadParams{
					Url: "https://example.com",
				},
			}

			genCode := step.GenCode{
				StepBase: build.NewStepBase("gencode", &download),
				Input: step.GenCodeParams{
					Name: "shahrouzz",
				},
			}
			compile := step.Compile{
				StepBase: build.NewStepBase("compile", &genCode),
			}

			err := build.Build([]build.Step{&compile})
			if err != nil {
				return errors.Errorf("build: %w", err)
			}

			// repr.Print(stepCompile)
			repr.Print(filepath.Join(compile.BuildDir(), compile.ExecutableRel))

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
