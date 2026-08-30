# Podderton

A container designed purelu to grab podcasts, store them according to your needs, and generate a (custom) feed(s).

There's no web interface - all configuration is done via YAML.

## Installation

```yaml
services:
  subscriber:
    image: ghcr.io/awfulwoman/podderton
    command: ["python", "run_subscriber.py", "/config/feeds.yaml"]
    volumes:
      - "<yourpath>/config:/config:ro"
      - subscriptions:/subscriptions
    environment:
      - PODDERTON_PATH=/

  generator:
    image: ghcr.io/awfulwoman/podderton
    command: ["python", "run_generator.py", "/config/feeds.yaml"]
    ports:
      - "9988:9988" # Change the first "9988" to whatever port you need
    volumes:
      - "<yourpath>/config:/config:ro"
      - subscriptions:/subscriptions:ro
      - feeds:/feeds
    environment:
      - PODDERTON_PATH=/

volumes:
  subscriptions:
  feeds:
```

Go to whever you've installed go to <http://127.0.0.1:9988> (or whatever URL you're using) and you should see a simple page listing the feeds. If a writable config file doesn't exist a default one will be created (on a read-only `/config` mount Podderton falls back to built-in defaults and logs a warning).

## Usage

A file called `feeds.yaml` is found in `<yourpath>/config/` i.e `<yourpath>/config/feeds.yaml`.

At a minimum the file should contain something like this:

```yaml
subscribe:
  feeds:
    - name: Three Bean Salad
      id: threebeansalad
      url: https://podcast.global.com/show/5234547/episodes/feed
```

Once the container is restarted Podderton will query any feeds that it finds, download them, and make a feed available (<http://127.0.0.1:9988/feeds.xml>) for you subscribe to via your podcast player of choice. Neat!

If you look in your podcast directory you'll see `subscriptions/threebeansalad/episodes/` with audio files gradually getting downloaded, alongside `meta.json` (simplified feed metadata) and `source.json` (the raw upstream feed). Generated RSS lands in `feeds/`.

### Public URL

Enclosure URLs in the generated feeds are made absolute at request time from the
`Host` header (and `X-Forwarded-Host` / `X-Forwarded-Proto` when behind a reverse
proxy), so most setups need no configuration. To force a value, set `url`:

```yaml
url: https://podcasts.example.com
```

### Filename formatting

Need to have a custom file format for saving files?

```yaml
subscribe:
  feeds:
    - name: Three Bean Salad
      id: threebeansalad
      url: https://podcast.global.com/show/5234547/episodes/feed
      file_format: "{yyyy-mm-dd}.ext" # .ext is replaced by whatever extension the feed provides.
```

Available tokens: `{yyyy-mm-dd}`, `{yyyy}`, `{mm}`, `{dd}` (zero-padded),
`{mmmm}`, `{dddd}` (not padded), `{title}`, `{description}`, `{episode}`,
`{season}`. An unknown token falls back to `{title}.ext`.

Want to alter the file format? Eeek, sorry, but Podderton isn't yet smart enough to rename already existing files. You'll need to handle that yourself.

### Custom feeds

Want to create custom feeds?

```yaml
subscribe:
  feeds:
    - name: Three Bean Salad
      id: threebeansalad
      url: https://podcast.global.com/show/5234547/episodes/feed
    - name: Beef and Dairy Network
      id: beef
      url: https://feeds.simplecast.com/4NOSW3hj
    - name: THe Rest is Politics
      id: restispolitics
      url: https://feeds.megaphone.fm/GLT9190936013
generate:
  feeds:
    - name: Funny Stuff
      id: funnystuff
      feeds:
        - threebeansalad
        - beef
    - name: Boring stuff
      id: boring
      feeds:
        - restispolitics
```

This custom feed will be available at <http://127.0.0.1:9988/funnystuff.xml>. Don't worry, it will also be listed on the webpage.

### Schedule

Want to change how often each service runs? Set the `interval` under `subscribe` and `generate`:

```yaml
subscribe:
  interval: "30m"  # How often to check for new episodes (default: 30m)
generate:
  interval: "5m"   # How often to check for new downloads (default: 5m)
```

These can also be set via environment variables: `PODDERTON_SUBSCRIBE_INTERVAL` and `PODDERTON_GENERATE_INTERVAL`.

### Misc

Don't want the utility webpage to be generated?

```yaml
webpage:
  display: false
```

Don't want the custom feeds you defined under `generate.feeds`?

```yaml
generate:
  feeds: false
```

Don't want any output feeds at all (no per-feed XML, no combined `feeds.xml`)?

```yaml
generate:
  type: false
```

Want to combine all the feeds into one output feed?

```yaml
generate:
  type: combined
```

Want to have a separate output feed for each input feed?

```yaml
generate:
  type: separate # default
```

## Architecture

Podderton runs as two services:

- **Subscriber**: checks configured feeds on a heartbeat interval, downloads new episodes, and touches a `.updated` signal file on the shared subscriptions volume when new content arrives.
- **Generator**: watches the timestamp of `.updated` on its own heartbeat interval, regenerates RSS feeds when it changes, and serves HTTP on port 9988.

The two services communicate via the `.updated` file on the shared subscriptions volume — the subscriber writes it, the generator only reads its mtime, so the generator can mount the volume read-only.

## Development

For local development, use the dev compose file which starts all three services (mock feed server, subscriber, generator) and mounts `src/` directly so code changes are reflected without rebuilding:

```bash
docker compose -f docker-compose.dev.yml up --build
```

## Internals

Podderton relies on the YAML file for configuration, and directories for storing podcasts. The webpage and feeds are generated on the fly. There's no state or fanciness involved.

Podderton is written in Python. Why? I dunno.

## Disclaimer

This is a very scratch-your-own-itch,very  part-time project by someone who is quite overworked, so please don't expect huge development to happen. However, PRs are always welcome!

Yes, I like Three Bean Salad.
