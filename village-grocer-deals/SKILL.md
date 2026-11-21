---
name: village-grocer-deals
description: Check the Village Grocer (Malaysian supermarket) Facebook page for new deals on everyday grocery items such as fruit, vegetables, bread, meat, seafood, eggs, rice, jam and drinks, and report them with post links and images. Use when the user asks about Village Grocer offers, promotions, specials, B1F1 or "Bumper" deals, or wants a daily Village Grocer deal alert. Not for other supermarkets or for store-opening, voucher or loyalty-points promos.
version: 1.1.0
license: MIT
compatibility: Needs Python 3.9+, internet access, and a ScrapeCreators API key in the SCRAPECREATORS_API_KEY environment variable.
metadata:
  author: SalocinDotTEN
  hermes:
    tags: [groceries, deals, malaysia, facebook, alerts]
    category: shopping
    config:
      - key: scrapecreators.api_key
        description: "ScrapeCreators API key used to read public Facebook page posts"
        prompt: "Enter your ScrapeCreators API key"
        url: "https://scrapecreators.com"
---

# Village Grocer deals

Finds new item deals posted on Village Grocer's Facebook page (facebook.com/myvillagegrocer) and turns them into a short alert.

## Requirements

1. Python 3.9 or newer. The script uses only the standard library.
2. A ScrapeCreators API key (https://scrapecreators.com). It reads public Facebook page posts without logging in. Each request returns about 3 posts and costs 1 credit.
3. The key must be in the environment as `SCRAPECREATORS_API_KEY`. If it is missing, stop and ask the user for it. Never print the key or write it into any file.

## Procedure

### 1. Fetch new posts

Run from this skill's directory:

```bash
python3 scripts/fetch_posts.py fetch --save-images ~/.village-grocer-deals/images
```

Useful options:
- `--lookback-days N` (default 3): ignore posts older than N days.
- `--max-pages N` (default 5): stop after N API requests (about 3 posts each).
- `--state PATH`: where already-reported post ids are stored. Default is `~/.village-grocer-deals/seen.json`.
- `--all`: include posts that were already reported, for a one-off "what's on now?" check.
- `--save-images DIR`: download each post's images into DIR and list them per post as `image_files`. Use it whenever you can open local files. It keeps image reading on your side, with no OCR or image service.
- `--page-url URL`: point at a different Facebook page. The filtering rules below were written for Village Grocer.

The script prints JSON:

```json
{
  "page_url": "...",
  "pages_read": 2,
  "posts_in_window": 5,
  "new_posts": [
    {"id": "...", "url": "...", "created": "2026-11-18T04:00:02Z", "text": "...", "images": ["https://..."], "image_files": ["/home/you/.village-grocer-deals/images/123_0.jpg"]}
  ]
}
```

If it exits with a non-zero code, report the error message to the user. Do not report "no deals" when the fetch failed.

### 2. Read the images

Look at every image of every new post with your own vision. Open the files in `image_files`, or the `images` URLs if you can't read local files. Note the dates, prices and item names printed on each one.

**When the image and the caption disagree, the image wins.** Village Grocer often reuses last week's caption. For example, a Bumper Sale posted on 20 Nov 2026 said "valid 13 - 16 November" in the caption, but its images said "20 - 23 November 2026". Trusting the caption would wrongly treat a live deal as expired.

If you cannot view images at all, use the caption. Then add "dates from caption, check the image" to that alert entry, and never drop a deal as expired based on the caption alone when the post is newer than those dates.

### 3. Pick out the deals

Read every post in `new_posts` and keep only the ones that pass the rules in `references/deal-rules.md`. In short:

- **Keep:** a price deal on specific food or grocery items. That means Buy 1 Free 1, % off, a special price, weekly specials, or promotions called "Bumper" or "Bumper Harvest". It covers fruit, vegetables, bread and bakery, chicken, pork, beef, seafood, eggs, rice, jam, dairy, pantry staples and drinks.
- **Skip:** new store or outlet opening promos, product showcases with no deal, delivery-code-only promos, spend-based vouchers and minimum-spend codes, app or loyalty points promos, contests, gift-with-purchase thresholds, and non-food items.

Posts often put the price only on the image, so judge each post on its caption and its images together. In a post that mixes food and non-food items, list only the food and drink items.

### 4. Write the alert

One entry per deal:

```markdown
**<Items>**
- Offer: <deal and price>
- Valid: <dates, if stated; image dates win over the caption>
- [Post](<url>)

![<short alt text>](<image url>)
```

Show up to 3 images per deal inline. Facebook image links expire after a few days, so an alert is meant for reading now, not for archiving.

If no post qualifies, reply with one line: "No new Village Grocer item deals since the last check."

### 5. Mark posts as reported

After the alert is delivered, record every post you reviewed, including the ones you skipped, so they don't come back next time:

```bash
python3 scripts/fetch_posts.py mark-seen <id> <id> ...
```

Skip this step for one-off `--all` checks.

## Running it daily

This skill does one check per run. To get a daily alert, use your assistant's scheduler (for example, a scheduled task or cron job that asks the assistant to "check Village Grocer deals"). Keep the same `--state` file between runs so each post is reported only once.

## Pitfalls

- An empty `new_posts` with `pages_read: 0` means the fetch did not work. That is not a quiet day.
- The API returns posts newest first, about 3 per request. The script stops early once a whole page has already been reported, to save credits.
- A caption's dates can be a week out of date. Check the image before calling a deal expired.
- Bakery, butter, oil and rice promos count as staples. A "spend RM30, get a free gift" post does not, even if it names food brands.
