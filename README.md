# Village Grocer deals skill

An AI agent skill that checks the [Village Grocer](https://www.facebook.com/myvillagegrocer) Facebook page for new deals on everyday groceries and sends a short alert with prices, valid dates, post links and images. Village Grocer is a supermarket chain in Malaysia.

It follows the open [Agent Skills](https://agentskills.io) format (`SKILL.md`), so the same folder works in Claude, ChatGPT / Codex, Hermes Agent and other assistants that support skills.

## What it reports

**Included:** Buy 1 Free 1 offers, percentage discounts, special prices, weekly specials and "Bumper" / "Bumper Harvest" promos on fruit, vegetables, bread, meat, seafood, eggs, rice, jam, dairy, pantry staples and drinks.

**Skipped:** store opening promos, product showcases with no deal, delivery codes, spend-based vouchers, minimum-spend codes, loyalty points promos, contests and non-food items.

**Dates come from the images.** Village Grocer often reuses last week's caption, so the assistant looks at each post's images with its own vision and trusts the dates printed there over the caption. No OCR or other image service is involved.

The full rules are in [`village-grocer-deals/references/deal-rules.md`](village-grocer-deals/references/deal-rules.md). Edit that file to change what counts as a deal.

## Requirements

- Python 3.9+ (standard library only, nothing to `pip install`)
- A [ScrapeCreators](https://scrapecreators.com) API key, used to read public Facebook posts. Each request reads about 3 posts and costs 1 credit, so a typical daily check costs 1 to 3 credits.
- An assistant that can run shell commands (Claude Code, Claude with code execution, Codex, Hermes and similar)

Set your key before use:

```bash
export SCRAPECREATORS_API_KEY="your-key-here"
```

## Install

The skill is the `village-grocer-deals/` folder. Clone once:

```bash
git clone https://github.com/SalocinDotTEN/village-grocer-deals-skill.git
cd village-grocer-deals-skill
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
cp -r village-grocer-deals ~/.claude/skills/
```

Or with the skills CLI: `npx skills add SalocinDotTEN/village-grocer-deals-skill`

### Claude.ai / Claude desktop

Download `village-grocer-deals.zip` from the [Releases](../../releases) page (or zip the `village-grocer-deals/` folder yourself). Then go to **Settings > Capabilities > Skills** and upload it. Code execution and network access need to be enabled, and the API key has to be available to the sandbox. You can also paste the key in when the assistant asks for it.

### ChatGPT desktop / Codex CLI

```bash
mkdir -p ~/.agents/skills
cp -r village-grocer-deals ~/.agents/skills/
```

Restart Codex if the skill doesn't appear. In Codex, invoke it with `$village-grocer-deals`. In the ChatGPT desktop app it shows up under **Skills**.

### Hermes Agent (Nous Research)

```bash
mkdir -p ~/.hermes/skills/shopping
cp -r village-grocer-deals ~/.hermes/skills/shopping/
```

Hermes prompts for the ScrapeCreators API key the first time the skill loads. Use it with `/village-grocer-deals`.

### Any other agent

Copy the folder to wherever your agent reads skills from, or point it at `village-grocer-deals/SKILL.md` and ask it to follow the instructions.

## Use

Ask your assistant:

> Check Village Grocer for new deals

To get a daily alert, schedule that prompt with your assistant's scheduler or a cron job. Reported posts are remembered in `~/.village-grocer-deals/seen.json`, so each deal shows up only once.

Run the script by hand:

```bash
cd village-grocer-deals
python3 scripts/fetch_posts.py fetch            # new posts as JSON
python3 scripts/fetch_posts.py fetch --all      # everything from the last 3 days
python3 scripts/fetch_posts.py mark-seen 123 456
```

## Tests

```bash
cd village-grocer-deals
python3 -m unittest discover tests
```

The tests run offline and don't need an API key.

## Notes

- Facebook image links expire after a few days, so alerts are meant to be read when they arrive.
- Village Grocer often puts the price only on the image. Assistants that can read images give better results.
- This project isn't affiliated with Village Grocer or Meta.

## License

MIT
