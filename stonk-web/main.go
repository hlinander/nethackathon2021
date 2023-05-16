package main

import (
	"context"
	"embed"
	"encoding/json"
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

type ClanReward struct {
	Name string
	Reward int64
}

type IndexPageData struct {
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
		data := IndexPageData{}
		tmpl.Execute(w, data)
	})

	http.HandleFunc("/poll", func(w http.ResponseWriter, r *http.Request) {
		var clans []*Clan
		err := pgxscan.Select(ctx, db, &clans, `SELECT id, name, power_gems FROM clans ORDER BY power_gems DESC`)
		if err != nil {
			fmt.Printf("Clan ERROR %v\n", err)
		}

		var players []*Player
		err = pgxscan.Select(ctx, db, &players, `SELECT id, clan, username, ticker FROM players`)
		if err != nil {
			fmt.Printf("Player ERROR %v\n", err)
		}
		
		var clan_rewards []*ClanReward
		err = pgxscan.Select(ctx, db, &clan_rewards, `select
	clans.name as name, SUM(rewards.score) as reward
from
	rewards inner join objectives on rewards.objective = objectives.id
	inner join players on players.id = rewards.player
	inner join clans on players.clan = clans.id
	group by clans.name`)
		if err != nil {
			fmt.Printf("CR ERROR %v\n", err)
		}

		type PollData struct {
			Clans   []*Clan
			Players []*Player
			ClanRewards []*ClanReward
		}

		data := PollData{
			Clans:   clans,
			Players: players,
			ClanRewards: clan_rewards,
		}

		jsonBytes, _ := json.Marshal(&data)
		w.Header().Set("Content-Type", "application/json")
		w.Write(jsonBytes)
	})

	log.Fatal(http.ListenAndServe(":8989", nil))
}
