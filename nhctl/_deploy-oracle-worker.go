package main

import "log"

func DeployOracleWorker(
	context BuildContext,
	dep *BuildOracleWorkerArtifact,
) error {
	log.Printf("dep passed to DeployOracleWorker: %s", dep.Path)
	return nil
}
