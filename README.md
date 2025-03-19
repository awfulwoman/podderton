# Podderton

A container designed purelu to grab podcasts, store them according to your needs, and generate a (custom) feed(s).

There's no web interface - all configuration is done via YAML.

## Installation

```yaml
services:
  podderton:
    ports:
      - "9988:9988" # Change the first "9988" to whatever port you need
    image: awfulwoman/podderton
    volumes:
      - "<yourpath>/config:/config"
      - "<yourpath>/podcasts:/podcasts"
```

Go to whever you've installed go to <http://127.0.0.1:9988> (or whatever URL you're using) and you should see a simple page listing the feeds. If a config file doesn't exist a default one will be created.

## Usage

A file called `feeds.yaml` is found in `<yourpath>/config/` i.e `<yourpath>/config/feeds.yaml`.

At a minimum the file should contain something like this:

```yaml
input:
  feeds:
    - name: Three Bean Salad
      id: threebeansalad
      url: https://podcast.global.com/show/5234547/episodes/feed
```

Once the container is restarted Podderton will query any feeds that it finds, download them, and make a feed available (<http://127.0.0.1:9988/feeds.xml>) for you subscribe to via your podcast player of choice. Neat! 

If you look in your podcast directory you'll see a directory called `threebeansalad` with audio files gradually getting downloaded.

### Filename formatting

Need to have a custom file format for saving files? 

```yaml
input:
  feeds:
    - name: Three Bean Salad
      id: threebeansalad
      url: https://podcast.global.com/show/5234547/episodes/feed
      file_format: "{yyyy-mm-dd}.ext" # Make sure to quote this!
```

Want to alter the file format? Eeek, sorry, but Podderton isn't yet smart enough to rename already existing files. You'll need to handle that yourself.

### Custom feeds

Want to create custom feeds?

```yaml
input: 
  feeds:
    - name: Three Bean Salad
      id: threebeansalad 
      url: https://podcast.global.com/show/5234547/episodes/feed
    - name: Beef and Dairy Network
      id: beef
      url: https://feeds.simplecast.com/4NOSW3hj
output:
  feeds:
    - name: Funny Stuff
      id: funnystuff
      feeds:
        - threebeansalad
        - beef
```

This custom feed will be available at <http://127.0.0.1:9988/funnystuff.xml>. Don't worry, it will also be listed on the webpage.

### Schedule

Want to change how often Podderton checks feeds? Add a cron-based schedule!

```yaml
input:
  schedule: "0 * * * *" # Quotes necessary here
```

You can also add a schedule for an individual feed.

```yaml
input:
  schedule: "0 * * * *"
  feeds:
    - name: Three Bean Salad
      id: threebeansalad 
      schedule: "0 30 * * *" # This will override the globale schedule
      url: https://podcast.global.com/show/5234547/episodes/feed
```

### Output feed refresh

```yaml
output:
  refresh: 5m # or 2h, 30s, or 1w if you're chill
```

### Misc

Don't want the webpage to be generated?

```yaml
webpage: 
  display: false
```

Don't want any outputted feeds? 

```yaml
output: 
  feeds: false
```

Want to disable the default output feed?

```yaml
output: 
  type: false
```

Want to combine all the feeds into one output feed?

```yaml
output: 
  type: combined
```

Want to have a separate output feed for each input feed?

```yaml
output: 
  type: separate # default
```

## Internals

Podderton relies on the YAML file for configuration, and directories for storing podcasts. The webpage and feeds are generated on the fly. There's no state or fanciness involved.

Podderton is written in Python. Why? I dunno.

## Disclaimer

This is a very part time project by someone who is quite overworked, so don't expect massive changes to happen. However PRs are always welcome!

Yes, I like Three Bean Salad.