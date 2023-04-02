package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/dustin/go-wikiparse"
)

func main() {
	file, err := os.OpenFile("nhwiki", os.O_RDONLY, 0)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	outFile, err := os.Create("nhwiki_all_pages_excl_src_talk_forum_usrtalk_file_filetalk.txt")
	if err != nil {
		panic(err)
	}
	defer outFile.Close()

	p, err := wikiparse.NewParser(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error setting up parser: %s", err)
		os.Exit(1)
	}

	count := 0
	for err == nil {
		var page *wikiparse.Page
		page, err = p.Next()
		if err == nil {
			if !strings.HasPrefix(page.Title, "Source:") &&
				!strings.HasPrefix(page.Title, "Talk:") &&
				!strings.HasPrefix(page.Title, "Forum:") &&
				!strings.HasPrefix(page.Title, "User talk:") &&
				!strings.HasPrefix(page.Title, "User:") &&
				!strings.HasPrefix(page.Title, "File:") &&
				!strings.HasPrefix(page.Title, "File talk:") {
				// fmt.Fprintf(outFile, "\n\n!!%s!!\n\n", page.Title)
				fmt.Fprintln(outFile, page.Revisions[len(page.Revisions)-1])
				count++
			}
		}
	}

	fmt.Printf("%d page exported", count)
}
