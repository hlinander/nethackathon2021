package build

import (
	"io"
	"io/fs"
	"os"
	"path/filepath"
)

func CopyDir(src, dst string) error {
	// Create destination directory if it doesn't exist
	err := os.MkdirAll(dst, os.ModePerm)
	if err != nil {
		return err
	}

	err = filepath.Walk(src, func(path string, info fs.FileInfo, err error) error {
		if err != nil {
			return err
		}

		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}

		dstPath := filepath.Join(dst, rel)

		if info.IsDir() {
			err = os.MkdirAll(dstPath, info.Mode())
			if err != nil {
				return err
			}
		} else {
			err = CopyFile(path, dstPath, info.Mode())
			if err != nil {
				return err
			}
		}
		return nil
	})
	return err
}

func CopyFile(src, dst string, mode fs.FileMode) error {
	srcFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	dstFile, err := os.OpenFile(dst, os.O_RDWR|os.O_CREATE|os.O_TRUNC, mode)
	if err != nil {
		return err
	}
	defer dstFile.Close()

	_, err = io.Copy(dstFile, srcFile)
	return err
}
