package main

import (
	"context"
	"embed"
	"fmt"
	"html/template"
	"io/fs"
	"log"
	"net/http"
	"os"

	"github.com/georgysavva/scany/pgxscan"
	"github.com/jackc/pgx/v4"
)

type Player struct {
	ID       int64
	Clan     int64
	Username string
	Ticker   string
}

type Clan struct {
	ID         int64
	Name       string
	Power_gems int64
}

type IndexPageData struct {
	Players []*Player
	Clans   []*Clan
}

//go:embed templates
var templateFromRoot embed.FS
var templateFS, _ = fs.Sub(templateFromRoot, "templates")

func main() {
	ctx := context.Background()
	dbUrl := "postgresql://postgres:vinst@192.168.1.148/nh"
	db, err := pgx.Connect(ctx, dbUrl)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Unable to connect to database: %v\n", err)
		os.Exit(1)
	}
	defer db.Close(ctx)

	tmpl := template.Must(template.ParseFS(templateFS, "index.html.template"))

	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.FS(templateFS))))

	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {

		var clans []*Clan
		err := pgxscan.Select(ctx, db, &clans, `SELECT id, name, power_gems FROM clans`)
		if err != nil {
			fmt.Printf("ERROR %v\n", err)
		}

		var players []*Player
		err = pgxscan.Select(ctx, db, &players, `SELECT id, clan, username, ticker FROM players`)
		if err != nil {
			fmt.Printf("ERROR %v\n", err)
		}
		data := IndexPageData{
			Players: players,
			Clans:   clans,
		}
		tmpl.Execute(w, data)

	})

	log.Fatal(http.ListenAndServe(":8080", nil))
}
