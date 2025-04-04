# QWTF Map Repo

Contains all known QWTF maps and their assets, as well as lits, locs and skins. If any are missing please submit a PR.


## How to submit a map

- Set up a local server for development: https://github.com/FortressOne/fortressonesv
- Fork this repo
- Commit files in format:
    ```
	fortress/package/<mapname>/
		maps/<mapname>.bsp
		sound/*.wav
		progs/*.(mdl|bsp)
	```
- Optionally include:
	```
	fortress/package/<mapname>/
		<mapname>.txt
		maps/<mapname>.ent
		maps/<mapname>.rtlights
		lits/<mapname>.lit
		locs/<mapname>.loc
		textures/<mapname>/*.(png|jpg)
		textures/levelshots/<mapname>.(png|jpg)
	```
- Push changes to your fork
- Submit pull request


## Docker

### Build map-repo

```
docker build --tag=map-repo .
```


### Deploy map-repo

```
docker tag map-repo fortressone/map-repo:latest
docker push fortressone/map-repo:latest
```


## Append map assets zip to bsp for clients that support this (FTE)

For all packages:
```
./package_bsps.sh
```

For a single package:
```
./package_bsps.sh fortress/package/<mapdir>
```

Maps will be built in fortress/maps/


## Deploy

GitHub actions automatically packages maps and syncs to S3. See:

- .github/workflows/workflow.yml
- action.yml
- Dockerfile


## Package map file structure

Maps packages uploaded to s3 are a bsp file concatenated with a zip file. zip files are shaped like this:

```
<mapname>.zip
	lits/<mapname>.lit
	locs/<mapname>.loc
	maps/
		<mapname>.ent
		<mapname>.rtlights
	progs/*.(mdl|bsp)
	sound/*.wav
	textures/
		<mapname>/*.(png|jpg)
		levelshots/<mapname>.(png|jpg)
    <mapname>.txt
```
