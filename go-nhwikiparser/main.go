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

	outFile, err := os.Create("nhwiki_title_indexed.txt")
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
				
				pagetext := fmt.Sprintf("%v", page.Revisions[len(page.Revisions)-1])
				lines := strings.Split(pagetext, "\n")
				    for i, line := range lines {
				        lines[i] = fmt.Sprintf("&&%s&&%d&&%s", page.Title, i, line)
				    }				// fmt.Fprintf(outFile, "\n\n!!%s!!\n\n", page.Title)
				newtext := strings.Join(lines, "\n")
				fmt.Fprintln(outFile, newtext)
				count++
			}
		}
	}

	fmt.Printf("%d page exported", count)
}
